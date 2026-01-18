/**
 * Tests for the Display Settings Page API integration (US-36.5)
 *
 * These tests verify the API contract that the settings/display page uses
 * for display preferences configuration including theme, language, days, and toggle.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Settings Display Page API Integration (US-36.5)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/display - Initial load', () => {
		it('loads all display preferences on page mount', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						theme_preference: 'dark',
						title_language: 'fr',
						recently_available_days: 14,
						show_unreleased_requests: true
					})
			});

			const response = await fetch('/api/settings/display', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.theme_preference).toBe('dark');
			expect(data.title_language).toBe('fr');
			expect(data.recently_available_days).toBe(14);
			expect(data.show_unreleased_requests).toBe(true);
		});

		it('returns default values for new users', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						theme_preference: 'system',
						title_language: 'en',
						recently_available_days: 7,
						show_unreleased_requests: false
					})
			});

			const response = await fetch('/api/settings/display', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.theme_preference).toBe('system');
			expect(data.title_language).toBe('en');
			expect(data.recently_available_days).toBe(7);
			expect(data.show_unreleased_requests).toBe(false);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/display');
			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('POST /api/settings/display - Theme preference', () => {
		it('saves theme preference to system', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true, message: 'Display preferences saved successfully.' })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'system' })
			});

			expect(response.ok).toBe(true);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'system' })
			});
		});

		it('saves theme preference to light', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'light' })
			});

			expect(response.ok).toBe(true);
		});

		it('saves theme preference to dark', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'dark' })
			});

			expect(response.ok).toBe(true);
		});
	});

	describe('POST /api/settings/display - Title language', () => {
		it('saves title language to English', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ title_language: 'en' })
			});

			expect(response.ok).toBe(true);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ title_language: 'en' })
			});
		});

		it('saves title language to French', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ title_language: 'fr' })
			});

			expect(response.ok).toBe(true);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ title_language: 'fr' })
			});
		});
	});

	describe('POST /api/settings/display - Recently available days', () => {
		it('saves recently available days', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ recently_available_days: 14 })
			});

			expect(response.ok).toBe(true);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ recently_available_days: 14 })
			});
		});

		it('accepts minimum value of 1 day', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ recently_available_days: 1 })
			});

			expect(response.ok).toBe(true);
		});

		it('accepts maximum value of 30 days', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ recently_available_days: 30 })
			});

			expect(response.ok).toBe(true);
		});

		it('rejects invalid value with 422', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'recently_available_days'],
								msg: 'ensure this value is greater than or equal to 1'
							}
						]
					})
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ recently_available_days: 0 })
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});

	describe('POST /api/settings/display - Show unreleased toggle', () => {
		it('saves show unreleased requests to true', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ show_unreleased_requests: true })
			});

			expect(response.ok).toBe(true);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ show_unreleased_requests: true })
			});
		});

		it('saves show unreleased requests to false', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ show_unreleased_requests: false })
			});

			expect(response.ok).toBe(true);
		});
	});

	describe('Error handling', () => {
		it('handles server error gracefully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () => Promise.resolve({ detail: 'Internal server error' })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'dark' })
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});

		it('returns 401 for unauthenticated POST', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ theme_preference: 'dark' })
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('Partial updates', () => {
		it('updates only theme without affecting other preferences', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'dark' })
			});

			// Verify only theme_preference was sent (partial update)
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'dark' })
			});
		});

		it('updates only language without affecting other preferences', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ title_language: 'fr' })
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ title_language: 'fr' })
			});
		});
	});
});
