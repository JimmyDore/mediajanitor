import { test, expect } from '@playwright/test';

test.describe('Old/Unwatched Content Page (US-3.1)', () => {
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
	});

	test('old content page renders with title', async ({ page }) => {
		// Mock old content API - must be set up BEFORE navigation
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0,
					total_size_bytes: 0,
					total_size_formatted: 'Unknown size'
				})
			});
		});

		await page.goto('/content/old-unwatched');
		await page.waitForLoadState('networkidle');

		// Should see the page title
		await expect(page.getByRole('heading', { name: /old.*unwatched/i })).toBeVisible();
	});

	test('shows loading state initially', async ({ page }) => {
		// Mock with a delay to see loading state
		await page.route('**/api/content/old-unwatched', async (route) => {
			await new Promise((r) => setTimeout(r, 500));
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0,
					total_size_bytes: 0,
					total_size_formatted: 'Unknown size'
				})
			});
		});

		await page.goto('/content/old-unwatched');

		// Should show loading state
		await expect(page.getByText(/loading/i)).toBeVisible();
	});

	test('shows empty state when no old content', async ({ page }) => {
		// Mock empty response
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0,
					total_size_bytes: 0,
					total_size_formatted: 'Unknown size'
				})
			});
		});

		await page.goto('/content/old-unwatched');
		await page.waitForLoadState('networkidle');

		// Should show empty state message
		await expect(page.getByText(/all your content has been watched/i)).toBeVisible();
	});

	test('displays content list with all required columns', async ({ page }) => {
		// Mock content response
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							jellyfin_id: 'movie-1',
							name: 'Old Movie 1',
							media_type: 'Movie',
							production_year: 2020,
							size_bytes: 15000000000,
							size_formatted: '14.0 GB',
							last_played_date: null,
							path: '/media/movies/Old Movie 1'
						}
					],
					total_count: 1,
					total_size_bytes: 15000000000,
					total_size_formatted: '14.0 GB'
				})
			});
		});

		await page.goto('/content/old-unwatched');
		await page.waitForLoadState('networkidle');

		// Should show the content item
		await expect(page.getByText('Old Movie 1')).toBeVisible();
		await expect(page.getByText('Movie')).toBeVisible();
		await expect(page.getByText('2020')).toBeVisible();
		await expect(page.getByText('14.0 GB').first()).toBeVisible();
	});

	test('shows total count and size in summary bar', async ({ page }) => {
		// Mock content response
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							jellyfin_id: 'movie-1',
							name: 'Movie 1',
							media_type: 'Movie',
							production_year: 2020,
							size_bytes: 10000000000,
							size_formatted: '9.3 GB',
							last_played_date: null,
							path: '/media/movies/Movie 1'
						},
						{
							jellyfin_id: 'movie-2',
							name: 'Movie 2',
							media_type: 'Movie',
							production_year: 2019,
							size_bytes: 8000000000,
							size_formatted: '7.5 GB',
							last_played_date: null,
							path: '/media/movies/Movie 2'
						}
					],
					total_count: 2,
					total_size_bytes: 18000000000,
					total_size_formatted: '16.8 GB'
				})
			});
		});

		await page.goto('/content/old-unwatched');
		await page.waitForLoadState('networkidle');

		// Should show total count and size
		await expect(page.getByText('16.8 GB').first()).toBeVisible();
	});

	test('shows "Never watched" for items without last played date', async ({ page }) => {
		// Mock content response with never watched item
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							jellyfin_id: 'movie-1',
							name: 'Never Watched Movie',
							media_type: 'Movie',
							production_year: 2020,
							size_bytes: 10000000000,
							size_formatted: '9.3 GB',
							last_played_date: null,
							path: '/media/movies/Never Watched'
						}
					],
					total_count: 1,
					total_size_bytes: 10000000000,
					total_size_formatted: '9.3 GB'
				})
			});
		});

		await page.goto('/content/old-unwatched');
		await page.waitForLoadState('networkidle');

		// Should show "Never watched" status
		await expect(page.getByText(/never watched/i)).toBeVisible();
	});

	test('displays both movies and series with type badges', async ({ page }) => {
		// Mock content response with both types
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							jellyfin_id: 'movie-1',
							name: 'Test Movie',
							media_type: 'Movie',
							production_year: 2020,
							size_bytes: 10000000000,
							size_formatted: '9.3 GB',
							last_played_date: null,
							path: '/media/movies/Test Movie'
						},
						{
							jellyfin_id: 'series-1',
							name: 'Test Series',
							media_type: 'Series',
							production_year: 2019,
							size_bytes: 50000000000,
							size_formatted: '46.6 GB',
							last_played_date: null,
							path: '/media/tv/Test Series'
						}
					],
					total_count: 2,
					total_size_bytes: 60000000000,
					total_size_formatted: '55.9 GB'
				})
			});
		});

		await page.goto('/content/old-unwatched');
		await page.waitForLoadState('networkidle');

		// Should show both items
		await expect(page.getByText('Test Movie')).toBeVisible();
		await expect(page.getByText('Test Series')).toBeVisible();
		// Should show type badges
		await expect(page.getByText('Movie').first()).toBeVisible();
		await expect(page.getByText('Series')).toBeVisible();
	});

	test('shows error message when API fails', async ({ page }) => {
		// Mock 401 error
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 401,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Session expired. Please log in again.' })
			});
		});

		await page.goto('/content/old-unwatched');
		await page.waitForLoadState('networkidle');

		// Should show error message
		await expect(page.getByText(/session expired/i)).toBeVisible();
	});

	test('navigation link to old content is present in header', async ({ page }) => {
		// Mock all endpoints needed for dashboard
		await page.route('**/api/hello', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: 'Hello World' })
			});
		});
		await page.route('**/api/sync/status', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					last_synced: null,
					status: null,
					media_items_count: null,
					requests_count: null,
					error: null
				})
			});
		});

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Should see Old Content link in header
		const oldContentLink = page.getByRole('link', { name: /old content/i });
		await expect(oldContentLink).toBeVisible();
	});

	test('clicking old content link navigates to the page', async ({ page }) => {
		// Mock all endpoints
		await page.route('**/api/hello', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: 'Hello World' })
			});
		});
		await page.route('**/api/sync/status', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					last_synced: null,
					status: null,
					media_items_count: null,
					requests_count: null,
					error: null
				})
			});
		});
		await page.route('**/api/content/old-unwatched', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0,
					total_size_bytes: 0,
					total_size_formatted: 'Unknown size'
				})
			});
		});

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Click on Old Content link
		await page.getByRole('link', { name: /old content/i }).click();
		await page.waitForLoadState('networkidle');

		// Should navigate to old content page
		await expect(page).toHaveURL('/content/old-unwatched');
		await expect(page.getByRole('heading', { name: /old.*unwatched/i })).toBeVisible();
	});
});
