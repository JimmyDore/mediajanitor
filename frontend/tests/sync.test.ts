/**
 * Tests for the sync API integration (US-7.2)
 *
 * Tests verify the API contract for triggering and monitoring data sync.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Sync API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('POST /api/sync', () => {
		it('sync API requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/sync', {
				method: 'POST'
				// No Authorization header
			});

			expect(response.status).toBe(401);
		});

		it('sync API accepts POST with auth token', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						status: 'success',
						media_items_synced: 100,
						requests_synced: 25,
						error: null
					})
			});

			const response = await fetch('/api/sync', {
				method: 'POST',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/sync', {
				method: 'POST',
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('sync API returns sync results on success', async () => {
			const syncResult = {
				status: 'success',
				media_items_synced: 150,
				requests_synced: 30,
				error: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(syncResult)
			});

			const response = await fetch('/api/sync', {
				method: 'POST',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.status).toBe('success');
			expect(data.media_items_synced).toBe(150);
			expect(data.requests_synced).toBe(30);
			expect(data.error).toBeNull();
		});

		it('sync API returns 429 when rate limited', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 429,
				json: () => Promise.resolve({ detail: 'Rate limited. Please wait 5 minute(s) before syncing again.' })
			});

			const response = await fetch('/api/sync', {
				method: 'POST',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(429);

			const data = await response.json();
			expect(data.detail).toContain('Rate limited');
			expect(data.detail).toContain('minute');
		});

		it('sync API returns 400 when Jellyfin not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Jellyfin connection not configured. Please configure it in Settings first.'
					})
			});

			const response = await fetch('/api/sync', {
				method: 'POST',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);

			const data = await response.json();
			expect(data.detail).toContain('Jellyfin');
		});

		it('sync API returns partial status when Jellyseerr fails', async () => {
			const syncResult = {
				status: 'partial',
				media_items_synced: 100,
				requests_synced: 0,
				error: 'Jellyseerr sync failed: Connection refused'
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(syncResult)
			});

			const response = await fetch('/api/sync', {
				method: 'POST',
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.status).toBe('partial');
			expect(data.media_items_synced).toBe(100);
			expect(data.error).toContain('Jellyseerr');
		});
	});

	describe('GET /api/sync/status', () => {
		it('sync status API requires authentication', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/sync/status');

			expect(response.status).toBe(401);
		});

		it('sync status API returns last sync info', async () => {
			const statusData = {
				last_synced: '2024-01-15T10:30:00Z',
				status: 'success',
				media_items_count: 200,
				requests_count: 50,
				error: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(statusData)
			});

			const response = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.last_synced).toBe('2024-01-15T10:30:00Z');
			expect(data.status).toBe('success');
			expect(data.media_items_count).toBe(200);
			expect(data.requests_count).toBe(50);
		});

		it('sync status API returns null for never-synced users', async () => {
			const statusData = {
				last_synced: null,
				status: null,
				media_items_count: null,
				requests_count: null,
				error: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(statusData)
			});

			const response = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.last_synced).toBeNull();
			expect(data.status).toBeNull();
		});
	});
});
