/**
 * Tests for Issues page sorting logic (US-35.1)
 *
 * Tests verify the Watched column sort order:
 * - DESC: date DESC → "Watched" (played=true, no date) → "Never" (played=false)
 * - ASC: "Never" → "Watched" → date ASC
 */
import { describe, it, expect } from 'vitest';

// Minimal item type for sorting tests
interface SortableItem {
	jellyfin_id: string;
	name: string;
	media_type: string;
	last_played_date: string | null;
	played: boolean | null;
}

// Helper to create test items
function createItem(
	id: string,
	lastPlayed: string | null,
	played: boolean | null = null
): SortableItem {
	return {
		jellyfin_id: id,
		name: `Item ${id}`,
		media_type: 'Movie',
		last_played_date: lastPlayed,
		played: played
	};
}

/**
 * The sorting function extracted from +page.svelte
 * This should match the 'watched' case in getSortedItems
 */
function sortByWatched(items: SortableItem[], order: 'asc' | 'desc'): SortableItem[] {
	return [...items].sort((a, b) => {
		// Get watch status priority: date (1) > played without date (2) > never (3)
		function getWatchPriority(item: SortableItem): number {
			if (item.last_played_date) return 1; // Has date - highest priority for DESC
			if (item.played) return 2; // Watched but no date
			return 3; // Never watched - lowest priority for DESC
		}

		const priorityA = getWatchPriority(a);
		const priorityB = getWatchPriority(b);

		// Different priorities - sort by priority
		if (priorityA !== priorityB) {
			const comparison = priorityA - priorityB;
			return order === 'asc' ? -comparison : comparison;
		}

		// Same priority - if both have dates, sort by date
		if (priorityA === 1 && priorityB === 1) {
			const dateA = new Date(a.last_played_date!).getTime();
			const dateB = new Date(b.last_played_date!).getTime();
			const comparison = dateA - dateB;
			return order === 'asc' ? comparison : -comparison;
		}

		// Same priority without dates (both "Watched" or both "Never") - maintain order
		return 0;
	});
}

