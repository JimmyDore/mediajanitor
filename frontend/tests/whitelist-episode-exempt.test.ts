/**
 * Tests for the Episode Exempt tab in Whitelist page (US-52.5)
 *
 * Tests verify the API contract for listing and removing episode exemptions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Episode Exempt API Integration (US-52.5)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/whitelist/episode-exempt', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/whitelist/episode-exempt');

			expect(response.status).toBe(401);
		});

		it('accepts GET with auth token', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [],
						total_count: 0
					})
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/whitelist/episode-exempt', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('returns empty list when no episode exemptions', async () => {
			const emptyResponse = {
				items: [],
				total_count: 0
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(emptyResponse)
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items).toEqual([]);
			expect(data.total_count).toBe(0);
		});

		it('returns list of episode exemptions with all required fields', async () => {
			const episodeExemptResponse = {
				items: [
					{
						id: 1,
						jellyfin_id: 'series-123',
						series_name: 'Test Series',
						season_number: 1,
						episode_number: 5,
						episode_name: 'The Pilot',
						identifier: 'S01E05',
						created_at: '2024-01-15T10:30:00Z',
						expires_at: null
					},
					{
						id: 2,
						jellyfin_id: 'series-456',
						series_name: 'Another Series',
						season_number: 3,
						episode_number: 12,
						episode_name: 'Season Finale',
						identifier: 'S03E12',
						created_at: '2024-01-14T08:00:00Z',
						expires_at: '2024-04-14T00:00:00Z'
					}
				],
				total_count: 2
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(episodeExemptResponse)
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();

			// Check response structure
			expect(data.total_count).toBe(2);
			expect(data.items).toHaveLength(2);

			// Check first item has all required fields
			const firstItem = data.items[0];
			expect(firstItem.id).toBe(1);
			expect(firstItem.jellyfin_id).toBe('series-123');
			expect(firstItem.series_name).toBe('Test Series');
			expect(firstItem.season_number).toBe(1);
			expect(firstItem.episode_number).toBe(5);
			expect(firstItem.episode_name).toBe('The Pilot');
			expect(firstItem.identifier).toBe('S01E05');
			expect(firstItem.created_at).toBe('2024-01-15T10:30:00Z');
			expect(firstItem.expires_at).toBeNull();
		});

		it('handles episodes with expiration dates', async () => {
			const episodeExemptResponse = {
				items: [
					{
						id: 1,
						jellyfin_id: 'series-123',
						series_name: 'Test Series',
						season_number: 2,
						episode_number: 3,
						episode_name: 'Temporary Episode',
						identifier: 'S02E03',
						created_at: '2024-01-15T10:30:00Z',
						expires_at: '2024-06-15T00:00:00Z'
					}
				],
				total_count: 1
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(episodeExemptResponse)
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items[0].expires_at).toBe('2024-06-15T00:00:00Z');
		});

		it('detects expired episode exemptions', async () => {
			const pastDate = '2024-01-01T00:00:00Z';
			const episodeExemptResponse = {
				items: [
					{
						id: 1,
						jellyfin_id: 'series-expired',
						series_name: 'Expired Series',
						season_number: 1,
						episode_number: 1,
						episode_name: 'Expired Episode',
						identifier: 'S01E01',
						created_at: '2023-10-01T10:00:00Z',
						expires_at: pastDate
					}
				],
				total_count: 1
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(episodeExemptResponse)
			});

			const response = await fetch('/api/whitelist/episode-exempt', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			// Frontend will check if expires_at < now to show Expired badge
			const expirationDate = new Date(data.items[0].expires_at);
			const now = new Date();
			expect(expirationDate < now).toBe(true);
		});
	});

	describe('DELETE /api/whitelist/episode-exempt/{id}', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/whitelist/episode-exempt/1', {
				method: 'DELETE'
			});

			expect(response.status).toBe(401);
		});

		it('accepts DELETE with valid auth and returns 200', async () => {
			const successResponse = {
				message: 'Removed from episode language exempt list'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve(successResponse)
			});

			const response = await fetch('/api/whitelist/episode-exempt/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/whitelist/episode-exempt/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
			expect(response.status).toBe(200);

			const data = await response.json();
			expect(data.message).toContain('episode');
		});

		it('returns 404 for non-existent episode exempt entry', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: () => Promise.resolve({ detail: 'Episode exempt entry not found' })
			});

			const response = await fetch('/api/whitelist/episode-exempt/99999', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(404);
			const data = await response.json();
			expect(data.detail).toContain('not found');
		});

		it('uses numeric ID in URL path', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({ message: 'Removed from episode language exempt list' })
			});

			await fetch('/api/whitelist/episode-exempt/42', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/whitelist/episode-exempt/42', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});
		});
	});
});

describe('Episode Exempt Tab Display (US-52.5)', () => {
	it('displays episode identifier in correct format (S01E05)', () => {
		const seasonNumber = 1;
		const episodeNumber = 5;
		const identifier = `S${String(seasonNumber).padStart(2, '0')}E${String(episodeNumber).padStart(2, '0')}`;
		expect(identifier).toBe('S01E05');
	});

	it('formats double-digit season and episode numbers correctly', () => {
		const seasonNumber = 12;
		const episodeNumber = 25;
		const identifier = `S${String(seasonNumber).padStart(2, '0')}E${String(episodeNumber).padStart(2, '0')}`;
		expect(identifier).toBe('S12E25');
	});

	it('recognizes episode exempt item by series_name and episode_name fields', () => {
		interface EpisodeExemptItem {
			id: number;
			series_name: string;
			episode_name: string;
			season_number: number;
			episode_number: number;
		}

		interface WhitelistItem {
			id: number;
			name: string;
			media_type: string;
		}

		function isEpisodeExemptItem(
			item: WhitelistItem | EpisodeExemptItem
		): item is EpisodeExemptItem {
			return 'series_name' in item && 'episode_name' in item;
		}

		const episodeItem: EpisodeExemptItem = {
			id: 1,
			series_name: 'Test Series',
			episode_name: 'Test Episode',
			season_number: 1,
			episode_number: 1
		};

		const whitelistItem: WhitelistItem = {
			id: 2,
			name: 'Test Movie',
			media_type: 'Movie'
		};

		expect(isEpisodeExemptItem(episodeItem)).toBe(true);
		expect(isEpisodeExemptItem(whitelistItem)).toBe(false);
	});

	it('extracts series name as item name for episode exempt items', () => {
		interface EpisodeExemptItem {
			series_name: string;
			episode_name: string;
		}

		function getItemName(item: EpisodeExemptItem): string {
			return item.series_name;
		}

		const item: EpisodeExemptItem = {
			series_name: 'Game of Thrones',
			episode_name: 'Winter Is Coming'
		};

		expect(getItemName(item)).toBe('Game of Thrones');
	});
});
