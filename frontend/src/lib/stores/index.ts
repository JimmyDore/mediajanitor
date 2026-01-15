/**
 * Svelte stores for global state management
 */

import { writable, derived } from 'svelte/store';
import type { Settings, ApiStats, AuthState } from '../types';

// Authentication state
function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>({
		isAuthenticated: false,
		user: null,
		isLoading: true
	});

	return {
		subscribe,
		setUser: (user: { id: number; email: string } | null) => {
			update((state) => ({
				...state,
				isAuthenticated: user !== null,
				user,
				isLoading: false
			}));
		},
		setLoading: (loading: boolean) => {
			update((state) => ({ ...state, isLoading: loading }));
		},
		logout: () => {
			if (typeof localStorage !== 'undefined') {
				localStorage.removeItem('access_token');
			}
			set({ isAuthenticated: false, user: null, isLoading: false });
		},
		checkAuth: async () => {
			if (typeof localStorage === 'undefined') {
				set({ isAuthenticated: false, user: null, isLoading: false });
				return false;
			}

			const token = localStorage.getItem('access_token');
			if (!token) {
				set({ isAuthenticated: false, user: null, isLoading: false });
				return false;
			}

			try {
				const response = await fetch('/api/auth/me', {
					headers: { Authorization: `Bearer ${token}` }
				});
				if (response.ok) {
					const user = await response.json();
					set({ isAuthenticated: true, user, isLoading: false });
					return true;
				} else {
					localStorage.removeItem('access_token');
					set({ isAuthenticated: false, user: null, isLoading: false });
					return false;
				}
			} catch {
				set({ isAuthenticated: false, user: null, isLoading: false });
				return false;
			}
		}
	};
}

export const auth = createAuthStore();

// Dashboard stats
export const dashboardStats = writable<ApiStats>({
	oldUnwatched: 0,
	largeMovies: 0,
	languageIssues: 0,
	unavailableRequests: 0,
	inProgressRequests: 0
});

// Loading state
export const isLoading = writable(false);

// Error state
export const globalError = writable<string | null>(null);

// Settings
export const settings = writable<Settings>({
	oldContentMonthsCutoff: 4,
	minAgeMonths: 3,
	largeMovieSizeThresholdGb: 13,
	recentItemsDaysBack: 1500,
	filterFutureReleases: true,
	filterRecentReleases: true,
	recentReleaseMonthsCutoff: 3
});

// Toast notifications
interface Toast {
	id: number;
	message: string;
	type: 'success' | 'error' | 'info';
}

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);
	let nextId = 0;

	return {
		subscribe,
		add: (message: string, type: Toast['type'] = 'info') => {
			const id = nextId++;
			update((toasts) => [...toasts, { id, message, type }]);

			// Auto-remove after 5 seconds
			setTimeout(() => {
				update((toasts) => toasts.filter((t) => t.id !== id));
			}, 5000);
		},
		remove: (id: number) => {
			update((toasts) => toasts.filter((t) => t.id !== id));
		}
	};
}

export const toasts = createToastStore();

// Theme preference
export type ThemePreference = 'light' | 'dark' | 'system';

interface ThemeState {
	preference: ThemePreference;
	isLoading: boolean;
}

function createThemeStore() {
	const { subscribe, set, update } = writable<ThemeState>({
		preference: 'system',
		isLoading: true
	});

	// Apply theme to document
	const applyTheme = (preference: ThemePreference) => {
		if (typeof document === 'undefined') return;

		const html = document.documentElement;
		if (preference === 'system') {
			html.removeAttribute('data-theme');
		} else {
			html.setAttribute('data-theme', preference);
		}
	};

	return {
		subscribe,
		applyTheme,
		setPreference: (preference: ThemePreference) => {
			update((state) => ({ ...state, preference }));
			applyTheme(preference);
		},
		loadFromApi: async () => {
			if (typeof localStorage === 'undefined') {
				set({ preference: 'system', isLoading: false });
				return;
			}

			const token = localStorage.getItem('access_token');
			if (!token) {
				set({ preference: 'system', isLoading: false });
				return;
			}

			try {
				const response = await fetch('/api/settings/display', {
					headers: { Authorization: `Bearer ${token}` }
				});
				if (response.ok) {
					const data = await response.json();
					const preference = data.theme_preference as ThemePreference;
					applyTheme(preference);
					set({ preference, isLoading: false });
				} else {
					set({ preference: 'system', isLoading: false });
				}
			} catch {
				set({ preference: 'system', isLoading: false });
			}
		},
		saveToApi: async (preference: ThemePreference): Promise<boolean> => {
			const token = localStorage?.getItem('access_token');
			if (!token) return false;

			try {
				const response = await fetch('/api/settings/display', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${token}`
					},
					body: JSON.stringify({ theme_preference: preference })
				});
				if (response.ok) {
					update((state) => ({ ...state, preference }));
					applyTheme(preference);
					return true;
				}
				return false;
			} catch {
				return false;
			}
		}
	};
}

export const theme = createThemeStore();
