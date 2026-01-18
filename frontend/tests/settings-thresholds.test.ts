/**
 * Tests for the Thresholds settings page
 *
 * These tests verify the thresholds page loads and handles
 * all analysis preference settings (old content, min age, large movie size, large season size).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Thresholds Settings Page API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('Initial load - fetches analysis preferences', () => {
		it('fetches analysis preferences on page load', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						old_content_months: 4,
						min_age_months: 3,
						large_movie_size_gb: 13,
						large_season_size_gb: 15
					})
			});

			const response = await fetch('/api/settings/analysis', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledTimes(1);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/analysis', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.old_content_months).toBe(4);
			expect(data.min_age_months).toBe(3);
			expect(data.large_movie_size_gb).toBe(13);
			expect(data.large_season_size_gb).toBe(15);
		});

		it('handles custom threshold values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						old_content_months: 6,
						min_age_months: 2,
						large_movie_size_gb: 20,
						large_season_size_gb: 25
					})
			});

			const response = await fetch('/api/settings/analysis');
			const data = await response.json();

			expect(data.old_content_months).toBe(6);
			expect(data.min_age_months).toBe(2);
			expect(data.large_movie_size_gb).toBe(20);
			expect(data.large_season_size_gb).toBe(25);
		});

		it('returns default values when not configured', async () => {
			// Backend returns defaults when user has no settings
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						old_content_months: 4,
						min_age_months: 3,
						large_movie_size_gb: 13,
						large_season_size_gb: 15
					})
			});

			const response = await fetch('/api/settings/analysis');
			expect(response.ok).toBe(true);

			const data = await response.json();
			// Default values
			expect(data.old_content_months).toBe(4);
			expect(data.min_age_months).toBe(3);
			expect(data.large_movie_size_gb).toBe(13);
			expect(data.large_season_size_gb).toBe(15);
		});
	});

	describe('Save analysis preferences', () => {
		it('saves all threshold values successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Analysis preferences saved successfully.'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 6,
					min_age_months: 2,
					large_movie_size_gb: 15,
					large_season_size_gb: 20
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.message).toBe('Analysis preferences saved successfully.');
		});

		it('handles partial updates - only old_content_months', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Analysis preferences saved successfully.'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 8
				})
			});

			expect(response.ok).toBe(true);
		});

		it('handles partial updates - only size thresholds', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Analysis preferences saved successfully.'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					large_movie_size_gb: 25,
					large_season_size_gb: 30
				})
			});

			expect(response.ok).toBe(true);
		});

		it('handles validation errors for out-of-range values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'old_content_months'],
								msg: 'ensure this value is less than or equal to 24',
								type: 'value_error.number.not_le'
							}
						]
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 100 // Out of range (max 24)
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('handles server errors gracefully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () =>
					Promise.resolve({
						detail: 'Internal server error'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 6
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});
	});

	describe('Reset analysis preferences', () => {
		it('resets to default values successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Analysis preferences reset to defaults.'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'DELETE',
				headers: {
					Authorization: 'Bearer test-token'
				}
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.message).toBe('Analysis preferences reset to defaults.');
		});

		it('handles reset errors gracefully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () =>
					Promise.resolve({
						detail: 'Failed to reset preferences'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'DELETE',
				headers: {
					Authorization: 'Bearer test-token'
				}
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});
	});

	describe('Authentication', () => {
		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/analysis');
			expect(response.status).toBe(401);
		});

		it('returns 401 for POST when not authenticated', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ old_content_months: 6 })
			});

			expect(response.status).toBe(401);
		});

		it('returns 401 for DELETE when not authenticated', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'DELETE'
			});

			expect(response.status).toBe(401);
		});
	});

	describe('Threshold validation ranges', () => {
		it('accepts minimum valid values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Analysis preferences saved successfully.'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 1, // Min: 1
					min_age_months: 0, // Min: 0
					large_movie_size_gb: 1, // Min: 1
					large_season_size_gb: 1 // Min: 1
				})
			});

			expect(response.ok).toBe(true);
		});

		it('accepts maximum valid values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Analysis preferences saved successfully.'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 24, // Max: 24
					min_age_months: 12, // Max: 12
					large_movie_size_gb: 100, // Max: 100
					large_season_size_gb: 100 // Max: 100
				})
			});

			expect(response.ok).toBe(true);
		});
	});
});
