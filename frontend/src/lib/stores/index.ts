/**
 * Svelte stores for global state management
 */

import { writable, derived, get } from 'svelte/store';
import type { Settings, ApiStats, AuthState } from '../types';

// In-memory token storage (more secure than localStorage)
let accessToken: string | null = null;
let tokenExpiresAt: number | null = null;
let refreshTimer: ReturnType<typeof setTimeout> | null = null;

// Token management functions
function getAccessToken(): string | null {
	return accessToken;
}

function setAccessToken(token: string | null, expiresIn?: number) {
	accessToken = token;
	if (token && expiresIn) {
		tokenExpiresAt = Date.now() + expiresIn * 1000;
	} else {
		tokenExpiresAt = null;
	}
}

function clearTokens() {
	accessToken = null;
	tokenExpiresAt = null;
	if (refreshTimer) {
		clearTimeout(refreshTimer);
		refreshTimer = null;
	}
}

// Authentication state
function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>({
		isAuthenticated: false,
		user: null,
		isLoading: true
	});

	// Schedule proactive token refresh 1 minute before expiration
	const scheduleTokenRefresh = () => {
		if (refreshTimer) {
			clearTimeout(refreshTimer);
			refreshTimer = null;
		}

		if (!tokenExpiresAt) return;

		// Refresh 60 seconds before expiration
		const refreshAt = tokenExpiresAt - 60 * 1000;
		const timeUntilRefresh = refreshAt - Date.now();

		if (timeUntilRefresh > 0) {
			refreshTimer = setTimeout(async () => {
				await store.refreshAccessToken();
			}, timeUntilRefresh);
		}
	};

	const store = {
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
		getToken: getAccessToken,
		setToken: (token: string | null, expiresIn?: number) => {
			setAccessToken(token, expiresIn);
			if (token && expiresIn) {
				scheduleTokenRefresh();
			}
		},
		logout: async () => {
			// Call backend to invalidate refresh token
			try {
				await fetch('/api/auth/logout', {
					method: 'POST',
					credentials: 'include' // Include cookies
				});
			} catch {
				// Ignore errors - we're logging out anyway
			}
			clearTokens();
			set({ isAuthenticated: false, user: null, isLoading: false });
		},
		refreshAccessToken: async (): Promise<boolean> => {
			try {
				const response = await fetch('/api/auth/refresh', {
					method: 'POST',
					credentials: 'include' // Include refresh token cookie
				});

				if (response.ok) {
					const data = await response.json();
					setAccessToken(data.access_token, data.expires_in);
					scheduleTokenRefresh();
					return true;
				}
				return false;
			} catch {
				return false;
			}
		},
		checkAuth: async () => {
			// First, try to get a fresh token via refresh
			const refreshed = await store.refreshAccessToken();

			if (refreshed && accessToken) {
				try {
					const response = await fetch('/api/auth/me', {
						headers: { Authorization: `Bearer ${accessToken}` }
					});
					if (response.ok) {
						const user = await response.json();
						set({ isAuthenticated: true, user, isLoading: false });
						return true;
					}
				} catch {
					// Fall through to unauthenticated
				}
			}

			clearTokens();
			set({ isAuthenticated: false, user: null, isLoading: false });
			return false;
		}
	};

	return store;
}

export const auth = createAuthStore();

/**
 * Wrapper for fetch that handles authentication and automatic token refresh.
 * Use this for all authenticated API calls.
 *
 * @param input - URL or Request object
 * @param init - Request options
 * @returns Response from the API
 * @throws Error if the request fails after token refresh attempt
 */
export async function authenticatedFetch(
	input: RequestInfo | URL,
	init?: RequestInit
): Promise<Response> {
	const token = auth.getToken();
	const headers = new Headers(init?.headers);

	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const response = await fetch(input, {
		...init,
		headers,
		credentials: 'include' // Always include cookies for refresh token
	});

	// If we get a 401, try to refresh the token and retry once
	if (response.status === 401 && token) {
		const refreshed = await auth.refreshAccessToken();

		if (refreshed) {
			const newToken = auth.getToken();
			if (newToken) {
				headers.set('Authorization', `Bearer ${newToken}`);
				return fetch(input, {
					...init,
					headers,
					credentials: 'include'
				});
			}
		}
	}

	return response;
}

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
			const token = getAccessToken();
			if (!token) {
				set({ preference: 'system', isLoading: false });
				return;
			}

			try {
				const response = await fetch('/api/settings/display', {
					headers: { Authorization: `Bearer ${token}` },
					credentials: 'include'
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
			const token = getAccessToken();
			if (!token) return false;

			try {
				const response = await fetch('/api/settings/display', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${token}`
					},
					credentials: 'include',
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
