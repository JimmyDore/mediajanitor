import { test, expect } from '@playwright/test';

test.describe('Complete Auth Flow E2E', () => {
	// Generate unique email for each test run to ensure idempotency
	const uniqueEmail = `e2e-${Date.now()}@example.com`;
	const testPassword = 'SecurePassword123!';

	test('complete auth flow: register → login → dashboard → settings → logout', async ({
		page
	}) => {
		// Step 1: Register a new user
		await page.goto('/register');

		// Verify register page loaded
		await expect(page.getByRole('heading', { name: /get started free/i })).toBeVisible();

		// Fill registration form
		await page.getByLabel(/email/i).fill(uniqueEmail);
		// Fill password first, then confirm password (there are two password fields)
		await page.locator('#password').fill(testPassword);
		await page.locator('#confirmPassword').fill(testPassword);

		// Submit registration
		await page.getByRole('button', { name: /create free account/i }).click();

		// Wait for redirect to login page after successful registration
		await page.waitForURL('/login', { timeout: 10000 });

		// Step 2: Login with the new user
		await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();

		// Fill login form
		await page.getByLabel(/email/i).fill(uniqueEmail);
		await page.getByLabel(/password/i).fill(testPassword);

		// Submit login
		await page.getByRole('button', { name: /log in/i }).click();

		// Wait for redirect to dashboard (home page)
		await page.waitForURL('/', { timeout: 10000 });

		// Step 3: Verify dashboard loaded
		// Dashboard shows sidebar with navigation when authenticated
		// Use heading role to be specific since "Dashboard" appears in multiple places
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 5000 });
		// Should see the sidebar with navigation items
		await expect(page.getByRole('link', { name: /issues/i })).toBeVisible();
		await expect(page.getByRole('link', { name: /settings/i })).toBeVisible();

		// Step 4: Navigate to settings
		await page.getByRole('link', { name: /settings/i }).click();
		await page.waitForURL('/settings', { timeout: 5000 });

		// Verify settings page loaded
		await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
		// Settings page should show the user's email in the sidebar
		await expect(page.getByText(uniqueEmail)).toBeVisible();

		// Step 5: Logout
		// Click on user section to open dropdown
		await page.locator('.user-btn').click();
		// Wait for dropdown to appear and click sign out
		await page.getByRole('button', { name: /sign out/i }).click();

		// Verify redirect to login page
		await page.waitForURL('/login', { timeout: 5000 });
		await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
	});

	test('protected routes redirect to login when not authenticated', async ({ page }) => {
		// Clear any stored tokens
		await page.goto('/');
		await page.evaluate(() => localStorage.clear());

		// Mock auth/me to return 401 (not authenticated)
		await page.route('**/api/auth/me', async (route) => {
			await route.fulfill({
				status: 401,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Not authenticated' })
			});
		});

		// Mock refresh endpoint to return 401 (no valid refresh token)
		await page.route('**/api/auth/refresh', async (route) => {
			await route.fulfill({
				status: 401,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Invalid refresh token' })
			});
		});

		// Try to access settings (protected route)
		await page.goto('/settings');

		// Should redirect to login
		await page.waitForURL('**/login**', { timeout: 5000 });
		await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
	});
});
