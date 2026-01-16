import { test, expect } from '@playwright/test';

test.describe('Settings Page (Smoke Tests)', () => {
	test('unauthenticated user is redirected to login', async ({ page }) => {
		// Clear any cookies that might be set
		await page.context().clearCookies();

		// Try to access settings (protected route)
		await page.goto('/settings');

		// Should redirect to login (may include ?redirect= query param)
		await page.waitForURL('**/login**', { timeout: 5000 });
		await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
	});

	test('settings page renders after login', async ({ page }) => {
		// Generate unique email for this test
		const uniqueEmail = `settings-e2e-${Date.now()}@example.com`;
		const testPassword = 'SecurePassword123!';

		// Step 1: Register a new user
		await page.goto('/register');
		await page.getByLabel(/email/i).fill(uniqueEmail);
		await page.locator('#password').fill(testPassword);
		await page.locator('#confirmPassword').fill(testPassword);
		await page.getByRole('button', { name: /create free account/i }).click();
		await page.waitForURL('/login', { timeout: 10000 });

		// Step 2: Login
		await page.getByLabel(/email/i).fill(uniqueEmail);
		await page.getByLabel(/password/i).fill(testPassword);
		await page.getByRole('button', { name: /log in/i }).click();
		await page.waitForURL('/', { timeout: 10000 });

		// Step 3: Navigate to settings
		await page.goto('/settings');
		await page.waitForURL('/settings', { timeout: 5000 });

		// Verify settings page loaded with key sections
		await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible({ timeout: 10000 });
		await expect(page.getByText('Connections')).toBeVisible();
		await expect(page.getByText('Jellyfin')).toBeVisible();
	});
});
