"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_jellyfin_response() -> dict:
    """Sample Jellyfin API response for testing."""
    return {
        "Items": [
            {
                "Id": "test-movie-1",
                "Name": "Test Movie",
                "Type": "Movie",
                "ProductionYear": 2023,
                "DateCreated": "2023-01-15T10:00:00Z",
                "Path": "/media/movies/Test Movie (2023)/movie.mkv",
                "UserData": {
                    "Played": True,
                    "LastPlayedDate": "2023-06-15T10:00:00Z",
                    "PlayCount": 1,
                },
                "MediaSources": [
                    {
                        "Size": 5000000000,  # 5GB
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "eng"},
                            {"Type": "Audio", "Language": "fre"},
                            {"Type": "Subtitle", "Language": "fre"},
                        ],
                    }
                ],
            },
            {
                "Id": "test-series-1",
                "Name": "Test Series",
                "Type": "Series",
                "ProductionYear": 2022,
                "DateCreated": "2022-06-01T10:00:00Z",
                "Path": "/media/tv/Test Series",
                "UserData": {
                    "Played": False,
                    "PlayCount": 0,
                },
            },
        ],
        "TotalRecordCount": 2,
    }


@pytest.fixture
def mock_jellyseerr_response() -> dict:
    """Sample Jellyseerr API response for testing."""
    return {
        "pageInfo": {"pages": 1, "results": 2},
        "results": [
            {
                "id": 1,
                "status": 2,  # Approved
                "createdAt": "2024-01-01T10:00:00Z",
                "media": {
                    "tmdbId": 12345,
                    "mediaType": "movie",
                    "status": 5,  # Available
                },
                "requestedBy": {"displayName": "TestUser"},
            },
            {
                "id": 2,
                "status": 1,  # Pending
                "createdAt": "2024-01-02T10:00:00Z",
                "media": {
                    "tmdbId": 67890,
                    "mediaType": "tv",
                    "status": 4,  # Partially Available
                    "seasons": [
                        {"seasonNumber": 1, "status": 5},
                        {"seasonNumber": 2, "status": 2},
                    ],
                },
                "requestedBy": {"displayName": "AnotherUser"},
            },
        ],
    }
