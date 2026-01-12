import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
	test('loads with email and password fields', async ({ page }) => {
		await page.goto('/login');

		await expect(page.getByLabel(/email/i)).toBeVisible();
		await expect(page.getByLabel(/password/i)).toBeVisible();
		await expect(page.getByRole('button', { name: /log in/i })).toBeVisible();
	});

	test('has link to register page', async ({ page }) => {
		await page.goto('/login');

		const registerLink = page.getByRole('link', { name: /sign up/i });
		await expect(registerLink).toBeVisible();
		await expect(registerLink).toHaveAttribute('href', '/register');
	});

	test('form can be filled', async ({ page }) => {
		await page.goto('/login');

		await page.getByLabel(/email/i).fill('test@example.com');
		await page.getByLabel(/password/i).fill('SecurePassword123!');

		// Verify values were entered
		await expect(page.getByLabel(/email/i)).toHaveValue('test@example.com');
		await expect(page.getByLabel(/password/i)).toHaveValue('SecurePassword123!');
	});

	test('email field has required validation', async ({ page }) => {
		await page.goto('/login');

		const emailInput = page.getByLabel(/email/i);
		await expect(emailInput).toHaveAttribute('required', '');
	});

	test('password field has required validation', async ({ page }) => {
		await page.goto('/login');

		const passwordInput = page.getByLabel(/password/i);
		await expect(passwordInput).toHaveAttribute('required', '');
	});
});
