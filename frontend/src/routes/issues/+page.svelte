<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	interface ContentIssueItem {
		jellyfin_id: string;
		name: string;
		media_type: string;
		production_year: number | null;
		size_bytes: number | null;
		size_formatted: string;
		last_played_date: string | null;
		path: string | null;
		issues: string[];
		language_issues: string[] | null;
		tmdb_id: string | null;
		imdb_id: string | null;
		// Request-specific fields
		requested_by: string | null;
		request_date: string | null;
		missing_seasons: number[] | null;
		release_date: string | null;  // Movie releaseDate or TV firstAirDate (YYYY-MM-DD)
	}

	interface ContentIssuesResponse {
		items: ContentIssueItem[];
		total_count: number;
		total_size_bytes: number;
		total_size_formatted: string;
	}

	type FilterType = 'all' | 'old' | 'large' | 'language' | 'requests' | 'multi';
	type SortField = 'name' | 'size' | 'date' | 'issues';
	type SortOrder = 'asc' | 'desc';
	type DurationOption = 'permanent' | '3months' | '6months' | '1year' | 'custom';
	type WhitelistType = 'content' | 'french-only' | 'language-exempt' | 'request';

	// Tooltip text for informational badges
	const badgeTooltips: Record<string, string> = {
		large: 'Re-download in lower quality from Radarr/Sonarr',
		request: 'Check status in Jellyseerr'
	};

	let loading = $state(true);
	let error = $state<string | null>(null);
	let data = $state<ContentIssuesResponse | null>(null);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let protectingIds = $state<Set<string>>(new Set());
	let frenchOnlyIds = $state<Set<string>>(new Set());
	let languageExemptIds = $state<Set<string>>(new Set());
	let hidingRequestIds = $state<Set<string>>(new Set());
	let activeFilter = $state<FilterType>('all');
	let sortField = $state<SortField>('size');
	let sortOrder = $state<SortOrder>('desc');

	// Duration picker state
	let showDurationPicker = $state(false);
	let selectedItem = $state<ContentIssueItem | null>(null);
	let selectedWhitelistType = $state<WhitelistType>('content');
	let selectedDuration = $state<DurationOption>('permanent');
	let customDate = $state('');

	const durationOptions: { value: DurationOption; label: string }[] = [
		{ value: 'permanent', label: 'Permanent' },
		{ value: '3months', label: '3 Months' },
		{ value: '6months', label: '6 Months' },
		{ value: '1year', label: '1 Year' },
		{ value: 'custom', label: 'Custom Date' }
	];

	function getExpirationDate(duration: DurationOption, customDateValue: string): string | null {
		if (duration === 'permanent') return null;
		if (duration === 'custom') {
			return customDateValue ? new Date(customDateValue + 'T00:00:00').toISOString() : null;
		}

		const now = new Date();
		switch (duration) {
			case '3months':
				now.setMonth(now.getMonth() + 3);
				break;
			case '6months':
				now.setMonth(now.getMonth() + 6);
				break;
			case '1year':
				now.setFullYear(now.getFullYear() + 1);
				break;
		}
		return now.toISOString();
	}

	function openDurationPicker(item: ContentIssueItem, type: WhitelistType) {
		selectedItem = item;
		selectedWhitelistType = type;
		selectedDuration = 'permanent';
		customDate = '';
		showDurationPicker = true;
	}

	function closeDurationPicker() {
		showDurationPicker = false;
		selectedItem = null;
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
		} else if (type === 'request') {
			await hideRequestWithExpiration(item, expiresAt);
		}
	}

	$effect(() => {
		const urlFilter = $page.url.searchParams.get('filter');
		if (urlFilter && ['all', 'old', 'large', 'language', 'requests', 'multi'].includes(urlFilter)) {
			activeFilter = urlFilter as FilterType;
		}
	});

	const filterLabels: Record<FilterType, string> = {
		all: 'All',
		old: 'Old',
		large: 'Large',
		language: 'Language',
		requests: 'Requests',
		multi: 'Multi-Issue'
	};

	function isRequestItem(item: ContentIssueItem): boolean {
		return item.issues.includes('request');
	}

	function formatLastWatched(lastPlayed: string | null): string {
		if (!lastPlayed) return 'Never';
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
		toast = { message, type };
		setTimeout(() => toast = null, 3000);
	}

	async function protectContentWithExpiration(item: ContentIssueItem, expiresAt: string | null) {
		const token = localStorage.getItem('access_token');
		if (!token) { showToast('Not authenticated', 'error'); return; }

		protectingIds = new Set([...protectingIds, item.jellyfin_id]);

		try {
			const response = await fetch('/api/whitelist/content', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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
		const token = localStorage.getItem('access_token');
		if (!token) { showToast('Not authenticated', 'error'); return; }

		frenchOnlyIds = new Set([...frenchOnlyIds, item.jellyfin_id]);

		try {
			const response = await fetch('/api/whitelist/french-only', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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
		const token = localStorage.getItem('access_token');
		if (!token) { showToast('Not authenticated', 'error'); return; }

		languageExemptIds = new Set([...languageExemptIds, item.jellyfin_id]);

		try {
			const response = await fetch('/api/whitelist/language-exempt', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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

	async function hideRequestWithExpiration(item: ContentIssueItem, expiresAt: string | null) {
		const token = localStorage.getItem('access_token');
		if (!token) { showToast('Not authenticated', 'error'); return; }

		hidingRequestIds = new Set([...hidingRequestIds, item.jellyfin_id]);

		// Extract numeric jellyseerr_id from "request-{id}" format
		const jellyseerrIdMatch = item.jellyfin_id.match(/^request-(\d+)$/);
		const jellyseerrId = jellyseerrIdMatch ? parseInt(jellyseerrIdMatch[1], 10) : parseInt(item.jellyfin_id, 10);

		try {
			const response = await fetch('/api/whitelist/requests', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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

	function getImdbUrl(item: ContentIssueItem): string | null {
		if (!item.imdb_id) return null;
		return `https://www.imdb.com/title/${item.imdb_id}`;
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
			const token = localStorage.getItem('access_token');
			if (!token) { error = 'Not authenticated'; return; }

			const filterParam = filter === 'all' ? '' : `?filter=${filter}`;
			const response = await fetch(`/api/content/issues${filterParam}`, {
				headers: { Authorization: `Bearer ${token}` }
			});

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
				case 'issues': comparison = a.issues.length - b.issues.length; break;
			}
			return sortOrder === 'asc' ? comparison : -comparison;
		});
	}

	onMount(() => fetchIssues(activeFilter));
</script>

<svelte:head>
	<title>Issues - Media Janitor</title>
</svelte:head>

{#if toast}
	<div class="toast toast-{toast.type}" role="alert">{toast.message}</div>
{/if}

<div class="issues-page">
	<header class="page-header">
		<div class="header-main">
			<h1>Issues</h1>
			{#if data && !loading}
				<span class="header-stats">
					{data.total_count} items · {data.total_size_formatted}
				</span>
			{/if}
		</div>
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

	{#if loading}
		<div class="loading">
			<span class="spinner"></span>
		</div>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else if data}
		{#if data.items.length === 0}
			<div class="empty">No issues found</div>
		{:else}
			<div class="table-container">
				<table class="issues-table">
					<thead>
						<tr>
							<th class="col-name">
								<button class="sort-btn" onclick={() => toggleSort('name')}>
									Name {sortField === 'name' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							<th class="col-issues">
								<button class="sort-btn" onclick={() => toggleSort('issues')}>
									Issues {sortField === 'issues' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							<th class="col-size">
								<button class="sort-btn" onclick={() => toggleSort('size')}>
									Size {sortField === 'size' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							{#if activeFilter === 'requests'}
								<th class="col-release">Release</th>
							{/if}
							<th class="col-watched">
								<button class="sort-btn" onclick={() => toggleSort('date')}>
									{activeFilter === 'requests' ? 'Requested' : 'Watched'} {sortField === 'date' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
						</tr>
					</thead>
					<tbody>
						{#each getSortedItems(data.items) as item}
							<tr>
								<td class="col-name">
									<div class="name-cell">
										<span class="item-name">{item.name}</span>
										{#if item.production_year}
											<span class="item-year">{item.production_year}</span>
										{/if}
										{#if isRequestItem(item) && item.missing_seasons && item.missing_seasons.length > 0}
											<span class="missing-seasons" title="Missing seasons">
												S{item.missing_seasons.join(', S')}
											</span>
										{/if}
										<span class="external-links">
											{#if getTmdbUrl(item)}
												<a href={getTmdbUrl(item)} target="_blank" rel="noopener noreferrer" class="external-link" title="View on TMDB">
													<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
														<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
														<polyline points="15 3 21 3 21 9"/>
														<line x1="10" y1="14" x2="21" y2="3"/>
													</svg>
												</a>
											{/if}
											{#if getImdbUrl(item)}
												<a href={getImdbUrl(item)} target="_blank" rel="noopener noreferrer" class="external-link" title="View on IMDB">
													<span class="imdb-badge">IMDb</span>
												</a>
											{/if}
										</span>
										{#if isRequestItem(item) && item.requested_by}
											<span class="requested-by">by {item.requested_by}</span>
										{/if}
									</div>
								</td>
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
												<!-- LARGE badge with info tooltip (no action) -->
												<span class="badge badge-large" title={badgeTooltips.large}>large</span>
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
								<td class="col-size">
									{#if isRequestItem(item)}
										<span class="text-muted">—</span>
									{:else}
										{item.size_formatted}
									{/if}
								</td>
								{#if activeFilter === 'requests'}
									<td class="col-release" class:future={isFutureRelease(item.release_date)}>
										{formatReleaseDate(item.release_date)}
									</td>
								{/if}
								<td class="col-watched" class:never={!isRequestItem(item) && !item.last_played_date}>
									{#if isRequestItem(item)}
										{formatRequestDate(item.request_date)}
									{:else}
										{formatLastWatched(item.last_played_date)}
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>

<!-- Duration Picker Modal -->
{#if showDurationPicker && selectedItem}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="modal-overlay" onclick={closeDurationPicker} role="presentation">
		<!-- svelte-ignore a11y_interactive_supports_focus -->
		<div class="modal" onclick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="modal-title">
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

<style>
	.issues-page {
		max-width: 1000px;
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
		text-transform: uppercase;
		letter-spacing: 0.05em;
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

	/* Columns */
	.col-name {
		width: 40%;
	}

	.name-cell {
		display: flex;
		align-items: baseline;
		gap: var(--space-2);
	}

	.item-name {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.item-year {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.missing-seasons {
		font-size: var(--font-size-xs);
		color: var(--warning);
		font-weight: var(--font-weight-medium);
	}

	.requested-by {
		font-size: var(--font-size-xs);
		color: var(--text-muted);
		font-style: italic;
	}

	.text-muted {
		color: var(--text-muted);
	}

	.external-links {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		margin-left: var(--space-1);
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

	.imdb-badge {
		font-size: 9px;
		font-weight: var(--font-weight-bold);
		background: #f5c518;
		color: #000;
		padding: 1px 3px;
		border-radius: 2px;
		letter-spacing: -0.02em;
	}

	.col-issues {
		width: 30%;
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
		width: 12%;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-release {
		width: 12%;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-release.future {
		color: var(--warning);
		font-weight: var(--font-weight-medium);
	}

	.col-watched {
		width: 13%;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-watched.never {
		color: var(--warning);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Responsive */
	@media (max-width: 768px) {
		.issues-page {
			padding: var(--space-4);
		}

		.col-watched {
			display: none;
		}

		.issues-table th,
		.issues-table td {
			padding: var(--space-2) var(--space-3);
		}
	}

	@media (max-width: 640px) {
		.filter-nav {
			overflow-x: auto;
		}

		.col-size {
			display: none;
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
</style>
