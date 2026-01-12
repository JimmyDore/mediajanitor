import { test, expect } from '@playwright/test';

test.describe('Manual Data Refresh (US-7.2)', () => {
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

		// Mock hello endpoint
		await page.route('**/api/hello', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: 'Hello World' })
			});
		});
	});

	test('shows refresh button on dashboard', async ({ page }) => {
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

		await page.goto('/');

		// Should see the refresh button
		await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
	});

	test('refresh button shows loading spinner when clicked', async ({ page }) => {
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

		// Mock sync endpoint with a delay to observe loading state
		await page.route('**/api/sync', async (route) => {
			await new Promise((r) => setTimeout(r, 500));
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					status: 'success',
					media_items_synced: 110,
					requests_synced: 30,
					error: null
				})
			});
		});

		await page.goto('/');

		// Click refresh button
		const refreshButton = page.getByRole('button', { name: /refresh/i });
		await refreshButton.click();

		// Should show "Syncing..." text while loading
		await expect(page.getByText('Syncing...')).toBeVisible();
	});

	test('shows success toast after successful sync', async ({ page }) => {
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

		// Mock successful sync
		await page.route('**/api/sync', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					status: 'success',
					media_items_synced: 150,
					requests_synced: 35,
					error: null
				})
			});
		});

		await page.goto('/');

		// Click refresh button
		await page.getByRole('button', { name: /refresh/i }).click();

		// Should show success toast
		await expect(page.getByRole('alert')).toBeVisible();
		await expect(page.getByText(/synced 150 media items/i)).toBeVisible();
	});

	test('shows error toast when rate limited', async ({ page }) => {
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

		// Mock rate limited response
		await page.route('**/api/sync', async (route) => {
			await route.fulfill({
				status: 429,
				contentType: 'application/json',
				body: JSON.stringify({
					detail: 'Rate limited. Please wait 5 minute(s) before syncing again.'
				})
			});
		});

		await page.goto('/');

		// Click refresh button
		await page.getByRole('button', { name: /refresh/i }).click();

		// Should show error toast with rate limit message
		await expect(page.getByRole('alert')).toBeVisible();
		await expect(page.getByText(/rate limited/i)).toBeVisible();
	});

	test('shows error toast when Jellyfin not configured', async ({ page }) => {
		// Mock sync status
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

		// Mock 400 error for unconfigured Jellyfin
		await page.route('**/api/sync', async (route) => {
			await route.fulfill({
				status: 400,
				contentType: 'application/json',
				body: JSON.stringify({
					detail: 'Jellyfin connection not configured. Please configure it in Settings first.'
				})
			});
		});

		await page.goto('/');

		// Click refresh button
		await page.getByRole('button', { name: /refresh/i }).click();

		// Should show error toast
		await expect(page.getByRole('alert')).toBeVisible();
		await expect(page.getByText(/jellyfin/i)).toBeVisible();
	});

	test('refresh button shows syncing state during sync', async ({ page }) => {
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

		let resolveSyncRequest: () => void;
		const syncPromise = new Promise<void>((resolve) => {
			resolveSyncRequest = resolve;
		});

		// Mock sync - hold the request until we verify loading state
		await page.route('**/api/sync', async (route) => {
			// Wait for test to verify loading state before completing
			await syncPromise;
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

		// Click refresh button
		const refreshButton = page.getByRole('button', { name: /refresh/i });
		await refreshButton.click();

		// Wait for syncing text to appear
		await expect(page.getByText('Syncing...')).toBeVisible({ timeout: 3000 });

		// The button should be disabled during sync
		await expect(page.getByRole('button').filter({ hasText: 'Syncing...' })).toBeDisabled();

		// Allow sync to complete
		resolveSyncRequest!();
	});

	test('dashboard shows last synced timestamp', async ({ page }) => {
		// Mock sync status with a specific timestamp
		await page.route('**/api/sync/status', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					last_synced: '2024-01-15T10:30:00Z',
					status: 'success',
					media_items_count: 200,
					requests_count: 50,
					error: null
				})
			});
		});

		await page.goto('/');

		// Should show last synced time
		await expect(page.getByText(/last synced/i)).toBeVisible();
		// Should show counts
		await expect(page.getByText(/200 media items/i)).toBeVisible();
		await expect(page.getByText(/50 requests/i)).toBeVisible();
	});

	test('shows "Never synced" when no previous sync', async ({ page }) => {
		// Mock sync status with null values
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

		// Should show "Never synced"
		await expect(page.getByText(/never synced/i)).toBeVisible();
	});
});
