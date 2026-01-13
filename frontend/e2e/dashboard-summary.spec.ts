import { test, expect } from '@playwright/test';

test.describe('Dashboard Summary Cards (US-D.1)', () => {
	test.beforeEach(async ({ page }) => {
		// Set up a mock token to bypass auth check
		await page.goto('/login');
		await page.evaluate(() => {
			localStorage.setItem('access_token', 'mock-token-for-ui-testing');
		});

		// Mock auth check to simulate logged-in user
		await page.route('**/api/auth/me', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ id: 1, email: 'test@example.com' })
			});
		});

		// Mock sync status
		await page.route('**/api/sync/status', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					last_synced: '2024-01-15T10:30:00Z',
					status: 'success',
					media_items_count: 100,
					requests_count: 25,
					error: null
				})
			});
		});
	});

	test('shows 4 issue cards on dashboard', async ({ page }) => {
		// Mock content summary
		await page.route('**/api/content/summary', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					old_content: { count: 221, total_size_bytes: 795995628512, total_size_formatted: '741.3 GB' },
					large_movies: { count: 5, total_size_bytes: 85899345920, total_size_formatted: '80.0 GB' },
					language_issues: { count: 12, total_size_bytes: 0, total_size_formatted: '0 B' },
					unavailable_requests: { count: 8, total_size_bytes: 0, total_size_formatted: '0 B' }
				})
			});
		});

		await page.goto('/');

		// Should see all 4 issue cards (using card labels within summary-cards section)
		await expect(page.locator('.summary-cards .card-label').filter({ hasText: 'Old Content' })).toBeVisible();
		await expect(page.locator('.summary-cards .card-label').filter({ hasText: 'Large Movies' })).toBeVisible();
		await expect(page.locator('.summary-cards .card-label').filter({ hasText: 'Language Issues' })).toBeVisible();
		await expect(page.locator('.summary-cards .card-label').filter({ hasText: 'Unavailable Requests' })).toBeVisible();
	});

	test('shows count and size for each issue card', async ({ page }) => {
		// Mock content summary
		await page.route('**/api/content/summary', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					old_content: { count: 221, total_size_bytes: 795995628512, total_size_formatted: '741.3 GB' },
					large_movies: { count: 7, total_size_bytes: 85899345920, total_size_formatted: '80.0 GB' },
					language_issues: { count: 12, total_size_bytes: 0, total_size_formatted: '0 B' },
					unavailable_requests: { count: 8, total_size_bytes: 0, total_size_formatted: '0 B' }
				})
			});
		});

		await page.goto('/');

		// Should show counts (using card-count within summary-cards)
		await expect(page.locator('.summary-cards .card-count').filter({ hasText: '221' })).toBeVisible();
		await expect(page.locator('.summary-cards .card-count').filter({ hasText: '7' })).toBeVisible();
		await expect(page.locator('.summary-cards .card-count').filter({ hasText: '12' })).toBeVisible();
		await expect(page.locator('.summary-cards .card-count').filter({ hasText: '8' })).toBeVisible();

		// Should show size for old content and large movies
		await expect(page.locator('.summary-cards .card-size').filter({ hasText: '741.3 GB' })).toBeVisible();
		await expect(page.locator('.summary-cards .card-size').filter({ hasText: '80.0 GB' })).toBeVisible();
	});

	test('cards are clickable and navigate to /issues with filter', async ({ page }) => {
		// Mock content summary
		await page.route('**/api/content/summary', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					old_content: { count: 10, total_size_bytes: 10000000000, total_size_formatted: '9.3 GB' },
					large_movies: { count: 2, total_size_bytes: 30000000000, total_size_formatted: '27.9 GB' },
					language_issues: { count: 3, total_size_bytes: 0, total_size_formatted: '0 B' },
					unavailable_requests: { count: 1, total_size_bytes: 0, total_size_formatted: '0 B' }
				})
			});
		});

		await page.goto('/');

		// Click on old content card
		await page.getByRole('button', { name: /view old content/i }).click();

		// Should navigate to /issues?filter=old
		await expect(page).toHaveURL(/\/issues\?filter=old/);
	});

	test('shows loading skeleton while fetching data', async ({ page }) => {
		// Mock content summary with delay
		await page.route('**/api/content/summary', async (route) => {
			await new Promise((r) => setTimeout(r, 1000));
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					old_content: { count: 10, total_size_bytes: 10000000000, total_size_formatted: '9.3 GB' },
					large_movies: { count: 2, total_size_bytes: 30000000000, total_size_formatted: '27.9 GB' },
					language_issues: { count: 3, total_size_bytes: 0, total_size_formatted: '0 B' },
					unavailable_requests: { count: 1, total_size_bytes: 0, total_size_formatted: '0 B' }
				})
			});
		});

		await page.goto('/');

		// Should show skeleton lines while loading (first one is enough to verify loading state)
		await expect(page.locator('.skeleton-line').first()).toBeVisible();
	});

	test('shows 0 issues gracefully when no problems exist', async ({ page }) => {
		// Mock content summary with all zeros
		await page.route('**/api/content/summary', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					old_content: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' },
					large_movies: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' },
					language_issues: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' },
					unavailable_requests: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' }
				})
			});
		});

		await page.goto('/');

		// Should show 0 for all counts (there will be four 0s)
		const zeroElements = page.locator('.card-count').filter({ hasText: '0' });
		await expect(zeroElements).toHaveCount(4);
	});

	test('navigates to correct filter for each card type', async ({ page }) => {
		// Mock content summary
		await page.route('**/api/content/summary', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					old_content: { count: 1, total_size_bytes: 1000000000, total_size_formatted: '1 GB' },
					large_movies: { count: 1, total_size_bytes: 15000000000, total_size_formatted: '14 GB' },
					language_issues: { count: 1, total_size_bytes: 0, total_size_formatted: '0 B' },
					unavailable_requests: { count: 1, total_size_bytes: 0, total_size_formatted: '0 B' }
				})
			});
		});

		// Test Large Movies card navigation
		await page.goto('/');
		await page.getByRole('button', { name: /view large movies/i }).click();
		await expect(page).toHaveURL(/\/issues\?filter=large/);

		// Test Language Issues card navigation
		await page.goto('/');
		await page.getByRole('button', { name: /view language issues/i }).click();
		await expect(page).toHaveURL(/\/issues\?filter=language/);

		// Test Unavailable Requests card navigation
		await page.goto('/');
		await page.getByRole('button', { name: /view unavailable requests/i }).click();
		await expect(page).toHaveURL(/\/issues\?filter=requests/);
	});

	test('cards have appropriate visual styling', async ({ page }) => {
		// Mock content summary
		await page.route('**/api/content/summary', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					old_content: { count: 5, total_size_bytes: 5000000000, total_size_formatted: '4.7 GB' },
					large_movies: { count: 2, total_size_bytes: 30000000000, total_size_formatted: '27.9 GB' },
					language_issues: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' },
					unavailable_requests: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' }
				})
			});
		});

		await page.goto('/');

		// Cards should have icons with specific color backgrounds
		await expect(page.locator('.card-icon.old')).toBeVisible();
		await expect(page.locator('.card-icon.large')).toBeVisible();
		await expect(page.locator('.card-icon.language')).toBeVisible();
		await expect(page.locator('.card-icon.requests')).toBeVisible();
	});

	test('summary data updates after sync', async ({ page }) => {
		let callCount = 0;

		// Mock content summary - return different data after sync
		await page.route('**/api/content/summary', async (route) => {
			callCount++;
			if (callCount === 1) {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						old_content: { count: 10, total_size_bytes: 10000000000, total_size_formatted: '9.3 GB' },
						large_movies: { count: 2, total_size_bytes: 30000000000, total_size_formatted: '27.9 GB' },
						language_issues: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' },
						unavailable_requests: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' }
					})
				});
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						old_content: { count: 15, total_size_bytes: 15000000000, total_size_formatted: '14.0 GB' },
						large_movies: { count: 3, total_size_bytes: 45000000000, total_size_formatted: '41.9 GB' },
						language_issues: { count: 1, total_size_bytes: 0, total_size_formatted: '0 B' },
						unavailable_requests: { count: 2, total_size_bytes: 0, total_size_formatted: '0 B' }
					})
				});
			}
		});

		// Mock sync endpoint
		await page.route('**/api/sync', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					status: 'success',
					media_items_synced: 100,
					requests_synced: 25,
					error: null
				})
			});
		});

		await page.goto('/');

		// Check initial count
		await expect(page.locator('.card-content').filter({ hasText: 'Old Content' }).locator('.card-count')).toContainText('10');

		// Trigger sync
		await page.getByRole('button', { name: /refresh/i }).click();

		// Wait for updated count
		await expect(page.locator('.card-content').filter({ hasText: 'Old Content' }).locator('.card-count')).toContainText('15');
	});
});