describe('Watched column sort order (US-35.1)', () => {
	describe('descending order (default click)', () => {
		it('sorts items with dates before "Watched" and "Never"', () => {
			const items = [
				createItem('never', null, false),
				createItem('watched-no-date', null, true),
				createItem('dated', '2025-01-15T10:00:00Z', true)
			];

			const sorted = sortByWatched(items, 'desc');

			expect(sorted[0].jellyfin_id).toBe('dated');
			expect(sorted[1].jellyfin_id).toBe('watched-no-date');
			expect(sorted[2].jellyfin_id).toBe('never');
		});

		it('sorts multiple dated items newest first', () => {
			const items = [
				createItem('old', '2024-01-01T10:00:00Z', true),
				createItem('new', '2025-12-01T10:00:00Z', true),
				createItem('mid', '2025-06-01T10:00:00Z', true)
			];

			const sorted = sortByWatched(items, 'desc');

			expect(sorted[0].jellyfin_id).toBe('new');
			expect(sorted[1].jellyfin_id).toBe('mid');
			expect(sorted[2].jellyfin_id).toBe('old');
		});

		it('handles mixed items in correct order: dates DESC → Watched → Never', () => {
			const items = [
				createItem('never-1', null, false),
				createItem('dated-old', '2024-01-01T10:00:00Z', true),
				createItem('watched-1', null, true),
				createItem('dated-new', '2025-12-01T10:00:00Z', true),
				createItem('never-2', null, false),
				createItem('watched-2', null, true)
			];

			const sorted = sortByWatched(items, 'desc');

			// First: dated items, newest first
			expect(sorted[0].jellyfin_id).toBe('dated-new');
			expect(sorted[1].jellyfin_id).toBe('dated-old');
			// Then: watched without date
			expect(sorted[2].jellyfin_id).toBe('watched-1');
			expect(sorted[3].jellyfin_id).toBe('watched-2');
			// Finally: never watched
			expect(sorted[4].jellyfin_id).toBe('never-1');
			expect(sorted[5].jellyfin_id).toBe('never-2');
		});
	});

	describe('ascending order (second click)', () => {
		it('sorts "Never" before "Watched" before dates', () => {
			const items = [
				createItem('dated', '2025-01-15T10:00:00Z', true),
				createItem('never', null, false),
				createItem('watched-no-date', null, true)
			];

			const sorted = sortByWatched(items, 'asc');

			expect(sorted[0].jellyfin_id).toBe('never');
			expect(sorted[1].jellyfin_id).toBe('watched-no-date');
			expect(sorted[2].jellyfin_id).toBe('dated');
		});

		it('sorts multiple dated items oldest first', () => {
			const items = [
				createItem('new', '2025-12-01T10:00:00Z', true),
				createItem('old', '2024-01-01T10:00:00Z', true),
				createItem('mid', '2025-06-01T10:00:00Z', true)
			];

			const sorted = sortByWatched(items, 'asc');

			expect(sorted[0].jellyfin_id).toBe('old');
			expect(sorted[1].jellyfin_id).toBe('mid');
			expect(sorted[2].jellyfin_id).toBe('new');
		});

		it('handles mixed items in correct order: Never → Watched → dates ASC', () => {
			const items = [
				createItem('dated-new', '2025-12-01T10:00:00Z', true),
				createItem('watched-1', null, true),
				createItem('never-1', null, false),
				createItem('dated-old', '2024-01-01T10:00:00Z', true),
				createItem('never-2', null, false),
				createItem('watched-2', null, true)
			];

			const sorted = sortByWatched(items, 'asc');

			// First: never watched
			expect(sorted[0].jellyfin_id).toBe('never-1');
			expect(sorted[1].jellyfin_id).toBe('never-2');
			// Then: watched without date
			expect(sorted[2].jellyfin_id).toBe('watched-1');
			expect(sorted[3].jellyfin_id).toBe('watched-2');
			// Finally: dated items, oldest first
			expect(sorted[4].jellyfin_id).toBe('dated-old');
			expect(sorted[5].jellyfin_id).toBe('dated-new');
		});
	});

	describe('edge cases', () => {
		it('handles empty array', () => {
			const sorted = sortByWatched([], 'desc');
			expect(sorted).toEqual([]);
		});

		it('handles single item', () => {
			const items = [createItem('single', '2025-01-01T10:00:00Z', true)];
			const sorted = sortByWatched(items, 'desc');
			expect(sorted.length).toBe(1);
			expect(sorted[0].jellyfin_id).toBe('single');
		});

		it('handles all items with same status (all never)', () => {
			const items = [
				createItem('a', null, false),
				createItem('b', null, false),
				createItem('c', null, false)
			];
			// Order should be stable (maintained)
			const sorted = sortByWatched(items, 'desc');
			expect(sorted.length).toBe(3);
		});

		it('handles all items with same status (all watched no date)', () => {
			const items = [
				createItem('a', null, true),
				createItem('b', null, true),
				createItem('c', null, true)
			];
			// Order should be stable (maintained)
			const sorted = sortByWatched(items, 'desc');
			expect(sorted.length).toBe(3);
		});

		it('handles played=null as "Never" (same as played=false)', () => {
			const items = [
				createItem('dated', '2025-01-15T10:00:00Z', true),
				createItem('null-played', null, null), // played is null
				createItem('false-played', null, false)
			];

			const sorted = sortByWatched(items, 'desc');

			// dated first, then both "never" items (null and false are equivalent)
			expect(sorted[0].jellyfin_id).toBe('dated');
			// null and false should both be at the end
			expect(['null-played', 'false-played']).toContain(sorted[1].jellyfin_id);
			expect(['null-played', 'false-played']).toContain(sorted[2].jellyfin_id);
		});

		it('works for both movies and series', () => {
			const movie: SortableItem = {
				jellyfin_id: 'movie',
				name: 'Movie',
				media_type: 'Movie',
				last_played_date: '2025-01-01T10:00:00Z',
				played: true
			};
			const series: SortableItem = {
				jellyfin_id: 'series',
				name: 'Series',
				media_type: 'Series',
				last_played_date: '2025-06-01T10:00:00Z',
				played: true
			};

			const sorted = sortByWatched([movie, series], 'desc');

			// Series has newer date, should be first
			expect(sorted[0].jellyfin_id).toBe('series');
			expect(sorted[1].jellyfin_id).toBe('movie');
		});
	});
});
