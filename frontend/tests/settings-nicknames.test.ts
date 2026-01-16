/**
 * Tests for the User Nicknames API integration (US-31.4)
 *
 * These tests verify the API contract that the settings page uses
 * for managing user nickname mappings.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('User Nicknames API Integration (US-31.4)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/nicknames', () => {
		it('returns empty list when no nicknames exist', async () => {
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

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.items).toEqual([]);
			expect(data.total_count).toBe(0);
		});

		it('returns list of nicknames when configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								id: 1,
								jellyseerr_username: 'john_doe',
								display_name: 'John',
								created_at: '2026-01-15T10:00:00Z'
							},
							{
								id: 2,
								jellyseerr_username: 'jane_doe',
								display_name: 'Jane',
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
			expect(data.items).toHaveLength(2);
			expect(data.items[0].jellyseerr_username).toBe('john_doe');
			expect(data.items[0].display_name).toBe('John');
			expect(data.total_count).toBe(2);
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

	describe('POST /api/settings/nicknames', () => {
		it('creates a new nickname mapping successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 201,
				json: () =>
					Promise.resolve({
						id: 1,
						jellyseerr_username: 'john_doe',
						display_name: 'John',
						created_at: '2026-01-15T10:00:00Z'
					})
			});

			const response = await fetch('/api/settings/nicknames', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					jellyseerr_username: 'john_doe',
					display_name: 'John'
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/nicknames', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					jellyseerr_username: 'john_doe',
					display_name: 'John'
				})
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.id).toBe(1);
			expect(data.jellyseerr_username).toBe('john_doe');
			expect(data.display_name).toBe('John');
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
					jellyseerr_username: 'john_doe',
					display_name: 'Johnny'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(409);
		});

		it('returns 422 when jellyseerr_username is empty', async () => {
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
					display_name: 'John'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/nicknames', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					jellyseerr_username: 'john_doe',
					display_name: 'John'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('PUT /api/settings/nicknames/:id', () => {
		it('updates an existing nickname successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						id: 1,
						jellyseerr_username: 'john_doe',
						display_name: 'Johnny',
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
					display_name: 'Johnny'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(404);
		});

		it('returns 422 when display_name is empty', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'display_name'],
								msg: 'String should have at least 1 characters',
								type: 'string_too_short'
							}
						]
					})
			});

			const response = await fetch('/api/settings/nicknames/1', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					display_name: ''
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});

	describe('DELETE /api/settings/nicknames/:id', () => {
		it('deletes a nickname successfully', async () => {
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

			const data = await response.json();
			expect(data.success).toBe(true);
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

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/nicknames/1', {
				method: 'DELETE'
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('CRUD workflow integration', () => {
		it('can create, read, update, and delete a nickname', async () => {
			// 1. Create a new nickname
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 201,
				json: () =>
					Promise.resolve({
						id: 1,
						jellyseerr_username: 'john_doe',
						display_name: 'John',
						created_at: '2026-01-15T10:00:00Z'
					})
			});

			const createResponse = await fetch('/api/settings/nicknames', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					jellyseerr_username: 'john_doe',
					display_name: 'John'
				})
			});
			expect(createResponse.ok).toBe(true);

			// 2. Read nicknames to verify creation
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [
							{
								id: 1,
								jellyseerr_username: 'john_doe',
								display_name: 'John',
								created_at: '2026-01-15T10:00:00Z'
							}
						],
						total_count: 1
					})
			});

			const listResponse = await fetch('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const listData = await listResponse.json();
			expect(listData.items).toHaveLength(1);

			// 3. Update the nickname
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						id: 1,
						jellyseerr_username: 'john_doe',
						display_name: 'Johnny',
						created_at: '2026-01-15T10:00:00Z'
					})
			});

			const updateResponse = await fetch('/api/settings/nicknames/1', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					display_name: 'Johnny'
				})
			});
			const updateData = await updateResponse.json();
			expect(updateData.display_name).toBe('Johnny');

			// 4. Delete the nickname
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Nickname deleted successfully'
					})
			});

			const deleteResponse = await fetch('/api/settings/nicknames/1', {
				method: 'DELETE',
				headers: { Authorization: 'Bearer test-token' }
			});
			expect(deleteResponse.ok).toBe(true);

			// 5. Verify deletion
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						items: [],
						total_count: 0
					})
			});

			const finalListResponse = await fetch('/api/settings/nicknames', {
				headers: { Authorization: 'Bearer test-token' }
			});
			const finalListData = await finalListResponse.json();
			expect(finalListData.items).toHaveLength(0);
		});
	});

	describe('POST /api/settings/nicknames/refresh (US-37.3)', () => {
		it('refreshes nicknames from Jellyfin users successfully', async () => {
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
			expect(data.success).toBe(true);
			expect(data.new_users_count).toBe(3);
			expect(data.message).toBe('3 new users added');
		});

		it('returns appropriate message when no new users found', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'No new users found',
						new_users_count: 0
					})
			});

			const response = await fetch('/api/settings/nicknames/refresh', {
				method: 'POST',
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.new_users_count).toBe(0);
			expect(data.message).toBe('No new users found');
		});

		it('returns singular message for 1 new user', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: '1 new user added',
						new_users_count: 1
					})
			});

			const response = await fetch('/api/settings/nicknames/refresh', {
				method: 'POST',
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.new_users_count).toBe(1);
			expect(data.message).toBe('1 new user added');
		});

		it('returns 400 when Jellyfin is not configured', async () => {
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

			const data = await response.json();
			expect(data.detail).toContain('Jellyfin');
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

			const data = await response.json();
			expect(data.detail).toContain('Failed to fetch');
		});

		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/nicknames/refresh', {
				method: 'POST'
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});
});
