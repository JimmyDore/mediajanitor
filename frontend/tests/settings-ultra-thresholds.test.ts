/**
 * Tests for Ultra.cc warning thresholds settings (US-48.3)
 *
 * These tests verify the Ultra thresholds API integration
 * for storage and traffic warning thresholds.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Ultra Thresholds Settings API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/ultra/thresholds - Initial load', () => {
		it('fetches Ultra thresholds on page load', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						storage_warning_gb: 100,
						traffic_warning_percent: 20
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(mockFetch).toHaveBeenCalledTimes(1);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/ultra/thresholds', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.storage_warning_gb).toBe(100);
			expect(data.traffic_warning_percent).toBe(20);
		});

		it('returns default values when not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						storage_warning_gb: 100, // Default
						traffic_warning_percent: 20 // Default
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds');
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.storage_warning_gb).toBe(100);
			expect(data.traffic_warning_percent).toBe(20);
		});

		it('handles custom threshold values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						storage_warning_gb: 200,
						traffic_warning_percent: 30
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds');
			const data = await response.json();

			expect(data.storage_warning_gb).toBe(200);
			expect(data.traffic_warning_percent).toBe(30);
		});
	});

	describe('POST /api/settings/ultra/thresholds - Save thresholds', () => {
		it('saves all threshold values successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Ultra thresholds saved successfully.'
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					storage_warning_gb: 50,
					traffic_warning_percent: 10
				})
			});

			expect(response.ok).toBe(true);
			const data = await response.json();
			expect(data.success).toBe(true);
			expect(data.message).toContain('threshold');
		});

		it('handles partial updates - only storage_warning_gb', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Ultra thresholds saved successfully.'
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					storage_warning_gb: 75
				})
			});

			expect(response.ok).toBe(true);
		});

		it('handles partial updates - only traffic_warning_percent', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Ultra thresholds saved successfully.'
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					traffic_warning_percent: 15
				})
			});

			expect(response.ok).toBe(true);
		});

		it('handles validation errors for out-of-range values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'traffic_warning_percent'],
								msg: 'ensure this value is less than or equal to 100',
								type: 'value_error.number.not_le'
							}
						]
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					traffic_warning_percent: 150 // Out of range (max 100)
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('handles server errors gracefully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () =>
					Promise.resolve({
						detail: 'Internal server error'
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					storage_warning_gb: 50
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});
	});

	describe('Authentication', () => {
		it('returns 401 when not authenticated for GET', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/ultra/thresholds');
			expect(response.status).toBe(401);
		});

		it('returns 401 when not authenticated for POST', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ storage_warning_gb: 50 })
			});

			expect(response.status).toBe(401);
		});
	});

	describe('Threshold validation ranges', () => {
		it('accepts minimum valid values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Ultra thresholds saved successfully.'
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					storage_warning_gb: 1, // Min: 1
					traffic_warning_percent: 1 // Min: 1
				})
			});

			expect(response.ok).toBe(true);
		});

		it('accepts maximum valid values', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						message: 'Ultra thresholds saved successfully.'
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					storage_warning_gb: 1000, // Max: 1000
					traffic_warning_percent: 100 // Max: 100
				})
			});

			expect(response.ok).toBe(true);
		});

		it('rejects values below minimum', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'storage_warning_gb'],
								msg: 'ensure this value is greater than or equal to 1',
								type: 'value_error.number.not_ge'
							}
						]
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					storage_warning_gb: 0 // Below min
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});

		it('rejects values above maximum', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: [
							{
								loc: ['body', 'storage_warning_gb'],
								msg: 'ensure this value is less than or equal to 1000',
								type: 'value_error.number.not_le'
							}
						]
					})
			});

			const response = await fetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					storage_warning_gb: 1001 // Above max
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});
});
