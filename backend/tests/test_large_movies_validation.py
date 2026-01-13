"""Validation test for US-V.2: Large Movies Detection.

This test queries the cached media items to find the largest movies
and compare against the 13GB threshold.

Run with: cd backend && uv run pytest tests/test_large_movies_validation.py -v -s
"""

import httpx
import pytest

BASE_URL = "http://localhost:8080"
TEST_EMAIL = "jimmy291295+2@gmail.com"
TEST_PASSWORD = "ZSh1YYNsr844!*"


class TestLargeMoviesValidation:
    """Validation tests for large movies detection (US-V.2)."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            assert response.status_code == 200, f"Login failed: {response.text}"
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_large_movies_count(self, auth_headers):
        """Test that /api/content/issues?filter=large returns correct count."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get(
                "/api/content/issues",
                params={"filter": "large"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            print(f"\n=== Large Movies (>13GB) ===")
            print(f"Count: {data['total_count']}")
            print(f"Total size: {data['total_size_formatted']}")

            if data["items"]:
                print("\nLarge movies found:")
                for item in data["items"]:
                    print(f"  - {item['name']}: {item['size_formatted']}")
            else:
                print("\nNo large movies found (all movies < 13GB)")

    def test_all_movies_sizes(self, auth_headers):
        """Get all content and analyze movie sizes."""
        with httpx.Client(base_url=BASE_URL) as client:
            # Get all issues (which includes all content)
            response = client.get(
                "/api/content/issues",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Filter for movies only and analyze sizes
            movies = [item for item in data["items"] if item["media_type"] == "Movie"]

            # Sort by size
            movies.sort(key=lambda x: x["size_bytes"] or 0, reverse=True)

            threshold_gb = 13
            threshold_bytes = threshold_gb * 1024 * 1024 * 1024

            print(f"\n=== Movie Size Analysis ===")
            print(f"Total movies with issues: {len(movies)}")
            print(f"Threshold: {threshold_gb} GB ({threshold_bytes:,} bytes)")
            print(f"\nTop 15 largest movies:")

            for i, movie in enumerate(movies[:15], 1):
                size_bytes = movie["size_bytes"] or 0
                size_gb = size_bytes / (1024 * 1024 * 1024)

                # Check both >= and > thresholds
                flag_gte = "✓ >= 13GB" if size_bytes >= threshold_bytes else ""
                flag_gt = "✓ > 13GB" if size_bytes > threshold_bytes else ""

                flag = f"[{flag_gte}] [{flag_gt}]" if flag_gte or flag_gt else ""

                print(f"  {i:2d}. {size_gb:7.2f} GB - {movie['name'][:45]:<45} {flag}")

            # Count movies at exactly threshold
            exactly_threshold = [m for m in movies
                               if (m["size_bytes"] or 0) == threshold_bytes]
            movies_gte = [m for m in movies
                        if (m["size_bytes"] or 0) >= threshold_bytes]
            movies_gt = [m for m in movies
                        if (m["size_bytes"] or 0) > threshold_bytes]

            print(f"\n=== Summary ===")
            print(f"Movies >= 13GB (original script logic): {len(movies_gte)}")
            print(f"Movies > 13GB (current app logic): {len(movies_gt)}")
            print(f"Movies exactly = 13GB: {len(exactly_threshold)}")
            print(f"\nDifference: {len(movies_gte) - len(movies_gt)} movies at exactly 13GB boundary")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
