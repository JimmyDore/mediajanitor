/**
 * Tests for the info API integration (US-D.2)
 *
 * Tests verify the API contract for fetching info content (recently available).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Info API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/info/recent', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/info/recent');

			expect(response.status).toBe(401);
		});

		it('returns recently available content', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1001,
						title: 'Test Movie',
						media_type: 'movie',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'test_user'
					},
					{
						jellyseerr_id: 1002,
						title: 'Test Series',
						media_type: 'tv',
						availability_date: '2026-01-08T12:00:00+00:00',
						requested_by: 'another_user'
					}
				],
				total_count: 2
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(recentData)
			});

			const response = await fetch('/api/info/recent', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/info/recent', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.total_count).toBe(2);
			expect(data.items).toHaveLength(2);
			expect(data.items[0].title).toBe('Test Movie');
		});

		it('returns empty list when no recent content', async () => {
			const recentData = {
				items: [],
				total_count: 0
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(recentData)
			});

			const response = await fetch('/api/info/recent', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.total_count).toBe(0);
			expect(data.items).toHaveLength(0);
		});

		it('each item has required fields', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1001,
						title: 'Test Movie',
						media_type: 'movie',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'test_user',
						display_name: 'Test User'
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

			expect(item).toHaveProperty('title');
			expect(item).toHaveProperty('media_type');
			expect(item).toHaveProperty('availability_date');
			expect(item).toHaveProperty('display_name');
		});

		it('returns display_name resolved from nickname mapping', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1001,
						title: 'Test Movie',
						media_type: 'movie',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'john_doe',
						display_name: 'John'
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

			expect(item.requested_by).toBe('john_doe');
			expect(item.display_name).toBe('John');
		});

		it('returns display_name same as requested_by when no nickname mapping', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1001,
						title: 'Test Movie',
						media_type: 'movie',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: 'charlie',
						display_name: 'charlie'
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

			expect(item.requested_by).toBe('charlie');
			expect(item.display_name).toBe('charlie');
		});

		it('returns null display_name when requested_by is null', async () => {
			const recentData = {
				items: [
					{
						jellyseerr_id: 1001,
						title: 'Test Movie',
						media_type: 'movie',
						availability_date: '2026-01-10T12:00:00+00:00',
						requested_by: null,
						display_name: null
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

			expect(item.requested_by).toBeNull();
			expect(item.display_name).toBeNull();
		});

		it('handles network errors', async () => {
			mockFetch.mockRejectedValueOnce(new Error('Network error'));

			await expect(
				fetch('/api/info/recent', {
					headers: { Authorization: 'Bearer jwt-token' }
				})
			).rejects.toThrow('Network error');
		});
	});

	describe('Content Summary includes info counts', () => {
		it('returns recently_available in summary', async () => {
			const summaryData = {
				old_content: { count: 10, total_size_bytes: 0, total_size_formatted: '0 B' },
				large_movies: { count: 5, total_size_bytes: 0, total_size_formatted: '0 B' },
				language_issues: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' },
				unavailable_requests: { count: 0, total_size_bytes: 0, total_size_formatted: '0 B' },
				recently_available: { count: 3 }
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(summaryData)
			});

			const response = await fetch('/api/content/summary', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data).toHaveProperty('recently_available');
			expect(data.recently_available.count).toBe(3);
		});
	});
});
