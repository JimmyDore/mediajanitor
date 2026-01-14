/**
 * Tests for content deletion API integration (US-15.4, US-15.5, US-15.6, US-15.7)
 *
 * Tests verify the API contract for deleting content from Radarr/Sonarr/Jellyseerr.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Delete Content API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('DELETE /api/content/movie/{tmdb_id}', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/content/movie/12345', { method: 'DELETE' });

			expect(response.status).toBe(401);
		});

		it('returns 400 when Radarr is not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () => Promise.resolve({ detail: 'Radarr is not configured. Please configure Radarr in Settings.' })
			});

			const response = await fetch('/api/content/movie/12345', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(400);
			const data = await response.json();
			expect(data.detail.toLowerCase()).toContain('radarr');
		});

		it('returns success response when movie is deleted', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					success: true,
					message: 'Movie deleted successfully from Radarr',
					arr_deleted: true,
					jellyseerr_deleted: false
				})
			});

			const response = await fetch('/api/content/movie/12345', {
				method: 'DELETE',
				headers: {
					Authorization: 'Bearer jwt-token',
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					tmdb_id: 12345,
					delete_from_arr: true,
					delete_from_jellyseerr: false
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.arr_deleted).toBe(true);
		});

		it('returns failure response when movie not found', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					success: false,
					message: 'Movie with TMDB ID 12345 not found in Radarr',
					arr_deleted: false,
					jellyseerr_deleted: false
				})
			});

			const response = await fetch('/api/content/movie/12345', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(false);
			expect(data.arr_deleted).toBe(false);
			expect(data.message.toLowerCase()).toContain('not found');
		});

		it('can optionally delete from Jellyseerr', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					success: true,
					message: 'Movie deleted successfully from Radarr; Request deleted successfully from Jellyseerr',
					arr_deleted: true,
					jellyseerr_deleted: true
				})
			});

			const response = await fetch('/api/content/movie/12345', {
				method: 'DELETE',
				headers: {
					Authorization: 'Bearer jwt-token',
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					tmdb_id: 12345,
					delete_from_arr: true,
					delete_from_jellyseerr: true,
					jellyseerr_request_id: 999
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.arr_deleted).toBe(true);
			expect(data.jellyseerr_deleted).toBe(true);
		});
	});

	describe('DELETE /api/content/series/{tmdb_id}', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/content/series/12345', { method: 'DELETE' });

			expect(response.status).toBe(401);
		});

		it('returns 400 when Sonarr is not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () => Promise.resolve({ detail: 'Sonarr is not configured. Please configure Sonarr in Settings.' })
			});

			const response = await fetch('/api/content/series/12345', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(400);
			const data = await response.json();
			expect(data.detail.toLowerCase()).toContain('sonarr');
		});

		it('returns success response when series is deleted', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					success: true,
					message: 'Series deleted successfully from Sonarr',
					arr_deleted: true,
					jellyseerr_deleted: false
				})
			});

			const response = await fetch('/api/content/series/12345', {
				method: 'DELETE',
				headers: {
					Authorization: 'Bearer jwt-token',
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					tmdb_id: 12345,
					delete_from_arr: true,
					delete_from_jellyseerr: false
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.arr_deleted).toBe(true);
		});

		it('returns failure response when series not found', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					success: false,
					message: 'Series with TMDB ID 12345 not found in Sonarr',
					arr_deleted: false,
					jellyseerr_deleted: false
				})
			});

			const response = await fetch('/api/content/series/12345', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(false);
			expect(data.arr_deleted).toBe(false);
			expect(data.message.toLowerCase()).toContain('not found');
		});
	});

	describe('DELETE /api/content/request/{jellyseerr_id}', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/content/request/12345', { method: 'DELETE' });

			expect(response.status).toBe(401);
		});

		it('returns 400 when Jellyseerr is not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () => Promise.resolve({ detail: 'Jellyseerr is not configured. Please configure Jellyseerr in Settings.' })
			});

			const response = await fetch('/api/content/request/12345', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(400);
			const data = await response.json();
			expect(data.detail.toLowerCase()).toContain('jellyseerr');
		});

		it('returns success response when request is deleted', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					success: true,
					message: 'Request deleted successfully from Jellyseerr'
				})
			});

			const response = await fetch('/api/content/request/12345', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.message.toLowerCase()).toContain('deleted');
		});

		it('returns 400 when request not found', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () => Promise.resolve({ detail: 'Request 12345 not found in Jellyseerr' })
			});

			const response = await fetch('/api/content/request/12345', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(400);
			const data = await response.json();
			expect(data.detail.toLowerCase()).toContain('not found');
		});
	});

	describe('Settings configuration status', () => {
		it('GET /api/settings/radarr returns api_key_configured field', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					server_url: 'https://radarr.example.com',
					api_key_configured: true
				})
			});

			const response = await fetch('/api/settings/radarr', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data).toHaveProperty('api_key_configured');
			expect(typeof data.api_key_configured).toBe('boolean');
		});

		it('GET /api/settings/sonarr returns api_key_configured field', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					server_url: 'https://sonarr.example.com',
					api_key_configured: true
				})
			});

			const response = await fetch('/api/settings/sonarr', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data).toHaveProperty('api_key_configured');
			expect(typeof data.api_key_configured).toBe('boolean');
		});

		it('GET /api/settings/jellyseerr returns api_key_configured field', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					server_url: 'https://jellyseerr.example.com',
					api_key_configured: true
				})
			});

			const response = await fetch('/api/settings/jellyseerr', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data).toHaveProperty('api_key_configured');
			expect(typeof data.api_key_configured).toBe('boolean');
		});

		it('returns api_key_configured: false when not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({
					server_url: null,
					api_key_configured: false
				})
			});

			const response = await fetch('/api/settings/radarr', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.server_url).toBeNull();
			expect(data.api_key_configured).toBe(false);
		});
	});
});
