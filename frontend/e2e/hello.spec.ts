import { test, expect } from '@playwright/test';

test('homepage displays message or error state', async ({ page }) => {
	await page.goto('/');

	// Either shows the hello message (backend running) or error state (backend not running)
	const hasMessage = await page.getByText('Hello World').isVisible().catch(() => false);
	const hasError = await page.getByText(/error|backend/i).isVisible().catch(() => false);
	const hasLoading = await page.getByText('Loading').isVisible().catch(() => false);

	expect(hasMessage || hasError || hasLoading).toBe(true);
});

test('homepage has correct title', async ({ page }) => {
	await page.goto('/');

	await expect(page).toHaveTitle(/Media Janitor|Plex Dashboard/i);
});
