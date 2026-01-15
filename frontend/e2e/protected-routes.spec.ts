import { test, expect } from '@playwright/test';

test.describe('Protected Routes', () => {
	test('unauthenticated user sees landing page on home', async ({ page }) => {
		// Clear any stored tokens
		await page.goto('/');
		await page.evaluate(() => localStorage.removeItem('access_token'));

		// Navigate to home page
		await page.goto('/');

		// Landing page is a public route, so it renders immediately without loading
		await expect(page.getByText('Keep Your Media Library Clean')).toBeVisible();
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

	test('public routes render immediately without loading state', async ({ page }) => {
		// Go to home page (public route)
		await page.goto('/');

		// Public routes should NOT show loading - they render immediately
		const hasLoading = await page.getByText('Loading...').isVisible().catch(() => false);
		expect(hasLoading).toBe(false);

		// Should show landing page content immediately
		await expect(page.getByText('Keep Your Media Library Clean')).toBeVisible();
	});
});
