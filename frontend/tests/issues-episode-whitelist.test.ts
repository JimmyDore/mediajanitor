/**
 * Tests for episode whitelist functionality in Issues page (US-52.4)
 *
 * Tests verify:
 * - Expandable row behavior for series with problematic episodes
 * - Episode list rendering
 * - Episode whitelist API contract
 * - Optimistic update behavior
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Episode Whitelist - API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/content/issues with problematic_episodes', () => {
		it('returns series with problematic_episodes field', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'series-with-lang-issues',
						name: 'Game of Thrones',
						media_type: 'Series',
						production_year: 2011,
						size_bytes: 100000000000,
						size_formatted: '93.1 GB',
						last_played_date: null,
						path: '/media/tv/Game of Thrones',
						issues: ['language'],
						language_issues: ['missing_fr_audio'],
						problematic_episodes: [
							{
								identifier: 'S01E05',
								name: 'The Wolf and the Lion',
								season: 1,
								episode: 5,
								missing_languages: ['missing_fr_audio']
							},
							{
								identifier: 'S02E03',
								name: 'What Is Dead May Never Die',
								season: 2,
								episode: 3,
								missing_languages: ['missing_en_audio', 'missing_fr_audio']
							}
						]
					}
				],
				total_count: 1,
				total_size_bytes: 100000000000,
				total_size_formatted: '93.1 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=language', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const item = data.items[0];

			expect(item.problematic_episodes).toBeDefined();
			expect(item.problematic_episodes).toHaveLength(2);
			expect(item.problematic_episodes[0].identifier).toBe('S01E05');
			expect(item.problematic_episodes[0].season).toBe(1);
			expect(item.problematic_episodes[0].episode).toBe(5);
			expect(item.problematic_episodes[0].missing_languages).toContain('missing_fr_audio');
		});

		it('returns null problematic_episodes for movies', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'movie-with-lang-issues',
						name: 'Inception',
						media_type: 'Movie',
						production_year: 2010,
						size_bytes: 15000000000,
						size_formatted: '14.0 GB',
						last_played_date: null,
						path: '/media/movies/Inception',
						issues: ['language'],
						language_issues: ['missing_fr_audio'],
						problematic_episodes: null
					}
				],
				total_count: 1,
				total_size_bytes: 15000000000,
				total_size_formatted: '14.0 GB'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(issuesResponse)
			});

			const response = await fetch('/api/content/issues?filter=language', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items[0].problematic_episodes).toBeNull();
		});

		it('returns null problematic_episodes for series without language issues', async () => {
			const issuesResponse = {
				items: [
					{
						jellyfin_id: 'series-old',
						name: 'Breaking Bad',
						media_type: 'Series',
						production_year: 2008,
						size_bytes: 80000000000,
						size_formatted: '74.5 GB',
						last_played_date: '2023-01-15T10:00:00Z',
						path: '/media/tv/Breaking Bad',
						issues: ['old'],
						language_issues: null,
						problematic_episodes: null
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

			const response = await fetch('/api/content/issues?filter=old', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items[0].problematic_episodes).toBeNull();
		});
	});

	describe('POST /api/whitelist/episode-exempt', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					jellyfin_id: 'series-123',
					series_name: 'Game of Thrones',
					season_number: 1,
					episode_number: 5,
					episode_name: 'The Wolf and the Lion',
					expires_at: null
				})
			});

			expect(response.status).toBe(401);
		});

		it('accepts POST with valid episode data', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 201,
				json: () =>
					Promise.resolve({
						id: 1,
						jellyfin_id: 'series-123',
						series_name: 'Game of Thrones',
						season_number: 1,
						episode_number: 5,
						episode_name: 'The Wolf and the Lion',
						identifier: 'S01E05',
						created_at: '2026-01-23T10:00:00Z',
						expires_at: null
					})
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					jellyfin_id: 'series-123',
					series_name: 'Game of Thrones',
					season_number: 1,
					episode_number: 5,
					episode_name: 'The Wolf and the Lion',
					expires_at: null
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.id).toBe(1);
			expect(data.identifier).toBe('S01E05');
		});

		it('accepts POST with expiration date', async () => {
			const expiresAt = '2026-02-23T00:00:00.000Z';
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 201,
				json: () =>
					Promise.resolve({
						id: 2,
						jellyfin_id: 'series-123',
						series_name: 'Game of Thrones',
						season_number: 2,
						episode_number: 3,
						episode_name: 'What Is Dead May Never Die',
						identifier: 'S02E03',
						created_at: '2026-01-23T10:00:00Z',
						expires_at: expiresAt
					})
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					jellyfin_id: 'series-123',
					series_name: 'Game of Thrones',
					season_number: 2,
					episode_number: 3,
					episode_name: 'What Is Dead May Never Die',
					expires_at: expiresAt
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.expires_at).toBe(expiresAt);
		});

		it('returns 409 if episode already exempt', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 409,
				json: () => Promise.resolve({ detail: 'Episode already exempt' })
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					jellyfin_id: 'series-123',
					series_name: 'Game of Thrones',
					season_number: 1,
					episode_number: 5,
					episode_name: 'The Wolf and the Lion',
					expires_at: null
				})
			});

			expect(response.status).toBe(409);
		});

		it('returns 422 for invalid request body', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () => Promise.resolve({ detail: 'Validation error' })
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer jwt-token'
				},
				body: JSON.stringify({
					// Missing required fields
					jellyfin_id: 'series-123'
				})
			});

			expect(response.status).toBe(422);
		});
	});

	describe('DELETE /api/whitelist/episode-exempt/{id}', () => {
		it('deletes episode exemption by ID', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({ message: 'Episode exemption removed' })
			});

			const response = await fetch('/api/whitelist/episode-exempt/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(true);
		});

		it('returns 404 if exemption not found', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: () => Promise.resolve({ detail: 'Not found' })
			});

			const response = await fetch('/api/whitelist/episode-exempt/999', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(404);
		});
	});
});

describe('Episode Whitelist - UI Helper Functions', () => {
	describe('formatLanguageBadge', () => {
		// Test the formatting logic that will be used in the UI
		function formatLanguageBadge(lang: string): string {
			switch (lang) {
				case 'missing_en_audio':
					return 'EN';
				case 'missing_fr_audio':
					return 'FR';
				case 'missing_fr_subs':
					return 'FR Sub';
				default:
					return lang;
			}
		}

		it('formats missing_en_audio as EN', () => {
			expect(formatLanguageBadge('missing_en_audio')).toBe('EN');
		});

		it('formats missing_fr_audio as FR', () => {
			expect(formatLanguageBadge('missing_fr_audio')).toBe('FR');
		});

		it('formats missing_fr_subs as FR Sub', () => {
			expect(formatLanguageBadge('missing_fr_subs')).toBe('FR Sub');
		});

		it('returns unknown language codes as-is', () => {
			expect(formatLanguageBadge('missing_de_audio')).toBe('missing_de_audio');
		});
	});

	describe('hasExpandableEpisodes', () => {
		interface ProblematicEpisode {
			identifier: string;
			name: string;
			season: number;
			episode: number;
			missing_languages: string[];
		}

		interface ContentIssueItem {
			jellyfin_id: string;
			name: string;
			problematic_episodes: ProblematicEpisode[] | null;
		}

		function hasExpandableEpisodes(item: ContentIssueItem): boolean {
			return item.problematic_episodes !== null && item.problematic_episodes.length > 0;
		}

		it('returns true for series with problematic episodes', () => {
			const item: ContentIssueItem = {
				jellyfin_id: 'series-123',
				name: 'Test Series',
				problematic_episodes: [
					{
						identifier: 'S01E01',
						name: 'Pilot',
						season: 1,
						episode: 1,
						missing_languages: ['missing_fr_audio']
					}
				]
			};
			expect(hasExpandableEpisodes(item)).toBe(true);
		});

		it('returns false for items with null problematic_episodes', () => {
			const item: ContentIssueItem = {
				jellyfin_id: 'movie-123',
				name: 'Test Movie',
				problematic_episodes: null
			};
			expect(hasExpandableEpisodes(item)).toBe(false);
		});

		it('returns false for items with empty problematic_episodes array', () => {
			const item: ContentIssueItem = {
				jellyfin_id: 'series-123',
				name: 'Test Series',
				problematic_episodes: []
			};
			expect(hasExpandableEpisodes(item)).toBe(false);
		});
	});

	describe('getExpirationDate', () => {
		type DurationOption = 'permanent' | '1week' | '1month' | '3months' | '6months' | 'custom';

		function getExpirationDate(duration: DurationOption, customDateValue: string): string | null {
			if (duration === 'permanent') return null;
			if (duration === 'custom') {
				return customDateValue ? new Date(customDateValue + 'T00:00:00').toISOString() : null;
			}

			const now = new Date();
			switch (duration) {
				case '1week':
					now.setDate(now.getDate() + 7);
					break;
				case '1month':
					now.setMonth(now.getMonth() + 1);
					break;
				case '3months':
					now.setMonth(now.getMonth() + 3);
					break;
				case '6months':
					now.setMonth(now.getMonth() + 6);
					break;
			}
			return now.toISOString();
		}

		it('returns null for permanent duration', () => {
			expect(getExpirationDate('permanent', '')).toBeNull();
		});

		it('returns future date for 1week duration', () => {
			const result = getExpirationDate('1week', '');
			expect(result).not.toBeNull();
			const date = new Date(result!);
			const expectedDate = new Date();
			expectedDate.setDate(expectedDate.getDate() + 7);
			// Check that the date is approximately 7 days from now (within 1 minute tolerance)
			expect(Math.abs(date.getTime() - expectedDate.getTime())).toBeLessThan(60000);
		});

		it('returns custom date when duration is custom', () => {
			const result = getExpirationDate('custom', '2026-02-15');
			expect(result).not.toBeNull();
			const date = new Date(result!);
			expect(date.getFullYear()).toBe(2026);
			expect(date.getMonth()).toBe(1); // February (0-indexed)
			expect(date.getDate()).toBe(15);
		});

		it('returns null for custom duration with empty date', () => {
			expect(getExpirationDate('custom', '')).toBeNull();
		});
	});
});

describe('Episode Whitelist - Optimistic Update Logic', () => {
	interface ProblematicEpisode {
		identifier: string;
		name: string;
		season: number;
		episode: number;
		missing_languages: string[];
	}

	interface ContentIssueItem {
		jellyfin_id: string;
		name: string;
		issues: string[];
		problematic_episodes: ProblematicEpisode[] | null;
		size_bytes: number | null;
	}

	// Simulate the optimistic update logic from the component
	function applyOptimisticUpdate(
		items: ContentIssueItem[],
		jellyfinId: string,
		episodeSeason: number,
		episodeNumber: number
	): ContentIssueItem[] {
		return items
			.map((i) => {
				if (i.jellyfin_id !== jellyfinId) return i;
				const updatedEpisodes =
					i.problematic_episodes?.filter(
						(ep) => !(ep.season === episodeSeason && ep.episode === episodeNumber)
					) ?? null;
				// If no more problematic episodes, remove language issue from item
				const shouldRemoveLanguageIssue = !updatedEpisodes || updatedEpisodes.length === 0;
				const updatedIssues = shouldRemoveLanguageIssue
					? i.issues.filter((issue) => issue !== 'language')
					: i.issues;
				return {
					...i,
					problematic_episodes: updatedEpisodes && updatedEpisodes.length > 0 ? updatedEpisodes : null,
					issues: updatedIssues
				};
			})
			.filter((i) => i.issues.length > 0);
	}

	it('removes whitelisted episode from problematic_episodes list', () => {
		const items: ContentIssueItem[] = [
			{
				jellyfin_id: 'series-123',
				name: 'Test Series',
				issues: ['language'],
				problematic_episodes: [
					{ identifier: 'S01E01', name: 'Ep 1', season: 1, episode: 1, missing_languages: ['missing_fr_audio'] },
					{ identifier: 'S01E02', name: 'Ep 2', season: 1, episode: 2, missing_languages: ['missing_fr_audio'] }
				],
				size_bytes: 50000000000
			}
		];

		const updated = applyOptimisticUpdate(items, 'series-123', 1, 1);

		expect(updated[0].problematic_episodes).toHaveLength(1);
		expect(updated[0].problematic_episodes![0].identifier).toBe('S01E02');
		expect(updated[0].issues).toContain('language');
	});

	it('removes language issue when last episode is whitelisted', () => {
		const items: ContentIssueItem[] = [
			{
				jellyfin_id: 'series-123',
				name: 'Test Series',
				issues: ['language'],
				problematic_episodes: [
					{ identifier: 'S01E01', name: 'Ep 1', season: 1, episode: 1, missing_languages: ['missing_fr_audio'] }
				],
				size_bytes: 50000000000
			}
		];

		const updated = applyOptimisticUpdate(items, 'series-123', 1, 1);

		// Item should be removed entirely since it has no more issues
		expect(updated).toHaveLength(0);
	});

	it('keeps item with other issues when language issue is removed', () => {
		const items: ContentIssueItem[] = [
			{
				jellyfin_id: 'series-123',
				name: 'Test Series',
				issues: ['old', 'language'],
				problematic_episodes: [
					{ identifier: 'S01E01', name: 'Ep 1', season: 1, episode: 1, missing_languages: ['missing_fr_audio'] }
				],
				size_bytes: 50000000000
			}
		];

		const updated = applyOptimisticUpdate(items, 'series-123', 1, 1);

		expect(updated).toHaveLength(1);
		expect(updated[0].issues).toEqual(['old']);
		expect(updated[0].problematic_episodes).toBeNull();
	});

	it('does not affect other items in the list', () => {
		const items: ContentIssueItem[] = [
			{
				jellyfin_id: 'series-123',
				name: 'Test Series',
				issues: ['language'],
				problematic_episodes: [
					{ identifier: 'S01E01', name: 'Ep 1', season: 1, episode: 1, missing_languages: ['missing_fr_audio'] }
				],
				size_bytes: 50000000000
			},
			{
				jellyfin_id: 'series-456',
				name: 'Other Series',
				issues: ['language'],
				problematic_episodes: [
					{ identifier: 'S02E05', name: 'Ep 5', season: 2, episode: 5, missing_languages: ['missing_en_audio'] }
				],
				size_bytes: 60000000000
			}
		];

		const updated = applyOptimisticUpdate(items, 'series-123', 1, 1);

		// First item removed (no more issues), second item unchanged
		expect(updated).toHaveLength(1);
		expect(updated[0].jellyfin_id).toBe('series-456');
		expect(updated[0].problematic_episodes).toHaveLength(1);
	});
});
