<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authenticatedFetch } from '$lib/stores';

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
	type SortField = 'name' | 'year' | 'size' | 'added' | 'last_watched';
	type SortOrder = 'asc' | 'desc';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let data = $state<LibraryResponse | null>(null);

	let activeFilter = $state<MediaTypeFilter>('all');
	let sortField = $state<SortField>('name');
	let sortOrder = $state<SortOrder>('asc');

	const filterLabels: Record<MediaTypeFilter, string> = {
		all: 'All',
		movie: 'Movies',
		series: 'Series'
	};

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

	async function fetchLibrary(filter: MediaTypeFilter) {
		loading = true;
		error = null;
		try {
			const params = new URLSearchParams();
			if (filter !== 'all') {
				params.set('type', filter);
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
		fetchLibrary(filter);
	}

	function toggleSort(field: SortField) {
		if (sortField === field) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortField = field;
			sortOrder = field === 'name' ? 'asc' : 'desc';
		}
		fetchLibrary(activeFilter);
	}

	onMount(() => {
		fetchLibrary(activeFilter);
	});
</script>

<svelte:head>
	<title>Library - Media Janitor</title>
</svelte:head>

<div class="library-page">
	<header class="page-header">
		<div class="header-main">
			<h1>Library</h1>
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
				onclick={() => setFilter(filter as MediaTypeFilter)}
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
			<div class="empty">
				<p>Your library is empty.</p>
				<p class="empty-hint">
					<a href="/settings">Configure Jellyfin</a> and run a sync to see your media here.
				</p>
			</div>
		{:else}
			<div class="table-container">
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
								<button class="sort-btn" onclick={() => toggleSort('added')}>
									Added {sortField === 'added' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
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
												<a href={getJellyfinUrl(item)} target="_blank" rel="noopener noreferrer" class="external-link service-badge" title="View in Jellyfin">
													<span class="service-badge-text jellyfin">JF</span>
												</a>
											{/if}
											{#if getTmdbUrl(item)}
												<a href={getTmdbUrl(item)} target="_blank" rel="noopener noreferrer" class="external-link service-badge" title="View on TMDB">
													<span class="service-badge-text tmdb">TMDB</span>
												</a>
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

	.service-badge {
		text-decoration: none;
	}

	.service-badge-text {
		font-size: 9px;
		font-weight: var(--font-weight-bold);
		padding: 1px 4px;
		border-radius: 2px;
		letter-spacing: -0.02em;
	}

	.service-badge-text.jellyfin {
		background: #00a4dc;
		color: #fff;
	}

	.service-badge-text.tmdb {
		background: #01b4e4;
		color: #fff;
	}

	.col-year {
		width: 10%;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-size {
		width: 12%;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-added {
		width: 15%;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
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
		.library-page {
			padding: var(--space-4);
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

		.col-watched {
			display: none;
		}
	}
</style>
