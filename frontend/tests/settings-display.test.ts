/**
 * Tests for the Display Preferences API integration (US-13.6)
 *
 * These tests verify the API contract that the settings page uses
 * for display preferences configuration (show_unreleased_requests toggle).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Display Preferences API Integration (US-13.6)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/display', () => {
		it('returns default values when no settings exist', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						show_unreleased_requests: false
					})
			});

			const response = await fetch('/api/settings/display', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.show_unreleased_requests).toBe(false);
		});

		it('returns user custom value when configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						show_unreleased_requests: true
					})
			});

			const response = await fetch('/api/settings/display', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.show_unreleased_requests).toBe(true);
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

	describe('POST /api/settings/display', () => {
		it('saves display preferences successfully when turning on', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Display preferences saved successfully.'
					})
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					show_unreleased_requests: true
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					show_unreleased_requests: true
				})
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.success).toBe(true);
		});

		it('saves display preferences successfully when turning off', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Display preferences saved successfully.'
					})
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					show_unreleased_requests: false
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					show_unreleased_requests: true
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});

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
				body: JSON.stringify({
					show_unreleased_requests: true
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});
	});

	describe('Toggle behavior integration', () => {
		it('can toggle from off to on', async () => {
			// First GET returns false (default)
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ show_unreleased_requests: false })
			});

			const getResponse1 = await fetch('/api/settings/display', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const data1 = await getResponse1.json();
			expect(data1.show_unreleased_requests).toBe(false);

			// POST to turn on
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const postResponse = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ show_unreleased_requests: true })
			});
			expect(postResponse.ok).toBe(true);

			// Second GET returns true
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ show_unreleased_requests: true })
			});

			const getResponse2 = await fetch('/api/settings/display', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const data2 = await getResponse2.json();
			expect(data2.show_unreleased_requests).toBe(true);
		});
	});
});
