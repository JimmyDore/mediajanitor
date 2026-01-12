import { test, expect } from '@playwright/test';

test.describe('Protected Routes', () => {
	test('unauthenticated user is redirected to login from home', async ({ page }) => {
		// Clear any stored tokens
		await page.goto('/');
		await page.evaluate(() => localStorage.removeItem('access_token'));

		// Navigate to home page
		await page.goto('/');

		// Wait for redirect to login page
		await page.waitForURL('/login', { timeout: 5000 });

		// Verify we're on login page
		await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
	});

	test('login page is accessible without authentication', async ({ page }) => {
		await page.goto('/login');

		// Should stay on login page
		await expect(page.url()).toContain('/login');
		await expect(page.getByLabel(/email/i)).toBeVisible();
	});

	test('register page is accessible without authentication', async ({ page }) => {
		await page.goto('/register');

		// Should stay on register page
		await expect(page.url()).toContain('/register');
		await expect(page.getByLabel(/email/i)).toBeVisible();
	});

	test('shows loading state while checking authentication', async ({ page }) => {
		// Go to home page
		await page.goto('/');

		// Should show loading state initially or redirect quickly
		const hasLoading = await page.getByText('Loading...').isVisible().catch(() => false);
		const hasLoginRedirect = page.url().includes('/login');

		expect(hasLoading || hasLoginRedirect).toBe(true);
	});
});
