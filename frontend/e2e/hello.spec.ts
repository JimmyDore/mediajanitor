import { test, expect } from '@playwright/test';

test('homepage displays landing page for unauthenticated users', async ({ page }) => {
	await page.goto('/');

	// For unauthenticated users, landing page shows immediately (no loading)
	// Verify landing page hero content is visible
	await expect(page.getByRole('heading', { name: 'Keep Your Media Library Clean' })).toBeVisible();
});

test('homepage has correct title', async ({ page }) => {
	await page.goto('/');

	await expect(page).toHaveTitle(/Media Janitor|Plex Dashboard/i);
});
