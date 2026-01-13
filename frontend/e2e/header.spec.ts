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

	test('header displays on protected pages with logo, nav links, and logout', async ({ page }) => {
		await page.goto('/');

		const header = page.locator('header');
		await expect(header.getByText('Media Janitor')).toBeVisible();
		await expect(header.getByRole('link', { name: /dashboard/i })).toBeVisible();
		await expect(header.getByRole('link', { name: /settings/i })).toBeVisible();
		await expect(header.getByRole('button', { name: /log out/i })).toBeVisible();
	});

	test('navigation links work', async ({ page }) => {
		await page.goto('/');

		// Navigate to settings
		const header = page.locator('header');
		await header.getByRole('link', { name: /settings/i }).click();
		await expect(page).toHaveURL('/settings');

		// Navigate back to dashboard
		await header.getByRole('link', { name: /dashboard/i }).click();
		await expect(page).not.toHaveURL('/settings');
	});

	test('header does not appear on public pages', async ({ page }) => {
		await page.goto('/login');
		await expect(page.getByText('Media Janitor')).not.toBeVisible();

		await page.goto('/register');
		await expect(page.getByText('Media Janitor')).not.toBeVisible();
	});
});
