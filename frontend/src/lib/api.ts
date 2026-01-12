/**
 * API client for Plex Dashboard backend
 */

const API_BASE = '/api';

interface FetchOptions extends RequestInit {
	params?: Record<string, string | number | boolean>;
}

class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

async function fetchApi<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
	const { params, ...fetchOptions } = options;

	let url = `${API_BASE}${endpoint}`;
	if (params) {
		const searchParams = new URLSearchParams();
		for (const [key, value] of Object.entries(params)) {
			searchParams.set(key, String(value));
		}
		url += `?${searchParams.toString()}`;
	}

	const response = await fetch(url, {
		...fetchOptions,
		headers: {
			'Content-Type': 'application/json',
			...fetchOptions.headers
		}
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
		throw new ApiError(response.status, errorData.detail || response.statusText);
	}

	return response.json();
}

// Content endpoints
export const contentApi = {
	getOldUnwatched: () => fetchApi<{ items: unknown[]; total_count: number }>('/content/old-unwatched'),
	getLargeMovies: (thresholdGb?: number) =>
		fetchApi<{ items: unknown[]; total_count: number }>('/content/large-movies', {
			params: thresholdGb ? { threshold_gb: thresholdGb } : undefined
		}),
	deleteContent: (id: string) =>
		fetchApi<{ success: boolean }>(`/content/${id}`, { method: 'DELETE' })
};

// Language endpoints
export const languageApi = {
	getIssues: (daysBack?: number) =>
		fetchApi<{ items: unknown[]; total_count: number }>('/language/issues', {
			params: daysBack ? { days_back: daysBack } : undefined
		}),
	triggerCheck: () => fetchApi<{ success: boolean }>('/language/check', { method: 'POST' })
};

// Jellyseerr endpoints
export const requestsApi = {
	getUnavailable: () => fetchApi<{ items: unknown[] }>('/requests/unavailable'),
	getInProgress: () => fetchApi<{ items: unknown[] }>('/requests/in-progress'),
	getRecentlyAvailable: () => fetchApi<{ items: unknown[] }>('/requests/recently-available')
};

// Whitelist endpoints
export const whitelistApi = {
	getList: (type: string) => fetchApi<{ items: unknown[] }>(`/whitelist/${type}`),
	addItem: (type: string, name: string) =>
		fetchApi<{ id: number }>(`/whitelist/${type}`, {
			method: 'POST',
			body: JSON.stringify({ name })
		}),
	removeItem: (type: string, id: number) =>
		fetchApi<{ success: boolean }>(`/whitelist/${type}/${id}`, { method: 'DELETE' })
};

// Settings endpoints
export const settingsApi = {
	get: () => fetchApi<Record<string, unknown>>('/settings'),
	update: (settings: Record<string, unknown>) =>
		fetchApi<Record<string, unknown>>('/settings', {
			method: 'PUT',
			body: JSON.stringify(settings)
		})
};

// Health check
export const healthApi = {
	check: () => fetchApi<{ status: string }>('/health')
};

export { ApiError };
