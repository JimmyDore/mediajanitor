<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { authenticatedFetch } from '$lib/stores';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import ServiceBadge from '$lib/components/ServiceBadge.svelte';

	interface LibraryItem {
		jellyfin_id: string;
		name: string;
		media_type: string;
		production_year: number | null;
		size_bytes: number | null;
		size_formatted: string;
		played: boolean;
		last_played_date: string | null;
		date_created: string | null;
		tmdb_id: string | null;
		sonarr_title_slug: string | null;
	}

	interface ServiceUrls {
		jellyfin_url: string | null;
		jellyseerr_url: string | null;
		radarr_url: string | null;
		sonarr_url: string | null;
	}

	interface LibraryResponse {
		items: LibraryItem[];
		total_count: number;
		total_size_bytes: number;
		total_size_formatted: string;
		service_urls: ServiceUrls | null;
	}

	type MediaTypeFilter = 'all' | 'movie' | 'series';
	type WatchedFilter = 'all' | 'true' | 'false';
	type SortField = 'name' | 'year' | 'size' | 'date_added' | 'last_watched';
	type SortOrder = 'asc' | 'desc';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let data = $state<LibraryResponse | null>(null);

	// Filter state
	let activeFilter = $state<MediaTypeFilter>('all');
	let searchQuery = $state('');
	let watchedFilter = $state<WatchedFilter>('all');
	let minYear = $state<number | null>(null);
	let maxYear = $state<number | null>(null);
	let minSizeGb = $state<number | null>(null);
	let maxSizeGb = $state<number | null>(null);
	let sortField = $state<SortField>('name');
	let sortOrder = $state<SortOrder>('asc');

	// Debounce timer
	let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	const filterLabels: Record<MediaTypeFilter, string> = {
		all: 'All',
		movie: 'Movies',
		series: 'Series'
	};

	const watchedLabels: Record<WatchedFilter, string> = {
		all: 'All',
		true: 'Watched',
		false: 'Unwatched'
	};

	const sortLabels: Record<SortField, string> = {
		name: 'Name',
		year: 'Year',
		size: 'Size',
		date_added: 'Date Added',
		last_watched: 'Last Watched'
	};

	// Check if any filters are active
	let hasActiveFilters = $derived(
		searchQuery.trim() !== '' ||
			watchedFilter !== 'all' ||
			minYear !== null ||
			maxYear !== null ||
			minSizeGb !== null ||
			maxSizeGb !== null ||
			sortField !== 'name' ||
			sortOrder !== 'asc'
	);

	function formatLastWatched(lastPlayed: string | null, played: boolean): string {
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
		if (played) return 'Watched';
		return 'Never';
	}

	function formatDateCreated(dateCreated: string | null): string {
		if (!dateCreated) return 'Unknown';
		try {
			const date = new Date(dateCreated);
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
		} catch {
			return '?';
		}
	}

	function getTmdbUrl(item: LibraryItem): string | null {
		if (!item.tmdb_id) return null;
		const mediaType = item.media_type.toLowerCase() === 'movie' ? 'movie' : 'tv';
		return `https://www.themoviedb.org/${mediaType}/${item.tmdb_id}`;
	}

	function getJellyfinUrl(item: LibraryItem): string | null {
		const baseUrl = data?.service_urls?.jellyfin_url;
		if (!baseUrl || !item.jellyfin_id) return null;
		return `${baseUrl.replace(/\/$/, '')}/web/index.html#!/details?id=${item.jellyfin_id}`;
	}

	function getJellyseerrUrl(item: LibraryItem): string | null {
		const baseUrl = data?.service_urls?.jellyseerr_url;
		if (!baseUrl || !item.tmdb_id) return null;
		// Jellyseerr URL pattern: /movie/{tmdb_id} or /tv/{tmdb_id}
		const mediaType = item.media_type.toLowerCase() === 'movie' ? 'movie' : 'tv';
		return `${baseUrl.replace(/\/$/, '')}/${mediaType}/${item.tmdb_id}`;
	}

	function getRadarrUrl(item: LibraryItem): string | null {
		// Only show for movies
		if (item.media_type.toLowerCase() !== 'movie') return null;
		const baseUrl = data?.service_urls?.radarr_url;
		if (!baseUrl || !item.tmdb_id) return null;
		// Radarr URL pattern for movie details (using TMDB ID): /movie/{tmdb_id}
		return `${baseUrl.replace(/\/$/, '')}/movie/${item.tmdb_id}`;
	}

	function getSonarrUrl(item: LibraryItem): string | null {
		// Only show for series
		if (item.media_type.toLowerCase() !== 'series') return null;
		const baseUrl = data?.service_urls?.sonarr_url;
		if (!baseUrl || !item.sonarr_title_slug) return null;
		// Sonarr URL pattern for series (using titleSlug): /series/{titleSlug}
		return `${baseUrl.replace(/\/$/, '')}/series/${item.sonarr_title_slug}`;
	}

	async function fetchLibrary() {
		loading = true;
		error = null;
		try {
			const params = new URLSearchParams();
			if (activeFilter !== 'all') {
				params.set('type', activeFilter);
			}
			if (searchQuery.trim()) {
				params.set('search', searchQuery.trim());
			}
			if (watchedFilter !== 'all') {
				params.set('watched', watchedFilter);
			}
			if (minYear !== null) {
				params.set('min_year', minYear.toString());
			}
			if (maxYear !== null) {
				params.set('max_year', maxYear.toString());
			}
			if (minSizeGb !== null) {
				params.set('min_size_gb', minSizeGb.toString());
			}
			if (maxSizeGb !== null) {
				params.set('max_size_gb', maxSizeGb.toString());
			}
			params.set('sort', sortField);
			params.set('order', sortOrder);

			const queryString = params.toString();
			const url = queryString ? `/api/library?${queryString}` : '/api/library';
			const response = await authenticatedFetch(url);

			if (response.status === 401) {
				error = 'Session expired';
				return;
			}
			if (!response.ok) {
				error = 'Failed to fetch library';
				return;
			}

			data = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch library';
		} finally {
			loading = false;
		}
	}

	function setFilter(filter: MediaTypeFilter) {
		activeFilter = filter;
		fetchLibrary();
	}

	function handleSearchInput(event: Event) {
		const target = event.target as HTMLInputElement;
		searchQuery = target.value;

		// Debounce the search
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
		searchDebounceTimer = setTimeout(() => {
			fetchLibrary();
		}, 300);
	}

	function clearSearch() {
		searchQuery = '';
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
		fetchLibrary();
	}

	function handleWatchedChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		watchedFilter = target.value as WatchedFilter;
		fetchLibrary();
	}

	function handleMinYearChange(event: Event) {
		const target = event.target as HTMLInputElement;
		minYear = target.value ? parseInt(target.value, 10) : null;
		fetchLibrary();
	}

	function handleMaxYearChange(event: Event) {
		const target = event.target as HTMLInputElement;
		maxYear = target.value ? parseInt(target.value, 10) : null;
		fetchLibrary();
	}

	function handleMinSizeChange(event: Event) {
		const target = event.target as HTMLInputElement;
		minSizeGb = target.value ? parseFloat(target.value) : null;
		fetchLibrary();
	}

	function handleMaxSizeChange(event: Event) {
		const target = event.target as HTMLInputElement;
		maxSizeGb = target.value ? parseFloat(target.value) : null;
		fetchLibrary();
	}

	function handleSortChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		sortField = target.value as SortField;
		fetchLibrary();
	}

	function toggleSortOrder() {
		sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		fetchLibrary();
	}

	function clearAllFilters() {
		searchQuery = '';
		watchedFilter = 'all';
		minYear = null;
		maxYear = null;
		minSizeGb = null;
		maxSizeGb = null;
		sortField = 'name';
		sortOrder = 'asc';
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
		fetchLibrary();
	}

	function toggleSort(field: SortField) {
		if (sortField === field) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortField = field;
			sortOrder = field === 'name' ? 'asc' : 'desc';
		}
		fetchLibrary();
	}

	onMount(() => {
		fetchLibrary();
	});

	onDestroy(() => {
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
	});
