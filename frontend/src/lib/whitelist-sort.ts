/**
 * Sorting helpers for the Whitelists page.
 *
 * All whitelist items are fetched up-front, so sorting is a pure function
 * applied client-side to the loaded list. Every whitelist variant shares the
 * `created_at` (added date) and `expires_at` (expiration, null = permanent)
 * fields, so we only need those two for ordering.
 */

export interface SortableWhitelistItem {
	created_at: string;
	expires_at: string | null;
}

export type WhitelistSortKey = 'added-desc' | 'added-asc' | 'expires-asc' | 'expires-desc';

export const SORT_OPTIONS: { value: WhitelistSortKey; label: string }[] = [
	{ value: 'added-desc', label: 'Added · Newest' },
	{ value: 'added-asc', label: 'Added · Oldest' },
	{ value: 'expires-asc', label: 'Expires · Soonest' },
	{ value: 'expires-desc', label: 'Expires · Latest' }
];

function toTime(dateStr: string | null): number {
	if (!dateStr) return 0;
	const t = new Date(dateStr).getTime();
	return Number.isNaN(t) ? 0 : t;
}

/**
 * Return a sorted copy of `items` (never mutates the input).
 *
 * Permanent items (null `expires_at`) are always grouped at the end when
 * sorting by expiration, regardless of direction, since they have no date.
 */
export function sortWhitelistItems<T extends SortableWhitelistItem>(
	items: readonly T[],
	sortKey: WhitelistSortKey
): T[] {
	const [field, dir] = sortKey.split('-') as ['added' | 'expires', 'asc' | 'desc'];
	const sorted = [...items];

	sorted.sort((a, b) => {
		if (field === 'expires') {
			const aPermanent = a.expires_at === null;
			const bPermanent = b.expires_at === null;
			if (aPermanent && bPermanent) return 0;
			if (aPermanent) return 1; // permanent always last
			if (bPermanent) return -1;
			const cmp = toTime(a.expires_at) - toTime(b.expires_at);
			return dir === 'asc' ? cmp : -cmp;
		}

		const cmp = toTime(a.created_at) - toTime(b.created_at);
		return dir === 'asc' ? cmp : -cmp;
	});

	return sorted;
}
