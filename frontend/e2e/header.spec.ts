import { test, expect } from '@playwright/test';

test.describe('Navigation Header (Smoke Tests)', () => {
	test.beforeEach(async ({ page }) => {
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
	});

	test('sidebar displays on protected pages with logo, nav links, and user menu', async ({ page }) => {
		await page.goto('/');

		const sidebar = page.locator('aside.sidebar');
		await expect(sidebar.getByText('Media Janitor')).toBeVisible();
		await expect(sidebar.getByRole('link', { name: /dashboard/i })).toBeVisible();
		await expect(sidebar.getByRole('link', { name: /settings/i })).toBeVisible();
		// User menu is accessible via user button
		await expect(sidebar.locator('.user-btn')).toBeVisible();
	});

	test('navigation links work', async ({ page }) => {
		await page.goto('/');

		// Navigate to settings
		const sidebar = page.locator('aside.sidebar');
		await sidebar.getByRole('link', { name: /settings/i }).click();
		await expect(page).toHaveURL('/settings');

		// Navigate back to dashboard
		await sidebar.getByRole('link', { name: /dashboard/i }).click();
		await expect(page).not.toHaveURL('/settings');
	});

	test('sidebar does not appear on public pages when logged out', async ({ page }) => {
		// Clear the mock auth to test logged-out state
		await page.evaluate(() => localStorage.removeItem('access_token'));

		// Sidebar should not appear for unauthenticated users on public pages
		await page.goto('/login');
		await expect(page.locator('aside.sidebar')).not.toBeVisible();

		await page.goto('/register');
		await expect(page.locator('aside.sidebar')).not.toBeVisible();
	});
});
