<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { authenticatedFetch } from '$lib/stores';
	import Toast from '$lib/components/Toast.svelte';
	import IssueFilters from '$lib/components/IssueFilters.svelte';
	import IssueRow from '$lib/components/IssueRow.svelte';
	import DurationPickerModal from '$lib/components/DurationPickerModal.svelte';
	import DeleteConfirmModal from '$lib/components/DeleteConfirmModal.svelte';

	interface ProblematicEpisode {
		identifier: string;
		name: string;
		season: number;
		episode: number;
		missing_languages: string[];
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
		date_created: string | null;
		issues: string[];
		language_issues: string[] | null;
		tmdb_id: string | null;
		imdb_id: string | null;
		sonarr_title_slug: string | null;
		jellyseerr_request_id: number | null;
		largest_season_size_bytes: number | null;
		largest_season_size_formatted: string | null;
		requested_by: string | null;
		request_date: string | null;
		missing_seasons: number[] | null;
		release_date: string | null;
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
	let expandedRows = $state<Set<string>>(new Set());
	let whitelistingEpisodeIds = $state<Set<string>>(new Set());
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
	let durationPickerTrigger = $state<HTMLElement | null>(null);

	// Episode duration picker state
	let showEpisodeDurationPicker = $state(false);
	let selectedEpisode = $state<{ item: ContentIssueItem; episode: ProblematicEpisode } | null>(null);
	let episodeDurationPickerTrigger = $state<HTMLElement | null>(null);

	// Delete confirmation modal state
	let showDeleteModal = $state(false);
	let deleteItem = $state<ContentIssueItem | null>(null);
	let deleteModalTrigger = $state<HTMLElement | null>(null);

	// Search handlers
	function handleSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		searchQuery = target.value;

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
		if (item.name.toLowerCase().includes(lowerQuery)) return true;
		if (item.production_year && item.production_year.toString().includes(lowerQuery)) return true;
		if (item.requested_by && item.requested_by.toLowerCase().includes(lowerQuery)) return true;

		return false;
	}

	function isMovieItem(item: ContentIssueItem): boolean {
		return item.media_type.toLowerCase() === 'movie';
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
		durationPickerTrigger = document.activeElement as HTMLElement | null;
		selectedItem = item;
		selectedWhitelistType = type;
		showDurationPicker = true;
	}

	function closeDurationPicker() {
		showDurationPicker = false;
		selectedItem = null;
		if (durationPickerTrigger) {
			durationPickerTrigger.focus();
			durationPickerTrigger = null;
		}
	}

	function openDeleteModal(item: ContentIssueItem) {
		deleteModalTrigger = document.activeElement as HTMLElement | null;
		deleteItem = item;
		showDeleteModal = true;
	}

	function closeDeleteModal() {
		showDeleteModal = false;
		deleteItem = null;
		if (deleteModalTrigger) {
			deleteModalTrigger.focus();
			deleteModalTrigger = null;
		}
	}

	function openEpisodeDurationPicker(item: ContentIssueItem, episode: ProblematicEpisode) {
		episodeDurationPickerTrigger = document.activeElement as HTMLElement | null;
		selectedEpisode = { item, episode };
		showEpisodeDurationPicker = true;
	}

	function closeEpisodeDurationPicker() {
		showEpisodeDurationPicker = false;
		selectedEpisode = null;
		if (episodeDurationPickerTrigger) {
			episodeDurationPickerTrigger.focus();
			episodeDurationPickerTrigger = null;
		}
	}

	function toggleRowExpansion(jellyfinId: string) {
		const newSet = new Set(expandedRows);
		if (newSet.has(jellyfinId)) {
			newSet.delete(jellyfinId);
		} else {
			newSet.add(jellyfinId);
		}
		expandedRows = newSet;
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

	async function confirmDelete(deleteFromArr: boolean, deleteFromJellyseerr: boolean) {
		if (!deleteItem || !deleteItem.tmdb_id) return;

		const item = deleteItem;
		const isMovie = isMovieType(item.media_type);
		const tmdbId = parseInt(item.tmdb_id as string, 10);

		closeDeleteModal();

		deletingIds = new Set([...deletingIds, item.jellyfin_id]);

		try {
			const endpoint = isMovie ? `/api/content/movie/${tmdbId}` : `/api/content/series/${tmdbId}`;

			let jellyseerrRequestId: number | null = null;
			if (item.jellyseerr_request_id) {
				jellyseerrRequestId = item.jellyseerr_request_id;
			} else if (item.jellyfin_id.startsWith('request-')) {
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

	async function handleDurationPickerConfirm(duration: DurationOption, customDate: string) {
		if (!selectedItem) return;

		const item = selectedItem;
		const type = selectedWhitelistType;
		const expiresAt = getExpirationDate(duration, customDate);

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

	async function handleEpisodeDurationPickerConfirm(duration: DurationOption, customDate: string) {
		if (!selectedEpisode) return;

		const { item, episode } = selectedEpisode;
		const expiresAt = getExpirationDate(duration, customDate);

		closeEpisodeDurationPicker();
		await whitelistEpisode(item, episode, expiresAt);
	}

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

			if (data) {
				data = {
					...data,
					items: data.items.map(i => {
						if (i.jellyfin_id !== item.jellyfin_id) return i;
						const updatedEpisodes = i.problematic_episodes?.filter(
							ep => !(ep.season === episode.season && ep.episode === episode.episode)
						) ?? null;
						const shouldRemoveLanguageIssue = !updatedEpisodes || updatedEpisodes.length === 0;
						const updatedIssues = shouldRemoveLanguageIssue
							? i.issues.filter(issue => issue !== 'language')
							: i.issues;
						return {
							...i,
							problematic_episodes: updatedEpisodes && updatedEpisodes.length > 0 ? updatedEpisodes : null,
							issues: updatedIssues
						};
					}).filter(i => i.issues.length > 0)
				};
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

	$effect(() => {
		const urlFilter = $page.url.searchParams.get('filter');
		if (urlFilter && ['all', 'old', 'large', 'language', 'requests'].includes(urlFilter)) {
			activeFilter = urlFilter as FilterType;
		}
	});

	function showToast(message: string, type: 'success' | 'error') {
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
		largeSubFilter = 'all';
		const url = filter === 'all' ? '/issues' : `/issues?filter=${filter}`;
		goto(url, { replaceState: true });
		fetchIssues(filter);
	}

	function setLargeSubFilter(subFilter: LargeSubFilter) {
		largeSubFilter = subFilter;
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
					const dateA = a.request_date
						? new Date(a.request_date).getTime()
						: (a.last_played_date ? new Date(a.last_played_date).getTime() : 0);
					const dateB = b.request_date
						? new Date(b.request_date).getTime()
						: (b.last_played_date ? new Date(b.last_played_date).getTime() : 0);
					comparison = dateA - dateB;
					break;
				case 'added':
					const addedA = a.date_created ? new Date(a.date_created).getTime() : 0;
					const addedB = b.date_created ? new Date(b.date_created).getTime() : 0;
					comparison = addedA - addedB;
					break;
				case 'issues': comparison = a.issues.length - b.issues.length; break;
				case 'requester':
					const reqA = a.requested_by?.toLowerCase() ?? '';
					const reqB = b.requested_by?.toLowerCase() ?? '';
					if (!reqA && reqB) comparison = 1;
					else if (reqA && !reqB) comparison = -1;
					else comparison = reqA.localeCompare(reqB);
					break;
				case 'release':
					const relA = a.release_date ? new Date(a.release_date).getTime() : 0;
					const relB = b.release_date ? new Date(b.release_date).getTime() : 0;
					if (!relA && relB) comparison = 1;
					else if (relA && !relB) comparison = -1;
					else comparison = relA - relB;
					break;
				case 'watched':
					function getWatchPriority(item: ContentIssueItem): number {
						if (item.last_played_date) return 1;
						if (item.played) return 2;
						return 3;
					}
					const priorityA = getWatchPriority(a);
					const priorityB = getWatchPriority(b);
					if (priorityA !== priorityB) {
						comparison = priorityA - priorityB;
					} else if (priorityA === 1) {
						const watchedDateA = new Date(a.last_played_date!).getTime();
						const watchedDateB = new Date(b.last_played_date!).getTime();
						comparison = watchedDateA - watchedDateB;
					}
					break;
			}
			return sortOrder === 'asc' ? comparison : -comparison;
		});
	}

	onMount(() => {
		fetchIssues(activeFilter);
		fetchConfigStatus();
	});
</script>

<svelte:head>
	<title>Issues - Media Janitor</title>
</svelte:head>

{#if toast}
	<Toast message={toast.message} type={toast.type} onclose={closeToast} />
{/if}

<div class="issues-page" aria-busy={loading}>
	<IssueFilters
		{activeFilter}
		{largeSubFilter}
		{searchQuery}
		totalCount={data?.total_count ?? null}
		totalSizeFormatted={data?.total_size_formatted ?? null}
		filteredCount={data ? getFilteredStats(data.items).count : null}
		filteredSizeFormatted={data ? formatSize(getFilteredStats(data.items).sizeBytes) : null}
		isFiltered={debouncedSearchQuery.trim() !== ''}
		{loading}
		onfilterChange={setFilter}
		onsubFilterChange={setLargeSubFilter}
		onsearchInput={handleSearchInput}
		onsearchClear={clearSearch}
	/>

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
						{#each getSortedItems(getFilteredItems(data.items)) as item (item.jellyfin_id)}
							<IssueRow
								{item}
								{activeFilter}
								serviceUrls={data.service_urls}
								{protectingIds}
								{frenchOnlyIds}
								{languageExemptIds}
								{largeWhitelistIds}
								{hidingRequestIds}
								{deletingIds}
								{whitelistingEpisodeIds}
								expanded={expandedRows.has(item.jellyfin_id)}
								canDeleteFromArr={canDeleteFromArr(item)}
								arrName={getArrName(item)}
								{badgeTooltips}
								onopenDurationPicker={openDurationPicker}
								onopenDeleteModal={openDeleteModal}
								ondeleteRequest={deleteRequest}
								ontoggleExpansion={toggleRowExpansion}
								onopenEpisodeDurationPicker={openEpisodeDurationPicker}
							/>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>

<!-- Duration Picker Modal -->
{#if showDurationPicker && selectedItem}
	<DurationPickerModal
		title="Set Whitelist Duration"
		description="Choose how long"
		itemName={selectedItem.name}
		confirmLabel="Confirm"
		onconfirm={handleDurationPickerConfirm}
		onclose={closeDurationPicker}
	/>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal && deleteItem}
	<DeleteConfirmModal
		itemName={deleteItem.name}
		arrName={getArrName(deleteItem)}
		canDeleteFromArr={canDeleteFromArr(deleteItem)}
		showJellyseerrOption={configStatus.jellyseerr_configured}
		onconfirm={confirmDelete}
		onclose={closeDeleteModal}
	/>
{/if}

<!-- Episode Duration Picker Modal -->
{#if showEpisodeDurationPicker && selectedEpisode}
	<DurationPickerModal
		title="Whitelist Episode"
		description="Choose how long {selectedEpisode.episode.identifier} of"
		itemName={selectedEpisode.item.name}
		confirmLabel="Whitelist"
		onconfirm={handleEpisodeDurationPickerConfirm}
		onclose={closeEpisodeDurationPicker}
	/>
{/if}

<style>
	.issues-page {
		max-width: var(--content-max-width, 1200px);
		margin: 0 auto;
		padding: var(--space-6);
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

	.issues-table :global(tr) {
		border-bottom: 1px solid var(--border);
	}

	.issues-table :global(tr:last-child) {
		border-bottom: none;
	}

	.issues-table :global(tr:hover) {
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

	/* Column widths - base */
	.col-name {
		width: 32%;
		min-width: 180px;
	}

	.requests-view .col-name {
		width: 42%;
	}

	.col-requester {
		width: 10%;
		min-width: 80px;
	}

	.col-issues {
		width: 28%;
		min-width: 140px;
	}

	.col-size {
		width: 10%;
		min-width: 80px;
		text-align: right;
	}

	.col-added {
		width: 10%;
		min-width: 80px;
		text-align: right;
	}

	.col-release {
		width: 10%;
		min-width: 80px;
		text-align: right;
	}

	.col-watched {
		width: 10%;
		min-width: 70px;
		text-align: right;
	}

	.col-actions {
		width: 48px;
		text-align: center;
	}

	.requests-view .col-actions {
		width: 72px;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-name {
			width: 38%;
			min-width: 260px;
		}

		.requests-view .col-name {
			width: 48%;
		}

		.col-requester {
			width: 9%;
			min-width: 95px;
		}

		.col-issues {
			width: 25%;
			min-width: 160px;
		}

		.col-size {
			width: 9%;
			min-width: 90px;
		}

		.col-added {
			width: 9%;
			min-width: 95px;
		}

		.col-release {
			width: 9%;
			min-width: 95px;
		}

		.col-watched {
			width: 9%;
			min-width: 80px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-name {
			width: 42%;
			min-width: 340px;
		}

		.requests-view .col-name {
			width: 52%;
		}

		.col-requester {
			width: 8%;
			min-width: 110px;
		}

		.col-issues {
			width: 22%;
			min-width: 180px;
		}

		.col-size {
			width: 8%;
			min-width: 100px;
		}

		.col-added {
			width: 8%;
			min-width: 110px;
		}

		.col-release {
			width: 8%;
			min-width: 110px;
		}

		.col-watched {
			width: 8%;
			min-width: 90px;
		}
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Mobile/Tablet Responsive Styles */
	@media (max-width: 1352px) {
		.issues-page {
			padding: var(--space-4);
		}

		/* Hide low-priority columns */
		.col-watched,
		.col-added,
		.col-size,
		.col-requester,
		.col-release {
			display: none;
		}

		/* Hide table header on mobile - use card layout */
		.issues-table thead {
			display: none;
		}

		/* Convert table to block layout */
		.issues-table,
		.issues-table tbody,
		.issues-table :global(tr) {
			display: block;
		}

		/* Each row becomes a card */
		.issues-table :global(tr) {
			padding: var(--space-3);
			border-bottom: 1px solid var(--border);
			display: grid;
			grid-template-columns: 1fr auto;
			grid-template-rows: auto auto;
			gap: var(--space-2);
			align-items: start;
		}

		/* Name cell spans left column */
		.issues-table :global(td.col-name) {
			grid-column: 1;
			grid-row: 1;
			width: 100%;
			padding: 0;
		}

		/* Issues cell below name */
		.issues-table :global(td.col-issues) {
			grid-column: 1;
			grid-row: 2;
			width: 100%;
			padding: 0;
		}

		/* Actions stay on right, vertically centered */
		.issues-table :global(td.col-actions) {
			grid-column: 2;
			grid-row: 1 / 3;
			display: flex;
			align-items: center;
			padding: 0;
			padding-left: var(--space-3);
		}

		/* Episode expansion row on mobile */
		.issues-table :global(tr.episode-row) {
			display: block;
			padding: 0;
			grid-template-columns: none;
		}

		.issues-table :global(tr.episode-row td) {
			display: block;
			width: 100%;
		}
	}

	/* Phone (≤480px) */
	@media (max-width: 480px) {
		.issues-page {
			padding: var(--space-3);
		}

		.issues-table :global(tr) {
			padding: var(--space-3);
		}
	}
</style>
