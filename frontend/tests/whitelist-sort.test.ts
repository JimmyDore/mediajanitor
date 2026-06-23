/**
 * Tests for whitelist sorting (sort by added date / expiration date).
 *
 * The whitelist page fetches all items client-side, so sorting is a pure
 * function applied to the already-loaded list.
 */
import { describe, it, expect } from 'vitest';
import {
	sortWhitelistItems,
	SORT_OPTIONS,
	type WhitelistSortKey,
	type SortableWhitelistItem
} from '$lib/whitelist-sort';

function item(
	id: number,
	created_at: string,
	expires_at: string | null
): SortableWhitelistItem & { id: number } {
	return { id, created_at, expires_at };
}

describe('sortWhitelistItems', () => {
	const a = item(1, '2024-01-10T00:00:00Z', '2026-03-01T00:00:00Z');
	const b = item(2, '2024-03-15T00:00:00Z', '2026-01-01T00:00:00Z');
	const c = item(3, '2024-02-01T00:00:00Z', null); // Permanent
	const d = item(4, '2024-05-20T00:00:00Z', '2026-12-31T00:00:00Z');

	const items = [a, b, c, d];

	it('sorts by added date, newest first (added-desc)', () => {
		const result = sortWhitelistItems(items, 'added-desc');
		expect(result.map((i) => i.id)).toEqual([4, 2, 3, 1]);
	});

	it('sorts by added date, oldest first (added-asc)', () => {
		const result = sortWhitelistItems(items, 'added-asc');
		expect(result.map((i) => i.id)).toEqual([1, 3, 2, 4]);
	});

	it('sorts by expiration date, soonest first (expires-asc), permanent last', () => {
		const result = sortWhitelistItems(items, 'expires-asc');
		// b (Jan 2026), a (Mar 2026), d (Dec 2026), then c (permanent)
		expect(result.map((i) => i.id)).toEqual([2, 1, 4, 3]);
	});

	it('sorts by expiration date, latest first (expires-desc), permanent last', () => {
		const result = sortWhitelistItems(items, 'expires-desc');
		// d (Dec 2026), a (Mar 2026), b (Jan 2026), then c (permanent)
		expect(result.map((i) => i.id)).toEqual([4, 1, 2, 3]);
	});

	it('keeps permanent (null expiry) items grouped at the end for both directions', () => {
		const c2 = item(5, '2024-06-01T00:00:00Z', null);
		const withTwoPermanent = [a, c, c2, b];
		const asc = sortWhitelistItems(withTwoPermanent, 'expires-asc');
		const desc = sortWhitelistItems(withTwoPermanent, 'expires-desc');
		// Last two are always the permanent ones
		expect(asc.slice(-2).every((i) => i.expires_at === null)).toBe(true);
		expect(desc.slice(-2).every((i) => i.expires_at === null)).toBe(true);
	});

	it('does not mutate the original array', () => {
		const original = [a, b, c, d];
		const snapshot = original.map((i) => i.id);
		sortWhitelistItems(original, 'added-asc');
		expect(original.map((i) => i.id)).toEqual(snapshot);
	});

	it('handles an empty list', () => {
		expect(sortWhitelistItems([], 'added-desc')).toEqual([]);
	});

	it('handles a single item', () => {
		expect(sortWhitelistItems([a], 'expires-asc')).toEqual([a]);
	});

	it('tolerates invalid date strings without throwing', () => {
		const bad = item(9, 'not-a-date', 'also-bad');
		expect(() => sortWhitelistItems([a, bad], 'added-asc')).not.toThrow();
		expect(() => sortWhitelistItems([a, bad], 'expires-desc')).not.toThrow();
	});

	it('exposes the four sort options for the UI', () => {
		const values = SORT_OPTIONS.map((o) => o.value);
		const expected: WhitelistSortKey[] = [
			'added-desc',
			'added-asc',
			'expires-asc',
			'expires-desc'
		];
		expect(values).toEqual(expected);
		// Every option has a human-readable label
		expect(SORT_OPTIONS.every((o) => o.label.length > 0)).toBe(true);
	});
});
