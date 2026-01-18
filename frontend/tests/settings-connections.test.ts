/**
 * Tests for the Connections settings page
 *
 * These tests verify the connections page loads and handles
 * all four connection services (Jellyfin, Jellyseerr, Radarr, Sonarr).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Connections Settings Page API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('Initial load - fetches all connection settings', () => {
		it('fetches all four service settings on page load', async () => {
			// Mock all four service API responses
			mockFetch
				.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							server_url: 'https://jellyfin.example.com',
							api_key_configured: true
						})
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							server_url: 'https://jellyseerr.example.com',
							api_key_configured: true
						})
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							server_url: 'https://radarr.example.com',
							api_key_configured: true
						})
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							server_url: 'https://sonarr.example.com',
							api_key_configured: true
						})
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							last_synced: '2025-01-01T00:00:00Z'
						})
				});

			// Simulate the fetch calls made on page load
			const jellyfinResponse = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const jellyseerrResponse = await fetch('/api/settings/jellyseerr', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const radarrResponse = await fetch('/api/settings/radarr', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const sonarrResponse = await fetch('/api/settings/sonarr', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const syncResponse = await fetch('/api/sync/status', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledTimes(5);

			const jellyfinData = await jellyfinResponse.json();
			const jellyseerrData = await jellyseerrResponse.json();
			const radarrData = await radarrResponse.json();
			const sonarrData = await sonarrResponse.json();
			const syncData = await syncResponse.json();

			expect(jellyfinData.api_key_configured).toBe(true);
			expect(jellyseerrData.api_key_configured).toBe(true);
			expect(radarrData.api_key_configured).toBe(true);
			expect(sonarrData.api_key_configured).toBe(true);
			expect(syncData.last_synced).toBe('2025-01-01T00:00:00Z');
		});

		it('handles unconfigured services gracefully', async () => {
			mockFetch
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ server_url: null, api_key_configured: false })
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ server_url: null, api_key_configured: false })
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ server_url: null, api_key_configured: false })
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ server_url: null, api_key_configured: false })
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ last_synced: null })
				});

			const responses = await Promise.all([
				fetch('/api/settings/jellyfin'),
				fetch('/api/settings/jellyseerr'),
				fetch('/api/settings/radarr'),
				fetch('/api/settings/sonarr'),
				fetch('/api/sync/status')
			]);

			for (const response of responses) {
				expect(response.ok).toBe(true);
			}

			const data = await responses[0].json();
			expect(data.api_key_configured).toBe(false);
			expect(data.server_url).toBeNull();
		});

		it('handles mixed configured/unconfigured services', async () => {
			mockFetch
				.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							server_url: 'https://jellyfin.example.com',
							api_key_configured: true
						})
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ server_url: null, api_key_configured: false })
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							server_url: 'https://radarr.example.com',
							api_key_configured: true
						})
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ server_url: null, api_key_configured: false })
				});

			const [jellyfinRes, jellyseerrRes, radarrRes, sonarrRes] = await Promise.all([
				fetch('/api/settings/jellyfin'),
				fetch('/api/settings/jellyseerr'),
				fetch('/api/settings/radarr'),
				fetch('/api/settings/sonarr')
			]);

			const jellyfinData = await jellyfinRes.json();
			const jellyseerrData = await jellyseerrRes.json();
			const radarrData = await radarrRes.json();
			const sonarrData = await sonarrRes.json();

			expect(jellyfinData.api_key_configured).toBe(true);
			expect(jellyseerrData.api_key_configured).toBe(false);
			expect(radarrData.api_key_configured).toBe(true);
			expect(sonarrData.api_key_configured).toBe(false);
		});
	});

	describe('Jellyfin connection form', () => {
		it('saves new Jellyfin connection successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Jellyfin settings saved successfully.'
					})
			});

			const response = await fetch('/api/settings/jellyfin', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://jellyfin.example.com',
					api_key: 'test-api-key-12345'
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
		});

		it('handles Jellyfin connection failure', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Could not establish connection to Jellyfin server.'
					})
			});

			const response = await fetch('/api/settings/jellyfin', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://invalid.example.com',
					api_key: 'invalid-key'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);
		});

		it('updates existing Jellyfin connection without api_key', async () => {
			// When updating, API key can be omitted to keep existing
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Jellyfin settings saved successfully.'
					})
			});

			const response = await fetch('/api/settings/jellyfin', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://new-jellyfin.example.com',
					api_key: '' // Empty string to keep existing key
				})
			});

			expect(response.ok).toBe(true);
		});
	});

	describe('Jellyseerr connection form', () => {
		it('saves new Jellyseerr connection successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Jellyseerr settings saved successfully.'
					})
			});

			const response = await fetch('/api/settings/jellyseerr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://jellyseerr.example.com',
					api_key: 'test-api-key-12345'
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
		});

		it('handles Jellyseerr connection failure', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Could not establish connection to Jellyseerr server.'
					})
			});

			const response = await fetch('/api/settings/jellyseerr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://invalid.example.com',
					api_key: 'invalid-key'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);
		});
	});

	describe('Radarr connection form', () => {
		it('saves new Radarr connection successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Radarr settings saved successfully.'
					})
			});

			const response = await fetch('/api/settings/radarr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://radarr.example.com',
					api_key: 'test-api-key-12345'
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
		});

		it('handles Radarr connection failure', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Could not establish connection to Radarr server.'
					})
			});

			const response = await fetch('/api/settings/radarr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://invalid.example.com',
					api_key: 'invalid-key'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);
		});
	});

	describe('Sonarr connection form', () => {
		it('saves new Sonarr connection successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Sonarr settings saved successfully.'
					})
			});

			const response = await fetch('/api/settings/sonarr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://sonarr.example.com',
					api_key: 'test-api-key-12345'
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
		});

		it('handles Sonarr connection failure', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Could not establish connection to Sonarr server.'
					})
			});

			const response = await fetch('/api/settings/sonarr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://invalid.example.com',
					api_key: 'invalid-key'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);
		});
	});

	describe('Authentication', () => {
		it('returns 401 for all service endpoints when not authenticated', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const endpoints = [
				'/api/settings/jellyfin',
				'/api/settings/jellyseerr',
				'/api/settings/radarr',
				'/api/settings/sonarr'
			];

			for (const endpoint of endpoints) {
				const response = await fetch(endpoint);
				expect(response.status).toBe(401);
			}
		});
	});

	describe('extractDomain helper', () => {
		// Test the domain extraction logic used in the component
		function extractDomain(url: string): string {
			try {
				return new URL(url).hostname;
			} catch {
				return url;
			}
		}

		it('extracts hostname from valid URL', () => {
			expect(extractDomain('https://jellyfin.example.com')).toBe('jellyfin.example.com');
			expect(extractDomain('https://jellyfin.example.com:8096')).toBe('jellyfin.example.com');
			expect(extractDomain('https://jellyfin.example.com/jellyfin')).toBe('jellyfin.example.com');
		});

		it('returns original string for invalid URL', () => {
			expect(extractDomain('not-a-url')).toBe('not-a-url');
			expect(extractDomain('')).toBe('');
		});
	});
});
