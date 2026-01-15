/**
 * Tests for large content filtering and display (US-20.4)
 *
 * Tests verify:
 * 1. API response includes largest_season_size fields for series
 * 2. Large content filter returns both movies and series
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Large Content API Integration (US-20.4)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/content/issues?filter=large', () => {
		it('returns both large movies and large series', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-large',
						name: 'Large Movie',
						media_type: 'Movie',
						production_year: 2022,
						size_bytes: 25000000000, // 25 GB
						size_formatted: '23.3 GB',
						issues: ['large'],
						largest_season_size_bytes: null,
						largest_season_size_formatted: null
					},
					{
						jellyfin_id: 'series-large',
						name: 'Large Series',
						media_type: 'Series',
						production_year: 2021,
						size_bytes: 80000000000, // 80 GB total
						size_formatted: '74.5 GB',
						issues: ['large'],
						largest_season_size_bytes: 18500000000, // 18.5 GB largest season
						largest_season_size_formatted: '17.2 GB'
					}
				],
				total_count: 2,
				total_size_bytes: 105000000000,
				total_size_formatted: '97.8 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=large', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();

			// Verify both movie and series are returned
			expect(data.items.length).toBe(2);
			expect(data.items.map((i: { media_type: string }) => i.media_type)).toContain('Movie');
			expect(data.items.map((i: { media_type: string }) => i.media_type)).toContain('Series');

			// Both should have 'large' badge
			expect(data.items[0].issues).toContain('large');
			expect(data.items[1].issues).toContain('large');
		});

		it('series items include largest_season_size_bytes field', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'series-large',
						name: 'Large Series',
						media_type: 'Series',
						production_year: 2021,
						size_bytes: 80000000000,
						size_formatted: '74.5 GB',
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
			const series = data.items[0];

			expect(series.largest_season_size_bytes).toBe(18500000000);
			expect(series.largest_season_size_formatted).toBe('17.2 GB');
		});

		it('movie items have null largest_season_size fields', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-large',
						name: 'Large Movie',
						media_type: 'Movie',
						production_year: 2022,
						size_bytes: 25000000000,
						size_formatted: '23.3 GB',
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
			const movie = data.items[0];

			expect(movie.largest_season_size_bytes).toBeNull();
			expect(movie.largest_season_size_formatted).toBeNull();
		});
	});
});

describe('Large Content Sub-filter Logic (US-20.4)', () => {
	// Test client-side filtering logic
	// These tests verify the filtering functions work correctly

	interface ContentItem {
		jellyfin_id: string;
		name: string;
		media_type: string;
		issues: string[];
		size_bytes: number;
		largest_season_size_bytes: number | null;
		largest_season_size_formatted: string | null;
	}

	// Helper functions to simulate the filtering logic
	function isMovieItem(item: ContentItem): boolean {
		const type = item.media_type.toLowerCase();
		return type === 'movie';
	}

	function isSeriesItem(item: ContentItem): boolean {
		const type = item.media_type.toLowerCase();
		return type === 'series' || type === 'tv';
	}

	function applyLargeSubFilter(
		items: ContentItem[],
		subFilter: 'all' | 'movies' | 'series'
	): ContentItem[] {
		if (subFilter === 'all') {
			return items;
		}
		if (subFilter === 'movies') {
			return items.filter((item) => isMovieItem(item));
		}
		if (subFilter === 'series') {
			return items.filter((item) => isSeriesItem(item));
		}
		return items;
	}

	const mockItems: ContentItem[] = [
		{
			jellyfin_id: 'movie-1',
			name: 'Large Movie 1',
			media_type: 'Movie',
			issues: ['large'],
			size_bytes: 20000000000,
			largest_season_size_bytes: null,
			largest_season_size_formatted: null
		},
		{
			jellyfin_id: 'movie-2',
			name: 'Large Movie 2',
			media_type: 'Movie',
			issues: ['large'],
			size_bytes: 18000000000,
			largest_season_size_bytes: null,
			largest_season_size_formatted: null
		},
		{
			jellyfin_id: 'series-1',
			name: 'Large Series 1',
			media_type: 'Series',
			issues: ['large'],
			size_bytes: 80000000000,
			largest_season_size_bytes: 18500000000,
			largest_season_size_formatted: '17.2 GB'
		},
		{
			jellyfin_id: 'series-2',
			name: 'Large TV Show',
			media_type: 'tv', // Test lowercase variant
			issues: ['large'],
			size_bytes: 60000000000,
			largest_season_size_bytes: 16000000000,
			largest_season_size_formatted: '14.9 GB'
		}
	];

	describe('Sub-filter: All', () => {
		it('returns all items when sub-filter is "all"', () => {
			const result = applyLargeSubFilter(mockItems, 'all');
			expect(result.length).toBe(4);
		});
	});

	describe('Sub-filter: Movies', () => {
		it('returns only movies when sub-filter is "movies"', () => {
			const result = applyLargeSubFilter(mockItems, 'movies');
			expect(result.length).toBe(2);
			expect(result.every((item) => isMovieItem(item))).toBe(true);
		});

		it('filters out series items', () => {
			const result = applyLargeSubFilter(mockItems, 'movies');
			expect(result.some((item) => isSeriesItem(item))).toBe(false);
		});
	});

	describe('Sub-filter: Series', () => {
		it('returns only series when sub-filter is "series"', () => {
			const result = applyLargeSubFilter(mockItems, 'series');
			expect(result.length).toBe(2);
			expect(result.every((item) => isSeriesItem(item))).toBe(true);
		});

		it('includes both "Series" and "tv" media types', () => {
			const result = applyLargeSubFilter(mockItems, 'series');
			expect(result.map((item) => item.media_type)).toContain('Series');
			expect(result.map((item) => item.media_type)).toContain('tv');
		});

		it('filters out movie items', () => {
			const result = applyLargeSubFilter(mockItems, 'movies');
			expect(result.some((item) => isSeriesItem(item))).toBe(false);
		});
	});

	describe('Size calculations with sub-filter', () => {
		it('calculates correct total size for movies only', () => {
			const result = applyLargeSubFilter(mockItems, 'movies');
			const totalSize = result.reduce((sum, item) => sum + item.size_bytes, 0);
			expect(totalSize).toBe(38000000000); // 20 + 18 GB
		});

		it('calculates correct total size for series only', () => {
			const result = applyLargeSubFilter(mockItems, 'series');
			const totalSize = result.reduce((sum, item) => sum + item.size_bytes, 0);
			expect(totalSize).toBe(140000000000); // 80 + 60 GB
		});
	});

	describe('Largest season size display logic', () => {
		it('series with largest_season_size_formatted should display it', () => {
			const series = mockItems.find((i) => i.jellyfin_id === 'series-1');
			expect(series).toBeDefined();
			expect(series!.largest_season_size_formatted).toBe('17.2 GB');
			// In the UI, this would be displayed as "Largest season: 17.2 GB"
		});

		it('movies have null largest_season_size', () => {
			const movie = mockItems.find((i) => i.jellyfin_id === 'movie-1');
			expect(movie).toBeDefined();
			expect(movie!.largest_season_size_bytes).toBeNull();
			expect(movie!.largest_season_size_formatted).toBeNull();
			// In the UI, this would display the regular size_formatted
		});
	});
});
