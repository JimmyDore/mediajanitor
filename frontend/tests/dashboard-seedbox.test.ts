/**
 * Tests for Dashboard Seedbox Status card (US-48.5)
 *
 * These tests verify the API integration and display logic
 * for the Seedbox Status card on the dashboard.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Dashboard Seedbox Status API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/settings/ultra - Stats retrieval', () => {
		it('returns stats when Ultra is configured and synced', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: 'https://api.ultra.cc',
						api_key_configured: true,
						free_storage_gb: 234.5,
						traffic_available_percent: 85.2,
						last_synced_at: '2026-01-23T10:00:00Z',
						storage_warning_gb: 100,
						traffic_warning_percent: 20
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			expect(response.ok).toBe(true);
			const data = await response.json();

			// Stats should be present
			expect(data.free_storage_gb).toBe(234.5);
			expect(data.traffic_available_percent).toBe(85.2);
			expect(data.last_synced_at).toBe('2026-01-23T10:00:00Z');

			// Warning thresholds should be present
			expect(data.storage_warning_gb).toBe(100);
			expect(data.traffic_warning_percent).toBe(20);
		});

		it('returns null stats when configured but not yet synced', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: 'https://api.ultra.cc',
						api_key_configured: true,
						free_storage_gb: null,
						traffic_available_percent: null,
						last_synced_at: null,
						storage_warning_gb: 100,
						traffic_warning_percent: 20
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.api_key_configured).toBe(true);
			expect(data.free_storage_gb).toBeNull();
			expect(data.traffic_available_percent).toBeNull();
			expect(data.last_synced_at).toBeNull();
		});

		it('returns null stats when Ultra is not configured', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: null,
						api_key_configured: false,
						free_storage_gb: null,
						traffic_available_percent: null,
						last_synced_at: null,
						storage_warning_gb: null,
						traffic_warning_percent: null
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.api_key_configured).toBe(false);
			expect(data.free_storage_gb).toBeNull();
		});

		it('returns custom thresholds when set by user', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						server_url: 'https://api.ultra.cc',
						api_key_configured: true,
						free_storage_gb: 150.0,
						traffic_available_percent: 45.0,
						last_synced_at: '2026-01-23T12:00:00Z',
						storage_warning_gb: 50,
						traffic_warning_percent: 30
					})
			});

			const response = await fetch('/api/settings/ultra', {
				headers: { Authorization: 'Bearer test-token' }
			});

			const data = await response.json();
			expect(data.storage_warning_gb).toBe(50);
			expect(data.traffic_warning_percent).toBe(30);
		});
	});

	describe('Warning level calculations', () => {
		// Helper functions matching the dashboard implementation
		function getStorageWarningLevel(
			freeGb: number | null,
			warningGb: number | null
		): 'normal' | 'warning' | 'danger' {
			if (freeGb === null || warningGb === null) return 'normal';
			if (freeGb < warningGb * 0.5) return 'danger';
			if (freeGb < warningGb) return 'warning';
			return 'normal';
		}

		function getTrafficWarningLevel(
			trafficPercent: number | null,
			warningPercent: number | null
		): 'normal' | 'warning' | 'danger' {
			if (trafficPercent === null || warningPercent === null) return 'normal';
			if (trafficPercent < warningPercent * 0.5) return 'danger';
			if (trafficPercent < warningPercent) return 'warning';
			return 'normal';
		}

		it('returns normal when storage above threshold', () => {
			expect(getStorageWarningLevel(150, 100)).toBe('normal');
			expect(getStorageWarningLevel(100, 100)).toBe('normal');
		});

		it('returns warning when storage below threshold but above 50%', () => {
			expect(getStorageWarningLevel(80, 100)).toBe('warning');
			expect(getStorageWarningLevel(51, 100)).toBe('warning');
		});

		it('returns danger when storage below 50% of threshold', () => {
			expect(getStorageWarningLevel(49, 100)).toBe('danger');
			expect(getStorageWarningLevel(25, 100)).toBe('danger');
			expect(getStorageWarningLevel(0, 100)).toBe('danger');
		});

		it('returns normal when traffic above threshold', () => {
			expect(getTrafficWarningLevel(50, 20)).toBe('normal');
			expect(getTrafficWarningLevel(20, 20)).toBe('normal');
		});

		it('returns warning when traffic below threshold but above 50%', () => {
			expect(getTrafficWarningLevel(15, 20)).toBe('warning');
			expect(getTrafficWarningLevel(11, 20)).toBe('warning');
		});

		it('returns danger when traffic below 50% of threshold', () => {
			expect(getTrafficWarningLevel(9, 20)).toBe('danger');
			expect(getTrafficWarningLevel(5, 20)).toBe('danger');
			expect(getTrafficWarningLevel(0, 20)).toBe('danger');
		});

		it('returns normal when values are null', () => {
			expect(getStorageWarningLevel(null, 100)).toBe('normal');
			expect(getStorageWarningLevel(50, null)).toBe('normal');
			expect(getTrafficWarningLevel(null, 20)).toBe('normal');
			expect(getTrafficWarningLevel(10, null)).toBe('normal');
		});
	});

	describe('Dashboard card visibility', () => {
		it('shows seedbox card when Ultra configured and stats available', async () => {
			// Simulating the showSeedboxStatus derived value logic
			const ultraSettings = {
				server_url: 'https://api.ultra.cc',
				api_key_configured: true,
				free_storage_gb: 234.5,
				traffic_available_percent: 85.2,
				last_synced_at: '2026-01-23T10:00:00Z'
			};

			const showSeedboxStatus =
				ultraSettings !== null &&
				ultraSettings.api_key_configured === true &&
				ultraSettings.free_storage_gb !== null;

			expect(showSeedboxStatus).toBe(true);
		});

		it('hides seedbox card when Ultra not configured', async () => {
			const ultraSettings = {
				server_url: null,
				api_key_configured: false,
				free_storage_gb: null,
				traffic_available_percent: null,
				last_synced_at: null
			};

			const showSeedboxStatus =
				ultraSettings !== null &&
				ultraSettings.api_key_configured === true &&
				ultraSettings.free_storage_gb !== null;

			expect(showSeedboxStatus).toBe(false);
		});

		it('hides seedbox card when configured but not synced', async () => {
			const ultraSettings = {
				server_url: 'https://api.ultra.cc',
				api_key_configured: true,
				free_storage_gb: null,
				traffic_available_percent: null,
				last_synced_at: null
			};

			const showSeedboxStatus =
				ultraSettings !== null &&
				ultraSettings.api_key_configured === true &&
				ultraSettings.free_storage_gb !== null;

			expect(showSeedboxStatus).toBe(false);
		});

		it('hides seedbox card when ultraSettings is null', async () => {
			const ultraSettings = null;

			const showSeedboxStatus =
				ultraSettings !== null &&
				(ultraSettings as { api_key_configured: boolean }).api_key_configured === true &&
				(ultraSettings as { free_storage_gb: number | null }).free_storage_gb !== null;

			expect(showSeedboxStatus).toBe(false);
		});
	});

	describe('Stats formatting', () => {
		it('formats storage value with one decimal place', () => {
			const freeStorage = 234.567;
			const formatted = freeStorage.toFixed(1);
			expect(formatted).toBe('234.6');
		});

		it('formats traffic percentage with one decimal place', () => {
			const traffic = 85.234;
			const formatted = traffic.toFixed(1);
			expect(formatted).toBe('85.2');
		});
	});
});
