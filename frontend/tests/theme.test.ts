/**
 * Unit tests for the theme store (US-16.2)
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';

// Mock fetch before importing the store
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const mockLocalStorage = {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn()
};
Object.defineProperty(global, 'localStorage', { value: mockLocalStorage });

// Mock document
const mockSetAttribute = vi.fn();
const mockRemoveAttribute = vi.fn();
Object.defineProperty(global, 'document', {
	value: {
		documentElement: {
			setAttribute: mockSetAttribute,
			removeAttribute: mockRemoveAttribute
		}
	}
});

describe('Theme Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.resetModules();
	});

	describe('Initial state', () => {
		test('starts with system preference and loading true', async () => {
			const { theme } = await import('../src/lib/stores/index.js');
			const state = get(theme);
			expect(state.preference).toBe('system');
			expect(state.isLoading).toBe(true);
		});
	});

	describe('setPreference', () => {
		test('sets light theme and applies to DOM', async () => {
			const { theme } = await import('../src/lib/stores/index.js');
			theme.setPreference('light');

			const state = get(theme);
			expect(state.preference).toBe('light');
			expect(mockSetAttribute).toHaveBeenCalledWith('data-theme', 'light');
		});

		test('sets dark theme and applies to DOM', async () => {
			const { theme } = await import('../src/lib/stores/index.js');
			theme.setPreference('dark');

			const state = get(theme);
			expect(state.preference).toBe('dark');
			expect(mockSetAttribute).toHaveBeenCalledWith('data-theme', 'dark');
		});

		test('sets system preference and removes attribute', async () => {
			const { theme } = await import('../src/lib/stores/index.js');
			theme.setPreference('system');

			const state = get(theme);
			expect(state.preference).toBe('system');
			expect(mockRemoveAttribute).toHaveBeenCalledWith('data-theme');
		});
	});

	describe('loadFromApi', () => {
		test('loads theme from API when authenticated', async () => {
			mockLocalStorage.getItem.mockReturnValue('test-token');
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ theme_preference: 'dark', show_unreleased_requests: false })
			});

			// Re-import to get fresh store
			vi.resetModules();
			const { theme } = await import('../src/lib/stores/index.js');
			await theme.loadFromApi();

			const state = get(theme);
			expect(state.preference).toBe('dark');
			expect(state.isLoading).toBe(false);
			expect(mockSetAttribute).toHaveBeenCalledWith('data-theme', 'dark');
		});

		test('defaults to system when not authenticated', async () => {
			mockLocalStorage.getItem.mockReturnValue(null);

			vi.resetModules();
			const { theme } = await import('../src/lib/stores/index.js');
			await theme.loadFromApi();

			const state = get(theme);
			expect(state.preference).toBe('system');
			expect(state.isLoading).toBe(false);
		});

		test('defaults to system when API fails', async () => {
			mockLocalStorage.getItem.mockReturnValue('test-token');
			mockFetch.mockResolvedValueOnce({
				ok: false
			});

			vi.resetModules();
			const { theme } = await import('../src/lib/stores/index.js');
			await theme.loadFromApi();

			const state = get(theme);
			expect(state.preference).toBe('system');
			expect(state.isLoading).toBe(false);
		});
	});

	describe('saveToApi', () => {
		test('saves theme preference to API', async () => {
			mockLocalStorage.getItem.mockReturnValue('test-token');
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ success: true })
			});

			vi.resetModules();
			const { theme } = await import('../src/lib/stores/index.js');
			const result = await theme.saveToApi('dark');

			expect(result).toBe(true);
			expect(mockFetch).toHaveBeenCalledWith('/api/settings/display', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: 'Bearer test-token'
				},
				body: JSON.stringify({ theme_preference: 'dark' })
			});
			expect(mockSetAttribute).toHaveBeenCalledWith('data-theme', 'dark');
		});

		test('returns false when not authenticated', async () => {
			mockLocalStorage.getItem.mockReturnValue(null);

			vi.resetModules();
			const { theme } = await import('../src/lib/stores/index.js');
			const result = await theme.saveToApi('dark');

			expect(result).toBe(false);
		});

		test('returns false when API fails', async () => {
			mockLocalStorage.getItem.mockReturnValue('test-token');
			mockFetch.mockResolvedValueOnce({
				ok: false
			});

			vi.resetModules();
			const { theme } = await import('../src/lib/stores/index.js');
			const result = await theme.saveToApi('dark');

			expect(result).toBe(false);
		});
	});
});
