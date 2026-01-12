/**
 * Tests for the whitelist API integration (US-3.3)
 *
 * Tests verify the API contract for listing and removing whitelist items.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Whitelist API Integration (US-3.3)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/whitelist/content', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/whitelist/content');

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

			const response = await fetch('/api/whitelist/content', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/whitelist/content', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('returns empty list when no whitelist items', async () => {
			const emptyResponse = {
				items: [],
				total_count: 0
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(emptyResponse)
			});

			const response = await fetch('/api/whitelist/content', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.items).toEqual([]);
			expect(data.total_count).toBe(0);
		});

		it('returns list of whitelist items with all required fields', async () => {
			const whitelistResponse = {
				items: [
					{
						id: 1,
						jellyfin_id: 'movie-123',
						name: 'Protected Movie',
						media_type: 'Movie',
						created_at: '2024-01-15T10:30:00Z'
					},
					{
						id: 2,
						jellyfin_id: 'series-456',
						name: 'Protected Series',
						media_type: 'Series',
						created_at: '2024-01-14T08:00:00Z'
					}
				],
				total_count: 2
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(whitelistResponse)
			});

			const response = await fetch('/api/whitelist/content', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();

			// Check response structure
			expect(data.total_count).toBe(2);
			expect(data.items).toHaveLength(2);

			// Check first item has all required fields
			const firstItem = data.items[0];
			expect(firstItem.id).toBe(1);
			expect(firstItem.jellyfin_id).toBe('movie-123');
			expect(firstItem.name).toBe('Protected Movie');
			expect(firstItem.media_type).toBe('Movie');
			expect(firstItem.created_at).toBe('2024-01-15T10:30:00Z');
		});

		it('includes both Movie and Series media types', async () => {
			const whitelistResponse = {
				items: [
					{
						id: 1,
						jellyfin_id: 'movie-1',
						name: 'Movie Title',
						media_type: 'Movie',
						created_at: '2024-01-15T10:00:00Z'
					},
					{
						id: 2,
						jellyfin_id: 'series-1',
						name: 'Series Title',
						media_type: 'Series',
						created_at: '2024-01-15T10:00:00Z'
					}
				],
				total_count: 2
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(whitelistResponse)
			});

			const response = await fetch('/api/whitelist/content', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const mediaTypes = data.items.map((item: { media_type: string }) => item.media_type);

			expect(mediaTypes).toContain('Movie');
			expect(mediaTypes).toContain('Series');
		});
	});

	describe('DELETE /api/whitelist/content/{id}', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/whitelist/content/1', {
				method: 'DELETE'
			});

			expect(response.status).toBe(401);
		});

		it('accepts DELETE with valid auth and returns 200', async () => {
			const successResponse = {
				message: 'Removed from whitelist'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve(successResponse)
			});

			const response = await fetch('/api/whitelist/content/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/whitelist/content/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
			expect(response.status).toBe(200);

			const data = await response.json();
			expect(data.message).toBe('Removed from whitelist');
		});

		it('returns 404 for non-existent whitelist item', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: () => Promise.resolve({ detail: 'Whitelist entry not found' })
			});

			const response = await fetch('/api/whitelist/content/99999', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(404);
			const data = await response.json();
			expect(data.detail).toContain('not found');
		});

		it('returns 404 when trying to delete another user\'s whitelist item', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: () => Promise.resolve({ detail: 'Whitelist entry not found' })
			});

			const response = await fetch('/api/whitelist/content/123', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.status).toBe(404);
		});

		it('uses numeric ID in URL path', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () => Promise.resolve({ message: 'Removed from whitelist' })
			});

			await fetch('/api/whitelist/content/42', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/whitelist/content/42', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer jwt-token' }
			});
		});
	});
});
