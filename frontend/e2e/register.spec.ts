import { test, expect } from '@playwright/test';

test.describe('Registration Page', () => {
	test('loads with email, password, and confirm password fields', async ({ page }) => {
		await page.goto('/register');

		await expect(page.getByLabel(/email/i)).toBeVisible();
		// Use exact label to distinguish from confirm password
		await expect(page.getByLabel('Password', { exact: true })).toBeVisible();
		await expect(page.getByLabel('Confirm Password')).toBeVisible();
		await expect(page.getByRole('button', { name: /create free account/i })).toBeVisible();
	});

	test('password field has minlength validation', async ({ page }) => {
		await page.goto('/register');

		// Use exact label to get the main password field
		const passwordInput = page.getByLabel('Password', { exact: true });
		await expect(passwordInput).toHaveAttribute('minlength', '8');
	});

	test('has link to login page', async ({ page }) => {
		await page.goto('/register');

		const loginLink = page.getByRole('link', { name: /log in/i });
		await expect(loginLink).toBeVisible();
		await expect(loginLink).toHaveAttribute('href', '/login');
	});

	test('form can be filled', async ({ page }) => {
		await page.goto('/register');

		await page.getByLabel(/email/i).fill('test@example.com');
		// Use locator by ID for specificity with password fields
		await page.locator('#password').fill('SecurePassword123!');
		await page.locator('#confirmPassword').fill('SecurePassword123!');

		// Verify values were entered
		await expect(page.getByLabel(/email/i)).toHaveValue('test@example.com');
		await expect(page.locator('#password')).toHaveValue('SecurePassword123!');
		await expect(page.locator('#confirmPassword')).toHaveValue('SecurePassword123!');
	});
});
