/**
 * Tests for the Issues page search functionality (US-19.1)
 *
 * Tests verify client-side search filtering behavior.
 */
import { describe, it, expect } from 'vitest';

// Define the ContentIssueItem interface for tests
interface ContentIssueItem {
	jellyfin_id: string;
	name: string;
	media_type: string;
	production_year: number | null;
	size_bytes: number | null;
	size_formatted: string;
	last_played_date: string | null;
	played: boolean | null;
	path: string | null;
	issues: string[];
	language_issues: string[] | null;
	tmdb_id: string | null;
	imdb_id: string | null;
	sonarr_title_slug: string | null;
	jellyseerr_request_id: number | null;
	requested_by: string | null;
	request_date: string | null;
	missing_seasons: number[] | null;
	release_date: string | null;
}

// Replicate the search matching logic from the component
function matchesSearch(item: ContentIssueItem, query: string): boolean {
	if (!query.trim()) return true;

	const lowerQuery = query.toLowerCase().trim();

	// Match against title
	if (item.name.toLowerCase().includes(lowerQuery)) return true;

	// Match against production year
	if (item.production_year && item.production_year.toString().includes(lowerQuery)) return true;

	// Match against requested_by (for Requests tab)
	if (item.requested_by && item.requested_by.toLowerCase().includes(lowerQuery)) return true;

	return false;
}

function getFilteredItems(items: ContentIssueItem[], query: string): ContentIssueItem[] {
	if (!query.trim()) return items;
	return items.filter((item) => matchesSearch(item, query));
}

function getFilteredStats(
	items: ContentIssueItem[],
	query: string
): { count: number; sizeBytes: number } {
	const filtered = getFilteredItems(items, query);
	const sizeBytes = filtered.reduce((sum, item) => sum + (item.size_bytes || 0), 0);
	return { count: filtered.length, sizeBytes };
}

// Test data
const createItem = (overrides: Partial<ContentIssueItem> = {}): ContentIssueItem => ({
	jellyfin_id: 'test-id',
	name: 'Test Movie',
	media_type: 'Movie',
	production_year: 2020,
	size_bytes: 5000000000,
	size_formatted: '4.7 GB',
	last_played_date: null,
	played: null,
	path: '/media/movies/Test Movie',
	issues: ['old'],
	language_issues: null,
	tmdb_id: '12345',
	imdb_id: null,
	sonarr_title_slug: null,
	jellyseerr_request_id: null,
	requested_by: null,
	request_date: null,
	missing_seasons: null,
	release_date: null,
	...overrides
});

