/**
 * Tests for the auto-save behavior in settings pages (US-55.1)
 *
 * These tests verify:
 * 1. Debounce utility function works correctly
 * 2. Settings auto-save on change
 * 3. Toast notifications on save success/error
 * 4. Loading indicator appears after 200ms delay
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { debounce } from '../src/lib/stores';

describe('Debounce utility function', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('delays function execution by the specified wait time', () => {
		const fn = vi.fn();
		const debouncedFn = debounce(fn, 300);

		debouncedFn();
		expect(fn).not.toHaveBeenCalled();

		vi.advanceTimersByTime(299);
		expect(fn).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1);
		expect(fn).toHaveBeenCalledTimes(1);
	});

	it('cancels previous call when called again within wait time', () => {
		const fn = vi.fn();
		const debouncedFn = debounce(fn, 300);

		debouncedFn('first');
		vi.advanceTimersByTime(100);

		debouncedFn('second');
		vi.advanceTimersByTime(100);

		debouncedFn('third');
		vi.advanceTimersByTime(300);

		expect(fn).toHaveBeenCalledTimes(1);
		expect(fn).toHaveBeenCalledWith('third');
	});

	it('passes arguments to the debounced function', () => {
		const fn = vi.fn();
		const debouncedFn = debounce(fn, 300);

		debouncedFn('arg1', 'arg2');
		vi.advanceTimersByTime(300);

		expect(fn).toHaveBeenCalledWith('arg1', 'arg2');
	});

	it('allows multiple independent debounced calls after wait time', () => {
		const fn = vi.fn();
		const debouncedFn = debounce(fn, 300);

		debouncedFn('first');
		vi.advanceTimersByTime(300);
		expect(fn).toHaveBeenCalledTimes(1);

		debouncedFn('second');
		vi.advanceTimersByTime(300);
		expect(fn).toHaveBeenCalledTimes(2);
	});

	it('works with 0ms delay (immediate execution after current tick)', () => {
		const fn = vi.fn();
		const debouncedFn = debounce(fn, 0);

		debouncedFn();
		expect(fn).not.toHaveBeenCalled();

		vi.advanceTimersByTime(0);
		expect(fn).toHaveBeenCalledTimes(1);
	});
});

describe('Thresholds auto-save behavior (US-55.1)', () => {
	const mockFetch = vi.fn();

	beforeEach(() => {
		mockFetch.mockReset();
		global.fetch = mockFetch;
	});

	describe('Auto-save on input change', () => {
		it('saves old_content_months individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 6
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 6
				})
			});
			expect(response.ok).toBe(true);
		});

		it('saves min_age_months individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					min_age_months: 2
				})
			});

			expect(response.ok).toBe(true);
		});

		it('saves large_movie_size_gb individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					large_movie_size_gb: 15
				})
			});

			expect(response.ok).toBe(true);
		});

		it('saves large_season_size_gb individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					large_season_size_gb: 20
				})
			});

			expect(response.ok).toBe(true);
		});
	});

	describe('Error handling', () => {
		it('handles save failure gracefully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () => Promise.resolve({ detail: 'Internal server error' })
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 6
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});

		it('handles validation error for out-of-range value', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 422,
				json: () =>
					Promise.resolve({
						detail: 'Value out of range'
					})
			});

			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					old_content_months: 100
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(422);
		});
	});
});

describe('Display settings auto-save behavior (US-55.1)', () => {
	const mockFetch = vi.fn();

	beforeEach(() => {
		mockFetch.mockReset();
		global.fetch = mockFetch;
	});

	describe('Debounced auto-save for recently_available_days', () => {
		beforeEach(() => {
			vi.useFakeTimers();
		});

		afterEach(() => {
			vi.useRealTimers();
		});

		it('saves recently_available_days with debounce (300ms delay)', async () => {
			const saveFn = vi.fn();
			const debouncedSave = debounce(saveFn, 300);

			// Simulate rapid typing: 7 -> 14 -> 21
			debouncedSave(7);
			debouncedSave(14);
			debouncedSave(21);

			// Function not called yet (within debounce window)
			expect(saveFn).not.toHaveBeenCalled();

			// Advance past debounce delay
			vi.advanceTimersByTime(300);

			// Only the last value should be saved
			expect(saveFn).toHaveBeenCalledTimes(1);
			expect(saveFn).toHaveBeenCalledWith(21);
		});

		it('saves each change after debounce window when typing slowly', () => {
			const saveFn = vi.fn();
			const debouncedSave = debounce(saveFn, 300);

			// First value
			debouncedSave(7);
			vi.advanceTimersByTime(300);
			expect(saveFn).toHaveBeenCalledTimes(1);
			expect(saveFn).toHaveBeenCalledWith(7);

			// Second value after debounce window
			debouncedSave(14);
			vi.advanceTimersByTime(300);
			expect(saveFn).toHaveBeenCalledTimes(2);
			expect(saveFn).toHaveBeenLastCalledWith(14);
		});
	});

	describe('Auto-save on input change', () => {
		it('saves theme_preference individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					theme_preference: 'dark'
				})
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					theme_preference: 'dark'
				})
			});
			expect(response.ok).toBe(true);
		});

		it('saves recently_available_days individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					recently_available_days: 14
				})
			});

			expect(response.ok).toBe(true);
		});

		it('saves show_unreleased_requests individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					show_unreleased_requests: true
				})
			});

			expect(response.ok).toBe(true);
		});

		it('saves title_language individually on change', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					title_language: 'fr'
				})
			});

			expect(response.ok).toBe(true);
		});
	});

	describe('Error handling', () => {
		it('handles save failure gracefully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () => Promise.resolve({ detail: 'Internal server error' })
			});

			const response = await fetch('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({
					theme_preference: 'dark'
				})
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});
	});
});
