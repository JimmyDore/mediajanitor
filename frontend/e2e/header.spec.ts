import { test, expect } from '@playwright/test';

test.describe('Navigation Header (Smoke Tests)', () => {
	// Generate unique email for these tests
	const uniqueEmail = `header-e2e-${Date.now()}@example.com`;
	const testPassword = 'SecurePassword123!';
	let isRegistered = false;

	test.beforeEach(async ({ page }) => {
		// Only register once per test file
		if (!isRegistered) {
			await page.goto('/register');
			await page.getByLabel(/email/i).fill(uniqueEmail);
			await page.locator('#password').fill(testPassword);
			await page.locator('#confirmPassword').fill(testPassword);
			await page.getByRole('button', { name: /create free account/i }).click();
			await page.waitForURL('/login', { timeout: 10000 });
			isRegistered = true;
		}

		// Login for each test
		await page.goto('/login');
		await page.getByLabel(/email/i).fill(uniqueEmail);
		await page.getByLabel(/password/i).fill(testPassword);
		await page.getByRole('button', { name: /log in/i }).click();
		await page.waitForURL('/', { timeout: 10000 });
	});

	test('sidebar displays on protected pages with logo, nav links, and user menu', async ({
		page
	}) => {
		const sidebar = page.locator('aside.sidebar');
		await expect(sidebar.getByText('Media Janitor')).toBeVisible({ timeout: 10000 });
		await expect(sidebar.getByRole('link', { name: /dashboard/i })).toBeVisible();
		await expect(sidebar.getByRole('link', { name: /settings/i })).toBeVisible();
		// User menu is accessible via user button
		await expect(sidebar.locator('.user-btn')).toBeVisible();
	});

	test('navigation links work', async ({ page }) => {
		// Wait for dashboard to load
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 10000 });

		// Navigate to settings (redirects to /settings/connections)
		const sidebar = page.locator('aside.sidebar');
		await sidebar.getByRole('link', { name: /settings/i }).click();
		await expect(page).toHaveURL('/settings/connections');

		// Navigate back to dashboard
		await sidebar.getByRole('link', { name: /dashboard/i }).click();
		await expect(page).toHaveURL('/');
	});

	test('sidebar does not appear on public pages when logged out', async ({ page }) => {
		// Clear cookies to log out
		await page.context().clearCookies();

		// Sidebar should not appear for unauthenticated users on public pages
		await page.goto('/login');
		await expect(page.locator('aside.sidebar')).not.toBeVisible();

		await page.goto('/register');
		await expect(page.locator('aside.sidebar')).not.toBeVisible();
	});
});