</script>

<svelte:head>
	<title>Library - Media Janitor</title>
</svelte:head>

<div class="library-page" aria-busy={loading}>
	<header class="page-header">
		<div class="header-main">
			<h1>Library</h1>
			{#if data && !loading}
				<span class="header-stats">
					{data.total_count} items · {data.total_size_formatted}
				</span>
			{/if}
		</div>

		<!-- Search Input -->
		<SearchInput
			value={searchQuery}
			placeholder="Search by title, year..."
			aria-label="Search library by title or year"
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
				onclick={() => setFilter(filter as MediaTypeFilter)}
			>
				{label}
			</button>
		{/each}
	</nav>

	<!-- Filters Row -->
	<div class="filters-row">
		<div class="filter-group">
			<label for="watched-filter">Status</label>
			<select id="watched-filter" class="filter-select" value={watchedFilter} onchange={handleWatchedChange}>
				{#each Object.entries(watchedLabels) as [value, label]}
					<option {value}>{label}</option>
				{/each}
			</select>
		</div>

		<div class="filter-group filter-group-range">
			<span class="filter-label">Year</span>
			<div class="range-inputs">
				<input
					type="number"
					class="filter-input"
					placeholder="Min"
					aria-label="Minimum year"
					value={minYear ?? ''}
					onchange={handleMinYearChange}
					min="1900"
					max="2099"
				/>
				<span class="range-separator">–</span>
				<input
					type="number"
					class="filter-input"
					placeholder="Max"
					aria-label="Maximum year"
					value={maxYear ?? ''}
					onchange={handleMaxYearChange}
					min="1900"
					max="2099"
				/>
			</div>
		</div>

		<div class="filter-group filter-group-range">
			<span class="filter-label">Size (GB)</span>
			<div class="range-inputs">
				<input
					type="number"
					class="filter-input"
					placeholder="Min"
					aria-label="Minimum size in GB"
					value={minSizeGb ?? ''}
					onchange={handleMinSizeChange}
					min="0"
					step="0.1"
				/>
				<span class="range-separator">–</span>
				<input
					type="number"
					class="filter-input"
					placeholder="Max"
					aria-label="Maximum size in GB"
					value={maxSizeGb ?? ''}
					onchange={handleMaxSizeChange}
					min="0"
					step="0.1"
				/>
			</div>
		</div>

		<div class="filter-group">
			<label for="sort-field">Sort by</label>
			<div class="sort-controls">
				<select id="sort-field" class="filter-select" value={sortField} onchange={handleSortChange}>
					{#each Object.entries(sortLabels) as [value, label]}
						<option {value}>{label}</option>
					{/each}
				</select>
				<button class="sort-order-btn" onclick={toggleSortOrder} title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}>
					{sortOrder === 'asc' ? '↑' : '↓'}
				</button>
			</div>
		</div>

		{#if hasActiveFilters}
			<button class="clear-filters-btn" onclick={clearAllFilters}>
				Clear filters
			</button>
		{/if}
	</div>

	{#if loading}
		<div class="loading" role="status" aria-label="Loading library">
			<span class="spinner" aria-hidden="true"></span>
		</div>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else if data}
		{#if data.items.length === 0}
			<div class="empty" aria-live="polite">
				<p>Your library is empty.</p>
				<p class="empty-hint">
					<a href="/settings">Configure Jellyfin</a> and run a sync to see your media here.
				</p>
			</div>
		{:else}
			<div class="table-container" aria-live="polite">
				<table class="library-table">
					<thead>
						<tr>
							<th class="col-name">
								<button class="sort-btn" onclick={() => toggleSort('name')}>
									Name {sortField === 'name' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							<th class="col-year">
								<button class="sort-btn" onclick={() => toggleSort('year')}>
									Year {sortField === 'year' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							<th class="col-size">
								<button class="sort-btn" onclick={() => toggleSort('size')}>
									Size {sortField === 'size' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							<th class="col-added">
								<button class="sort-btn" onclick={() => toggleSort('date_added')}>
									Added {sortField === 'date_added' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
							<th class="col-watched">
								<button class="sort-btn" onclick={() => toggleSort('last_watched')}>
									Last Watched {sortField === 'last_watched' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
								</button>
							</th>
						</tr>
					</thead>
					<tbody>
						{#each data.items as item}
							<tr>
								<td class="col-name">
									<div class="name-cell">
										<span class="item-name" title={item.name}>{item.name}</span>
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
								<td class="col-year">
									{item.production_year ?? '—'}
								</td>
								<td class="col-size">
									{item.size_formatted}
								</td>
								<td class="col-added">
									{formatDateCreated(item.date_created)}
								</td>
								<td class="col-watched" class:never={!item.played && !item.last_played_date}>
									{formatLastWatched(item.last_played_date, item.played)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>

<style>
	.library-page {
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

	/* Filters Row */
	.filters-row {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-4);
		align-items: flex-end;
		margin-bottom: var(--space-6);
		padding: var(--space-4);
		background: var(--bg-secondary);
		border-radius: var(--radius-md);
		border: 1px solid var(--border);
	}

	.filter-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.filter-group label,
	.filter-label {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.filter-select {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
		cursor: pointer;
		min-width: 100px;
	}

	.filter-select:focus {
		outline: none;
		border-color: var(--accent);
	}

	.filter-group-range .range-inputs {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.filter-input {
		width: 70px;
		padding: var(--space-2) var(--space-2);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
		text-align: center;
	}

	.filter-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.filter-input::placeholder {
		color: var(--text-muted);
	}

	/* Hide spinner buttons on number inputs */
	.filter-input::-webkit-outer-spin-button,
	.filter-input::-webkit-inner-spin-button {
		-webkit-appearance: none;
		appearance: none;
		margin: 0;
	}
	.filter-input[type=number] {
		-moz-appearance: textfield;
		appearance: textfield;
	}

	.range-separator {
		color: var(--text-muted);
		font-size: var(--font-size-sm);
	}

	.sort-controls {
		display: flex;
		gap: var(--space-1);
	}

	.sort-order-btn {
		padding: var(--space-2);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
		cursor: pointer;
		min-width: 32px;
	}

	.sort-order-btn:hover {
		background: var(--bg-hover);
	}

	.clear-filters-btn {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-muted);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.clear-filters-btn:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
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

	.empty-hint {
		margin-top: var(--space-2);
		font-size: var(--font-size-sm);
	}

	.empty-hint a {
		color: var(--accent);
		text-decoration: none;
	}

	.empty-hint a:hover {
		text-decoration: underline;
	}

	/* Table */
	.table-container {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.library-table {
		width: 100%;
		border-collapse: collapse;
		table-layout: fixed;
	}

	.library-table th,
	.library-table td {
		padding: var(--space-3) var(--space-4);
		text-align: left;
	}

	.library-table th {
		background: var(--bg-secondary);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
		border-bottom: 1px solid var(--border);
	}

	.library-table tr {
		border-bottom: 1px solid var(--border);
	}

	.library-table tr:last-child {
		border-bottom: none;
	}

	.library-table tr:hover {
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
		min-width: 180px;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-name {
			width: 44%;
			min-width: 260px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-name {
			width: 48%;
			min-width: 340px;
		}
	}

	.name-cell {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.item-name {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
		flex: 1;
	}

	.external-links {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		flex-shrink: 0;
	}

	.col-year {
		width: 10%;
		min-width: 60px;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-year {
			width: 9%;
			min-width: 70px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-year {
			width: 8%;
			min-width: 80px;
		}
	}

	.col-size {
		width: 12%;
		min-width: 70px;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-size {
			width: 10%;
			min-width: 85px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-size {
			width: 9%;
			min-width: 100px;
		}
	}

	.col-added {
		width: 15%;
		min-width: 90px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-added {
			width: 13%;
			min-width: 105px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-added {
			width: 12%;
			min-width: 120px;
		}
	}

	.col-watched {
		width: 13%;
		min-width: 75px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	/* Large desktop (≥1440px) */
	@media (min-width: 1440px) {
		.col-watched {
			width: 11%;
			min-width: 85px;
		}
	}

	/* Ultrawide / 4K (≥1920px) */
	@media (min-width: 1920px) {
		.col-watched {
			width: 10%;
			min-width: 95px;
		}
	}

	.col-watched.never {
		color: var(--warning);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Responsive */
	@media (max-width: 768px) {
		.library-page {
			padding: var(--space-4);
		}

		.filters-row {
			gap: var(--space-3);
			padding: var(--space-3);
		}

		.filter-group-range {
			width: 100%;
		}

		.col-added {
			display: none;
		}

		.library-table th,
		.library-table td {
			padding: var(--space-2) var(--space-3);
		}
	}

	@media (max-width: 640px) {
		.filter-nav {
			overflow-x: auto;
		}

		.filters-row {
			flex-direction: column;
			align-items: stretch;
		}

		.filter-group {
			width: 100%;
		}

		.filter-select {
			width: 100%;
		}

		.filter-input {
			flex: 1;
		}

		.col-watched {
			display: none;
		}
	}
</style>
