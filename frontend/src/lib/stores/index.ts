/**
 * Svelte stores for global state management
 */

import { writable } from 'svelte/store';
import type { Settings, ApiStats } from '../types';

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
