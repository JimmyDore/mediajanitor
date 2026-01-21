import { test, expect } from '@playwright/test';

// Skip tests that require a running backend in CI
const skipInCI = process.env.CI ? test.skip : test;

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

	skipInCI('settings page renders after login with sidebar navigation', async ({ page }) => {
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

		// Step 3: Navigate to settings - should redirect to /settings/connections
		await page.goto('/settings');
		await page.waitForURL('/settings/connections', { timeout: 5000 });

		// Verify breadcrumb navigation is present
		const breadcrumb = page.locator('nav[aria-label="Breadcrumb"]');
		await expect(breadcrumb).toBeVisible({ timeout: 10000 });
		await expect(breadcrumb.getByText('Dashboard')).toBeVisible();
		await expect(breadcrumb.getByText('Settings')).toBeVisible();

		// Verify sidebar navigation shows 4 sections
		const sidebarNav = page.locator('aside[aria-label="Settings navigation"]');
		await expect(sidebarNav).toBeVisible();
		await expect(sidebarNav.getByText('Connections')).toBeVisible();
		await expect(sidebarNav.getByText('Thresholds')).toBeVisible();
		await expect(sidebarNav.getByText('Users')).toBeVisible();
		await expect(sidebarNav.getByText('Display')).toBeVisible();

		// Verify Connections nav item is active (since we're on /settings/connections)
		const connectionsLink = sidebarNav.getByRole('link', { name: /connections/i });
		await expect(connectionsLink).toHaveClass(/active/);

		// Verify page title/heading for Connections section
		await expect(page.getByRole('heading', { name: /connections/i })).toBeVisible();
	});

	skipInCI('settings sidebar navigation works', async ({ page }) => {
		// Generate unique email for this test
		const uniqueEmail = `settings-nav-${Date.now()}@example.com`;
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
		await page.goto('/settings/connections');
		await page.waitForURL('/settings/connections', { timeout: 5000 });

		// Click Thresholds link
		const sidebarNav = page.locator('aside[aria-label="Settings navigation"]');
		await sidebarNav.getByRole('link', { name: /thresholds/i }).click();
		await page.waitForURL('/settings/thresholds', { timeout: 5000 });
		await expect(page.getByRole('heading', { name: /thresholds/i })).toBeVisible();

		// Click Users link
		await sidebarNav.getByRole('link', { name: /users/i }).click();
		await page.waitForURL('/settings/users', { timeout: 5000 });
		await expect(page.getByRole('heading', { name: /users/i })).toBeVisible();

		// Click Display link
		await sidebarNav.getByRole('link', { name: /display/i }).click();
		await page.waitForURL('/settings/display', { timeout: 5000 });
		await expect(page.getByRole('heading', { name: /display/i })).toBeVisible();

		// Click back to Connections
		await sidebarNav.getByRole('link', { name: /connections/i }).click();
		await page.waitForURL('/settings/connections', { timeout: 5000 });
		await expect(page.getByRole('heading', { name: /connections/i })).toBeVisible();
	});
});
