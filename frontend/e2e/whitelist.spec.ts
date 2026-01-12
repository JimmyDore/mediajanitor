import { test, expect } from '@playwright/test';

test.describe('Whitelist Page (US-3.3)', () => {
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

	test('whitelist page renders with title', async ({ page }) => {
		// Mock whitelist API - must be set up BEFORE navigation
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0
				})
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Should see the page title
		await expect(page.getByRole('heading', { name: /protected content/i })).toBeVisible();
	});

	test('shows loading state initially', async ({ page }) => {
		// Mock with a delay to see loading state
		await page.route('**/api/whitelist/content', async (route) => {
			await new Promise((r) => setTimeout(r, 500));
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0
				})
			});
		});

		await page.goto('/whitelist');

		// Should show loading state
		await expect(page.getByText(/loading/i)).toBeVisible();
	});

	test('shows empty state when no whitelist items', async ({ page }) => {
		// Mock empty response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0
				})
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Should show empty state message
		await expect(page.getByText(/no content in your whitelist/i)).toBeVisible();
	});

	test('displays whitelist items with all required columns', async ({ page }) => {
		// Mock whitelist response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 1,
							jellyfin_id: 'movie-1',
							name: 'Protected Movie',
							media_type: 'Movie',
							created_at: '2024-01-15T10:30:00Z'
						}
					],
					total_count: 1
				})
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Should show the whitelist item
		await expect(page.getByText('Protected Movie')).toBeVisible();
		await expect(page.getByText('Movie').first()).toBeVisible();
		// Should show date added
		await expect(page.getByText(/jan 15, 2024/i)).toBeVisible();
	});

	test('shows total count in summary bar', async ({ page }) => {
		// Mock whitelist response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 1,
							jellyfin_id: 'movie-1',
							name: 'Movie 1',
							media_type: 'Movie',
							created_at: '2024-01-15T10:00:00Z'
						},
						{
							id: 2,
							jellyfin_id: 'series-1',
							name: 'Series 1',
							media_type: 'Series',
							created_at: '2024-01-14T10:00:00Z'
						}
					],
					total_count: 2
				})
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Should show total count
		await expect(page.getByText('2').first()).toBeVisible();
	});

	test('displays both movies and series with type badges', async ({ page }) => {
		// Mock whitelist response with both types
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 1,
							jellyfin_id: 'movie-1',
							name: 'Test Movie',
							media_type: 'Movie',
							created_at: '2024-01-15T10:00:00Z'
						},
						{
							id: 2,
							jellyfin_id: 'series-1',
							name: 'Test Series',
							media_type: 'Series',
							created_at: '2024-01-14T10:00:00Z'
						}
					],
					total_count: 2
				})
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Should show both items
		await expect(page.getByText('Test Movie')).toBeVisible();
		await expect(page.getByText('Test Series')).toBeVisible();
		// Should show type badges
		await expect(page.getByText('Movie').first()).toBeVisible();
		await expect(page.getByText('Series')).toBeVisible();
	});

	test('shows Remove button for each whitelist item', async ({ page }) => {
		// Mock whitelist response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 1,
							jellyfin_id: 'movie-1',
							name: 'Protected Movie',
							media_type: 'Movie',
							created_at: '2024-01-15T10:00:00Z'
						}
					],
					total_count: 1
				})
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Should see Remove button
		const removeButton = page.getByRole('button', { name: /remove/i });
		await expect(removeButton).toBeVisible();
	});

	test('clicking Remove button calls delete API', async ({ page }) => {
		let deleteCalled = false;

		// Mock whitelist GET response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 123,
							jellyfin_id: 'movie-1',
							name: 'Protected Movie',
							media_type: 'Movie',
							created_at: '2024-01-15T10:00:00Z'
						}
					],
					total_count: 1
				})
			});
		});

		// Mock whitelist DELETE response
		await page.route('**/api/whitelist/content/123', async (route) => {
			deleteCalled = true;
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: 'Removed from whitelist' })
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Click Remove button
		await page.getByRole('button', { name: /remove/i }).click();

		// Wait for API call
		await page.waitForTimeout(500);
		expect(deleteCalled).toBe(true);
	});

	test('shows success toast after removing item', async ({ page }) => {
		// Mock whitelist GET response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 1,
							jellyfin_id: 'movie-1',
							name: 'Protected Movie',
							media_type: 'Movie',
							created_at: '2024-01-15T10:00:00Z'
						}
					],
					total_count: 1
				})
			});
		});

		// Mock whitelist DELETE response
		await page.route('**/api/whitelist/content/1', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: 'Removed from whitelist' })
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Click Remove button
		await page.getByRole('button', { name: /remove/i }).click();

		// Should see success toast
		await expect(page.getByText(/removed from whitelist/i)).toBeVisible();
	});

	test('removes item from list after successful deletion', async ({ page }) => {
		// Mock whitelist GET response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 1,
							jellyfin_id: 'movie-1',
							name: 'Protected Movie',
							media_type: 'Movie',
							created_at: '2024-01-15T10:00:00Z'
						}
					],
					total_count: 1
				})
			});
		});

		// Mock whitelist DELETE response
		await page.route('**/api/whitelist/content/1', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: 'Removed from whitelist' })
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Verify item is visible
		await expect(page.getByText('Protected Movie')).toBeVisible();

		// Click Remove button
		await page.getByRole('button', { name: /remove/i }).click();

		// Item should disappear from the list
		await expect(page.getByText('Protected Movie')).not.toBeVisible();
	});

	test('shows error toast when delete API fails', async ({ page }) => {
		// Mock whitelist GET response
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [
						{
							id: 1,
							jellyfin_id: 'movie-1',
							name: 'Protected Movie',
							media_type: 'Movie',
							created_at: '2024-01-15T10:00:00Z'
						}
					],
					total_count: 1
				})
			});
		});

		// Mock whitelist DELETE with 404 error
		await page.route('**/api/whitelist/content/1', async (route) => {
			await route.fulfill({
				status: 404,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Item not found in whitelist' })
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Click Remove button
		await page.getByRole('button', { name: /remove/i }).click();

		// Should see error toast
		await expect(page.getByText(/not found/i)).toBeVisible();
	});

	test('navigation link to whitelist is present in header', async ({ page }) => {
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

		// Should see Whitelist link in header
		const whitelistLink = page.getByRole('link', { name: /whitelist/i });
		await expect(whitelistLink).toBeVisible();
	});

	test('clicking whitelist link navigates to the page', async ({ page }) => {
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
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0
				})
			});
		});

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Click on Whitelist link
		await page.getByRole('link', { name: /whitelist/i }).click();
		await page.waitForLoadState('networkidle');

		// Should navigate to whitelist page
		await expect(page).toHaveURL('/whitelist');
		await expect(page.getByRole('heading', { name: /protected content/i })).toBeVisible();
	});

	test('whitelist link shows active state when on whitelist page', async ({ page }) => {
		// Mock whitelist API
		await page.route('**/api/whitelist/content', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [],
					total_count: 0
				})
			});
		});

		await page.goto('/whitelist');
		await page.waitForLoadState('networkidle');

		// Whitelist link should have active class
		const whitelistLink = page.getByRole('link', { name: /whitelist/i });
		await expect(whitelistLink).toHaveClass(/active/);
	});
});
