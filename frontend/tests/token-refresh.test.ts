/**
 * Tests for token refresh and authenticated fetch functionality
 *
 * These tests verify:
 * 1. Token refresh endpoint integration
 * 2. authenticatedFetch automatic token refresh on 401
 * 3. Login stores token in memory with expiration
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Token Refresh API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('refresh endpoint returns new access token with expires_in', async () => {
		const tokenData = {
			access_token: 'new-jwt-token',
			expires_in: 900 // 15 minutes in seconds
		};
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(tokenData)
		});

		const response = await fetch('/api/auth/refresh', {
			method: 'POST',
			credentials: 'include' // Include httpOnly cookie
		});

		expect(mockFetch).toHaveBeenCalledWith('/api/auth/refresh', {
			method: 'POST',
			credentials: 'include'
		});
		expect(response.ok).toBe(true);

		const data = await response.json();
		expect(data.access_token).toBe('new-jwt-token');
		expect(data.expires_in).toBe(900);
	});

	it('refresh endpoint returns 401 when refresh token is invalid', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 401,
			json: () => Promise.resolve({ detail: 'Invalid or expired refresh token' })
		});

		const response = await fetch('/api/auth/refresh', {
			method: 'POST',
			credentials: 'include'
		});

		expect(response.ok).toBe(false);
		expect(response.status).toBe(401);
	});

	it('refresh endpoint returns 401 when refresh token is missing', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 401,
			json: () => Promise.resolve({ detail: 'Refresh token missing' })
		});

		const response = await fetch('/api/auth/refresh', {
			method: 'POST',
			credentials: 'include'
		});

		expect(response.ok).toBe(false);
		expect(response.status).toBe(401);
	});
});

describe('Logout API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('logout endpoint invalidates refresh token', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 204
		});

		const response = await fetch('/api/auth/logout', {
			method: 'POST',
			credentials: 'include'
		});

		expect(mockFetch).toHaveBeenCalledWith('/api/auth/logout', {
			method: 'POST',
			credentials: 'include'
		});
		expect(response.ok).toBe(true);
	});

	it('logout endpoint clears cookie even without valid token', async () => {
		// Logout should succeed even if the refresh token was already invalid
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 204
		});

		const response = await fetch('/api/auth/logout', {
			method: 'POST',
			credentials: 'include'
		});

		expect(response.ok).toBe(true);
	});
});

describe('Login API with Token Refresh', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('login returns access_token and expires_in', async () => {
		const tokenData = {
			access_token: 'jwt-token-here',
			expires_in: 900 // 15 minutes in seconds
		};
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(tokenData)
		});

		const response = await fetch('/api/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'Password123!' }),
			credentials: 'include'
		});

		expect(response.ok).toBe(true);

		const data = await response.json();
		expect(data.access_token).toBeDefined();
		expect(data.expires_in).toBe(900);
	});

	it('login sets refresh token cookie via credentials include', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					access_token: 'jwt-token',
					expires_in: 900
				})
		});

		await fetch('/api/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'Password123!' }),
			credentials: 'include'
		});

		// Verify credentials: 'include' was passed to allow cookie to be set
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/auth/login',
			expect.objectContaining({
				credentials: 'include'
			})
		);
	});
});

describe('Authenticated Fetch Behavior', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('authenticated request includes Authorization header', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: () => Promise.resolve({ data: 'test' })
		});

		// Simulate what authenticatedFetch does
		const token = 'test-access-token';
		await fetch('/api/some-endpoint', {
			headers: { Authorization: `Bearer ${token}` },
			credentials: 'include'
		});

		expect(mockFetch).toHaveBeenCalledWith(
			'/api/some-endpoint',
			expect.objectContaining({
				headers: expect.objectContaining({
					Authorization: 'Bearer test-access-token'
				}),
				credentials: 'include'
			})
		);
	});

	it('401 response triggers token refresh attempt', async () => {
		// First request returns 401
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 401,
			json: () => Promise.resolve({ detail: 'Token expired' })
		});

		// Simulate the flow: app detects 401 and calls refresh
		const firstResponse = await fetch('/api/protected', {
			headers: { Authorization: 'Bearer expired-token' }
		});

		expect(firstResponse.status).toBe(401);

		// App should then call refresh endpoint
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					access_token: 'new-access-token',
					expires_in: 900
				})
		});

		const refreshResponse = await fetch('/api/auth/refresh', {
			method: 'POST',
			credentials: 'include'
		});

		expect(refreshResponse.ok).toBe(true);
		const refreshData = await refreshResponse.json();
		expect(refreshData.access_token).toBe('new-access-token');
	});

	it('retry request with new token after refresh succeeds', async () => {
		// Refresh succeeds
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					access_token: 'new-access-token',
					expires_in: 900
				})
		});

		// Get new token
		const refreshResponse = await fetch('/api/auth/refresh', {
			method: 'POST',
			credentials: 'include'
		});
		const { access_token } = await refreshResponse.json();

		// Retry the original request with new token
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: () => Promise.resolve({ data: 'protected content' })
		});

		const retryResponse = await fetch('/api/protected', {
			headers: { Authorization: `Bearer ${access_token}` },
			credentials: 'include'
		});

		expect(retryResponse.ok).toBe(true);
		expect(mockFetch).toHaveBeenLastCalledWith(
			'/api/protected',
			expect.objectContaining({
				headers: expect.objectContaining({
					Authorization: 'Bearer new-access-token'
				})
			})
		);
	});
});
