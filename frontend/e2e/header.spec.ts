import { test, expect } from '@playwright/test';

test.describe('Navigation Header', () => {
	test.describe('with mocked authentication', () => {
		test.beforeEach(async ({ page }) => {
			// Set up a mock token to bypass auth check
			await page.goto('/login');
			await page.evaluate(() => {
				localStorage.setItem('access_token', 'mock-token-for-ui-testing');
			});

			// Mock auth endpoint
			await page.route('**/api/auth/me', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 1, email: 'test@example.com' })
				});
			});

			// Mock settings endpoints
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

			// Mock hello endpoint
			await page.route('**/api/hello', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ message: 'Hello World' })
				});
			});
		});

		test('header displays app logo on dashboard', async ({ page }) => {
			await page.goto('/');

			// Check logo is visible
			await expect(page.getByText('Media Janitor')).toBeVisible();
		});

		test('header displays navigation links on dashboard', async ({ page }) => {
			await page.goto('/');

			// Check navigation links are visible in header
			const header = page.locator('header');
			await expect(header.getByRole('link', { name: /dashboard/i })).toBeVisible();
			await expect(header.getByRole('link', { name: /settings/i })).toBeVisible();
		});

		test('header displays logout button on dashboard', async ({ page }) => {
			await page.goto('/');

			const header = page.locator('header');
			await expect(header.getByRole('button', { name: /log out/i })).toBeVisible();
		});

		test('dashboard link is highlighted on home page', async ({ page }) => {
			await page.goto('/');

			const header = page.locator('header');
			const dashboardLink = header.getByRole('link', { name: /dashboard/i });
			await expect(dashboardLink).toHaveClass(/active/);
		});

		test('settings link is highlighted on settings page', async ({ page }) => {
			await page.goto('/settings');

			const header = page.locator('header');
			const settingsLink = header.getByRole('link', { name: /settings/i });
			await expect(settingsLink).toHaveClass(/active/);
		});

		test('clicking settings link navigates to settings', async ({ page }) => {
			await page.goto('/');

			const header = page.locator('header');
			await header.getByRole('link', { name: /settings/i }).click();
			await page.waitForURL('/settings');

			await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
		});

		test('clicking dashboard link navigates to dashboard', async ({ page }) => {
			await page.goto('/settings');

			const header = page.locator('header');
			await header.getByRole('link', { name: /dashboard/i }).click();
			await page.waitForURL('/');

			// Should be on dashboard
			await expect(page.url()).not.toContain('/settings');
		});

		test('clicking logo navigates to dashboard', async ({ page }) => {
			await page.goto('/settings');

			const header = page.locator('header');
			await header.getByText('Media Janitor').click();
			await page.waitForURL('/');

			// Should be on dashboard
			await expect(page.url()).not.toContain('/settings');
		});

		test('header appears on settings page', async ({ page }) => {
			await page.goto('/settings');

			const header = page.locator('header');
			await expect(header.getByText('Media Janitor')).toBeVisible();
			await expect(header.getByRole('link', { name: /dashboard/i })).toBeVisible();
			await expect(header.getByRole('link', { name: /settings/i })).toBeVisible();
		});
	});

	test.describe('without authentication', () => {
		test('header does not appear on login page', async ({ page }) => {
			await page.goto('/login');

			// Logo should not appear (header is not shown on public routes)
			await expect(page.getByText('Media Janitor')).not.toBeVisible();
		});

		test('header does not appear on register page', async ({ page }) => {
			await page.goto('/register');

			// Logo should not appear (header is not shown on public routes)
			await expect(page.getByText('Media Janitor')).not.toBeVisible();
		});
	});
});
