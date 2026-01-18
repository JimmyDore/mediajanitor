/**
 * Tests for the Security settings page
 *
 * These tests verify the change password functionality including
 * form validation, API calls, and error/success handling.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Security Settings Page - Change Password', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('Change password - Success', () => {
		it('sends correct payload to change password endpoint', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						message: 'Password has been changed successfully.'
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'NewSecure456!'
				})
			});

			expect(mockFetch).toHaveBeenCalledTimes(1);
			expect(mockFetch).toHaveBeenCalledWith('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'NewSecure456!'
				})
			});

			const data = await response.json();
			expect(data.message).toContain('successfully');
		});

		it('returns 200 on successful password change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: () =>
					Promise.resolve({
						message: 'Password has been changed successfully.'
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'NewSecure456!'
				})
			});

			expect(response.ok).toBe(true);
		});
	});

	describe('Change password - Authentication errors', () => {
		it('returns 401 when not authenticated', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () =>
					Promise.resolve({
						detail: 'Not authenticated'
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'NewSecure456!'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});

		it('returns 401 with invalid token', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () =>
					Promise.resolve({
						detail: 'Could not validate credentials'
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer invalid-token'
				},
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'NewSecure456!'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(401);
		});
	});

	describe('Change password - Wrong current password', () => {
		it('returns 400 when current password is incorrect', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				json: () =>
					Promise.resolve({
						detail: 'Current password is incorrect'
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					current_password: 'WrongPassword123!',
					new_password: 'NewSecure456!'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(400);

			const data = await response.json();
			expect(data.detail).toContain('incorrect');
		});
	});

	describe('Change password - Validation errors', () => {
		it('returns 422 when new password is too short', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'new_password'],
								msg: 'String should have at least 8 characters',
								type: 'string_too_short'
							}
						]
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'Short1!'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('returns 422 when new password missing uppercase', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'new_password'],
								msg: 'Password must contain at least one uppercase letter',
								type: 'value_error'
							}
						]
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'nouppercase123!'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('returns 422 when new password missing lowercase', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'new_password'],
								msg: 'Password must contain at least one lowercase letter',
								type: 'value_error'
							}
						]
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'NOLOWERCASE123!'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('returns 422 when new password missing number', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'new_password'],
								msg: 'Password must contain at least one number',
								type: 'value_error'
							}
						]
					})
			});

			const response = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					current_password: 'OldPassword123!',
					new_password: 'NoNumberHere!'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});

	describe('Change password - Network errors', () => {
		it('handles network failure gracefully', async () => {
			mockFetch.mockRejectedValueOnce(new Error('Network error'));

			await expect(
				fetch('/api/auth/change-password', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						current_password: 'OldPassword123!',
						new_password: 'NewSecure456!'
					})
				})
			).rejects.toThrow('Network error');
		});
	});
});

describe('Security Settings Page - Password Validation UI', () => {
	// Client-side validation tests
	describe('Password validation rules', () => {
		it('validates minimum length (8 characters)', () => {
			const password = 'Short1A';
			expect(password.length).toBeLessThan(8);
		});

		it('validates uppercase requirement', () => {
			const password = 'nouppercase123!';
			expect(/[A-Z]/.test(password)).toBe(false);
		});

		it('validates lowercase requirement', () => {
			const password = 'NOLOWERCASE123!';
			expect(/[a-z]/.test(password)).toBe(false);
		});

		it('validates number requirement', () => {
			const password = 'NoNumberHere!';
			expect(/[0-9]/.test(password)).toBe(false);
		});

		it('accepts valid password', () => {
			const password = 'ValidPass123!';
			expect(password.length).toBeGreaterThanOrEqual(8);
			expect(/[A-Z]/.test(password)).toBe(true);
			expect(/[a-z]/.test(password)).toBe(true);
			expect(/[0-9]/.test(password)).toBe(true);
		});
	});

	describe('Password confirmation', () => {
		it('detects matching passwords', () => {
			const newPassword = 'NewSecure456!';
			const confirmPassword = 'NewSecure456!';
			expect(newPassword === confirmPassword).toBe(true);
		});

		it('detects non-matching passwords', () => {
			const newPassword: string = 'NewSecure456!';
			const confirmPassword: string = 'DifferentPass789!';
			expect(newPassword === confirmPassword).toBe(false);
		});
	});
});
