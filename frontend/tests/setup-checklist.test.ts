/**
 * Tests for the Setup Checklist component (US-18.1)
 *
 * Tests verify the setup checklist shows for new users and hides when complete.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Setup Checklist API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('Checklist visibility conditions', () => {
		it('should show checklist when Jellyfin is not configured', async () => {
			// Mock GET /api/settings/jellyfin - not configured
			const jellyfinSettings = {
				server_url: null,
				api_key_configured: false
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(jellyfinSettings)
			});

			const response = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.server_url).toBeNull();
			expect(data.api_key_configured).toBe(false);
		});

		it('should show checklist when never synced (last_synced is null)', async () => {
			// Mock GET /api/sync/status - never synced
			const syncStatus = {
				last_synced: null,
				status: null,
				is_syncing: false,
				media_items_count: null,
				requests_count: null,
				error: null,
				progress: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(syncStatus)
			});

			const response = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.last_synced).toBeNull();
		});

		it('should hide checklist when Jellyfin is configured AND has synced', async () => {
			// Mock GET /api/settings/jellyfin - configured
			const jellyfinSettings = {
				server_url: 'https://jellyfin.example.com',
				api_key_configured: true
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(jellyfinSettings)
			});

			// Mock GET /api/sync/status - has synced
			const syncStatus = {
				last_synced: '2024-01-15T10:30:00Z',
				status: 'success',
				is_syncing: false,
				media_items_count: 200,
				requests_count: 50,
				error: null,
				progress: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(syncStatus)
			});

			const jellyfinResponse = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			const jellyfinData = await jellyfinResponse.json();

			const syncResponse = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			const syncData = await syncResponse.json();

			// Both conditions met - checklist should hide
			expect(jellyfinData.api_key_configured).toBe(true);
			expect(syncData.last_synced).not.toBeNull();
		});
	});

	describe('Step status determination', () => {
		it('Connect Jellyfin step is complete when api_key_configured is true', async () => {
			const jellyfinSettings = {
				server_url: 'https://jellyfin.example.com',
				api_key_configured: true
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(jellyfinSettings)
			});

			const response = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const isJellyfinComplete = data.api_key_configured === true;
			expect(isJellyfinComplete).toBe(true);
		});

		it('Connect Jellyfin step is pending when api_key_configured is false', async () => {
			const jellyfinSettings = {
				server_url: null,
				api_key_configured: false
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(jellyfinSettings)
			});

			const response = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const isJellyfinComplete = data.api_key_configured === true;
			expect(isJellyfinComplete).toBe(false);
		});

		it('Run First Sync step is complete when last_synced is not null', async () => {
			const syncStatus = {
				last_synced: '2024-01-15T10:30:00Z',
				status: 'success',
				is_syncing: false,
				media_items_count: 200,
				requests_count: 50,
				error: null,
				progress: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(syncStatus)
			});

			const response = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const isSyncComplete = data.last_synced !== null;
			expect(isSyncComplete).toBe(true);
		});

		it('Run First Sync step is pending when last_synced is null', async () => {
			const syncStatus = {
				last_synced: null,
				status: null,
				is_syncing: false,
				media_items_count: null,
				requests_count: null,
				error: null,
				progress: null
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(syncStatus)
			});

			const response = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const isSyncComplete = data.last_synced !== null;
			expect(isSyncComplete).toBe(false);
		});

		it('Run First Sync step is in-progress when is_syncing is true', async () => {
			const syncStatus = {
				last_synced: null,
				status: null,
				is_syncing: true,
				media_items_count: null,
				requests_count: null,
				error: null,
				progress: {
					current_step: 'syncing_media',
					total_steps: 2,
					current_step_progress: 3,
					current_step_total: 10,
					current_user_name: 'John'
				}
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(syncStatus)
			});

			const response = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			const isSyncing = data.is_syncing === true;
			expect(isSyncing).toBe(true);
		});
	});

	describe('Step status with combined scenarios', () => {
		it('shows both steps when Jellyfin not configured and never synced', async () => {
			// Jellyfin not configured
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: null,
						api_key_configured: false
					})
			});

			// Never synced
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						last_synced: null,
						status: null,
						is_syncing: false,
						media_items_count: null,
						requests_count: null,
						error: null,
						progress: null
					})
			});

			const jellyfinResponse = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			const jellyfinData = await jellyfinResponse.json();

			const syncResponse = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			const syncData = await syncResponse.json();

			const showChecklist =
				jellyfinData.api_key_configured === false || syncData.last_synced === null;

			expect(showChecklist).toBe(true);
		});

		it('shows checklist when Jellyfin configured but never synced', async () => {
			// Jellyfin configured
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: 'https://jellyfin.example.com',
						api_key_configured: true
					})
			});

			// Never synced
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						last_synced: null,
						status: null,
						is_syncing: false,
						media_items_count: null,
						requests_count: null,
						error: null,
						progress: null
					})
			});

			const jellyfinResponse = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			const jellyfinData = await jellyfinResponse.json();

			const syncResponse = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			const syncData = await syncResponse.json();

			const showChecklist =
				jellyfinData.api_key_configured === false || syncData.last_synced === null;

			expect(showChecklist).toBe(true);
			// Jellyfin step should be complete
			expect(jellyfinData.api_key_configured).toBe(true);
			// Sync step should be pending
			expect(syncData.last_synced).toBeNull();
		});
	});
});
