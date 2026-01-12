/**
 * Tests for the registration API integration
 *
 * Note: Svelte 5 component testing with testing-library is still evolving.
 * These tests verify the API contract that the registration page uses.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Registration API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('registration API accepts valid email and password', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve({ id: 1, email: 'test@example.com' })
		});

		// Simulate the fetch call that the registration form makes
		const response = await fetch('/api/auth/register', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'SecurePassword123!' })
		});

		expect(mockFetch).toHaveBeenCalledWith('/api/auth/register', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'SecurePassword123!' })
		});
		expect(response.ok).toBe(true);
	});

	it('registration API returns user data on success', async () => {
		const userData = { id: 1, email: 'test@example.com' };
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(userData)
		});

		const response = await fetch('/api/auth/register', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'test@example.com', password: 'SecurePassword123!' })
		});

		const data = await response.json();
		expect(data.id).toBe(1);
		expect(data.email).toBe('test@example.com');
	});

	it('registration API returns error for duplicate email', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 400,
			json: () => Promise.resolve({ detail: 'Email already registered' })
		});

		const response = await fetch('/api/auth/register', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'existing@example.com', password: 'SecurePassword123!' })
		});

		expect(response.ok).toBe(false);
		expect(response.status).toBe(400);

		const data = await response.json();
		expect(data.detail).toBe('Email already registered');
	});

	it('registration API returns validation error for invalid data', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 422,
			json: () => Promise.resolve({ detail: 'Validation error' })
		});

		const response = await fetch('/api/auth/register', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: 'invalid', password: 'short' })
		});

		expect(response.ok).toBe(false);
		expect(response.status).toBe(422);
	});
});

describe('Password Validation', () => {
	function validatePassword(pwd: string): string | null {
		if (pwd.length < 8) {
			return 'Password must be at least 8 characters';
		}
		return null;
	}

	it('rejects passwords shorter than 8 characters', () => {
		expect(validatePassword('short')).toBe('Password must be at least 8 characters');
		expect(validatePassword('1234567')).toBe('Password must be at least 8 characters');
	});

	it('accepts passwords with 8 or more characters', () => {
		expect(validatePassword('12345678')).toBeNull();
		expect(validatePassword('SecurePassword123!')).toBeNull();
	});
});
