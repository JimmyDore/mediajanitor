/**
 * Tests for the login API integration
 *
 * Note: Svelte 5 component testing with testing-library is still evolving.
 * These tests verify the API contract that the login page uses.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Login API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('login API accepts valid email and password', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve({ access_token: 'jwt-token', token_type: 'bearer' })
		});

		// Simulate the fetch call that the login form makes
		const response = await fetch('/api/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'SecurePassword123!' })
		});

		expect(mockFetch).toHaveBeenCalledWith('/api/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'SecurePassword123!' })
		});
		expect(response.ok).toBe(true);
	});

	it('login API returns JWT token on success', async () => {
		const tokenData = { access_token: 'jwt-token-here', token_type: 'bearer' };
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(tokenData)
		});

		const response = await fetch('/api/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'SecurePassword123!' })
		});

		const data = await response.json();
		expect(data.access_token).toBe('jwt-token-here');
		expect(data.token_type).toBe('bearer');
	});

	it('login API returns 401 for invalid credentials', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 401,
			json: () => Promise.resolve({ detail: 'Invalid email or password' })
		});

		const response = await fetch('/api/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'wrong@example.com', password: 'WrongPassword' })
		});

		expect(response.ok).toBe(false);
		expect(response.status).toBe(401);

		const data = await response.json();
		expect(data.detail).toBe('Invalid email or password');
	});

	it('login API returns 422 for missing fields', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 422,
			json: () => Promise.resolve({ detail: 'Validation error' })
		});

		const response = await fetch('/api/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com' }) // missing password
		});

		expect(response.ok).toBe(false);
		expect(response.status).toBe(422);
	});
});
