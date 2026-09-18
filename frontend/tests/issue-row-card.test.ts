/**
 * Tests for the IssueRow markup the responsive card layout relies on.
 *
 * Below 1020px of table width the Issues table renders each row as a card
 * (styles live in IssueRow, not the page, so Svelte scoping reaches the <td>s).
 * The card shows each meta cell with its `data-label` and hides `is-empty` cells.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import IssueRow from '../src/lib/components/IssueRow.svelte';

type Item = ComponentProps<typeof IssueRow>['item'];

const baseItem: Item = {
	jellyfin_id: 'abc',
	name: 'Fallout',
	media_type: 'Series',
	production_year: 2024,
	size_bytes: 1000,
	size_formatted: '1.0 KB',
	last_played_date: null,
	played: false,
	path: null,
	date_created: '2025-12-18T00:00:00Z',
	issues: ['old'],
	language_issues: null,
	tmdb_id: '1',
	imdb_id: null,
	sonarr_title_slug: null,
	jellyseerr_request_id: null,
	largest_season_size_bytes: null,
	largest_season_size_formatted: null,
	requested_by: null,
	request_date: null,
	missing_seasons: null,
	release_date: null,
	problematic_episodes: null
};

function renderRow(item: Item, activeFilter = 'all') {
	const table = document.createElement('table');
	const tbody = document.createElement('tbody');
	table.appendChild(tbody);
	document.body.appendChild(table);
	const noop = () => {};
	render(IssueRow, {
		target: tbody,
		props: {
			item,
			activeFilter,
			serviceUrls: null,
			protectingIds: new Set<string>(),
			frenchOnlyIds: new Set<string>(),
			languageExemptIds: new Set<string>(),
			largeWhitelistIds: new Set<string>(),
			hidingRequestIds: new Set<string>(),
			deletingIds: new Set<string>(),
			whitelistingEpisodeIds: new Set<string>(),
			expanded: false,
			canDeleteFromArr: true,
			arrName: 'Sonarr',
			badgeTooltips: {},
			onopenDurationPicker: noop,
			onopenDeleteModal: noop,
			ondeleteRequest: noop,
			ontoggleExpansion: noop,
			onopenEpisodeDurationPicker: noop
		}
	});
	return tbody.querySelector('tr.issue-row') as HTMLTableRowElement;
}

describe('IssueRow card layout markup', () => {
	afterEach(() => {
		cleanup();
		document.body.innerHTML = '';
	});

	it('labels the date cells of a library item and keeps them visible', () => {
		const row = renderRow(baseItem);

		const added = row.querySelector('td.col-added')!;
		const watched = row.querySelector('td.col-watched')!;
		expect(added.getAttribute('data-label')).toBe('Added');
		expect(watched.getAttribute('data-label')).toBe('Watched');
		expect(added.classList.contains('is-empty')).toBe(false);
		expect(row.querySelector('td.col-size')!.classList.contains('is-empty')).toBe(false);
	});

	it('marks size and added as empty for requests and labels the request cells', () => {
		const request = {
			...baseItem,
			jellyfin_id: 'request-42',
			issues: ['request'],
			requested_by: 'jojoleboss',
			request_date: '2026-02-01T00:00:00Z',
			release_date: '2026-01-28'
		};
		const row = renderRow(request, 'requests');

		expect(row.querySelector('td.col-size')!.classList.contains('is-empty')).toBe(true);
		expect(row.querySelector('td.col-added')!.classList.contains('is-empty')).toBe(true);
		expect(row.querySelector('td.col-requester')!.getAttribute('data-label')).toBe('By');
		expect(row.querySelector('td.col-release')!.getAttribute('data-label')).toBe('Release');
		expect(row.querySelector('td.col-watched')!.getAttribute('data-label')).toBe('Requested');
		expect(row.querySelector('td.col-watched')!.classList.contains('is-empty')).toBe(false);
	});

	it('hides request cells that have no value', () => {
		const request = { ...baseItem, jellyfin_id: 'request-7', issues: ['request'] };
		const row = renderRow(request, 'requests');

		expect(row.querySelector('td.col-requester')!.classList.contains('is-empty')).toBe(true);
		expect(row.querySelector('td.col-release')!.classList.contains('is-empty')).toBe(true);
		expect(row.querySelector('td.col-watched')!.classList.contains('is-empty')).toBe(true);
	});

	it('puts the year and links in a meta group separate from the title', () => {
		const row = renderRow(baseItem);

		const nameCell = row.querySelector('.name-cell')!;
		expect(nameCell.querySelector(':scope > .item-name')!.textContent).toBe('Fallout');
		expect(nameCell.querySelector(':scope > .name-meta .item-year')!.textContent).toBe('2024');
		expect(nameCell.querySelector(':scope > .name-meta .external-links')).not.toBeNull();
	});
});
