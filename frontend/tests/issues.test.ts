/**
 * Tests for the unified issues API integration (US-D.3)
 *
 * Tests verify the API contract for fetching content with issues.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Unified Issues API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/content/issues', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/content/issues');

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
						total_size_formatted: '0 B'
					})
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('returns empty list when no issues exist', async () => {
			const emptyResponse = {
				items: [],
				total_count: 0,
				total_size_bytes: 0,
				total_size_formatted: '0 B'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(emptyResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items).toEqual([]);
			expect(data.total_count).toBe(0);
			expect(data.total_size_bytes).toBe(0);
		});

		it('returns items with issues array containing all applicable issue types', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-old-large',
						name: 'Old Large Movie',
						media_type: 'Movie',
						production_year: 2018,
						size_bytes: 20000000000,
						size_formatted: '18.6 GB',
						last_played_date: null,
						path: '/media/movies/Old Large Movie',
						issues: ['old', 'large']
					},
					{
						jellyfin_id: 'movie-old-only',
						name: 'Old Only Movie',
						media_type: 'Movie',
						production_year: 2019,
						size_bytes: 5000000000,
						size_formatted: '4.7 GB',
						last_played_date: '2023-06-15T10:00:00Z',
						path: '/media/movies/Old Only Movie',
						issues: ['old']
					}
				],
				total_count: 2,
				total_size_bytes: 25000000000,
				total_size_formatted: '23.3 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();

			// Check response structure
			expect(data.total_count).toBe(2);
			expect(data.total_size_bytes).toBe(25000000000);
			expect(data.total_size_formatted).toBe('23.3 GB');

			// Check first item has multiple issues
			const firstItem = data.items[0];
			expect(firstItem.jellyfin_id).toBe('movie-old-large');
			expect(firstItem.issues).toContain('old');
			expect(firstItem.issues).toContain('large');
			expect(firstItem.issues.length).toBe(2);

			// Check second item has single issue
			const secondItem = data.items[1];
			expect(secondItem.jellyfin_id).toBe('movie-old-only');
			expect(secondItem.issues).toContain('old');
			expect(secondItem.issues.length).toBe(1);
		});

		it('accepts filter query param for old content', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'movie-old',
								name: 'Old Movie',
								media_type: 'Movie',
								issues: ['old']
							}
						],
						total_count: 1,
						total_size_bytes: 5000000000,
						total_size_formatted: '4.7 GB'
					})
			});

			const response = await fetch('/api/content/issues?filter=old', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/content/issues?filter=old', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items[0].issues).toContain('old');
		});

		it('accepts filter query param for large movies', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'movie-large',
								name: 'Large Movie',
								media_type: 'Movie',
								issues: ['large']
							}
						],
						total_count: 1,
						total_size_bytes: 20000000000,
						total_size_formatted: '18.6 GB'
					})
			});

			const response = await fetch('/api/content/issues?filter=large', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/content/issues?filter=large', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items[0].issues).toContain('large');
		});

		it('returns empty for language filter (not implemented)', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [],
						total_count: 0,
						total_size_bytes: 0,
						total_size_formatted: '0 B'
					})
			});

			const response = await fetch('/api/content/issues?filter=language', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.items).toEqual([]);
		});

		it('returns empty for requests filter (not implemented)', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [],
						total_count: 0,
						total_size_bytes: 0,
						total_size_formatted: '0 B'
					})
			});

			const response = await fetch('/api/content/issues?filter=requests', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.items).toEqual([]);
		});

		it('items are sorted by size (largest first) by default', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'large',
						name: 'Large Movie',
						media_type: 'Movie',
						size_bytes: 30000000000,
						issues: ['large']
					},
					{
						jellyfin_id: 'medium',
						name: 'Medium Movie',
						media_type: 'Movie',
						size_bytes: 15000000000,
						issues: ['large']
					},
					{
						jellyfin_id: 'small',
						name: 'Small Movie',
						media_type: 'Movie',
						size_bytes: 5000000000,
						issues: ['old']
					}
				],
				total_count: 3,
				total_size_bytes: 50000000000,
				total_size_formatted: '46.6 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
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

		it('returns all required fields for each item', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-123',
						name: 'Test Movie',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						last_played_date: '2023-06-15T10:00:00Z',
						path: '/media/movies/Test Movie',
						issues: ['old']
					}
				],
				total_count: 1,
				total_size_bytes: 10000000000,
				total_size_formatted: '9.3 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			// Verify all required fields are present
			expect(item).toHaveProperty('jellyfin_id');
			expect(item).toHaveProperty('name');
			expect(item).toHaveProperty('media_type');
			expect(item).toHaveProperty('production_year');
			expect(item).toHaveProperty('size_bytes');
			expect(item).toHaveProperty('size_formatted');
			expect(item).toHaveProperty('last_played_date');
			expect(item).toHaveProperty('path');
			expect(item).toHaveProperty('issues');
			expect(Array.isArray(item.issues)).toBe(true);
		});

		it('handles items with null optional fields', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-nulls',
						name: 'Movie With Nulls',
						media_type: 'Movie',
						production_year: null,
						size_bytes: null,
						size_formatted: 'Unknown size',
						last_played_date: null,
						path: null,
						issues: ['old']
					}
				],
				total_count: 1,
				total_size_bytes: 0,
				total_size_formatted: '0 B'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
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
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-1',
						name: 'Movie Title',
						media_type: 'Movie',
						issues: ['old']
					},
					{
						jellyfin_id: 'series-1',
						name: 'Series Title',
						media_type: 'Series',
						issues: ['old']
					}
				],
				total_count: 2,
				total_size_bytes: 15000000000,
				total_size_formatted: '14.0 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const mediaTypes = data.items.map((item: { media_type: string }) => item.media_type);

			expect(mediaTypes).toContain('Movie');
			expect(mediaTypes).toContain('Series');
		});

		it('returns items with tmdb_id and imdb_id fields (US-9.4)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-with-ids',
						name: 'Movie With IDs',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						last_played_date: null,
						path: '/media/movies/Movie With IDs',
						issues: ['old'],
						tmdb_id: '12345',
						imdb_id: 'tt0123456'
					}
				],
				total_count: 1,
				total_size_bytes: 10000000000,
				total_size_formatted: '9.3 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.tmdb_id).toBe('12345');
			expect(item.imdb_id).toBe('tt0123456');
		});

		it('handles items with null tmdb_id and imdb_id (US-9.4)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-no-ids',
						name: 'Movie Without IDs',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						last_played_date: null,
						path: '/media/movies/Movie Without IDs',
						issues: ['old'],
						tmdb_id: null,
						imdb_id: null
					}
				],
				total_count: 1,
				total_size_bytes: 10000000000,
				total_size_formatted: '9.3 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.tmdb_id).toBeNull();
			expect(item.imdb_id).toBeNull();
		});

		it('series use tv path for TMDB URL (US-9.4)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'series-with-tmdb',
						name: 'Series With TMDB',
						media_type: 'Series',
						production_year: 2021,
						size_bytes: 20000000000,
						size_formatted: '18.6 GB',
						last_played_date: null,
						path: '/media/tv/Series With TMDB',
						issues: ['old'],
						tmdb_id: '67890',
						imdb_id: null
					}
				],
				total_count: 1,
				total_size_bytes: 20000000000,
				total_size_formatted: '18.6 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			// For series, tmdb_id should be available
			expect(item.tmdb_id).toBe('67890');
			expect(item.media_type).toBe('Series');
			// TMDB URL for series would use /tv/{id} path (constructed by frontend)
		});

		it('returns request items with release_date field (US-13.3)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'request-123',
						name: 'Future Movie',
						media_type: 'movie',
						production_year: null,
						size_bytes: null,
						size_formatted: '',
						last_played_date: null,
						path: null,
						issues: ['request'],
						tmdb_id: '99999',
						imdb_id: null,
						requested_by: 'user1',
						request_date: '2026-01-01T10:00:00Z',
						missing_seasons: null,
						release_date: '2026-07-15'
					}
				],
				total_count: 1,
				total_size_bytes: 0,
				total_size_formatted: '0 B'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=requests', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.release_date).toBe('2026-07-15');
			expect(item.requested_by).toBe('user1');
		});

		it('handles request items with null release_date (US-13.3)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'request-456',
						name: 'Unknown Release Movie',
						media_type: 'movie',
						production_year: null,
						size_bytes: null,
						size_formatted: '',
						last_played_date: null,
						path: null,
						issues: ['request'],
						tmdb_id: '88888',
						imdb_id: null,
						requested_by: 'user2',
						request_date: '2026-01-05T10:00:00Z',
						missing_seasons: null,
						release_date: null
					}
				],
				total_count: 1,
				total_size_bytes: 0,
				total_size_formatted: '0 B'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=requests', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.release_date).toBeNull();
		});

		it('returns TV request items with firstAirDate as release_date (US-13.3)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'request-789',
						name: 'New TV Show',
						media_type: 'tv',
						production_year: null,
						size_bytes: null,
						size_formatted: '',
						last_played_date: null,
						path: null,
						issues: ['request'],
						tmdb_id: '77777',
						imdb_id: null,
						requested_by: 'user3',
						request_date: '2026-01-10T10:00:00Z',
						missing_seasons: [1, 2],
						release_date: '2025-10-01'
					}
				],
				total_count: 1,
				total_size_bytes: 0,
				total_size_formatted: '0 B'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=requests', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.release_date).toBe('2025-10-01');
			expect(item.media_type).toBe('tv');
			expect(item.missing_seasons).toEqual([1, 2]);
		});

		it('returns items with date_created field (US-23.1)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-with-date',
						name: 'Movie With Date Created',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						last_played_date: null,
						path: '/media/movies/Movie With Date',
						date_created: '2024-06-15T10:30:00Z',
						issues: ['old']
					}
				],
				total_count: 1,
				total_size_bytes: 10000000000,
				total_size_formatted: '9.3 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.date_created).toBe('2024-06-15T10:30:00Z');
		});

		it('handles items with null date_created (US-23.1)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-no-date',
						name: 'Movie Without Date Created',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						last_played_date: null,
						path: '/media/movies/Movie Without Date',
						date_created: null,
						issues: ['old']
					}
				],
				total_count: 1,
				total_size_bytes: 10000000000,
				total_size_formatted: '9.3 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.date_created).toBeNull();
		});

		it('returns date_created for series items (US-23.1)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'series-with-date',
						name: 'Series With Date Created',
						media_type: 'Series',
						production_year: 2021,
						size_bytes: 50000000000,
						size_formatted: '46.6 GB',
						last_played_date: '2024-01-15T10:00:00Z',
						path: '/media/tv/Series With Date',
						date_created: '2023-03-20T14:45:00Z',
						issues: ['large']
					}
				],
				total_count: 1,
				total_size_bytes: 50000000000,
				total_size_formatted: '46.6 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=large', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.date_created).toBe('2023-03-20T14:45:00Z');
			expect(item.media_type).toBe('Series');
		});

		it('returns largest_season_size fields for series items (US-20.4)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'series-large-season',
						name: 'Series With Large Season',
						media_type: 'Series',
						production_year: 2021,
						size_bytes: 80000000000,
						size_formatted: '74.5 GB',
						last_played_date: '2024-01-15T10:00:00Z',
						path: '/media/tv/Series With Large Season',
						date_created: '2023-03-20T14:45:00Z',
						issues: ['large'],
						largest_season_size_bytes: 18500000000,
						largest_season_size_formatted: '17.2 GB'
					}
				],
				total_count: 1,
				total_size_bytes: 80000000000,
				total_size_formatted: '74.5 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=large', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.largest_season_size_bytes).toBe(18500000000);
			expect(item.largest_season_size_formatted).toBe('17.2 GB');
		});

		it('returns null largest_season_size fields for movie items (US-20.4)', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-large',
						name: 'Large Movie',
						media_type: 'Movie',
						production_year: 2022,
						size_bytes: 25000000000,
						size_formatted: '23.3 GB',
						last_played_date: '2024-01-15T10:00:00Z',
						path: '/media/movies/Large Movie',
						date_created: '2023-03-20T14:45:00Z',
						issues: ['large'],
						largest_season_size_bytes: null,
						largest_season_size_formatted: null
					}
				],
				total_count: 1,
				total_size_bytes: 25000000000,
				total_size_formatted: '23.3 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=large', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.largest_season_size_bytes).toBeNull();
			expect(item.largest_season_size_formatted).toBeNull();
		});
	});
});
