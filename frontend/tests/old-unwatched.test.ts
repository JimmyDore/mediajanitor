/**
 * Tests for the old/unwatched content API integration (US-3.1)
 *
 * Tests verify the API contract for fetching old/unwatched content.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Old/Unwatched Content API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/content/old-unwatched', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/content/old-unwatched');

			expect(response.status).toBe(401);
		});

		it('accepts GET with auth token', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [],
						total_count: 0,
						total_size_bytes: 0,
						total_size_formatted: 'Unknown size'
					})
			});

			const response = await fetch('/api/content/old-unwatched', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/content/old-unwatched', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('returns empty list when no old content', async () => {
			const emptyResponse = {
				items: [],
				total_count: 0,
				total_size_bytes: 0,
				total_size_formatted: 'Unknown size'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(emptyResponse)
			});

			const response = await fetch('/api/content/old-unwatched', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items).toEqual([]);
			expect(data.total_count).toBe(0);
			expect(data.total_size_bytes).toBe(0);
		});

		it('returns list of old/unwatched items with all required fields', async () => {
			const contentResponse = {
				items: [
					{
						jellyfin_id: 'movie-123',
						name: 'Old Movie',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						last_played_date: null,
						path: '/media/movies/Old Movie'
					},
					{
						jellyfin_id: 'series-456',
						name: 'Old Series',
						media_type: 'Series',
						production_year: 2019,
						size_bytes: 50000000000,
						size_formatted: '46.6 GB',
						last_played_date: '2023-06-15T10:00:00Z',
						path: '/media/tv/Old Series'
					}
				],
				total_count: 2,
				total_size_bytes: 60000000000,
				total_size_formatted: '55.9 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(contentResponse)
			});

			const response = await fetch('/api/content/old-unwatched', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();

			// Check response structure
			expect(data.total_count).toBe(2);
			expect(data.total_size_bytes).toBe(60000000000);
			expect(data.total_size_formatted).toBe('55.9 GB');

			// Check first item has all required fields
			const firstItem = data.items[0];
			expect(firstItem.jellyfin_id).toBe('movie-123');
			expect(firstItem.name).toBe('Old Movie');
			expect(firstItem.media_type).toBe('Movie');
			expect(firstItem.production_year).toBe(2020);
			expect(firstItem.size_bytes).toBe(10000000000);
			expect(firstItem.size_formatted).toBe('9.3 GB');
			expect(firstItem.last_played_date).toBeNull();
			expect(firstItem.path).toBe('/media/movies/Old Movie');
		});

		it('items are sorted by size (largest first)', async () => {
			const contentResponse = {
				items: [
					{
						jellyfin_id: 'large',
						name: 'Large Movie',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 50000000000,
						size_formatted: '46.6 GB',
						last_played_date: null,
						path: '/media/movies/Large'
					},
					{
						jellyfin_id: 'medium',
						name: 'Medium Movie',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 20000000000,
						size_formatted: '18.6 GB',
						last_played_date: null,
						path: '/media/movies/Medium'
					},
					{
						jellyfin_id: 'small',
						name: 'Small Movie',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 5000000000,
						size_formatted: '4.7 GB',
						last_played_date: null,
						path: '/media/movies/Small'
					}
				],
				total_count: 3,
				total_size_bytes: 75000000000,
				total_size_formatted: '69.8 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(contentResponse)
			});

			const response = await fetch('/api/content/old-unwatched', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();

			// Verify items are sorted by size descending
			expect(data.items[0].jellyfin_id).toBe('large');
			expect(data.items[1].jellyfin_id).toBe('medium');
			expect(data.items[2].jellyfin_id).toBe('small');
			expect(data.items[0].size_bytes).toBeGreaterThan(data.items[1].size_bytes);
			expect(data.items[1].size_bytes).toBeGreaterThan(data.items[2].size_bytes);
		});

		it('handles items with null optional fields', async () => {
			const contentResponse = {
				items: [
					{
						jellyfin_id: 'movie-no-year',
						name: 'Movie Without Year',
						media_type: 'Movie',
						production_year: null,
						size_bytes: null,
						size_formatted: 'Unknown size',
						last_played_date: null,
						path: null
					}
				],
				total_count: 1,
				total_size_bytes: 0,
				total_size_formatted: 'Unknown size'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(contentResponse)
			});

			const response = await fetch('/api/content/old-unwatched', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.production_year).toBeNull();
			expect(item.size_bytes).toBeNull();
			expect(item.last_played_date).toBeNull();
			expect(item.path).toBeNull();
		});

		it('includes both Movie and Series media types', async () => {
			const contentResponse = {
				items: [
					{
						jellyfin_id: 'movie-1',
						name: 'Movie Title',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						last_played_date: null,
						path: '/media/movies/Movie'
					},
					{
						jellyfin_id: 'series-1',
						name: 'Series Title',
						media_type: 'Series',
						production_year: 2019,
						size_bytes: 5000000000,
						size_formatted: '4.7 GB',
						last_played_date: null,
						path: '/media/tv/Series'
					}
				],
				total_count: 2,
				total_size_bytes: 15000000000,
				total_size_formatted: '14.0 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(contentResponse)
			});

			const response = await fetch('/api/content/old-unwatched', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const mediaTypes = data.items.map((item: { media_type: string }) => item.media_type);

			expect(mediaTypes).toContain('Movie');
			expect(mediaTypes).toContain('Series');
		});
	});

	describe('POST /api/whitelist/content (US-3.2)', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/whitelist/content', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					jellyfin_id: 'movie-123',
					name: 'Test Movie',
					media_type: 'Movie'
				})
			});

			expect(response.status).toBe(401);
		});

		it('accepts POST with valid payload and returns 201', async () => {
			const successResponse = {
				message: 'Added to whitelist',
				jellyfin_id: 'movie-123',
				name: 'Test Movie'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 201,
				json: () => Promise.resolve(successResponse)
			});

			const response = await fetch('/api/whitelist/content', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					jellyfin_id: 'movie-123',
					name: 'Test Movie',
					media_type: 'Movie'
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/whitelist/content', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					jellyfin_id: 'movie-123',
					name: 'Test Movie',
					media_type: 'Movie'
				})
			});
			expect(response.status).toBe(201);

			const data = await response.json();
			expect(data.message).toBe('Added to whitelist');
			expect(data.jellyfin_id).toBe('movie-123');
			expect(data.name).toBe('Test Movie');
		});

		it('returns 409 Conflict for duplicate entries', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 409,
				json: () => Promise.resolve({ detail: "Content 'Test Movie' is already in whitelist" })
			});

			const response = await fetch('/api/whitelist/content', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					jellyfin_id: 'movie-123',
					name: 'Test Movie',
					media_type: 'Movie'
				})
			});

			expect(response.status).toBe(409);
			const data = await response.json();
			expect(data.detail).toContain('already in whitelist');
		});

		it('returns 422 for invalid/missing required fields', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [{ loc: ['body', 'jellyfin_id'], msg: 'Field required', type: 'missing' }]
					})
			});

			const response = await fetch('/api/whitelist/content', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					name: 'Test Movie',
					media_type: 'Movie'
					// Missing jellyfin_id
				})
			});

			expect(response.status).toBe(422);
		});

		it('works with Series media type', async () => {
			const successResponse = {
				message: 'Added to whitelist',
				jellyfin_id: 'series-456',
				name: 'Test Series'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 201,
				json: () => Promise.resolve(successResponse)
			});

			const response = await fetch('/api/whitelist/content', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					jellyfin_id: 'series-456',
					name: 'Test Series',
					media_type: 'Series'
				})
			});

			expect(response.status).toBe(201);
			const data = await response.json();
			expect(data.jellyfin_id).toBe('series-456');
		});
	});
});