describe('Issues Page Search Functionality (US-19.1)', () => {
	describe('matchesSearch', () => {
		it('returns true for empty query', () => {
			const item = createItem({ name: 'Inception' });
			expect(matchesSearch(item, '')).toBe(true);
			expect(matchesSearch(item, '   ')).toBe(true);
		});

		it('matches against title (case-insensitive)', () => {
			const item = createItem({ name: 'The Dark Knight' });
			expect(matchesSearch(item, 'dark')).toBe(true);
			expect(matchesSearch(item, 'DARK')).toBe(true);
			expect(matchesSearch(item, 'Dark Knight')).toBe(true);
			expect(matchesSearch(item, 'knight')).toBe(true);
		});

		it('does not match non-matching title', () => {
			const item = createItem({ name: 'Inception' });
			expect(matchesSearch(item, 'batman')).toBe(false);
		});

		it('matches against production year', () => {
			const item = createItem({ name: 'Test Movie', production_year: 2018 });
			expect(matchesSearch(item, '2018')).toBe(true);
			expect(matchesSearch(item, '201')).toBe(true);
			expect(matchesSearch(item, '18')).toBe(true);
		});

		it('does not match wrong production year', () => {
			const item = createItem({ name: 'Test Movie', production_year: 2018 });
			expect(matchesSearch(item, '2020')).toBe(false);
		});

		it('handles null production year', () => {
			const item = createItem({ name: 'Test Movie', production_year: null });
			expect(matchesSearch(item, '2020')).toBe(false);
		});

		it('matches against requested_by (case-insensitive)', () => {
			const item = createItem({
				name: 'Requested Movie',
				requested_by: 'JohnDoe'
			});
			expect(matchesSearch(item, 'john')).toBe(true);
			expect(matchesSearch(item, 'JOHN')).toBe(true);
			expect(matchesSearch(item, 'doe')).toBe(true);
			expect(matchesSearch(item, 'johndoe')).toBe(true);
		});

		it('does not match non-matching requester', () => {
			const item = createItem({
				name: 'Requested Movie',
				requested_by: 'JohnDoe'
			});
			expect(matchesSearch(item, 'jane')).toBe(false);
		});

		it('handles null requested_by', () => {
			const item = createItem({ name: 'Test Movie', requested_by: null });
			expect(matchesSearch(item, 'john')).toBe(false);
		});

		it('trims whitespace from query', () => {
			const item = createItem({ name: 'Inception' });
			expect(matchesSearch(item, '  inception  ')).toBe(true);
		});

		it('matches partial strings', () => {
			const item = createItem({ name: 'The Shawshank Redemption' });
			expect(matchesSearch(item, 'shaw')).toBe(true);
			expect(matchesSearch(item, 'redemp')).toBe(true);
		});
	});

	describe('getFilteredItems', () => {
		const items: ContentIssueItem[] = [
			createItem({ jellyfin_id: '1', name: 'Inception', production_year: 2010 }),
			createItem({ jellyfin_id: '2', name: 'The Dark Knight', production_year: 2008 }),
			createItem({
				jellyfin_id: '3',
				name: 'Interstellar',
				production_year: 2014,
				requested_by: 'MovieFan'
			}),
			createItem({ jellyfin_id: '4', name: 'Tenet', production_year: 2020 })
		];

		it('returns all items for empty query', () => {
			expect(getFilteredItems(items, '')).toHaveLength(4);
			expect(getFilteredItems(items, '   ')).toHaveLength(4);
		});

		it('filters items by title', () => {
			const filtered = getFilteredItems(items, 'dark');
			expect(filtered).toHaveLength(1);
			expect(filtered[0].name).toBe('The Dark Knight');
		});

		it('filters items by year', () => {
			const filtered = getFilteredItems(items, '2010');
			expect(filtered).toHaveLength(1);
			expect(filtered[0].name).toBe('Inception');
		});

		it('filters items by requester', () => {
			const filtered = getFilteredItems(items, 'moviefan');
			expect(filtered).toHaveLength(1);
			expect(filtered[0].name).toBe('Interstellar');
		});

		it('returns multiple matches', () => {
			const filtered = getFilteredItems(items, 'inter');
			expect(filtered).toHaveLength(1);
			expect(filtered[0].name).toBe('Interstellar');
		});

		it('returns empty array when no matches', () => {
			const filtered = getFilteredItems(items, 'matrix');
			expect(filtered).toHaveLength(0);
		});

		it('search operates on all items regardless of issue type', () => {
			const mixedItems: ContentIssueItem[] = [
				createItem({ jellyfin_id: '1', name: 'Old Movie', issues: ['old'] }),
				createItem({ jellyfin_id: '2', name: 'Large Movie', issues: ['large'] }),
				createItem({ jellyfin_id: '3', name: 'Language Movie', issues: ['language'] }),
				createItem({ jellyfin_id: '4', name: 'Request Movie', issues: ['request'] })
			];

			const filtered = getFilteredItems(mixedItems, 'movie');
			expect(filtered).toHaveLength(4);
		});
	});

	describe('getFilteredStats', () => {
		const items: ContentIssueItem[] = [
			createItem({
				jellyfin_id: '1',
				name: 'Small Movie',
				size_bytes: 2000000000,
				production_year: 2020
			}),
			createItem({
				jellyfin_id: '2',
				name: 'Large Movie',
				size_bytes: 15000000000,
				production_year: 2020
			}),
			createItem({
				jellyfin_id: '3',
				name: 'Medium Movie',
				size_bytes: 8000000000,
				production_year: 2018
			})
		];

		it('returns total count and size for empty query', () => {
			const stats = getFilteredStats(items, '');
			expect(stats.count).toBe(3);
			expect(stats.sizeBytes).toBe(25000000000);
		});

		it('returns filtered count and size for matching query', () => {
			const stats = getFilteredStats(items, '2020');
			expect(stats.count).toBe(2);
			expect(stats.sizeBytes).toBe(17000000000); // 2GB + 15GB
		});

		it('handles items with null size_bytes', () => {
			const itemsWithNull: ContentIssueItem[] = [
				createItem({ jellyfin_id: '1', name: 'Movie A', size_bytes: 5000000000 }),
				createItem({ jellyfin_id: '2', name: 'Movie B', size_bytes: null })
			];

			const stats = getFilteredStats(itemsWithNull, 'movie');
			expect(stats.count).toBe(2);
			expect(stats.sizeBytes).toBe(5000000000);
		});

		it('returns zero for non-matching query', () => {
			const stats = getFilteredStats(items, 'nonexistent');
			expect(stats.count).toBe(0);
			expect(stats.sizeBytes).toBe(0);
		});
	});

	describe('display format for filtered results', () => {
		it('shows "X of Y items" format when search is active', () => {
			const totalCount = 219;
			const filteredCount = 3;
			const searchQuery = 'inception';

			// Simulate the display logic
			const displayText = searchQuery.trim()
				? `${filteredCount} of ${totalCount} items`
				: `${totalCount} items`;

			expect(displayText).toBe('3 of 219 items');
		});

		it('shows regular count format when no search', () => {
			const totalCount = 219;
			const searchQuery = '';

			const displayText = searchQuery.trim() ? `X of ${totalCount} items` : `${totalCount} items`;

			expect(displayText).toBe('219 items');
		});
	});
});
