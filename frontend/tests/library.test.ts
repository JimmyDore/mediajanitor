/**
 * Tests for the Library API integration (US-22.2)
 *
 * Tests verify the API contract for fetching the complete library.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Library API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/library', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/library');

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
						total_size_formatted: '0 B',
						service_urls: null
					})
			});

			const response = await fetch('/api/library', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('returns empty list when library is empty', async () => {
			const emptyResponse = {
				items: [],
				total_count: 0,
				total_size_bytes: 0,
				total_size_formatted: '0 B',
				service_urls: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(emptyResponse)
			});

			const response = await fetch('/api/library', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items).toEqual([]);
			expect(data.total_count).toBe(0);
			expect(data.total_size_bytes).toBe(0);
		});

		it('returns library items with all required fields', async () => {
			const libraryResponse = {
				items: [
					{
						jellyfin_id: 'movie-123',
						name: 'Test Movie',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						played: true,
						last_played_date: '2024-06-15T10:00:00Z',
						date_created: '2024-01-15T10:00:00Z',
						tmdb_id: '12345'
					},
					{
						jellyfin_id: 'series-456',
						name: 'Test Series',
						media_type: 'Series',
						production_year: 2021,
						size_bytes: 50000000000,
						size_formatted: '46.6 GB',
						played: false,
						last_played_date: null,
						date_created: '2023-03-20T14:00:00Z',
						tmdb_id: '67890'
					}
				],
				total_count: 2,
				total_size_bytes: 60000000000,
				total_size_formatted: '55.9 GB',
				service_urls: {
					jellyfin_url: 'https://jellyfin.example.com',
					jellyseerr_url: 'https://jellyseerr.example.com',
					radarr_url: null,
					sonarr_url: null
				}
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(libraryResponse)
			});

			const response = await fetch('/api/library', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.total_count).toBe(2);
			expect(data.total_size_bytes).toBe(60000000000);
			expect(data.total_size_formatted).toBe('55.9 GB');

			// Check first item (movie)
			const movie = data.items[0];
			expect(movie.jellyfin_id).toBe('movie-123');
			expect(movie.name).toBe('Test Movie');
			expect(movie.media_type).toBe('Movie');
			expect(movie.production_year).toBe(2020);
			expect(movie.size_bytes).toBe(10000000000);
			expect(movie.size_formatted).toBe('9.3 GB');
			expect(movie.played).toBe(true);
			expect(movie.last_played_date).toBe('2024-06-15T10:00:00Z');
			expect(movie.date_created).toBe('2024-01-15T10:00:00Z');
			expect(movie.tmdb_id).toBe('12345');

			// Check second item (series)
			const series = data.items[1];
			expect(series.media_type).toBe('Series');
			expect(series.played).toBe(false);
			expect(series.last_played_date).toBeNull();
		});

		it('accepts type filter for movies', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'movie-1',
								name: 'Movie 1',
								media_type: 'Movie',
								production_year: 2020,
								size_bytes: 10000000000,
								size_formatted: '9.3 GB',
								played: true,
								last_played_date: '2024-06-15T10:00:00Z',
								date_created: '2024-01-15T10:00:00Z',
								tmdb_id: '12345'
							}
						],
						total_count: 1,
						total_size_bytes: 10000000000,
						total_size_formatted: '9.3 GB',
						service_urls: null
					})
			});

			const response = await fetch('/api/library?type=movie', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library?type=movie', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items[0].media_type).toBe('Movie');
		});

		it('accepts type filter for series', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'series-1',
								name: 'Series 1',
								media_type: 'Series',
								production_year: 2021,
								size_bytes: 50000000000,
								size_formatted: '46.6 GB',
								played: false,
								last_played_date: null,
								date_created: '2023-03-20T14:00:00Z',
								tmdb_id: '67890'
							}
						],
						total_count: 1,
						total_size_bytes: 50000000000,
						total_size_formatted: '46.6 GB',
						service_urls: null
					})
			});

			const response = await fetch('/api/library?type=series', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library?type=series', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items[0].media_type).toBe('Series');
		});

		it('returns service_urls for external links', async () => {
			const libraryResponse = {
				items: [],
				total_count: 0,
				total_size_bytes: 0,
				total_size_formatted: '0 B',
				service_urls: {
					jellyfin_url: 'https://jellyfin.example.com',
					jellyseerr_url: 'https://jellyseerr.example.com',
					radarr_url: 'https://radarr.example.com',
					sonarr_url: 'https://sonarr.example.com'
				}
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(libraryResponse)
			});

			const response = await fetch('/api/library', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.service_urls.jellyfin_url).toBe('https://jellyfin.example.com');
			expect(data.service_urls.jellyseerr_url).toBe('https://jellyseerr.example.com');
			expect(data.service_urls.radarr_url).toBe('https://radarr.example.com');
			expect(data.service_urls.sonarr_url).toBe('https://sonarr.example.com');
		});

		it('handles items with null optional fields', async () => {
			const libraryResponse = {
				items: [
					{
						jellyfin_id: 'movie-nulls',
						name: 'Movie With Nulls',
						media_type: 'Movie',
						production_year: null,
						size_bytes: null,
						size_formatted: 'Unknown',
						played: false,
						last_played_date: null,
						date_created: null,
						tmdb_id: null
					}
				],
				total_count: 1,
				total_size_bytes: 0,
				total_size_formatted: '0 B',
				service_urls: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(libraryResponse)
			});

			const response = await fetch('/api/library', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.production_year).toBeNull();
			expect(item.size_bytes).toBeNull();
			expect(item.last_played_date).toBeNull();
			expect(item.date_created).toBeNull();
			expect(item.tmdb_id).toBeNull();
		});

		it('includes both Movie and Series media types', async () => {
			const libraryResponse = {
				items: [
					{
						jellyfin_id: 'movie-1',
						name: 'Movie Title',
						media_type: 'Movie',
						production_year: 2020,
						size_bytes: 10000000000,
						size_formatted: '9.3 GB',
						played: true,
						last_played_date: '2024-06-15T10:00:00Z',
						date_created: '2024-01-15T10:00:00Z',
						tmdb_id: '12345'
					},
					{
						jellyfin_id: 'series-1',
						name: 'Series Title',
						media_type: 'Series',
						production_year: 2021,
						size_bytes: 50000000000,
						size_formatted: '46.6 GB',
						played: false,
						last_played_date: null,
						date_created: '2023-03-20T14:00:00Z',
						tmdb_id: '67890'
					}
				],
				total_count: 2,
				total_size_bytes: 60000000000,
				total_size_formatted: '55.9 GB',
				service_urls: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(libraryResponse)
			});

			const response = await fetch('/api/library', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const mediaTypes = data.items.map((item: { media_type: string }) => item.media_type);

			expect(mediaTypes).toContain('Movie');
			expect(mediaTypes).toContain('Series');
		});

		it('accepts sort parameter', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [],
						total_count: 0,
						total_size_bytes: 0,
						total_size_formatted: '0 B',
						service_urls: null
					})
			});

			const response = await fetch('/api/library?sort=size&order=desc', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library?sort=size&order=desc', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('accepts search parameter', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'movie-1',
								name: 'Inception',
								media_type: 'Movie',
								production_year: 2010,
								size_bytes: 15000000000,
								size_formatted: '14.0 GB',
								played: true,
								last_played_date: '2024-06-15T10:00:00Z',
								date_created: '2024-01-15T10:00:00Z',
								tmdb_id: '27205'
							}
						],
						total_count: 1,
						total_size_bytes: 15000000000,
						total_size_formatted: '14.0 GB',
						service_urls: null
					})
			});

			const response = await fetch('/api/library?search=inception', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library?search=inception', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items[0].name).toBe('Inception');
		});

		it('accepts watched filter', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'movie-1',
								name: 'Watched Movie',
								media_type: 'Movie',
								production_year: 2020,
								size_bytes: 10000000000,
								size_formatted: '9.3 GB',
								played: true,
								last_played_date: '2024-06-15T10:00:00Z',
								date_created: '2024-01-15T10:00:00Z',
								tmdb_id: '12345'
							}
						],
						total_count: 1,
						total_size_bytes: 10000000000,
						total_size_formatted: '9.3 GB',
						service_urls: null
					})
			});

			const response = await fetch('/api/library?watched=true', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library?watched=true', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items[0].played).toBe(true);
		});
	});
});
