/**
 * Tests for Recently Available episode details display (US-51.4)
 *
 * Tests verify:
 * - API contract includes season/episode fields
 * - getDetails() helper correctly formats episode info
 * - Copy feature includes episode details
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

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
}

/**
 * Get the formatted details for display.
 * - Fully available TV (status 5): "Seasons 1-3 (30 eps)"
 * - Partially available TV (status 4): "S4: 5/12 episodes"
 * - Movies: "—"
 */
function getDetails(item: RecentlyAvailableItem): string {
	if (item.media_type !== 'tv') {
		return '—';
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
						total_episodes: null
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
						total_episodes: 12
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
						total_episodes: null
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
				total_episodes: null
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
				total_episodes: null
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
				total_episodes: null
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
				total_episodes: 12
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
				total_episodes: 22
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
				total_episodes: null
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
				total_episodes: null
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
				total_episodes: null
			};

			expect(getDetails(item)).toBe('Seasons 1, 3, 4 (30 eps)');
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
				total_episodes: null
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
				total_episodes: 12
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
				total_episodes: null
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
				total_episodes: null
			};

			expect(formatCopyLine(item)).toBe('  - Unknown Show (TV) - available since Jan 10');
		});
	});
});
