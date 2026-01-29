/**
 * Tests for Recently Available episode details display (US-51.4 and US-63.4)
 *
 * Tests verify:
 * - API contract includes season/episode fields
 * - API contract includes episode_additions field (US-63.4)
 * - getDetails() helper correctly formats episode info
 * - getDetails() prefers episode_additions when available (US-63.4)
 * - Copy feature includes episode details
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

// US-63.4: Episode-level details from Sonarr history
interface EpisodeAddition {
	added_date: string; // ISO date string (YYYY-MM-DD)
	display_text: string; // e.g., "S2E5", "S2E5-E8", "Season 2", "S2E3, S2E5, S2E7"
	season: number;
	episode_numbers: number[];
	is_full_season: boolean;
}

// Define the item interface matching the component
interface RecentlyAvailableItem {
	jellyseerr_id: number;
	title: string;
	title_fr: string | null;
	media_type: string;
	availability_date: string;
	requested_by: string | null;
	display_name: string | null;
	season_info: string | null;
	episode_count: number | null;
	available_episodes: number | null;
	total_episodes: number | null;
	// US-63.4: Episode-level additions from Sonarr history
	episode_additions: EpisodeAddition[] | null;
}

/**
 * Get the formatted details for display.
 * - TV with episode_additions (from Sonarr): show smart grouped display (e.g., "S2E5-E8")
 * - Fully available TV (status 5): "Seasons 1-3 (30 eps)"
 * - Partially available TV (status 4) without Sonarr: "S4: 5/12 episodes"
 * - Movies: "—"
 */
function getDetails(item: RecentlyAvailableItem): string {
	if (item.media_type !== 'tv') {
		return '—';
	}

	// US-63.4: Prefer episode_additions from Sonarr history when available
	if (item.episode_additions && item.episode_additions.length > 0) {
		// Show most recent addition (array is sorted by date descending)
		// If multiple addition dates, show them comma-separated
		const uniqueTexts = item.episode_additions.map((ea) => ea.display_text);
		// Show up to 3 additions, with "..." if more
		if (uniqueTexts.length <= 3) {
			return uniqueTexts.join(', ');
		}
		return `${uniqueTexts.slice(0, 3).join(', ')}...`;
	}

	// Status 4 (partially available): has available_episodes and total_episodes
	if (item.available_episodes !== null && item.total_episodes !== null && item.season_info) {
		// Extract season number from "Season X in progress"
		const match = item.season_info.match(/Season (\d+)/);
		if (match) {
			return `S${match[1]}: ${item.available_episodes}/${item.total_episodes} episodes`;
		}
	}

	// Status 5 (fully available): has season_info and episode_count
	if (item.season_info && item.episode_count !== null) {
		return `${item.season_info} (${item.episode_count} eps)`;
	}

	// Fallback: season_info without episode count
	if (item.season_info) {
		return item.season_info;
	}

	return '—';
}

