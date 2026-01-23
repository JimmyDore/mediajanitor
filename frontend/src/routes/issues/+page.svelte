<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { authenticatedFetch } from '$lib/stores';
	import Toast from '$lib/components/Toast.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import ServiceBadge from '$lib/components/ServiceBadge.svelte';

	interface ProblematicEpisode {
		identifier: string;  // e.g., "S01E05"
		name: string;  // Episode title
		season: number;
		episode: number;
		missing_languages: string[];  // e.g., ["missing_en_audio", "missing_fr_audio"]
	}

	interface ContentIssueItem {
		jellyfin_id: string;
		name: string;
		media_type: string;
		production_year: number | null;
		size_bytes: number | null;
		size_formatted: string;
		last_played_date: string | null;
		played: boolean | null;
		path: string | null;
		date_created: string | null;  // When content was added to the library (ISO format)
		issues: string[];
		language_issues: string[] | null;
		tmdb_id: string | null;
		imdb_id: string | null;
		sonarr_title_slug: string | null;  // Sonarr titleSlug for external links (e.g., "arcane")
		jellyseerr_request_id: number | null;  // Matching Jellyseerr request ID (for reconciliation)
		// Series-specific fields for large content detection
		largest_season_size_bytes: number | null;  // For series only - largest season size
		largest_season_size_formatted: string | null;  // Formatted version (e.g., "18.5 GB")
		// Request-specific fields
		requested_by: string | null;
		request_date: string | null;
		missing_seasons: number[] | null;
		release_date: string | null;  // Movie releaseDate or TV firstAirDate (YYYY-MM-DD)
		// US-52.2: Episodes with language issues (for TV series only)
		problematic_episodes: ProblematicEpisode[] | null;
	}

	interface ServiceUrls {
		jellyfin_url: string | null;
		jellyseerr_url: string | null;
		radarr_url: string | null;
		sonarr_url: string | null;
	}

	interface ContentIssuesResponse {
		items: ContentIssueItem[];
		total_count: number;
		total_size_bytes: number;
		total_size_formatted: string;
		service_urls: ServiceUrls | null;
	}

	interface SettingsConfigStatus {
		radarr_configured: boolean;
		sonarr_configured: boolean;
		jellyseerr_configured: boolean;
	}

	type FilterType = 'all' | 'old' | 'large' | 'language' | 'requests';
	type LargeSubFilter = 'all' | 'movies' | 'series';
	type SortField = 'name' | 'size' | 'date' | 'issues' | 'added' | 'requester' | 'release' | 'watched';
	type SortOrder = 'asc' | 'desc';
	type DurationOption = 'permanent' | '1week' | '1month' | '3months' | '6months' | 'custom';
	type WhitelistType = 'content' | 'french-only' | 'language-exempt' | 'large' | 'request';

	// Tooltip text for informational badges
	const badgeTooltips: Record<string, string> = {
		large: 'Re-download in lower quality from Radarr/Sonarr',
		request: 'Check status in Jellyseerr'
	};

	let loading = $state(true);
	let error = $state<string | null>(null);
	let data = $state<ContentIssuesResponse | null>(null);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let toastTimer: ReturnType<typeof setTimeout> | null = null;
	let protectingIds = $state<Set<string>>(new Set());
	let frenchOnlyIds = $state<Set<string>>(new Set());
	let languageExemptIds = $state<Set<string>>(new Set());
	let largeWhitelistIds = $state<Set<string>>(new Set());
	let hidingRequestIds = $state<Set<string>>(new Set());
	let deletingIds = $state<Set<string>>(new Set());
	let activeFilter = $state<FilterType>('all');
	let largeSubFilter = $state<LargeSubFilter>('all');
	// US-52.4: Expanded rows for series with problematic episodes
	let expandedRows = $state<Set<string>>(new Set());
	// US-52.4: Episode whitelisting state (key: jellyfin_id-season-episode)
	let whitelistingEpisodeIds = $state<Set<string>>(new Set());
	// US-52.4: Episode duration picker state
	let showEpisodeDurationPicker = $state(false);
	let selectedEpisode = $state<{ item: ContentIssueItem; episode: ProblematicEpisode } | null>(null);
	let episodeDuration = $state<DurationOption>('permanent');
	let episodeCustomDate = $state('');
	let episodeDurationPickerModal = $state<HTMLElement | null>(null);
	let episodeDurationPickerTrigger = $state<HTMLElement | null>(null);
	let sortField = $state<SortField>('size');
	let sortOrder = $state<SortOrder>('desc');

	// Search state
	let searchQuery = $state('');
	let debouncedSearchQuery = $state('');
	let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	// Configuration status
	let configStatus = $state<SettingsConfigStatus>({
		radarr_configured: false,
		sonarr_configured: false,
		jellyseerr_configured: false
	});

	// Duration picker state
	let showDurationPicker = $state(false);
	let selectedItem = $state<ContentIssueItem | null>(null);
	let selectedWhitelistType = $state<WhitelistType>('content');
	let selectedDuration = $state<DurationOption>('permanent');
	let customDate = $state('');

	// Delete confirmation modal state
	let showDeleteModal = $state(false);
	let deleteItem = $state<ContentIssueItem | null>(null);
	let deleteFromArr = $state(true);
	let deleteFromJellyseerr = $state(true);

	// Modal element references for focus trapping
	let durationPickerModal = $state<HTMLElement | null>(null);
	let deleteModalElement = $state<HTMLElement | null>(null);

	// Trigger element references for focus restoration
	let durationPickerTrigger = $state<HTMLElement | null>(null);
	let deleteModalTrigger = $state<HTMLElement | null>(null);

	const durationOptions: { value: DurationOption; label: string }[] = [
		{ value: 'permanent', label: 'Permanent' },
		{ value: '1week', label: '1 Week' },
		{ value: '1month', label: '1 Month' },
		{ value: '3months', label: '3 Months' },
		{ value: '6months', label: '6 Months' },
		{ value: 'custom', label: 'Custom Date' }
	];

	// Search handlers
	function handleSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		searchQuery = target.value;

		// Debounce the search
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
		searchDebounceTimer = setTimeout(() => {
			debouncedSearchQuery = searchQuery;
		}, 300);
	}

	function clearSearch() {
		searchQuery = '';
		debouncedSearchQuery = '';
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
			searchDebounceTimer = null;
		}
	}

	function matchesSearch(item: ContentIssueItem, query: string): boolean {
		if (!query.trim()) return true;

		const lowerQuery = query.toLowerCase().trim();

		// Match against title
		if (item.name.toLowerCase().includes(lowerQuery)) return true;

		// Match against production year
		if (item.production_year && item.production_year.toString().includes(lowerQuery)) return true;

		// Match against requested_by (for Requests tab)
		if (item.requested_by && item.requested_by.toLowerCase().includes(lowerQuery)) return true;

		return false;
	}

	function isMovieItem(item: ContentIssueItem): boolean {
		const type = item.media_type.toLowerCase();
		return type === 'movie';
	}

	function isSeriesItem(item: ContentIssueItem): boolean {
		const type = item.media_type.toLowerCase();
		return type === 'series' || type === 'tv';
	}

	function applyLargeSubFilter(items: ContentIssueItem[]): ContentIssueItem[] {
		if (activeFilter !== 'large' || largeSubFilter === 'all') {
			return items;
		}
		if (largeSubFilter === 'movies') {
			return items.filter(item => isMovieItem(item));
		}
		if (largeSubFilter === 'series') {
			return items.filter(item => isSeriesItem(item));
		}
		return items;
	}

	function getFilteredItems(items: ContentIssueItem[]): ContentIssueItem[] {
		let filtered = applyLargeSubFilter(items);
		if (!debouncedSearchQuery.trim()) return filtered;
		return filtered.filter(item => matchesSearch(item, debouncedSearchQuery));
	}

	function getFilteredStats(items: ContentIssueItem[]): { count: number; sizeBytes: number } {
		const filtered = getFilteredItems(items);
		const sizeBytes = filtered.reduce((sum, item) => sum + (item.size_bytes || 0), 0);
		return { count: filtered.length, sizeBytes };
	}

	function getExpirationDate(duration: DurationOption, customDateValue: string): string | null {
		if (duration === 'permanent') return null;
		if (duration === 'custom') {
			return customDateValue ? new Date(customDateValue + 'T00:00:00').toISOString() : null;
		}

		const now = new Date();
		switch (duration) {
			case '1week':
				now.setDate(now.getDate() + 7);
				break;
			case '1month':
				now.setMonth(now.getMonth() + 1);
				break;
			case '3months':
				now.setMonth(now.getMonth() + 3);
				break;
			case '6months':
				now.setMonth(now.getMonth() + 6);
				break;
		}
		return now.toISOString();
	}

	function openDurationPicker(item: ContentIssueItem, type: WhitelistType) {
		// Capture trigger element before opening modal (for focus restoration)
		durationPickerTrigger = document.activeElement as HTMLElement | null;
		selectedItem = item;
		selectedWhitelistType = type;
		selectedDuration = 'permanent';
		customDate = '';
		showDurationPicker = true;
	}

	function closeDurationPicker() {
		showDurationPicker = false;
		selectedItem = null;
		// Restore focus to trigger element
		if (durationPickerTrigger) {
			durationPickerTrigger.focus();
			durationPickerTrigger = null;
		}
	}

	// Delete modal functions
	function openDeleteModal(item: ContentIssueItem) {
		// Capture trigger element before opening modal (for focus restoration)
		deleteModalTrigger = document.activeElement as HTMLElement | null;
		deleteItem = item;
		deleteFromArr = true;
		deleteFromJellyseerr = true;
		showDeleteModal = true;
	}

	function closeDeleteModal() {
		showDeleteModal = false;
		deleteItem = null;
		// Restore focus to trigger element
		if (deleteModalTrigger) {
			deleteModalTrigger.focus();
			deleteModalTrigger = null;
		}
	}

	// Get all focusable elements within a container
	function getFocusableElements(container: HTMLElement): HTMLElement[] {
		const selector = 'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
		return Array.from(container.querySelectorAll<HTMLElement>(selector));
	}

	// Handle keyboard events for modals (Escape to close, Tab/Shift+Tab for focus trap)
	function handleKeydown(event: KeyboardEvent) {
		// Handle Escape key to close modals
		if (event.key === 'Escape') {
			if (showEpisodeDurationPicker) {
				closeEpisodeDurationPicker();
			} else if (showDurationPicker) {
				closeDurationPicker();
			} else if (showDeleteModal) {
				closeDeleteModal();
			}
			return;
		}

		// Handle Tab/Shift+Tab for focus trapping within modals
		if (event.key === 'Tab') {
			const activeModal = showEpisodeDurationPicker ? episodeDurationPickerModal :
				(showDurationPicker ? durationPickerModal : (showDeleteModal ? deleteModalElement : null));
			if (!activeModal) return;

			const focusableElements = getFocusableElements(activeModal);
			if (focusableElements.length === 0) return;

			const currentElement = document.activeElement as HTMLElement;
			const currentIndex = focusableElements.indexOf(currentElement);
			const lastIndex = focusableElements.length - 1;

			if (event.shiftKey) {
				// Shift+Tab: go to previous, wrap to last if at first
				if (currentIndex <= 0) {
					event.preventDefault();
					focusableElements[lastIndex].focus();
				}
			} else {
				// Tab: go to next, wrap to first if at last
				if (currentIndex >= lastIndex) {
					event.preventDefault();
					focusableElements[0].focus();
				}
			}
		}
	}

	function isMovieType(mediaType: string): boolean {
		return mediaType.toLowerCase() === 'movie';
	}

	function canDeleteFromArr(item: ContentIssueItem): boolean {
		const isMovie = isMovieType(item.media_type);
		return isMovie ? configStatus.radarr_configured : configStatus.sonarr_configured;
	}

	function getArrName(item: ContentIssueItem): string {
		return isMovieType(item.media_type) ? 'Radarr' : 'Sonarr';
	}

	async function confirmDelete() {
		if (!deleteItem || !deleteItem.tmdb_id) return;

		const item = deleteItem;
		const isMovie = isMovieType(item.media_type);
		const tmdbId = parseInt(item.tmdb_id as string, 10);

		closeDeleteModal();

		deletingIds = new Set([...deletingIds, item.jellyfin_id]);

		try {
			// Determine endpoint and build request body
			const endpoint = isMovie ? `/api/content/movie/${tmdbId}` : `/api/content/series/${tmdbId}`;

			// Get jellyseerr_request_id: either from reconciliation or from request-{id} format
			let jellyseerrRequestId: number | null = null;
			if (item.jellyseerr_request_id) {
				// Use the reconciled ID (available for Jellyfin items with matching Jellyseerr requests)
				jellyseerrRequestId = item.jellyseerr_request_id;
			} else if (item.jellyfin_id.startsWith('request-')) {
				// Extract from jellyfin_id prefix (for request items)
				jellyseerrRequestId = parseInt(item.jellyfin_id.replace('request-', ''), 10);
			}

			const requestBody = {
				tmdb_id: tmdbId,
				delete_from_arr: deleteFromArr,
				delete_from_jellyseerr: deleteFromJellyseerr,
				jellyseerr_request_id: jellyseerrRequestId
			};

			const response = await authenticatedFetch(endpoint, {
				method: 'DELETE',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(requestBody)
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 400) {
				const errorData = await response.json();
				showToast(errorData.detail || 'Deletion failed', 'error');
				return;
			}
			if (!response.ok) { showToast('Deletion failed', 'error'); return; }

			const result = await response.json();

			// Remove item from list on success
			if (result.success && data) {
				const removedItem = data.items.find((i) => i.jellyfin_id === item.jellyfin_id);
				const removedSize = removedItem?.size_bytes || 0;
				data = {
					...data,
					items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
					total_count: data.total_count - 1,
					total_size_bytes: data.total_size_bytes - removedSize,
					total_size_formatted: formatSize(data.total_size_bytes - removedSize)
				};
				showToast('Deleted successfully', 'success');
			} else {
				showToast(result.message || 'Deletion failed', result.success ? 'success' : 'error');
			}
		} catch {
			showToast('Deletion failed', 'error');
		} finally {
			const newSet = new Set(deletingIds);
			newSet.delete(item.jellyfin_id);
			deletingIds = newSet;
		}
	}

	async function deleteRequest(item: ContentIssueItem) {
		// Extract jellyseerr_id from request-{id} format
		const jellyseerrIdMatch = item.jellyfin_id.match(/^request-(\d+)$/);
		if (!jellyseerrIdMatch) {
			showToast('Invalid request ID', 'error');
			return;
		}
		const jellyseerrId = parseInt(jellyseerrIdMatch[1], 10);

		deletingIds = new Set([...deletingIds, item.jellyfin_id]);

		try {
			const response = await authenticatedFetch(`/api/content/request/${jellyseerrId}`, {
				method: 'DELETE'
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 400) {
				const errorData = await response.json();
				showToast(errorData.detail || 'Deletion failed', 'error');
				return;
			}
			if (!response.ok) { showToast('Deletion failed', 'error'); return; }

			// Remove item from list on success
			if (data) {
				data = {
					...data,
					items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
					total_count: data.total_count - 1
				};
			}
			showToast('Request deleted', 'success');
		} catch {
			showToast('Deletion failed', 'error');
		} finally {
			const newSet = new Set(deletingIds);
			newSet.delete(item.jellyfin_id);
			deletingIds = newSet;
		}
	}

	async function fetchConfigStatus() {
		try {
			const [radarrRes, sonarrRes, jellyseerrRes] = await Promise.all([
				authenticatedFetch('/api/settings/radarr'),
				authenticatedFetch('/api/settings/sonarr'),
				authenticatedFetch('/api/settings/jellyseerr')
			]);

			if (radarrRes.ok) {
				const radarrData = await radarrRes.json();
				configStatus.radarr_configured = radarrData.api_key_configured;
			}
			if (sonarrRes.ok) {
				const sonarrData = await sonarrRes.json();
				configStatus.sonarr_configured = sonarrData.api_key_configured;
			}
			if (jellyseerrRes.ok) {
				const jellyseerrData = await jellyseerrRes.json();
				configStatus.jellyseerr_configured = jellyseerrData.api_key_configured;
			}
		} catch {
			// Silently fail - buttons will be disabled
		}
	}

	async function confirmWhitelist() {
		if (!selectedItem) return;

		const item = selectedItem;
		const type = selectedWhitelistType;
		const expiresAt = getExpirationDate(selectedDuration, customDate);

		closeDurationPicker();

		if (type === 'content') {
			await protectContentWithExpiration(item, expiresAt);
		} else if (type === 'french-only') {
			await markAsFrenchOnlyWithExpiration(item, expiresAt);
		} else if (type === 'language-exempt') {
			await markAsLanguageExemptWithExpiration(item, expiresAt);
		} else if (type === 'large') {
			await addToLargeWhitelistWithExpiration(item, expiresAt);
		} else if (type === 'request') {
			await hideRequestWithExpiration(item, expiresAt);
		}
	}

	// US-52.4: Toggle row expansion for series with problematic episodes
	function toggleRowExpansion(jellyfinId: string) {
		const newSet = new Set(expandedRows);
		if (newSet.has(jellyfinId)) {
			newSet.delete(jellyfinId);
		} else {
			newSet.add(jellyfinId);
		}
		expandedRows = newSet;
	}

	// US-52.4: Check if a row has expandable episodes
	function hasExpandableEpisodes(item: ContentIssueItem): boolean {
		return item.problematic_episodes !== null && item.problematic_episodes.length > 0;
	}

	// US-52.4: Open episode duration picker
	function openEpisodeDurationPicker(item: ContentIssueItem, episode: ProblematicEpisode) {
		episodeDurationPickerTrigger = document.activeElement as HTMLElement | null;
		selectedEpisode = { item, episode };
		episodeDuration = 'permanent';
		episodeCustomDate = '';
		showEpisodeDurationPicker = true;
	}

	// US-52.4: Close episode duration picker
	function closeEpisodeDurationPicker() {
		showEpisodeDurationPicker = false;
		selectedEpisode = null;
		if (episodeDurationPickerTrigger) {
			episodeDurationPickerTrigger.focus();
			episodeDurationPickerTrigger = null;
		}
	}

	// US-52.4: Confirm episode whitelist
	async function confirmEpisodeWhitelist() {
		if (!selectedEpisode) return;

		const { item, episode } = selectedEpisode;
		const expiresAt = getExpirationDate(episodeDuration, episodeCustomDate);

		closeEpisodeDurationPicker();
		await whitelistEpisode(item, episode, expiresAt);
	}

	// US-52.4: Whitelist an episode
	async function whitelistEpisode(item: ContentIssueItem, episode: ProblematicEpisode, expiresAt: string | null) {
		const episodeKey = `${item.jellyfin_id}-${episode.season}-${episode.episode}`;
		whitelistingEpisodeIds = new Set([...whitelistingEpisodeIds, episodeKey]);

		try {
			const response = await authenticatedFetch('/api/whitelist/episode-exempt', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					jellyfin_id: item.jellyfin_id,
					series_name: item.name,
					season_number: episode.season,
					episode_number: episode.episode,
					episode_name: episode.name,
					expires_at: expiresAt
				})
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 409) { showToast('Episode already exempt', 'error'); return; }
			if (!response.ok) { showToast('Failed to whitelist episode', 'error'); return; }

			// Optimistic update: remove episode from the item's problematic_episodes list
			if (data) {
				data = {
					...data,
					items: data.items.map(i => {
						if (i.jellyfin_id !== item.jellyfin_id) return i;
						const updatedEpisodes = i.problematic_episodes?.filter(
							ep => !(ep.season === episode.season && ep.episode === episode.episode)
						) ?? null;
						// If no more problematic episodes, remove language issue from item
						// and potentially remove item from list if it was the only issue
						const shouldRemoveLanguageIssue = !updatedEpisodes || updatedEpisodes.length === 0;
						const updatedIssues = shouldRemoveLanguageIssue
							? i.issues.filter(issue => issue !== 'language')
							: i.issues;
						return {
							...i,
							problematic_episodes: updatedEpisodes && updatedEpisodes.length > 0 ? updatedEpisodes : null,
							issues: updatedIssues
						};
					}).filter(i => {
						// Remove items with no remaining issues
						return i.issues.length > 0;
					})
				};
				// Update total count
				const newCount = data.items.length;
				const newSize = data.items.reduce((sum, i) => sum + (i.size_bytes || 0), 0);
				data = {
					...data,
					total_count: newCount,
					total_size_bytes: newSize,
					total_size_formatted: formatSize(newSize)
				};
			}
			showToast('Episode whitelisted', 'success');
		} catch { showToast('Failed to whitelist episode', 'error'); }
		finally {
			const newSet = new Set(whitelistingEpisodeIds);
			newSet.delete(episodeKey);
			whitelistingEpisodeIds = newSet;
		}
	}

	// US-52.4: Format missing language badge text
	function formatLanguageBadge(lang: string): string {
		switch (lang) {
			case 'missing_en_audio': return 'EN';
			case 'missing_fr_audio': return 'FR';
			case 'missing_fr_subs': return 'FR Sub';
			default: return lang;
		}
	}

	$effect(() => {
		const urlFilter = $page.url.searchParams.get('filter');
		if (urlFilter && ['all', 'old', 'large', 'language', 'requests'].includes(urlFilter)) {
			activeFilter = urlFilter as FilterType;
		}
	});

	const filterLabels: Record<FilterType, string> = {
		all: 'All',
		old: 'Old',
		large: 'Large',
		language: 'Language',
		requests: 'Unavailable'
	};

	function isRequestItem(item: ContentIssueItem): boolean {
		return item.issues.includes('request');
	}

	function formatLastWatched(lastPlayed: string | null, played: boolean | null): string {
		// If we have a date, format it
		if (lastPlayed) {
			try {
				const date = new Date(lastPlayed);
				const now = new Date();
				const daysAgo = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
				if (daysAgo > 365) return `${Math.floor(daysAgo / 365)}y`;
				if (daysAgo > 30) return `${Math.floor(daysAgo / 30)}mo`;
				return `${daysAgo}d`;
			} catch {
				return '?';
			}
		}
		// No date - check if it was played
		if (played) return 'Watched';
		return 'Never';
	}

	function formatRequestDate(requestDate: string | null): string {
		if (!requestDate) return '—';
		try {
			const date = new Date(requestDate);
			const now = new Date();
			const daysAgo = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
			if (daysAgo > 365) return `${Math.floor(daysAgo / 365)}y ago`;
			if (daysAgo > 30) return `${Math.floor(daysAgo / 30)}mo ago`;
			if (daysAgo === 0) return 'Today';
			if (daysAgo === 1) return 'Yesterday';
			return `${daysAgo}d ago`;
		} catch {
			return '?';
		}
	}

	function formatReleaseDate(releaseDate: string | null): string {
		if (!releaseDate) return '—';
		try {
			const date = new Date(releaseDate);
			// Format as "Jan 15, 2026"
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
		} catch {
			return '?';
		}
	}

	function formatDateCreated(dateCreated: string | null): string {
		if (!dateCreated) return 'Unknown';
		try {
			const date = new Date(dateCreated);
			// Format as "Jan 15, 2024"
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
		} catch {
			return '?';
		}
	}

	function isFutureRelease(releaseDate: string | null): boolean {
		if (!releaseDate) return false;
		try {
			const date = new Date(releaseDate);
			const today = new Date();
			today.setHours(0, 0, 0, 0);
			return date > today;
		} catch {
			return false;
		}
	}

	function showToast(message: string, type: 'success' | 'error') {
		// Clear any existing timer
		if (toastTimer) {
			clearTimeout(toastTimer);
		}
		toast = { message, type };
		toastTimer = setTimeout(() => {
			toast = null;
			toastTimer = null;
		}, 3000);
	}

	function closeToast() {
		if (toastTimer) {
			clearTimeout(toastTimer);
			toastTimer = null;
		}
		toast = null;
	}

	async function protectContentWithExpiration(item: ContentIssueItem, expiresAt: string | null) {
		protectingIds = new Set([...protectingIds, item.jellyfin_id]);

		try {
			const response = await authenticatedFetch('/api/whitelist/content', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ jellyfin_id: item.jellyfin_id, name: item.name, media_type: item.media_type, expires_at: expiresAt })
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 409) { showToast('Already protected', 'error'); return; }
			if (!response.ok) { showToast('Failed to protect', 'error'); return; }

			if (data) {
				const removedItem = data.items.find((i) => i.jellyfin_id === item.jellyfin_id);
				const removedSize = removedItem?.size_bytes || 0;
				data = {
					...data,
					items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
					total_count: data.total_count - 1,
					total_size_bytes: data.total_size_bytes - removedSize,
					total_size_formatted: formatSize(data.total_size_bytes - removedSize)
				};
			}
			showToast('Protected', 'success');
		} catch { showToast('Failed', 'error'); }
		finally {
			const newSet = new Set(protectingIds);
			newSet.delete(item.jellyfin_id);
			protectingIds = newSet;
		}
	}

	async function markAsFrenchOnlyWithExpiration(item: ContentIssueItem, expiresAt: string | null) {
		frenchOnlyIds = new Set([...frenchOnlyIds, item.jellyfin_id]);

		try {
			const response = await authenticatedFetch('/api/whitelist/french-only', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ jellyfin_id: item.jellyfin_id, name: item.name, media_type: item.media_type, expires_at: expiresAt })
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 409) { showToast('Already FR-only', 'error'); return; }
			if (!response.ok) { showToast('Failed', 'error'); return; }

			if (data) {
				const currentItem = data.items.find((i) => i.jellyfin_id === item.jellyfin_id);
				if (currentItem) {
					const hasOnlyEnglishIssue = currentItem.language_issues?.length === 1 && currentItem.language_issues[0] === 'missing_en_audio';
					if (hasOnlyEnglishIssue && currentItem.issues.length === 1) {
						const removedSize = currentItem.size_bytes || 0;
						data = {
							...data,
							items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
							total_count: data.total_count - 1,
							total_size_bytes: data.total_size_bytes - removedSize,
							total_size_formatted: formatSize(data.total_size_bytes - removedSize)
						};
					} else {
						await fetchIssues(activeFilter);
					}
				}
			}
			showToast('Marked FR-only', 'success');
		} catch { showToast('Failed', 'error'); }
		finally {
			const newSet = new Set(frenchOnlyIds);
			newSet.delete(item.jellyfin_id);
			frenchOnlyIds = newSet;
		}
	}

	async function markAsLanguageExemptWithExpiration(item: ContentIssueItem, expiresAt: string | null) {
		languageExemptIds = new Set([...languageExemptIds, item.jellyfin_id]);

		try {
			const response = await authenticatedFetch('/api/whitelist/language-exempt', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ jellyfin_id: item.jellyfin_id, name: item.name, media_type: item.media_type, expires_at: expiresAt })
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 409) { showToast('Already exempt', 'error'); return; }
			if (!response.ok) { showToast('Failed', 'error'); return; }

			if (data) {
				const currentItem = data.items.find((i) => i.jellyfin_id === item.jellyfin_id);
				if (currentItem) {
					const hasOnlyLanguageIssue = currentItem.issues.length === 1 && currentItem.issues[0] === 'language';
					if (hasOnlyLanguageIssue) {
						const removedSize = currentItem.size_bytes || 0;
						data = {
							...data,
							items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
							total_count: data.total_count - 1,
							total_size_bytes: data.total_size_bytes - removedSize,
							total_size_formatted: formatSize(data.total_size_bytes - removedSize)
						};
					} else {
						await fetchIssues(activeFilter);
					}
				}
			}
			showToast('Language exempt', 'success');
		} catch { showToast('Failed', 'error'); }
		finally {
			const newSet = new Set(languageExemptIds);
			newSet.delete(item.jellyfin_id);
			languageExemptIds = newSet;
		}
	}

	async function addToLargeWhitelistWithExpiration(item: ContentIssueItem, expiresAt: string | null) {
		largeWhitelistIds = new Set([...largeWhitelistIds, item.jellyfin_id]);

		try {
			const response = await authenticatedFetch('/api/whitelist/large', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ jellyfin_id: item.jellyfin_id, name: item.name, media_type: item.media_type, expires_at: expiresAt })
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 409) { showToast('Already whitelisted', 'error'); return; }
			if (!response.ok) { showToast('Failed', 'error'); return; }

			if (data) {
				const currentItem = data.items.find((i) => i.jellyfin_id === item.jellyfin_id);
				if (currentItem) {
					const hasOnlyLargeIssue = currentItem.issues.length === 1 && currentItem.issues[0] === 'large';
					if (hasOnlyLargeIssue) {
						const removedSize = currentItem.size_bytes || 0;
						data = {
							...data,
							items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
							total_count: data.total_count - 1,
							total_size_bytes: data.total_size_bytes - removedSize,
							total_size_formatted: formatSize(data.total_size_bytes - removedSize)
						};
					} else {
						await fetchIssues(activeFilter);
					}
				}
			}
			showToast('Large content whitelisted', 'success');
		} catch { showToast('Failed', 'error'); }
		finally {
			const newSet = new Set(largeWhitelistIds);
			newSet.delete(item.jellyfin_id);
			largeWhitelistIds = newSet;
		}
	}

	async function hideRequestWithExpiration(item: ContentIssueItem, expiresAt: string | null) {
		hidingRequestIds = new Set([...hidingRequestIds, item.jellyfin_id]);

		// Extract numeric jellyseerr_id from "request-{id}" format
		const jellyseerrIdMatch = item.jellyfin_id.match(/^request-(\d+)$/);
		const jellyseerrId = jellyseerrIdMatch ? parseInt(jellyseerrIdMatch[1], 10) : parseInt(item.jellyfin_id, 10);

		try {
			const response = await authenticatedFetch('/api/whitelist/requests', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ jellyseerr_id: jellyseerrId, title: item.name, media_type: item.media_type, expires_at: expiresAt })
			});

			if (response.status === 401) { showToast('Session expired', 'error'); return; }
			if (response.status === 409) { showToast('Already hidden', 'error'); return; }
			if (!response.ok) { showToast('Failed to hide', 'error'); return; }

			// Remove item from list
			if (data) {
				data = {
					...data,
					items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
					total_count: data.total_count - 1
				};
			}
			showToast('Hidden', 'success');
		} catch { showToast('Failed', 'error'); }
		finally {
			const newSet = new Set(hidingRequestIds);
			newSet.delete(item.jellyfin_id);
			hidingRequestIds = newSet;
		}
	}

	function hasMissingEnglishAudio(item: ContentIssueItem): boolean {
		return item.language_issues?.includes('missing_en_audio') ?? false;
	}

	function hasLanguageIssues(item: ContentIssueItem): boolean {
		return item.issues.includes('language');
	}

	function getTmdbUrl(item: ContentIssueItem): string | null {
		if (!item.tmdb_id) return null;
		// Handle both Jellyfin (Movie/Series) and Jellyseerr (movie/tv) media types
		const mediaType = item.media_type.toLowerCase() === 'movie' ? 'movie' : 'tv';
		return `https://www.themoviedb.org/${mediaType}/${item.tmdb_id}`;
	}


	function getJellyfinUrl(item: ContentIssueItem): string | null {
		// Only show for Jellyfin content (not request items)
		if (isRequestItem(item)) return null;
		const baseUrl = data?.service_urls?.jellyfin_url;
		if (!baseUrl || !item.jellyfin_id) return null;
		// Jellyfin web URL pattern: /web/index.html#!/details?id={jellyfin_id}
		return `${baseUrl.replace(/\/$/, '')}/web/index.html#!/details?id=${item.jellyfin_id}`;
	}

	function getJellyseerrUrl(item: ContentIssueItem): string | null {
		const baseUrl = data?.service_urls?.jellyseerr_url;
		if (!baseUrl || !item.tmdb_id) return null;
		// Jellyseerr URL pattern: /movie/{tmdb_id} or /tv/{tmdb_id}
		const mediaType = item.media_type.toLowerCase() === 'movie' ? 'movie' : 'tv';
		return `${baseUrl.replace(/\/$/, '')}/${mediaType}/${item.tmdb_id}`;
	}

	function getRadarrUrl(item: ContentIssueItem): string | null {
		// Only show for movies
		if (item.media_type.toLowerCase() !== 'movie') return null;
		const baseUrl = data?.service_urls?.radarr_url;
		if (!baseUrl || !item.tmdb_id) return null;
		// Radarr URL pattern for movie details (using TMDB ID): /movie/{tmdb_id}
		return `${baseUrl.replace(/\/$/, '')}/movie/${item.tmdb_id}`;
	}

	function getSonarrUrl(item: ContentIssueItem): string | null {
		// Only show for series
		if (item.media_type.toLowerCase() !== 'series' && item.media_type.toLowerCase() !== 'tv') return null;
		const baseUrl = data?.service_urls?.sonarr_url;
		if (!baseUrl || !item.sonarr_title_slug) return null;
		// Sonarr URL pattern for series (using titleSlug): /series/{titleSlug}
		return `${baseUrl.replace(/\/$/, '')}/series/${item.sonarr_title_slug}`;
	}

	function formatSize(sizeBytes: number): string {
		if (sizeBytes === 0) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		let size = sizeBytes;
		let unitIndex = 0;
		while (size >= 1024 && unitIndex < units.length - 1) {
			size /= 1024;
			unitIndex++;
		}
		return unitIndex === 0 ? `${Math.round(size)} ${units[unitIndex]}` : `${size.toFixed(1)} ${units[unitIndex]}`;
	}

	async function fetchIssues(filter: FilterType) {
		loading = true;
		error = null;
		try {
			const filterParam = filter === 'all' ? '' : `?filter=${filter}`;
			const response = await authenticatedFetch(`/api/content/issues${filterParam}`);

			if (response.status === 401) { error = 'Session expired'; return; }
			if (!response.ok) { error = 'Failed to fetch issues'; return; }

			data = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch issues';
		} finally {
			loading = false;
		}
	}

	function setFilter(filter: FilterType) {
		activeFilter = filter;
		// Reset sub-filter when changing tabs
		largeSubFilter = 'all';
		const url = filter === 'all' ? '/issues' : `/issues?filter=${filter}`;
		goto(url, { replaceState: true });
		fetchIssues(filter);
	}

	function toggleSort(field: SortField) {
		if (sortField === field) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortField = field;
			sortOrder = field === 'name' ? 'asc' : 'desc';
		}
	}

	function getSortedItems(items: ContentIssueItem[]): ContentIssueItem[] {
		return [...items].sort((a, b) => {
			let comparison = 0;
			switch (sortField) {
				case 'name': comparison = a.name.localeCompare(b.name); break;
				case 'size': comparison = (a.size_bytes || 0) - (b.size_bytes || 0); break;
				case 'date':
					// For requests, use request_date; for content, use last_played_date
					const dateA = a.request_date
						? new Date(a.request_date).getTime()
						: (a.last_played_date ? new Date(a.last_played_date).getTime() : 0);
					const dateB = b.request_date
						? new Date(b.request_date).getTime()
						: (b.last_played_date ? new Date(b.last_played_date).getTime() : 0);
					comparison = dateA - dateB;
					break;
				case 'added':
					// Sort by date_created (when content was added to library)
					const addedA = a.date_created ? new Date(a.date_created).getTime() : 0;
					const addedB = b.date_created ? new Date(b.date_created).getTime() : 0;
					comparison = addedA - addedB;
					break;
				case 'issues': comparison = a.issues.length - b.issues.length; break;
				case 'requester':
					// Sort alphabetically by requester name (nulls last)
					const reqA = a.requested_by?.toLowerCase() ?? '';
					const reqB = b.requested_by?.toLowerCase() ?? '';
					if (!reqA && reqB) comparison = 1;
					else if (reqA && !reqB) comparison = -1;
					else comparison = reqA.localeCompare(reqB);
					break;
				case 'release':
					// Sort by release date (nulls last)
					const relA = a.release_date ? new Date(a.release_date).getTime() : 0;
					const relB = b.release_date ? new Date(b.release_date).getTime() : 0;
					if (!relA && relB) comparison = 1;
					else if (relA && !relB) comparison = -1;
					else comparison = relA - relB;
					break;
				case 'watched':
					// Sort by watched status: date > "Watched" (no date) > "Never"
					// Priority: 1 = has date, 2 = played without date, 3 = never
					function getWatchPriority(item: ContentIssueItem): number {
						if (item.last_played_date) return 1;
						if (item.played) return 2;
						return 3;
					}
					const priorityA = getWatchPriority(a);
					const priorityB = getWatchPriority(b);
					if (priorityA !== priorityB) {
						// Different priorities: in DESC, lower number comes first
						comparison = priorityA - priorityB;
					} else if (priorityA === 1) {
						// Both have dates: sort by date
						const watchedDateA = new Date(a.last_played_date!).getTime();
						const watchedDateB = new Date(b.last_played_date!).getTime();
						comparison = watchedDateA - watchedDateB;
					}
					// Same priority without dates: maintain stable order (comparison = 0)
					break;
			}
			return sortOrder === 'asc' ? comparison : -comparison;
		});
	}

	// Auto-focus when duration picker modal opens
	$effect(() => {
		if (showDurationPicker && durationPickerModal) {
			// Focus the first radio input (Permanent option)
			const focusable = getFocusableElements(durationPickerModal);
			if (focusable.length > 0) {
				focusable[0].focus();
			}
		}
	});

	// Auto-focus when delete modal opens (focus Cancel button as safer default)
	$effect(() => {
		if (showDeleteModal && deleteModalElement) {
			// Focus the Cancel button (btn-secondary) as the safer default
			const cancelButton = deleteModalElement.querySelector<HTMLElement>('.btn-secondary');
			if (cancelButton) {
				cancelButton.focus();
			}
		}
	});

	// US-52.4: Auto-focus when episode duration picker modal opens
	$effect(() => {
		if (showEpisodeDurationPicker && episodeDurationPickerModal) {
			const focusable = getFocusableElements(episodeDurationPickerModal);
			if (focusable.length > 0) {
				focusable[0].focus();
			}
		}
	});

	onMount(() => {
		fetchIssues(activeFilter);
		fetchConfigStatus();
	});
