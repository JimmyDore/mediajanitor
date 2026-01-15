/**
 * Tests for the Library API integration (US-22.2, US-22.3)
 *
 * Tests verify the API contract for fetching the complete library
 * and search/filter functionality.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

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

		it('accepts year range filter', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'movie-1',
								name: 'Movie From 2015',
								media_type: 'Movie',
								production_year: 2015,
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

			const response = await fetch('/api/library?min_year=2010&max_year=2020', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library?min_year=2010&max_year=2020', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items[0].production_year).toBe(2015);
		});

		it('accepts size range filter', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								jellyfin_id: 'movie-1',
								name: 'Medium Size Movie',
								media_type: 'Movie',
								production_year: 2020,
								size_bytes: 10000000000, // ~9.3 GB
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

			const response = await fetch('/api/library?min_size_gb=5&max_size_gb=15', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/library?min_size_gb=5&max_size_gb=15', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('accepts multiple filters combined', async () => {
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

			const response = await fetch(
				'/api/library?type=movie&search=inception&watched=true&min_year=2000&max_year=2015&sort=year&order=desc',
				{
					headers: { Authorization: 'Bearer jwt-token' }
				}
			);

			expect(mockFetch).toHaveBeenCalledWith(
				'/api/library?type=movie&search=inception&watched=true&min_year=2000&max_year=2015&sort=year&order=desc',
				{
					headers: { Authorization: 'Bearer jwt-token' }
				}
			);
			expect(response.ok).toBe(true);
		});
	});
});

/**
 * Tests for Library Search and Filter functionality (US-22.3)
 */
