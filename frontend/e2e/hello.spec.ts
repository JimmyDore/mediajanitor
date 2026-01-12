import { test, expect } from '@playwright/test';

test('homepage displays hello message from API', async ({ page }) => {
	await page.goto('/');

	// Wait for the API response to be displayed
	await expect(page.getByText('Hello World')).toBeVisible();
});

test('homepage has correct title', async ({ page }) => {
	await page.goto('/');

	await expect(page).toHaveTitle(/Media Janitor|Plex Dashboard/i);
});
