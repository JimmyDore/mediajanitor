import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
	// Note: Settings page is protected. These tests verify UI elements
	// after manually setting up authentication state.

	test('unauthenticated user is redirected to login from settings', async ({ page }) => {
		// Mock the auth endpoint to return 401 (unauthenticated)
		await page.route('**/api/auth/me', async (route) => {
			await route.fulfill({
				status: 401,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Not authenticated' })
			});
		});

		// Clear any stored tokens
		await page.goto('/login');
		await page.evaluate(() => localStorage.removeItem('access_token'));

		// Navigate to settings page
		await page.goto('/settings');

		// Wait for redirect to login page
		await page.waitForURL('/login', { timeout: 5000 });

		// Verify we're on login page
		await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
	});

	test.describe('with mocked authentication', () => {
		test.beforeEach(async ({ page }) => {
			// Set up a mock token to bypass auth check
			await page.goto('/login');
			await page.evaluate(() => {
				localStorage.setItem('access_token', 'mock-token-for-ui-testing');
			});
		});

		test('settings page renders with Jellyfin section', async ({ page }) => {
			await page.route('**/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('**/api/settings/jellyfin', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.route('**/api/settings/jellyseerr', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.goto('/settings');

			await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
			await expect(page.getByRole('heading', { name: /jellyfin connection/i })).toBeVisible();
			await expect(page.getByText(/connect your jellyfin server/i)).toBeVisible();
		});

		test('settings page has server URL and API key fields', async ({ page }) => {
			await page.route('**/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('**/api/settings/jellyfin', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.route('**/api/settings/jellyseerr', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.goto('/settings');

			// Check Jellyfin fields exist
			await expect(page.locator('#jellyfin-url')).toBeVisible();
			await expect(page.locator('#jellyfin-api-key')).toBeVisible();
		});

		test('settings page shows connect button when not configured', async ({ page }) => {
			await page.route('**/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('**/api/settings/jellyfin', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.route('**/api/settings/jellyseerr', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.goto('/settings');

			await expect(page.getByRole('button', { name: /connect to jellyfin/i })).toBeVisible();
			await expect(page.getByText(/not connected/i).first()).toBeVisible();
		});

		test('settings page shows update button when Jellyfin already configured', async ({ page }) => {
			await page.route('**/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('**/api/settings/jellyfin', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						server_url: 'https://jellyfin.example.com',
						api_key_configured: true
					})
				});
			});

			await page.route('**/api/settings/jellyseerr', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.goto('/settings');

			// Jellyfin should show update button and connected status
			const jellyfinSection = page.locator('section').filter({ hasText: /jellyfin connection/i });
			await expect(jellyfinSection.getByRole('button', { name: /update connection/i })).toBeVisible();
			await expect(jellyfinSection.getByText(/connected to/i)).toBeVisible();
		});

		test('settings form can be filled', async ({ page }) => {
			await page.route('**/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('**/api/settings/jellyfin', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.route('**/api/settings/jellyseerr', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.goto('/settings');

			// Fill in the form
			await page.locator('#jellyfin-url').fill('https://my-jellyfin.example.com');
			await page.locator('#jellyfin-api-key').fill('my-api-key-12345');

			// Verify values were entered
			await expect(page.locator('#jellyfin-url')).toHaveValue('https://my-jellyfin.example.com');
			await expect(page.locator('#jellyfin-api-key')).toHaveValue('my-api-key-12345');
		});

		test('settings page has back button to dashboard', async ({ page }) => {
			await page.route('**/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('**/api/settings/jellyfin', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.route('**/api/settings/jellyseerr', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ server_url: null, api_key_configured: false })
				});
			});

			await page.goto('/settings');

			const backButton = page.getByRole('button', { name: /back to dashboard/i });
			await expect(backButton).toBeVisible();
		});
	});
});
