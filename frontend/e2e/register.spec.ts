import { test, expect } from '@playwright/test';

test.describe('Registration Page', () => {
	test('loads with email and password fields', async ({ page }) => {
		await page.goto('/register');

		await expect(page.getByLabel(/email/i)).toBeVisible();
		await expect(page.getByLabel(/password/i)).toBeVisible();
		await expect(page.getByRole('button', { name: /create free account/i })).toBeVisible();
	});

	test('password field has minlength validation', async ({ page }) => {
		await page.goto('/register');

		const passwordInput = page.getByLabel(/password/i);
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
		await page.getByLabel(/password/i).fill('SecurePassword123!');

		// Verify values were entered
		await expect(page.getByLabel(/email/i)).toHaveValue('test@example.com');
		await expect(page.getByLabel(/password/i)).toHaveValue('SecurePassword123!');
	});
});