</script>

<!-- Listen for Escape key to close modals -->
<svelte:window onkeydown={handleKeydown} />

<svelte:head>
	<title>Issues - Media Janitor</title>
</svelte:head>

{#if toast}
	<Toast message={toast.message} type={toast.type} onclose={closeToast} />
{/if}

<div class="issues-page" aria-busy={loading}>
	<header class="page-header">
		<div class="header-main">
			<h1>Issues</h1>
			{#if data && !loading}
				{@const filteredStats = getFilteredStats(data.items)}
				<span class="header-stats">
					{#if debouncedSearchQuery.trim()}
						{filteredStats.count} of {data.total_count} items · {formatSize(filteredStats.sizeBytes)}
					{:else}
						{data.total_count} items · {data.total_size_formatted}
					{/if}
				</span>
			{/if}
		</div>
		<SearchInput
			value={searchQuery}
			placeholder="Search by title, year..."
			aria-label="Search issues by title or year"
			oninput={handleSearchInput}
			onclear={clearSearch}
		/>
	</header>

	<!-- Filter Tabs (underline style) -->
	<nav class="filter-nav">
		{#each Object.entries(filterLabels) as [filter, label]}
			<button
				class="filter-tab"
				class:active={activeFilter === filter}
				onclick={() => setFilter(filter as FilterType)}
			>
				{label}
			</button>
		{/each}
	</nav>

	<!-- Sub-filter for Large tab -->
	{#if activeFilter === 'large'}
		<div class="sub-filter-nav">
			<button
				class="sub-filter-btn"
				class:active={largeSubFilter === 'all'}
				onclick={() => largeSubFilter = 'all'}
			>
				All
			</button>
			<button
				class="sub-filter-btn"
				class:active={largeSubFilter === 'movies'}
				onclick={() => largeSubFilter = 'movies'}
			>
				Movies
			</button>
			<button
				class="sub-filter-btn"
				class:active={largeSubFilter === 'series'}
				onclick={() => largeSubFilter = 'series'}
			>
				Series
			</button>
		</div>
	{/if}

	{#if loading}
		<div class="loading" role="status" aria-label="Loading issues">
			<span class="spinner" aria-hidden="true"></span>
		</div>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else if data}
		{#if data.items.length === 0}
			<div class="empty" aria-live="polite">No issues found</div>
		{:else if getFilteredItems(data.items).length === 0}
			<div class="empty" aria-live="polite">No matching items found</div>
		{:else}
			<div class="table-container" aria-live="polite">
				<table class="issues-table" class:requests-view={activeFilter === 'requests'}>
					<thead>
						<tr>
							<th class="col-name">
								<button class="sort-btn" onclick={() => toggleSort('name')}>
									Name {sortField === 'name' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							{#if activeFilter === 'requests'}
								<th class="col-requester">
									<button class="sort-btn" onclick={() => toggleSort('requester')}>
										Requester {sortField === 'requester' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
									</button>
								</th>
							{/if}
							{#if activeFilter !== 'requests'}
								<th class="col-issues">
									<button class="sort-btn" onclick={() => toggleSort('issues')}>
										Issues {sortField === 'issues' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
									</button>
								</th>
							{/if}
							<th class="col-size">
								<button class="sort-btn" onclick={() => toggleSort('size')}>
									Size {sortField === 'size' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							<th class="col-added">
								<button class="sort-btn" onclick={() => toggleSort('added')}>
									Added {sortField === 'added' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							{#if activeFilter === 'requests'}
								<th class="col-release">
									<button class="sort-btn" onclick={() => toggleSort('release')}>
										Release {sortField === 'release' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
									</button>
								</th>
							{/if}
							<th class="col-watched">
								{#if activeFilter === 'requests'}
									<button class="sort-btn" onclick={() => toggleSort('date')}>
										Requested {sortField === 'date' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
									</button>
								{:else}
									<button class="sort-btn" onclick={() => toggleSort('watched')}>
										Watched {sortField === 'watched' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
									</button>
								{/if}
							</th>
							<th class="col-actions"></th>
						</tr>
					</thead>
					<tbody>
						{#each getSortedItems(getFilteredItems(data.items)) as item}
							<tr
								class:expandable={hasExpandableEpisodes(item)}
								class:expanded={expandedRows.has(item.jellyfin_id)}
								onclick={(e) => {
									// Only toggle if clicking on the row itself (not buttons/links)
									const target = e.target as HTMLElement;
									if (hasExpandableEpisodes(item) && !target.closest('button, a, .badge-action')) {
										toggleRowExpansion(item.jellyfin_id);
									}
								}}
								role={hasExpandableEpisodes(item) ? 'button' : undefined}
								tabindex={hasExpandableEpisodes(item) ? 0 : undefined}
								aria-expanded={hasExpandableEpisodes(item) ? expandedRows.has(item.jellyfin_id) : undefined}
								onkeydown={(e) => {
									if (hasExpandableEpisodes(item) && (e.key === 'Enter' || e.key === ' ')) {
										e.preventDefault();
										toggleRowExpansion(item.jellyfin_id);
									}
								}}
							>
								<td class="col-name">
									<div class="name-cell">
										<div class="title-row">
											{#if hasExpandableEpisodes(item)}
												<span class="expand-icon" aria-hidden="true">
													{#if expandedRows.has(item.jellyfin_id)}
														<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
															<polyline points="6 9 12 15 18 9"/>
														</svg>
													{:else}
														<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
															<polyline points="9 18 15 12 9 6"/>
														</svg>
													{/if}
												</span>
											{/if}
											<span class="item-name" title={item.name}>{item.name}</span>
											<span class="item-year">{item.production_year ?? '—'}</span>
											{#if hasExpandableEpisodes(item)}
												<span class="episode-count" title="Episodes with language issues">
													{item.problematic_episodes?.length} {item.problematic_episodes?.length === 1 ? 'episode' : 'episodes'}
												</span>
											{/if}
											{#if isRequestItem(item) && item.missing_seasons && item.missing_seasons.length > 0}
												<span class="missing-seasons" title="Missing seasons">
													S{item.missing_seasons.join(', S')}
												</span>
											{/if}
										</div>
										<span class="external-links">
											{#if getJellyfinUrl(item)}
												<ServiceBadge service="jellyfin" url={getJellyfinUrl(item) ?? ''} title="View in Jellyfin" />
											{/if}
											{#if getJellyseerrUrl(item)}
												<ServiceBadge service="jellyseerr" url={getJellyseerrUrl(item) ?? ''} title="View in Jellyseerr" />
											{/if}
											{#if getRadarrUrl(item)}
												<ServiceBadge service="radarr" url={getRadarrUrl(item) ?? ''} title="View in Radarr" />
											{/if}
											{#if getSonarrUrl(item)}
												<ServiceBadge service="sonarr" url={getSonarrUrl(item) ?? ''} title="View in Sonarr" />
											{/if}
											{#if getTmdbUrl(item)}
												<ServiceBadge service="tmdb" url={getTmdbUrl(item) ?? ''} title="View on TMDB" />
											{/if}
										</span>
									</div>
								</td>
								{#if activeFilter === 'requests'}
									<td class="col-requester">
										{item.requested_by ?? '—'}
									</td>
								{/if}
								{#if activeFilter !== 'requests'}
								<td class="col-issues">
									<div class="badge-groups">
										{#each item.issues as issue}
											{#if issue === 'old'}
												<!-- OLD badge with inline protect action -->
												<span class="badge-group">
													<span class="badge badge-old">old</span>
													<button
														class="badge-action"
														onclick={() => openDurationPicker(item, 'content')}
														disabled={protectingIds.has(item.jellyfin_id)}
														title="Protect from deletion"
													>
														{#if protectingIds.has(item.jellyfin_id)}
															<span class="badge-spin"></span>
														{:else}
															<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
																<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
															</svg>
														{/if}
													</button>
												</span>
											{:else if issue === 'language'}
												<!-- LANGUAGE badge with inline actions -->
												<span class="badge-group">
													<span class="badge badge-language">language</span>
													{#if hasMissingEnglishAudio(item)}
														<button
															class="badge-action"
															onclick={() => openDurationPicker(item, 'french-only')}
															disabled={frenchOnlyIds.has(item.jellyfin_id)}
															title="Mark as French-only"
														>
															{#if frenchOnlyIds.has(item.jellyfin_id)}
																<span class="badge-spin"></span>
															{:else}
																FR
															{/if}
														</button>
													{/if}
													<button
														class="badge-action"
														onclick={() => openDurationPicker(item, 'language-exempt')}
														disabled={languageExemptIds.has(item.jellyfin_id)}
														title="Exempt from language checks"
													>
														{#if languageExemptIds.has(item.jellyfin_id)}
															<span class="badge-spin"></span>
														{:else}
															<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
																<polyline points="20 6 9 17 4 12"/>
															</svg>
														{/if}
													</button>
												</span>
											{:else if issue === 'large'}
												<!-- LARGE badge with whitelist action -->
												<span class="badge-group">
													<span class="badge badge-large" title={badgeTooltips.large}>large</span>
													<button
														class="badge-action"
														onclick={() => openDurationPicker(item, 'large')}
														disabled={largeWhitelistIds.has(item.jellyfin_id)}
														title="Keep in high quality"
													>
														{#if largeWhitelistIds.has(item.jellyfin_id)}
															<span class="badge-spin"></span>
														{:else}
															<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
																<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
															</svg>
														{/if}
													</button>
												</span>
											{:else if issue === 'request'}
												<!-- REQUEST badge with hide action -->
												<span class="badge-group">
													<span class="badge badge-request" title={badgeTooltips.request}>request</span>
													<button
														class="badge-action"
														onclick={() => openDurationPicker(item, 'request')}
														disabled={hidingRequestIds.has(item.jellyfin_id)}
														title="Hide this request"
													>
														{#if hidingRequestIds.has(item.jellyfin_id)}
															<span class="badge-spin"></span>
														{:else}
															<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
																<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
																<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
																<line x1="1" y1="1" x2="23" y2="23"/>
															</svg>
														{/if}
													</button>
												</span>
											{:else}
												<span class="badge badge-{issue}">{issue}</span>
											{/if}
										{/each}
									</div>
								</td>
								{/if}
								<td class="col-size">
									{#if isRequestItem(item)}
										<span class="text-muted">—</span>
									{:else if isSeriesItem(item) && item.largest_season_size_formatted}
										<span class="size-with-label" title="Largest season size">
											<span class="size-label">Largest season:</span>
											<span class="size-value">{item.largest_season_size_formatted}</span>
										</span>
									{:else}
										{item.size_formatted}
									{/if}
								</td>
								<td class="col-added">
									{#if isRequestItem(item)}
										<span class="text-muted">—</span>
									{:else}
										{formatDateCreated(item.date_created)}
									{/if}
								</td>
								{#if activeFilter === 'requests'}
									<td class="col-release" class:future={isFutureRelease(item.release_date)}>
										{formatReleaseDate(item.release_date)}
									</td>
								{/if}
								<td class="col-watched" class:never={!isRequestItem(item) && !item.last_played_date && !item.played}>
									{#if isRequestItem(item)}
										{formatRequestDate(item.request_date)}
									{:else}
										{formatLastWatched(item.last_played_date, item.played)}
									{/if}
								</td>
								<td class="col-actions">
									{#if isRequestItem(item)}
										<!-- Request items: whitelist and delete buttons -->
										<div class="action-buttons">
											<button
												class="btn-action btn-whitelist"
												onclick={() => openDurationPicker(item, 'request')}
												disabled={hidingRequestIds.has(item.jellyfin_id)}
												title="Hide this request"
											>
												{#if hidingRequestIds.has(item.jellyfin_id)}
													<span class="btn-spinner"></span>
												{:else}
													<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
														<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
														<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
														<line x1="1" y1="1" x2="23" y2="23"/>
													</svg>
												{/if}
											</button>
											<button
												class="btn-action btn-delete"
												onclick={() => deleteRequest(item)}
												disabled={deletingIds.has(item.jellyfin_id) || !configStatus.jellyseerr_configured}
												title={!configStatus.jellyseerr_configured ? 'Jellyseerr not configured' : 'Delete request from Jellyseerr'}
											>
												{#if deletingIds.has(item.jellyfin_id)}
													<span class="btn-spinner"></span>
												{:else}
													<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
														<polyline points="3 6 5 6 21 6"/>
														<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
													</svg>
												{/if}
											</button>
										</div>
									{:else}
										<!-- Content items: delete from Radarr/Sonarr -->
										<button
											class="btn-delete"
											onclick={() => openDeleteModal(item)}
											disabled={deletingIds.has(item.jellyfin_id) || !item.tmdb_id || !canDeleteFromArr(item)}
											title={!item.tmdb_id ? 'No TMDB ID' : !canDeleteFromArr(item) ? `${getArrName(item)} not configured` : `Delete from ${getArrName(item)}`}
										>
											{#if deletingIds.has(item.jellyfin_id)}
												<span class="btn-spinner"></span>
											{:else}
												<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
													<polyline points="3 6 5 6 21 6"/>
													<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
												</svg>
											{/if}
										</button>
									{/if}
								</td>
							</tr>
							<!-- US-52.4: Expanded episode list -->
							{#if hasExpandableEpisodes(item) && expandedRows.has(item.jellyfin_id)}
								<tr class="episode-row">
									<td colspan={activeFilter === 'requests' ? 7 : 6}>
										<div class="episode-list">
											{#each item.problematic_episodes ?? [] as episode}
												{@const episodeKey = `${item.jellyfin_id}-${episode.season}-${episode.episode}`}
												<div class="episode-item">
													<span class="episode-identifier">{episode.identifier}</span>
													<span class="episode-name" title={episode.name}>{episode.name}</span>
													<div class="episode-badges">
														{#each episode.missing_languages as lang}
															<span class="episode-badge badge-missing-{lang.replace('missing_', '').replace('_', '-')}">
																{formatLanguageBadge(lang)}
															</span>
														{/each}
													</div>
													<button
														class="btn-whitelist-episode"
														onclick={(e) => {
															e.stopPropagation();
															openEpisodeDurationPicker(item, episode);
														}}
														disabled={whitelistingEpisodeIds.has(episodeKey)}
														title="Whitelist this episode"
													>
														{#if whitelistingEpisodeIds.has(episodeKey)}
															<span class="btn-spinner"></span>
														{:else}
															Whitelist
														{/if}
													</button>
												</div>
											{/each}
										</div>
									</td>
								</tr>
							{/if}
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>

<!-- Duration Picker Modal -->
{#if showDurationPicker && selectedItem}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="modal-overlay" onclick={closeDurationPicker} onkeydown={handleKeydown} role="presentation" tabindex="-1">
		<div class="modal" bind:this={durationPickerModal} onclick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="modal-title" tabindex="0">
			<h3 id="modal-title">Set Whitelist Duration</h3>
			<p class="modal-desc">Choose how long <strong>{selectedItem.name}</strong> should be whitelisted.</p>

			<div class="duration-options">
				{#each durationOptions as option}
					<label class="duration-option" class:selected={selectedDuration === option.value}>
						<input
							type="radio"
							name="duration"
							value={option.value}
							checked={selectedDuration === option.value}
							onchange={() => selectedDuration = option.value}
						/>
						<span class="option-label">{option.label}</span>
					</label>
				{/each}
			</div>

			{#if selectedDuration === 'custom'}
				<div class="custom-date-input">
					<label for="custom-date">Expiration Date</label>
					<input
						id="custom-date"
						type="date"
						bind:value={customDate}
						min={new Date().toISOString().split('T')[0]}
					/>
				</div>
			{/if}

			<div class="modal-actions">
				<button class="btn-secondary" onclick={closeDurationPicker}>Cancel</button>
				<button
					class="btn-primary"
					onclick={confirmWhitelist}
					disabled={selectedDuration === 'custom' && !customDate}
				>
					Confirm
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal && deleteItem}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="modal-overlay" onclick={closeDeleteModal} onkeydown={handleKeydown} role="presentation" tabindex="-1">
		<div class="modal delete-modal" bind:this={deleteModalElement} onclick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="delete-modal-title" tabindex="0">
			<h3 id="delete-modal-title">Delete Content</h3>
			<p class="modal-desc">
				Are you sure you want to delete <strong>{deleteItem.name}</strong>?
				This action cannot be undone.
			</p>

			<div class="delete-options">
				<label class="delete-option">
					<input
						type="checkbox"
						bind:checked={deleteFromArr}
						disabled={!canDeleteFromArr(deleteItem)}
					/>
					<span class="option-text">
						Delete from {getArrName(deleteItem)}
						{#if !canDeleteFromArr(deleteItem)}
							<span class="option-hint">(not configured)</span>
						{/if}
					</span>
				</label>

				{#if configStatus.jellyseerr_configured}
					<label class="delete-option">
						<input
							type="checkbox"
							bind:checked={deleteFromJellyseerr}
						/>
						<span class="option-text">Delete from Jellyseerr (if request exists)</span>
					</label>
				{/if}
			</div>

			<div class="delete-warning">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
					<line x1="12" y1="9" x2="12" y2="13"/>
					<line x1="12" y1="17" x2="12.01" y2="17"/>
				</svg>
				<span>Files will be permanently deleted from disk</span>
			</div>

			<div class="modal-actions">
				<button class="btn-secondary" onclick={closeDeleteModal}>Cancel</button>
				<button
					class="btn-danger"
					onclick={confirmDelete}
					disabled={!deleteFromArr && !deleteFromJellyseerr}
				>
					Delete
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- US-52.4: Episode Duration Picker Modal -->
{#if showEpisodeDurationPicker && selectedEpisode}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="modal-overlay" onclick={closeEpisodeDurationPicker} onkeydown={handleKeydown} role="presentation" tabindex="-1">
		<div class="modal" bind:this={episodeDurationPickerModal} onclick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="episode-modal-title" tabindex="0">
			<h3 id="episode-modal-title">Whitelist Episode</h3>
			<p class="modal-desc">
				Choose how long <strong>{selectedEpisode.episode.identifier}</strong> of <strong>{selectedEpisode.item.name}</strong> should be exempt from language checks.
			</p>

			<div class="duration-options">
				{#each durationOptions as option}
					<label class="duration-option" class:selected={episodeDuration === option.value}>
						<input
							type="radio"
							name="episode-duration"
							value={option.value}
							checked={episodeDuration === option.value}
							onchange={() => episodeDuration = option.value}
						/>
						<span class="option-label">{option.label}</span>
					</label>
				{/each}
			</div>

			{#if episodeDuration === 'custom'}
				<div class="custom-date-input">
					<label for="episode-custom-date">Expiration Date</label>
					<input
						id="episode-custom-date"
						type="date"
						bind:value={episodeCustomDate}
						min={new Date().toISOString().split('T')[0]}
					/>
				</div>
			{/if}

			<div class="modal-actions">
				<button class="btn-secondary" onclick={closeEpisodeDurationPicker}>Cancel</button>
				<button
					class="btn-primary"
					onclick={confirmEpisodeWhitelist}
					disabled={episodeDuration === 'custom' && !episodeCustomDate}
				>
					Whitelist
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.issues-page {
		max-width: var(--content-max-width, 1200px);
		margin: 0 auto;
		padding: var(--space-6);
	}

	.page-header {
		margin-bottom: var(--space-6);
	}

	.header-main {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
	}

	.header-stats {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		font-family: var(--font-mono);
	}

	/* Filter nav - underline style */
	.filter-nav {
		display: flex;
		gap: var(--space-1);
		border-bottom: 1px solid var(--border);
		margin-bottom: var(--space-6);
	}

	.filter-tab {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.filter-tab:hover {
		color: var(--text-primary);
	}

	.filter-tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--accent);
	}

	/* Sub-filter nav for Large tab */
	.sub-filter-nav {
		display: flex;
		gap: var(--space-2);
		margin-bottom: var(--space-4);
	}

	.sub-filter-btn {
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.sub-filter-btn:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.sub-filter-btn.active {
		background: var(--accent);
		color: white;
		border-color: var(--accent);
	}

	/* Loading & Error */
	.loading {
		display: flex;
		justify-content: center;
		padding: var(--space-12);
	}

	.spinner {
		width: 24px;
		height: 24px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.error-box {
		padding: var(--space-4);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
	}

	.empty {
		padding: var(--space-8);
		text-align: center;
		color: var(--text-muted);
	}

	/* Table */
	.table-container {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.issues-table {
		width: 100%;
		border-collapse: collapse;
		table-layout: fixed;
	}

	.issues-table th,
	.issues-table td {
		padding: var(--space-3) var(--space-4);
		text-align: left;
	}

	.issues-table th {
		background: var(--bg-secondary);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		color: var(--text-muted);
		border-bottom: 1px solid var(--border);
	}

	.issues-table tr {
		border-bottom: 1px solid var(--border);
	}

	.issues-table tr:last-child {
		border-bottom: none;
	}

	.issues-table tr:hover {
		background: var(--bg-hover);
	}

	.sort-btn {
		background: none;
		border: none;
		font: inherit;
		color: inherit;
		cursor: pointer;
		padding: 0;
	}

	.sort-btn:hover {
		color: var(--text-primary);
	}

	/* ==========================================================================
	   Responsive Table Columns
	   ==========================================================================
	   Base (mobile/small desktop): Compact column widths
	   ≥1440px: Expand Name column, other columns use more space
	   ≥1920px: Maximum expansion for comfortable viewing
	   ========================================================================== */

	/* Base column widths (default) */
	.col-name {
		width: 32%;
		min-width: 180px;
	}

	/* Expand Name column when Issues column is hidden (requests tab) */
	.requests-view .col-name {
		width: 42%;
	}

	/* Large desktop (≥1440px) - columns expand */
	@media (min-width: 1440px) {
		.col-name {
			width: 38%;
			min-width: 260px;
		}

		.requests-view .col-name {
			width: 48%;
		}
	}

	/* Ultrawide / 4K (≥1920px) - maximum expansion */
	@media (min-width: 1920px) {
		.col-name {
			width: 42%;
			min-width: 340px;
		}

		.requests-view .col-name {
			width: 52%;
		}
	}

	.name-cell {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
		flex: 1;
	}

	.item-name {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 60px;
		flex: 1 1 auto;
	}

	.item-year {
		font-size: var(--font-size-sm);
		font-family: var(--font-mono);
		color: var(--text-muted);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.col-requester {
		width: 10%;
		min-width: 80px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-requester {
			width: 9%;
			min-width: 95px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-requester {
			width: 8%;
			min-width: 110px;
		}
	}

	.missing-seasons {
		font-size: var(--font-size-xs);
		color: var(--warning);
		font-weight: var(--font-weight-medium);
	}

	.text-muted {
		color: var(--text-muted);
	}

	.external-links {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		flex-shrink: 0;
	}

	.external-link {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--text-muted);
		opacity: 0.6;
		transition: all var(--transition-fast);
		text-decoration: none;
	}

	.external-link:hover {
		color: var(--accent);
		opacity: 1;
	}

	.col-issues {
		width: 28%;
		min-width: 140px;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-issues {
			width: 25%;
			min-width: 160px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-issues {
			width: 22%;
			min-width: 180px;
		}
	}

	/* Badge groups - container for inline badges with actions */
	.badge-groups {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.badge-group {
		display: inline-flex;
		align-items: center;
		gap: 0;
	}

	.badge {
		display: inline-flex;
		align-items: center;
		padding: 2px 6px;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		border-radius: var(--radius-sm);
		cursor: default;
	}

	/* Badges in groups get rounded only on the left */
	.badge-group .badge {
		border-radius: var(--radius-sm) 0 0 var(--radius-sm);
	}

	.badge-old {
		background: var(--danger-light);
		color: var(--danger);
	}

	.badge-large {
		background: var(--warning-light);
		color: var(--warning);
		cursor: help;
	}

	.badge-language {
		background: var(--info-light);
		color: var(--info);
	}

	.badge-request {
		background: rgba(139, 92, 246, 0.1);
		color: #8b5cf6;
		cursor: help;
	}

	/* Inline action button attached to badge */
	.badge-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 22px;
		height: 20px;
		padding: 0 4px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-left: none;
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
		font-size: 9px;
		font-weight: var(--font-weight-bold);
	}

	/* First action button gets straight left edge */
	.badge-action:first-of-type {
		border-left: 1px solid var(--border);
	}

	/* Last action button in group gets rounded right edge */
	.badge-action:last-child {
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
	}

	.badge-action:hover:not(:disabled) {
		color: var(--text-primary);
		background: var(--bg-hover);
		border-color: var(--text-muted);
	}

	.badge-action:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.badge-spin {
		width: 10px;
		height: 10px;
		border: 1.5px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.col-size {
		width: 10%;
		min-width: 80px;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-size {
			width: 9%;
			min-width: 90px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-size {
			width: 8%;
			min-width: 100px;
		}
	}

	/* Size display for series with largest season */
	.size-with-label {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 1px;
		line-height: 1.2;
	}

	.size-label {
		font-size: var(--font-size-xs);
		font-family: var(--font-sans);
		color: var(--text-muted);
	}

	.size-value {
		font-family: var(--font-mono);
	}

	.col-added {
		width: 10%;
		min-width: 80px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-added {
			width: 9%;
			min-width: 95px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-added {
			width: 8%;
			min-width: 110px;
		}
	}

	.col-release {
		width: 10%;
		min-width: 80px;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-release {
			width: 9%;
			min-width: 95px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-release {
			width: 8%;
			min-width: 110px;
		}
	}

	.col-release.future {
		color: var(--warning);
		font-weight: var(--font-weight-medium);
	}

	.col-watched {
		width: 10%;
		min-width: 70px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-watched {
			width: 9%;
			min-width: 80px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-watched {
			width: 8%;
			min-width: 90px;
		}
	}

	.col-watched.never {
		color: var(--warning);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* ==========================================================================
	   Mobile Responsive Styles
	   ========================================================================== */

	/* Tablet and below (≤768px) */
	@media (max-width: 768px) {
		.issues-page {
			padding: var(--space-4);
		}

		/* Hide low-priority columns */
		.col-watched,
		.col-added,
		.col-size {
			display: none;
		}

		/* Hide table header on mobile - use card layout */
		.issues-table thead {
			display: none;
		}

		/* Convert table to block layout */
		.issues-table,
		.issues-table tbody,
		.issues-table tr {
			display: block;
		}

		/* Each row becomes a card */
		.issues-table tr {
			padding: var(--space-3);
			border-bottom: 1px solid var(--border);
			display: grid;
			grid-template-columns: 1fr auto;
			grid-template-rows: auto auto;
			gap: var(--space-2);
			align-items: start;
		}

		/* Name cell spans left column */
		.issues-table td.col-name {
			grid-column: 1;
			grid-row: 1;
			width: 100%;
			padding: 0;
		}

		/* Issues cell below name */
		.issues-table td.col-issues {
			grid-column: 1;
			grid-row: 2;
			width: 100%;
			padding: 0;
		}

		/* Actions stay on right, vertically centered */
		.issues-table td.col-actions {
			grid-column: 2;
			grid-row: 1 / 3;
			display: flex;
			align-items: center;
			padding: 0;
			padding-left: var(--space-3);
		}

		/* Name cell internal layout - stack vertically */
		.name-cell {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-2);
		}

		/* Title row: wrap naturally */
		.title-row {
			flex-wrap: wrap;
			gap: var(--space-1) var(--space-2);
			width: 100%;
			align-items: baseline;
		}

		/* Let name wrap to multiple lines */
		.item-name {
			white-space: normal;
			word-break: break-word;
			flex: 1 1 auto;
			min-width: 0;
			max-width: none;
			line-height: 1.3;
		}

		/* Year inline with name */
		.item-year {
			flex-shrink: 0;
		}

		/* Hide episode count on mobile - chevron is enough indicator */
		.episode-count {
			display: none;
		}

		/* Hide external links on mobile */
		.external-links {
			display: none;
		}

		/* Badges row - horizontal wrap */
		.badge-groups {
			flex-direction: row;
			flex-wrap: wrap;
			gap: var(--space-2);
		}

		/* Hide requester column on mobile */
		.col-requester {
			display: none;
		}

		/* Hide release column on mobile */
		.col-release {
			display: none;
		}

		/* Episode expansion row on mobile */
		.issues-table tr.episode-row {
			display: block;
			padding: 0;
			grid-template-columns: none;
		}

		.issues-table tr.episode-row td {
			display: block;
			width: 100%;
		}

		.episode-list {
			padding: var(--space-3);
			padding-left: var(--space-4);
		}
	}

	/* Phone (≤480px) */
	@media (max-width: 480px) {
		.issues-page {
			padding: var(--space-3);
		}

		.issues-table tr {
			padding: var(--space-3);
		}

		/* Readable text size */
		.item-name {
			font-size: var(--font-size-sm);
		}

		.item-year {
			font-size: var(--font-size-xs);
		}

		.episode-count {
			font-size: 11px;
			padding: 1px 6px;
		}

		/* Slightly smaller badges but still readable */
		.badge {
			padding: 2px 5px;
			font-size: 10px;
		}

		.badge-action {
			min-width: 18px;
			height: 18px;
			font-size: 8px;
		}
	}

	/* Small phone (≤380px) - ultra compact */
	@media (max-width: 380px) {
		.filter-nav {
			gap: 0;
		}

		.filter-tab {
			padding: var(--space-2) var(--space-2);
			font-size: var(--font-size-xs);
		}
	}

	@media (max-width: 640px) {
		.filter-nav {
			overflow-x: auto;
			-webkit-overflow-scrolling: touch;
		}
	}

	/* Modal Styles */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		animation: fade-in 0.15s ease-out;
	}

	.modal {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
		width: 100%;
		max-width: 380px;
		margin: var(--space-4);
		animation: slide-up 0.2s ease-out;
	}

	.modal h3 {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		margin: 0 0 var(--space-2) 0;
	}

	.modal-desc {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin: 0 0 var(--space-5) 0;
	}

	.modal-desc strong {
		color: var(--text-primary);
	}

	.duration-options {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin-bottom: var(--space-4);
	}

	.duration-option {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.duration-option:hover {
		background: var(--bg-hover);
	}

	.duration-option.selected {
		border-color: var(--accent);
		background: var(--accent-light);
	}

	.duration-option input {
		margin: 0;
		accent-color: var(--accent);
	}

	.option-label {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
	}

	.custom-date-input {
		margin-bottom: var(--space-4);
	}

	.custom-date-input label {
		display: block;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		margin-bottom: var(--space-2);
		color: var(--text-secondary);
	}

	.custom-date-input input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-secondary);
		color: var(--text-primary);
		font-size: var(--font-size-sm);
	}

	.custom-date-input input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}

	.btn-primary {
		padding: var(--space-2) var(--space-4);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-secondary {
		padding: var(--space-2) var(--space-4);
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-secondary:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes slide-up {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* Action Buttons */
	.col-actions {
		width: 48px;
		text-align: center;
	}

	/* Wider actions column for requests tab (two buttons) */
	.requests-view .col-actions {
		width: 72px;
	}

	.action-buttons {
		display: inline-flex;
		gap: var(--space-1);
	}

	.btn-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		padding: 0;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-action:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-whitelist:hover:not(:disabled) {
		color: var(--accent);
		border-color: var(--accent);
		background: var(--accent-light);
	}

	.btn-delete {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		padding: 0;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-delete:hover:not(:disabled) {
		color: var(--danger);
		border-color: var(--danger);
		background: var(--danger-light);
	}

	.btn-delete:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-spinner {
		width: 12px;
		height: 12px;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Delete Modal */
	.delete-modal {
		max-width: 420px;
	}

	.delete-options {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin-bottom: var(--space-4);
	}

	.delete-option {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.delete-option:hover {
		background: var(--bg-hover);
	}

	.delete-option input {
		margin: 0;
		accent-color: var(--accent);
	}

	.delete-option input:disabled {
		opacity: 0.5;
	}

	.option-text {
		font-size: var(--font-size-sm);
	}

	.option-hint {
		color: var(--text-muted);
		font-size: var(--font-size-xs);
	}

	.delete-warning {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-4);
	}

	.btn-danger {
		padding: var(--space-2) var(--space-4);
		background: var(--danger);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-danger:hover:not(:disabled) {
		background: #b91c1c;
	}

	.btn-danger:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* US-52.4: Expandable rows for series with problematic episodes */
	tr.expandable {
		cursor: pointer;
	}

	tr.expandable:hover {
		background: var(--bg-hover);
	}

	tr.expanded {
		background: var(--bg-secondary);
	}

	.expand-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		margin-right: var(--space-1);
		color: var(--text-muted);
		flex-shrink: 0;
	}

	.episode-count {
		font-size: var(--font-size-xs);
		color: var(--info);
		font-weight: var(--font-weight-medium);
		padding: 1px 6px;
		background: var(--info-light);
		border-radius: var(--radius-sm);
		white-space: nowrap;
	}

	/* US-52.4: Episode list styles */
	tr.episode-row {
		background: var(--bg-secondary);
	}

	tr.episode-row:hover {
		background: var(--bg-secondary);
	}

	tr.episode-row td {
		padding: 0;
	}

	.episode-list {
		padding: var(--space-3) var(--space-4);
		padding-left: calc(var(--space-4) + 24px);
		border-top: 1px solid var(--border);
	}

	.episode-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) var(--space-3);
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		margin-bottom: var(--space-2);
	}

	.episode-item:last-child {
		margin-bottom: 0;
	}

	.episode-identifier {
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		min-width: 60px;
	}

	.episode-name {
		flex: 1;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.episode-badges {
		display: flex;
		gap: var(--space-1);
		flex-shrink: 0;
	}

	.episode-badge {
		display: inline-flex;
		align-items: center;
		padding: 1px 6px;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		border-radius: var(--radius-sm);
	}

	.badge-missing-en-audio {
		background: var(--danger-light);
		color: var(--danger);
	}

	.badge-missing-fr-audio {
		background: var(--warning-light);
		color: var(--warning);
	}

	.badge-missing-fr-subs {
		background: var(--info-light);
		color: var(--info);
	}

	.btn-whitelist-episode {
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
		flex-shrink: 0;
		min-width: 75px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.btn-whitelist-episode:hover:not(:disabled) {
		color: var(--accent);
		border-color: var(--accent);
		background: var(--accent-light);
	}

	.btn-whitelist-episode:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Responsive: hide episode list details on mobile */
	@media (max-width: 768px) {
		.episode-list {
			padding-left: var(--space-4);
		}

		.episode-name {
			max-width: 100px;
		}
	}

	@media (max-width: 640px) {
		.episode-badges {
			display: none;
		}
	}
</style>
