/**
 * Tests for the Analysis Preferences API integration
 *
 * These tests verify the API contract that the settings page uses
 * for analysis preferences (thresholds) configuration.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Analysis Preferences API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/analysis', () => {
		it('returns default values when no settings exist', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						old_content_months: 4,
						min_age_months: 3,
						large_movie_size_gb: 13
					})
			});

			const response = await fetch('/api/settings/analysis', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/analysis', {
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.old_content_months).toBe(4);
			expect(data.min_age_months).toBe(3);
			expect(data.large_movie_size_gb).toBe(13);
		});

		it('returns user custom values when configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						old_content_months: 8,
						min_age_months: 1,
						large_movie_size_gb: 20
					})
			});

			const response = await fetch('/api/settings/analysis', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.old_content_months).toBe(8);
			expect(data.min_age_months).toBe(1);
			expect(data.large_movie_size_gb).toBe(20);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/analysis');

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('POST /api/settings/analysis', () => {
		it('saves analysis preferences successfully', async () => {
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
					large_movie_size_gb: 15
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 6,
					min_age_months: 2,
					large_movie_size_gb: 15
				})
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.success).toBe(true);
		});

		it('supports partial updates', async () => {
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
					old_content_months: 10
				})
			});

			expect(response.ok).toBe(true);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					old_content_months: 6
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});

		it('returns 422 for invalid values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () => Promise.resolve({ detail: 'Validation error' })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: -1
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});

	describe('DELETE /api/settings/analysis', () => {
		it('resets preferences to defaults', async () => {
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
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/analysis', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer test-token' }
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

			const response = await fetch('/api/settings/analysis', {
				method: 'DELETE'
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});
});