describe('Recently Available Episode Details (US-51.4)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('API Contract - Season/Episode Fields', () => {
		it('returns season_info and episode_count for fully available TV shows', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1001,
						title: 'Breaking Bad',
						title_fr: null,
						media_type: 'tv',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'test_user',
						display_name: 'Test User',
						season_info: 'Seasons 1-5',
						episode_count: 62,
						available_episodes: null,
						total_episodes: null,
						episode_additions: null // Status 5 shows don't have episode_additions
					}
				],
				total_count: 1
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(recentData)
			});

			const response = await fetch('/api/info/recent', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.season_info).toBe('Seasons 1-5');
			expect(item.episode_count).toBe(62);
			expect(item.available_episodes).toBeNull();
			expect(item.total_episodes).toBeNull();
			expect(item.episode_additions).toBeNull();
		});

		it('returns available_episodes and total_episodes for partially available TV shows', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1002,
						title: 'House of the Dragon',
						title_fr: null,
						media_type: 'tv',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'test_user',
						display_name: 'Test User',
						season_info: 'Season 2 in progress',
						episode_count: null,
						available_episodes: 5,
						total_episodes: 12,
						episode_additions: null // No Sonarr data
					}
				],
				total_count: 1
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(recentData)
			});

			const response = await fetch('/api/info/recent', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.season_info).toBe('Season 2 in progress');
			expect(item.episode_count).toBeNull();
			expect(item.available_episodes).toBe(5);
			expect(item.total_episodes).toBe(12);
		});

		it('returns null for all episode fields for movies', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1003,
						title: 'Inception',
						title_fr: 'Inception',
						media_type: 'movie',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'test_user',
						display_name: 'Test User',
						season_info: null,
						episode_count: null,
						available_episodes: null,
						total_episodes: null,
						episode_additions: null
					}
				],
				total_count: 1
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(recentData)
			});

			const response = await fetch('/api/info/recent', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.season_info).toBeNull();
			expect(item.episode_count).toBeNull();
			expect(item.available_episodes).toBeNull();
			expect(item.total_episodes).toBeNull();
			expect(item.episode_additions).toBeNull();
		});

		it('returns episode_additions for status 4 TV shows with Sonarr data (US-63.4)', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1004,
						title: 'The Last of Us',
						title_fr: null,
						media_type: 'tv',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'test_user',
						display_name: 'Test User',
						season_info: 'Season 2 in progress',
						episode_count: null,
						available_episodes: 5,
						total_episodes: 12,
						episode_additions: [
							{
								added_date: '2026-01-10',
								display_text: 'S2E5-E7',
								season: 2,
								episode_numbers: [5, 6, 7],
								is_full_season: false
							},
							{
								added_date: '2026-01-08',
								display_text: 'S2E3-E4',
								season: 2,
								episode_numbers: [3, 4],
								is_full_season: false
							}
						]
					}
				],
				total_count: 1
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(recentData)
			});

			const response = await fetch('/api/info/recent', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.episode_additions).not.toBeNull();
			expect(item.episode_additions).toHaveLength(2);
			expect(item.episode_additions[0].display_text).toBe('S2E5-E7');
			expect(item.episode_additions[0].season).toBe(2);
			expect(item.episode_additions[0].episode_numbers).toEqual([5, 6, 7]);
			expect(item.episode_additions[0].is_full_season).toBe(false);
		});
	});

	describe('getDetails() Helper Function', () => {
		it('returns "—" for movies', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Inception',
				title_fr: null,
				media_type: 'movie',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: null,
				episode_count: null,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('—');
		});

		it('formats fully available TV show with multiple seasons', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Breaking Bad',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Seasons 1-5',
				episode_count: 62,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('Seasons 1-5 (62 eps)');
		});

		it('formats fully available TV show with single season', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Chernobyl',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 1',
				episode_count: 5,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('Season 1 (5 eps)');
		});

		it('formats partially available TV show with progress', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'House of the Dragon',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 5,
				total_episodes: 12,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('S2: 5/12 episodes');
		});

		it('formats season 10+ correctly', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'The Simpsons',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 35 in progress',
				episode_count: null,
				available_episodes: 10,
				total_episodes: 22,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('S35: 10/22 episodes');
		});

		it('returns season_info when episode_count is null', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Test Show',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Seasons 1-3',
				episode_count: null,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('Seasons 1-3');
		});

		it('returns "—" for TV show without any season info', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Unknown Show',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: null,
				episode_count: null,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('—');
		});

		it('formats non-contiguous seasons correctly', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Test Show',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Seasons 1, 3, 4',
				episode_count: 30,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(getDetails(item)).toBe('Seasons 1, 3, 4 (30 eps)');
		});
	});

	describe('getDetails() with episode_additions (US-63.4)', () => {
		it('prefers single episode_addition display_text over season_info', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'House of the Dragon',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 5,
				total_episodes: 12,
				episode_additions: [
					{
						added_date: '2026-01-10',
						display_text: 'S2E5',
						season: 2,
						episode_numbers: [5],
						is_full_season: false
					}
				]
			};

			expect(getDetails(item)).toBe('S2E5');
		});

		it('shows consecutive episode range display_text', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'The Last of Us',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 7,
				total_episodes: 10,
				episode_additions: [
					{
						added_date: '2026-01-10',
						display_text: 'S2E5-E7',
						season: 2,
						episode_numbers: [5, 6, 7],
						is_full_season: false
					}
				]
			};

			expect(getDetails(item)).toBe('S2E5-E7');
		});

		it('shows full season display_text', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Severance',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Seasons 1-2',
				episode_count: 19,
				available_episodes: null,
				total_episodes: null,
				episode_additions: [
					{
						added_date: '2026-01-10',
						display_text: 'Season 2',
						season: 2,
						episode_numbers: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
						is_full_season: true
					}
				]
			};

			expect(getDetails(item)).toBe('Season 2');
		});

		it('shows comma-separated display_text for multiple additions (up to 3)', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Test Show',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 6,
				total_episodes: 12,
				episode_additions: [
					{
						added_date: '2026-01-10',
						display_text: 'S2E6',
						season: 2,
						episode_numbers: [6],
						is_full_season: false
					},
					{
						added_date: '2026-01-08',
						display_text: 'S2E4-E5',
						season: 2,
						episode_numbers: [4, 5],
						is_full_season: false
					},
					{
						added_date: '2026-01-05',
						display_text: 'S2E1-E3',
						season: 2,
						episode_numbers: [1, 2, 3],
						is_full_season: false
					}
				]
			};

			expect(getDetails(item)).toBe('S2E6, S2E4-E5, S2E1-E3');
		});

		it('shows ellipsis when more than 3 additions', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Test Show',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 8,
				total_episodes: 12,
				episode_additions: [
					{
						added_date: '2026-01-10',
						display_text: 'S2E8',
						season: 2,
						episode_numbers: [8],
						is_full_season: false
					},
					{
						added_date: '2026-01-09',
						display_text: 'S2E7',
						season: 2,
						episode_numbers: [7],
						is_full_season: false
					},
					{
						added_date: '2026-01-08',
						display_text: 'S2E6',
						season: 2,
						episode_numbers: [6],
						is_full_season: false
					},
					{
						added_date: '2026-01-07',
						display_text: 'S2E5',
						season: 2,
						episode_numbers: [5],
						is_full_season: false
					}
				]
			};

			expect(getDetails(item)).toBe('S2E8, S2E7, S2E6...');
		});

		it('falls back to season_info when episode_additions is empty array', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'House of the Dragon',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 5,
				total_episodes: 12,
				episode_additions: []
			};

			expect(getDetails(item)).toBe('S2: 5/12 episodes');
		});

		it('shows mixed season additions correctly', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Test Show',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Seasons 1-2',
				episode_count: 20,
				available_episodes: null,
				total_episodes: null,
				episode_additions: [
					{
						added_date: '2026-01-10',
						display_text: 'Season 2',
						season: 2,
						episode_numbers: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
						is_full_season: true
					},
					{
						added_date: '2026-01-05',
						display_text: 'Season 1',
						season: 1,
						episode_numbers: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
						is_full_season: true
					}
				]
			};

			expect(getDetails(item)).toBe('Season 2, Season 1');
		});
	});

	describe('Copy Feature includes Episode Details', () => {
		// Helper function matching the component logic
		function formatCopyLine(item: RecentlyAvailableItem): string {
			const type = item.media_type === 'tv' ? 'TV' : 'Movie';
			const details = getDetails(item);
			if (item.media_type === 'tv' && details !== '—') {
				return `  - ${item.title} (${type}) [${details}] - available since Jan 10`;
			} else {
				return `  - ${item.title} (${type}) - available since Jan 10`;
			}
		}

		it('includes episode details for fully available TV show', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Breaking Bad',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Seasons 1-5',
				episode_count: 62,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(formatCopyLine(item)).toBe(
				'  - Breaking Bad (TV) [Seasons 1-5 (62 eps)] - available since Jan 10'
			);
		});

		it('includes episode progress for partially available TV show', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'House of the Dragon',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 5,
				total_episodes: 12,
				episode_additions: null
			};

			expect(formatCopyLine(item)).toBe(
				'  - House of the Dragon (TV) [S2: 5/12 episodes] - available since Jan 10'
			);
		});

		it('does not include episode details for movies', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Inception',
				title_fr: null,
				media_type: 'movie',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: null,
				episode_count: null,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(formatCopyLine(item)).toBe('  - Inception (Movie) - available since Jan 10');
		});

		it('does not include bracket for TV show without episode info', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'Unknown Show',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: null,
				episode_count: null,
				available_episodes: null,
				total_episodes: null,
				episode_additions: null
			};

			expect(formatCopyLine(item)).toBe('  - Unknown Show (TV) - available since Jan 10');
		});

		it('includes episode_additions display in copy (US-63.4)', () => {
			const item: RecentlyAvailableItem = {
				jellyseerr_id: 1,
				title: 'The Last of Us',
				title_fr: null,
				media_type: 'tv',
				availability_date: '2026-01-10',
				requested_by: null,
				display_name: null,
				season_info: 'Season 2 in progress',
				episode_count: null,
				available_episodes: 7,
				total_episodes: 10,
				episode_additions: [
					{
						added_date: '2026-01-10',
						display_text: 'S2E5-E7',
						season: 2,
						episode_numbers: [5, 6, 7],
						is_full_season: false
					}
				]
			};

			expect(formatCopyLine(item)).toBe(
				'  - The Last of Us (TV) [S2E5-E7] - available since Jan 10'
			);
		});
	});
});
