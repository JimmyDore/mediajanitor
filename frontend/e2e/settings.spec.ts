import { test, expect } from '@playwright/test';

test.describe('Settings Page (Smoke Tests)', () => {
	test('unauthenticated user is redirected to login', async ({ page }) => {
		await page.route('**/api/auth/me', async (route) => {
			await route.fulfill({
				status: 401,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Not authenticated' })
			});
		});

		await page.goto('/login');
		await page.evaluate(() => localStorage.removeItem('access_token'));
		await page.goto('/settings');
		await page.waitForURL('/login', { timeout: 5000 });

		await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
	});

	test('settings page renders with connection sections', async ({ page }) => {
		await page.goto('/login');
		await page.evaluate(() => {
			localStorage.setItem('access_token', 'mock-token-for-ui-testing');
		});

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
	});
});
