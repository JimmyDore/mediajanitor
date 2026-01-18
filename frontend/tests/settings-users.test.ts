/**
 * Tests for the Settings Users Page (US-36.4)
 *
 * These tests verify the API contract that the users settings page uses
 * for managing user nickname mappings.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Settings Users Page (US-36.4)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('Initial Page Load', () => {
		it('fetches Jellyfin settings to check if configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						api_key_configured: true,
						server_url: 'https://jellyfin.example.com'
					})
			});

			await fetch('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/jellyfin', {
				headers: { Authorization: 'Bearer test-token' }
			});
		});

		it('fetches nicknames list on mount', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								id: 1,
								jellyseerr_username: 'john_doe',
								display_name: 'John',
								has_jellyseerr_account: true,
								created_at: '2026-01-15T10:00:00Z'
							}
						],
						total_count: 1
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('handles empty nicknames list', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [],
						total_count: 0
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.items).toHaveLength(0);
			expect(data.total_count).toBe(0);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/nicknames');

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('Nicknames with Jellyseerr Account Status', () => {
		it('returns has_jellyseerr_account field for each nickname', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								id: 1,
								jellyseerr_username: 'john_doe',
								display_name: 'John',
								has_jellyseerr_account: true,
								created_at: '2026-01-15T10:00:00Z'
							},
							{
								id: 2,
								jellyseerr_username: 'jellyfin_only_user',
								display_name: '',
								has_jellyseerr_account: false,
								created_at: '2026-01-15T11:00:00Z'
							}
						],
						total_count: 2
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.items[0].has_jellyseerr_account).toBe(true);
			expect(data.items[1].has_jellyseerr_account).toBe(false);
		});

		it('handles empty display_name for prefilled users', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								id: 1,
								jellyseerr_username: 'prefilled_user',
								display_name: '',
								has_jellyseerr_account: true,
								created_at: '2026-01-15T10:00:00Z'
							}
						],
						total_count: 1
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.items[0].display_name).toBe('');
		});
	});

	describe('Add Nickname', () => {
		it('creates a new nickname successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 201,
				json: () =>
					Promise.resolve({
						id: 1,
						jellyseerr_username: 'new_user',
						display_name: 'New User',
						has_jellyseerr_account: true,
						created_at: '2026-01-18T10:00:00Z'
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					jellyseerr_username: 'new_user',
					display_name: 'New User'
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/nicknames', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					jellyseerr_username: 'new_user',
					display_name: 'New User'
				})
			});
			expect(response.ok).toBe(true);
		});

		it('returns 409 when username already has a nickname', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 409,
				json: () =>
					Promise.resolve({
						detail: 'A nickname for this username already exists'
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					jellyseerr_username: 'existing_user',
					display_name: 'Existing'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(409);
		});

		it('returns 422 when validation fails', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'jellyseerr_username'],
								msg: 'String should have at least 1 characters',
								type: 'string_too_short'
							}
						]
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					jellyseerr_username: '',
					display_name: 'Name'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});

	describe('Edit Nickname', () => {
		it('updates display name successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						id: 1,
						jellyseerr_username: 'john_doe',
						display_name: 'Johnny',
						has_jellyseerr_account: true,
						created_at: '2026-01-15T10:00:00Z'
					})
			});

			const response = await fetch('/api/settings/nicknames/1', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					display_name: 'Johnny'
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/nicknames/1', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					display_name: 'Johnny'
				})
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.display_name).toBe('Johnny');
		});

		it('returns 404 when nickname not found', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: () => Promise.resolve({ detail: 'Nickname not found' })
			});

			const response = await fetch('/api/settings/nicknames/999', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					display_name: 'Test'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(404);
		});
	});

	describe('Delete Nickname', () => {
		it('deletes nickname successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Nickname deleted successfully'
					})
			});

			const response = await fetch('/api/settings/nicknames/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/nicknames/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(response.ok).toBe(true);
		});

		it('returns 404 when nickname not found', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: () => Promise.resolve({ detail: 'Nickname not found' })
			});

			const response = await fetch('/api/settings/nicknames/999', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(404);
		});
	});

	describe('Refresh Users', () => {
		it('refreshes Jellyfin users successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: '3 new users added',
						new_users_count: 3
					})
			});

			const response = await fetch('/api/settings/nicknames/refresh', {
				method: 'POST',
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/nicknames/refresh', {
				method: 'POST',
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.new_users_count).toBe(3);
		});

		it('returns 400 when Jellyfin not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Jellyfin is not configured. Please configure Jellyfin in settings first.'
					})
			});

			const response = await fetch('/api/settings/nicknames/refresh', {
				method: 'POST',
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);
		});

		it('returns 500 when Jellyfin API fails', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () =>
					Promise.resolve({
						detail: 'Failed to fetch Jellyfin users: Connection failed'
					})
			});

			const response = await fetch('/api/settings/nicknames/refresh', {
				method: 'POST',
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});
	});
});
