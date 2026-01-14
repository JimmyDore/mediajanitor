/**
 * Tests for the Sonarr settings API integration
 *
 * These tests verify the API contract that the settings page uses
 * for Sonarr connection configuration.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Sonarr Settings API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/sonarr', () => {
		it('returns unconfigured state when no settings exist', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ server_url: null, api_key_configured: false })
			});

			const response = await fetch('/api/settings/sonarr', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/sonarr', {
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
						server_url: 'https://sonarr.example.com',
						api_key_configured: true
					})
			});

			const response = await fetch('/api/settings/sonarr', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.server_url).toBe('https://sonarr.example.com');
			expect(data.api_key_configured).toBe(true);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/sonarr');

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('POST /api/settings/sonarr', () => {
		it('saves Sonarr settings successfully', async () => {
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

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/sonarr', {
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
			expect(data.message).toContain('Sonarr');
		});

		it('returns error when connection validation fails', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Could not establish connection to Sonarr server. Please check URL and API key.'
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

			const data = await response.json();
			expect(data.detail).toContain('connection');
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/sonarr', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					server_url: 'https://sonarr.example.com',
					api_key: 'test-key'
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

			const response = await fetch('/api/settings/sonarr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'not-a-valid-url',
					api_key: 'test-key'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('returns 422 for missing API key', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () => Promise.resolve({ detail: 'Validation error' })
			});

			const response = await fetch('/api/settings/sonarr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					server_url: 'https://sonarr.example.com'
					// missing api_key
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});
});
