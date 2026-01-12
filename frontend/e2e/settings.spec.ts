import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
	// Note: Settings page is protected. These tests verify UI elements
	// after manually setting up authentication state.

	test('unauthenticated user is redirected to login from settings', async ({ page }) => {
		// Mock the auth endpoint to return 401 (unauthenticated)
		await page.route('/api/auth/me', async (route) => {
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
			// Note: The actual /me endpoint will fail, but we can test UI rendering
			await page.goto('/login');
			await page.evaluate(() => {
				localStorage.setItem('access_token', 'mock-token-for-ui-testing');
			});
		});

		test('settings page renders with Jellyfin section', async ({ page }) => {
			// Mock the auth check and settings API
			await page.route('/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('/api/settings/jellyfin', async (route) => {
				if (route.request().method() === 'GET') {
					await route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({ server_url: null, api_key_configured: false })
					});
				}
			});

			await page.goto('/settings');

			// Wait for page to load
			await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();

			// Verify Jellyfin section is present
			await expect(page.getByRole('heading', { name: /jellyfin connection/i })).toBeVisible();
			await expect(page.getByText(/connect your jellyfin server/i)).toBeVisible();
		});

		test('settings page has server URL and API key fields', async ({ page }) => {
			await page.route('/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('/api/settings/jellyfin', async (route) => {
				if (route.request().method() === 'GET') {
					await route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({ server_url: null, api_key_configured: false })
					});
				}
			});

			await page.goto('/settings');

			await expect(page.getByLabel(/server url/i)).toBeVisible();
			await expect(page.getByLabel(/api key/i)).toBeVisible();
		});

		test('settings page shows connect button when not configured', async ({ page }) => {
			await page.route('/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('/api/settings/jellyfin', async (route) => {
				if (route.request().method() === 'GET') {
					await route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({ server_url: null, api_key_configured: false })
					});
				}
			});

			await page.goto('/settings');

			await expect(page.getByRole('button', { name: /connect to jellyfin/i })).toBeVisible();
			await expect(page.getByText(/not connected/i)).toBeVisible();
		});

		test('settings page shows update button when already configured', async ({ page }) => {
			await page.route('/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('/api/settings/jellyfin', async (route) => {
				if (route.request().method() === 'GET') {
					await route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({
							server_url: 'https://jellyfin.example.com',
							api_key_configured: true
						})
					});
				}
			});

			await page.goto('/settings');

			await expect(page.getByRole('button', { name: /update connection/i })).toBeVisible();
			await expect(page.getByText(/connected to/i)).toBeVisible();
		});

		test('settings form can be filled', async ({ page }) => {
			await page.route('/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('/api/settings/jellyfin', async (route) => {
				if (route.request().method() === 'GET') {
					await route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({ server_url: null, api_key_configured: false })
					});
				}
			});

			await page.goto('/settings');

			// Fill in the form
			await page.getByLabel(/server url/i).fill('https://my-jellyfin.example.com');
			await page.getByLabel(/api key/i).fill('my-api-key-12345');

			// Verify values were entered
			await expect(page.getByLabel(/server url/i)).toHaveValue('https://my-jellyfin.example.com');
			await expect(page.getByLabel(/api key/i)).toHaveValue('my-api-key-12345');
		});

		test('settings page has back button to dashboard', async ({ page }) => {
			await page.route('/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			await page.route('/api/settings/jellyfin', async (route) => {
				if (route.request().method() === 'GET') {
					await route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({ server_url: null, api_key_configured: false })
					});
				}
			});

			await page.goto('/settings');

			const backButton = page.getByRole('button', { name: /back to dashboard/i });
			await expect(backButton).toBeVisible();
		});
	});
});
