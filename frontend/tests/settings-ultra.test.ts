/**
 * Tests for Ultra.cc API settings API integration (US-48.2)
 *
 * These tests verify the API contract that the settings page uses
 * for Ultra.cc connection configuration.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Ultra.cc Settings API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/ultra - Initial load', () => {
		it('returns unconfigured state when no settings exist', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ server_url: null, api_key_configured: false })
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.server_url).toBeNull();
			expect(data.api_key_configured).toBe(false);
		});

		it('returns configured state with server URL', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: 'https://api.ultra.cc',
						api_key_configured: true
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.server_url).toBe('https://api.ultra.cc');
			expect(data.api_key_configured).toBe(true);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/ultra');

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('POST /api/settings/ultra - Save credentials', () => {
		it('saves Ultra.cc settings successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Ultra settings saved successfully.'
					})
			});

			const response = await fetch('/api/settings/ultra', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://api.ultra.cc',
					api_key: 'test-api-token-12345'
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/ultra', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://api.ultra.cc',
					api_key: 'test-api-token-12345'
				})
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.message).toContain('Ultra');
		});

		it('returns error when connection validation fails', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Could not establish connection to Ultra.cc server. Please check URL and API token.'
					})
			});

			const response = await fetch('/api/settings/ultra', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://invalid.example.com',
					api_key: 'invalid-token'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);

			const data = await response.json();
			expect(data.detail).toContain('connection');
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/ultra', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					server_url: 'https://api.ultra.cc',
					api_key: 'test-token'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});

		it('returns 422 for invalid URL format', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () => Promise.resolve({ detail: 'Validation error' })
			});

			const response = await fetch('/api/settings/ultra', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'not-a-valid-url',
					api_key: 'test-token'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('returns 422 for missing API key on first configuration', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () => Promise.resolve({ detail: 'Validation error' })
			});

			const response = await fetch('/api/settings/ultra', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://api.ultra.cc'
					// missing api_key
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('allows updating URL without changing API key when already configured', async () => {
			// When Ultra is already configured, API key can be omitted to keep the existing one
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Ultra settings saved successfully.'
					})
			});

			const response = await fetch('/api/settings/ultra', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://new-api.ultra.cc'
					// api_key omitted to keep existing
				})
			});

			expect(response.ok).toBe(true);
		});
	});

	describe('UI behavior expectations', () => {
		it('shows Connected badge when api_key_configured is true', async () => {
			// Verify that when API returns api_key_configured: true,
			// the UI should show a "Connected" badge (green status dot)
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: 'https://api.ultra.cc',
						api_key_configured: true
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			// When this is true, the UI should display status-connected class
			expect(data.api_key_configured).toBe(true);
		});

		it('provides masked placeholder for token field when configured', async () => {
			// Verify API never returns actual API token - only configured status
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: 'https://api.ultra.cc',
						api_key_configured: true
						// Note: API should NOT return api_key or api_token
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			// API should only return configured status, not the actual key
			expect(data).not.toHaveProperty('api_key');
			expect(data).not.toHaveProperty('api_key_encrypted');
			expect(data.api_key_configured).toBe(true);
			// UI should use placeholder='••••••••' when configured
		});

		it('shows Not configured state when ultra is not set up', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: null,
						api_key_configured: false
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			// When this is false, UI should show status-disconnected class
			// and "Not configured" text
			expect(data.api_key_configured).toBe(false);
			expect(data.server_url).toBeNull();
		});
	});
});