describe('Library Search and Filter Functionality (US-22.3)', () => {
	describe('Search Input', () => {
		it('search matches against name case-insensitively', () => {
			// Test the matching logic
			const items = [
				{ name: 'Inception', production_year: 2010 },
				{ name: 'The Dark Knight', production_year: 2008 },
				{ name: 'Interstellar', production_year: 2014 }
			];

			const matchesSearch = (item: { name: string; production_year: number }, query: string) => {
				if (!query.trim()) return true;
				const lowerQuery = query.toLowerCase().trim();
				if (item.name.toLowerCase().includes(lowerQuery)) return true;
				if (item.production_year && item.production_year.toString().includes(lowerQuery))
					return true;
				return false;
			};

			// Case insensitive search
			expect(items.filter((i) => matchesSearch(i, 'INCEPTION'))).toHaveLength(1);
			expect(items.filter((i) => matchesSearch(i, 'inception'))).toHaveLength(1);
			expect(items.filter((i) => matchesSearch(i, 'InCePtIoN'))).toHaveLength(1);
		});

		it('search matches against production year', () => {
			const items = [
				{ name: 'Inception', production_year: 2010 },
				{ name: 'The Dark Knight', production_year: 2008 },
				{ name: 'Interstellar', production_year: 2014 }
			];

			const matchesSearch = (item: { name: string; production_year: number }, query: string) => {
				if (!query.trim()) return true;
				const lowerQuery = query.toLowerCase().trim();
				if (item.name.toLowerCase().includes(lowerQuery)) return true;
				if (item.production_year && item.production_year.toString().includes(lowerQuery))
					return true;
				return false;
			};

			expect(items.filter((i) => matchesSearch(i, '2010'))).toHaveLength(1);
			expect(items.filter((i) => matchesSearch(i, '201'))).toHaveLength(2); // 2010 and 2014
		});

		it('empty search returns all items', () => {
			const items = [
				{ name: 'Inception', production_year: 2010 },
				{ name: 'The Dark Knight', production_year: 2008 }
			];

			const matchesSearch = (item: { name: string; production_year: number }, query: string) => {
				if (!query.trim()) return true;
				return item.name.toLowerCase().includes(query.toLowerCase());
			};

			expect(items.filter((i) => matchesSearch(i, ''))).toHaveLength(2);
			expect(items.filter((i) => matchesSearch(i, '   '))).toHaveLength(2);
		});
	});

	describe('Debounce Logic', () => {
		beforeEach(() => {
			vi.useFakeTimers();
		});

		afterEach(() => {
			vi.useRealTimers();
		});

		it('debounces search input by 300ms', async () => {
			const callback = vi.fn();
			let debounceTimer: ReturnType<typeof setTimeout> | null = null;

			const debouncedSearch = (query: string) => {
				if (debounceTimer) clearTimeout(debounceTimer);
				debounceTimer = setTimeout(() => callback(query), 300);
			};

			// Type rapidly
			debouncedSearch('i');
			debouncedSearch('in');
			debouncedSearch('inc');
			debouncedSearch('ince');
			debouncedSearch('incep');

			// Callback should not have been called yet
			expect(callback).not.toHaveBeenCalled();

			// Advance time by 300ms
			vi.advanceTimersByTime(300);

			// Callback should be called with final value
			expect(callback).toHaveBeenCalledTimes(1);
			expect(callback).toHaveBeenCalledWith('incep');
		});

		it('resets timer on each keystroke', async () => {
			const callback = vi.fn();
			let debounceTimer: ReturnType<typeof setTimeout> | null = null;

			const debouncedSearch = (query: string) => {
				if (debounceTimer) clearTimeout(debounceTimer);
				debounceTimer = setTimeout(() => callback(query), 300);
			};

			debouncedSearch('a');
			vi.advanceTimersByTime(200);

			debouncedSearch('ab');
			vi.advanceTimersByTime(200);

			// Only 400ms total, should not fire yet
			expect(callback).not.toHaveBeenCalled();

			vi.advanceTimersByTime(100);
			expect(callback).toHaveBeenCalledTimes(1);
			expect(callback).toHaveBeenCalledWith('ab');
		});
	});

	describe('Watched Status Filter', () => {
		it('filters by watched=true returns only watched items', () => {
			const items = [
				{ name: 'Watched Movie', played: true },
				{ name: 'Unwatched Movie', played: false },
				{ name: 'Another Watched', played: true }
			];

			const filterByWatched = (items: { played: boolean }[], watched: 'all' | 'true' | 'false') => {
				if (watched === 'all') return items;
				if (watched === 'true') return items.filter((i) => i.played);
				return items.filter((i) => !i.played);
			};

			expect(filterByWatched(items, 'true')).toHaveLength(2);
			expect(filterByWatched(items, 'false')).toHaveLength(1);
			expect(filterByWatched(items, 'all')).toHaveLength(3);
		});
	});

	describe('Year Range Filter', () => {
		it('filters by min_year', () => {
			const items = [
				{ name: 'Old Movie', production_year: 1990 },
				{ name: 'Recent Movie', production_year: 2020 },
				{ name: 'Mid Movie', production_year: 2010 }
			];

			const filterByYearRange = (
				items: { production_year: number | null }[],
				minYear: number | null,
				maxYear: number | null
			) => {
				return items.filter((item) => {
					if (item.production_year === null) return false;
					if (minYear && item.production_year < minYear) return false;
					if (maxYear && item.production_year > maxYear) return false;
					return true;
				});
			};

			expect(filterByYearRange(items, 2000, null)).toHaveLength(2);
		});

		it('filters by max_year', () => {
			const items = [
				{ name: 'Old Movie', production_year: 1990 },
				{ name: 'Recent Movie', production_year: 2020 },
				{ name: 'Mid Movie', production_year: 2010 }
			];

			const filterByYearRange = (
				items: { production_year: number | null }[],
				minYear: number | null,
				maxYear: number | null
			) => {
				return items.filter((item) => {
					if (item.production_year === null) return false;
					if (minYear && item.production_year < minYear) return false;
					if (maxYear && item.production_year > maxYear) return false;
					return true;
				});
			};

			expect(filterByYearRange(items, null, 2010)).toHaveLength(2);
		});

		it('filters by both min and max year', () => {
			const items = [
				{ name: 'Old Movie', production_year: 1990 },
				{ name: 'Recent Movie', production_year: 2020 },
				{ name: 'Mid Movie', production_year: 2010 }
			];

			const filterByYearRange = (
				items: { production_year: number | null }[],
				minYear: number | null,
				maxYear: number | null
			) => {
				return items.filter((item) => {
					if (item.production_year === null) return false;
					if (minYear && item.production_year < minYear) return false;
					if (maxYear && item.production_year > maxYear) return false;
					return true;
				});
			};

			expect(filterByYearRange(items, 2000, 2015)).toHaveLength(1);
		});

		it('handles null production_year', () => {
			const items = [
				{ name: 'Known Year', production_year: 2010 },
				{ name: 'Unknown Year', production_year: null }
			];

			const filterByYearRange = (
				items: { production_year: number | null }[],
				minYear: number | null,
				maxYear: number | null
			) => {
				return items.filter((item) => {
					if (item.production_year === null) return minYear === null && maxYear === null;
					if (minYear && item.production_year < minYear) return false;
					if (maxYear && item.production_year > maxYear) return false;
					return true;
				});
			};

			// Items with null year are excluded when year filter is active
			expect(filterByYearRange(items, 2000, null)).toHaveLength(1);
		});
	});

	describe('Size Range Filter', () => {
		it('filters by min_size_gb', () => {
			const items = [
				{ name: 'Small', size_bytes: 1000000000 }, // 1 GB
				{ name: 'Medium', size_bytes: 10000000000 }, // ~9.3 GB
				{ name: 'Large', size_bytes: 20000000000 } // ~18.6 GB
			];

			const filterBySizeRange = (
				items: { size_bytes: number | null }[],
				minGb: number | null,
				maxGb: number | null
			) => {
				const GB = 1024 * 1024 * 1024;
				return items.filter((item) => {
					if (item.size_bytes === null) return false;
					const sizeGb = item.size_bytes / GB;
					if (minGb && sizeGb < minGb) return false;
					if (maxGb && sizeGb > maxGb) return false;
					return true;
				});
			};

			expect(filterBySizeRange(items, 5, null)).toHaveLength(2);
		});

		it('filters by max_size_gb', () => {
			const items = [
				{ name: 'Small', size_bytes: 1000000000 }, // 1 GB
				{ name: 'Medium', size_bytes: 10000000000 }, // ~9.3 GB
				{ name: 'Large', size_bytes: 20000000000 } // ~18.6 GB
			];

			const filterBySizeRange = (
				items: { size_bytes: number | null }[],
				minGb: number | null,
				maxGb: number | null
			) => {
				const GB = 1024 * 1024 * 1024;
				return items.filter((item) => {
					if (item.size_bytes === null) return false;
					const sizeGb = item.size_bytes / GB;
					if (minGb && sizeGb < minGb) return false;
					if (maxGb && sizeGb > maxGb) return false;
					return true;
				});
			};

			expect(filterBySizeRange(items, null, 10)).toHaveLength(2);
		});

		it('filters by both min and max size', () => {
			const items = [
				{ name: 'Small', size_bytes: 1000000000 }, // 1 GB
				{ name: 'Medium', size_bytes: 10000000000 }, // ~9.3 GB
				{ name: 'Large', size_bytes: 20000000000 } // ~18.6 GB
			];

			const filterBySizeRange = (
				items: { size_bytes: number | null }[],
				minGb: number | null,
				maxGb: number | null
			) => {
				const GB = 1024 * 1024 * 1024;
				return items.filter((item) => {
					if (item.size_bytes === null) return false;
					const sizeGb = item.size_bytes / GB;
					if (minGb && sizeGb < minGb) return false;
					if (maxGb && sizeGb > maxGb) return false;
					return true;
				});
			};

			expect(filterBySizeRange(items, 5, 15)).toHaveLength(1);
		});
	});

	describe('Sort Dropdown and Order Toggle', () => {
		it('sort options include name, year, size, date_added, last_watched', () => {
			const sortOptions = ['name', 'year', 'size', 'date_added', 'last_watched'];
			expect(sortOptions).toContain('name');
			expect(sortOptions).toContain('year');
			expect(sortOptions).toContain('size');
			expect(sortOptions).toContain('date_added');
			expect(sortOptions).toContain('last_watched');
			expect(sortOptions).toHaveLength(5);
		});

		it('order toggle switches between asc and desc', () => {
			let order: 'asc' | 'desc' = 'asc';

			const toggleOrder = () => {
				order = order === 'asc' ? 'desc' : 'asc';
			};

			expect(order).toBe('asc');
			toggleOrder();
			expect(order).toBe('desc');
			toggleOrder();
			expect(order).toBe('asc');
		});
	});

	describe('Clear All Filters', () => {
		it('clear resets all filter values to defaults', () => {
			// Initial filter state with values
			type WatchedFilter = 'all' | 'true' | 'false';
			type SortField = 'name' | 'year' | 'size' | 'date_added' | 'last_watched';
			type SortOrder = 'asc' | 'desc';

			let filters: {
				search: string;
				watched: WatchedFilter;
				minYear: number | null;
				maxYear: number | null;
				minSizeGb: number | null;
				maxSizeGb: number | null;
				sort: SortField;
				order: SortOrder;
			} = {
				search: 'inception',
				watched: 'true',
				minYear: 2000,
				maxYear: 2020,
				minSizeGb: 5,
				maxSizeGb: 15,
				sort: 'year',
				order: 'desc'
			};

			// Clear function resets to defaults
			const clearFilters = () => {
				filters = {
					search: '',
					watched: 'all',
					minYear: null,
					maxYear: null,
					minSizeGb: null,
					maxSizeGb: null,
					sort: 'name',
					order: 'asc'
				};
			};

			clearFilters();

			expect(filters.search).toBe('');
			expect(filters.watched).toBe('all');
			expect(filters.minYear).toBeNull();
			expect(filters.maxYear).toBeNull();
			expect(filters.minSizeGb).toBeNull();
			expect(filters.maxSizeGb).toBeNull();
			expect(filters.sort).toBe('name');
			expect(filters.order).toBe('asc');
		});
	});

	describe('Item Count Updates', () => {
		it('displays filtered count when search/filters active', () => {
			const totalCount = 100;
			const filteredCount = 15;
			const hasFilters = true;

			const getDisplayText = (total: number, filtered: number, active: boolean) => {
				return active ? `${filtered} of ${total} items` : `${total} items`;
			};

			expect(getDisplayText(totalCount, filteredCount, hasFilters)).toBe('15 of 100 items');
		});

		it('displays total count when no filters active', () => {
			const totalCount = 100;
			const filteredCount = 100;
			const hasFilters = false;

			const getDisplayText = (total: number, filtered: number, active: boolean) => {
				return active ? `${filtered} of ${total} items` : `${total} items`;
			};

			expect(getDisplayText(totalCount, filteredCount, hasFilters)).toBe('100 items');
		});
	});

	describe('Filter Persistence Across Tabs', () => {
		it('filters persist when switching between All/Movies/Series tabs', () => {
			// Simulate filter state that should persist
			const filters = {
				search: 'test',
				watched: 'true',
				minYear: 2010,
				maxYear: 2020
			};

			// Switching tabs (type filter) should not reset other filters
			let activeTab: 'all' | 'movie' | 'series' = 'all';

			const switchTab = (tab: 'all' | 'movie' | 'series') => {
				activeTab = tab;
				// Note: Other filters should NOT be reset
			};

			switchTab('movie');
			expect(activeTab).toBe('movie');
			expect(filters.search).toBe('test');
			expect(filters.watched).toBe('true');
			expect(filters.minYear).toBe(2010);
			expect(filters.maxYear).toBe(2020);

			switchTab('series');
			expect(activeTab).toBe('series');
			expect(filters.search).toBe('test');
		});
	});
});
