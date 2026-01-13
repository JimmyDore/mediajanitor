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

	let loading = $state(true);
	let error = $state<string | null>(null);
	let data = $state<ContentIssuesResponse | null>(null);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let protectingIds = $state<Set<string>>(new Set());
	let frenchOnlyIds = $state<Set<string>>(new Set());
	let languageExemptIds = $state<Set<string>>(new Set());
	let activeFilter = $state<FilterType>('all');
	let sortField = $state<SortField>('size');
	let sortOrder = $state<SortOrder>('desc');

	// Initialize filter from URL
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

	function formatPath(path: string | null): string {
		if (!path) return '';
		const parts = path.split('/').filter((p) => p);
		if (parts.length >= 5) {
			return `${parts[3]}/${parts[4]}`;
		}
		return path;
	}

	function formatLastWatched(lastPlayed: string | null): string {
		if (!lastPlayed) {
			return 'Never watched';
		}
		try {
			const date = new Date(lastPlayed);
			const now = new Date();
			const daysAgo = Math.floor(
				(now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
			);
			if (daysAgo > 365) {
				const yearsAgo = Math.floor(daysAgo / 365);
				return `${yearsAgo}+ year${yearsAgo > 1 ? 's' : ''} ago`;
			}
			if (daysAgo > 30) {
				const monthsAgo = Math.floor(daysAgo / 30);
				return `${monthsAgo} month${monthsAgo > 1 ? 's' : ''} ago`;
			}
			return `${daysAgo} day${daysAgo !== 1 ? 's' : ''} ago`;
		} catch {
			return 'Unknown';
		}
	}

	function wasNeverWatched(item: ContentIssueItem): boolean {
		return !item.last_played_date;
	}

	function showToast(message: string, type: 'success' | 'error') {
		toast = { message, type };
		setTimeout(() => {
			toast = null;
		}, 3000);
	}

	async function protectContent(item: ContentIssueItem) {
		const token = localStorage.getItem('access_token');
		if (!token) {
			showToast('Not authenticated', 'error');
			return;
		}

		protectingIds = new Set([...protectingIds, item.jellyfin_id]);

		try {
			const response = await fetch('/api/whitelist/content', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					jellyfin_id: item.jellyfin_id,
					name: item.name,
					media_type: item.media_type
				})
			});

			if (response.status === 401) {
				showToast('Session expired. Please log in again.', 'error');
				return;
			}

			if (response.status === 409) {
				showToast('Content is already in whitelist', 'error');
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				showToast(errorData.detail || 'Failed to protect content', 'error');
				return;
			}

			// Remove item from the list immediately
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

			showToast('Added to whitelist', 'success');
		} catch (e) {
			showToast(e instanceof Error ? e.message : 'Failed to protect content', 'error');
		} finally {
			const newSet = new Set(protectingIds);
			newSet.delete(item.jellyfin_id);
			protectingIds = newSet;
		}
	}

	async function markAsFrenchOnly(item: ContentIssueItem) {
		const token = localStorage.getItem('access_token');
		if (!token) {
			showToast('Not authenticated', 'error');
			return;
		}

		frenchOnlyIds = new Set([...frenchOnlyIds, item.jellyfin_id]);

		try {
			const response = await fetch('/api/whitelist/french-only', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					jellyfin_id: item.jellyfin_id,
					name: item.name,
					media_type: item.media_type
				})
			});

			if (response.status === 401) {
				showToast('Session expired. Please log in again.', 'error');
				return;
			}

			if (response.status === 409) {
				showToast('Already marked as French-only', 'error');
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				showToast(errorData.detail || 'Failed to mark as French-only', 'error');
				return;
			}

			// Remove item from the list if it only had missing_en_audio issue
			// If it also has missing_fr_audio, it stays but without the EN issue
			if (data) {
				const currentItem = data.items.find((i) => i.jellyfin_id === item.jellyfin_id);
				if (currentItem) {
					const hasOnlyEnglishIssue =
						currentItem.language_issues?.length === 1 &&
						currentItem.language_issues[0] === 'missing_en_audio';

					if (hasOnlyEnglishIssue && currentItem.issues.length === 1) {
						// Only had language issue and only missing EN - remove completely
						const removedSize = currentItem.size_bytes || 0;
						data = {
							...data,
							items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
							total_count: data.total_count - 1,
							total_size_bytes: data.total_size_bytes - removedSize,
							total_size_formatted: formatSize(data.total_size_bytes - removedSize)
						};
					} else {
						// Has other issues - just refresh to get updated state
						await fetchIssues(activeFilter);
					}
				}
			}

			showToast('Marked as French-only', 'success');
		} catch (e) {
			showToast(e instanceof Error ? e.message : 'Failed to mark as French-only', 'error');
		} finally {
			const newSet = new Set(frenchOnlyIds);
			newSet.delete(item.jellyfin_id);
			frenchOnlyIds = newSet;
		}
	}

	function hasMissingEnglishAudio(item: ContentIssueItem): boolean {
		return item.language_issues?.includes('missing_en_audio') ?? false;
	}

	function hasLanguageIssues(item: ContentIssueItem): boolean {
		return item.issues.includes('language');
	}

	async function markAsLanguageExempt(item: ContentIssueItem) {
		const token = localStorage.getItem('access_token');
		if (!token) {
			showToast('Not authenticated', 'error');
			return;
		}

		languageExemptIds = new Set([...languageExemptIds, item.jellyfin_id]);

		try {
			const response = await fetch('/api/whitelist/language-exempt', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					jellyfin_id: item.jellyfin_id,
					name: item.name,
					media_type: item.media_type
				})
			});

			if (response.status === 401) {
				showToast('Session expired. Please log in again.', 'error');
				return;
			}

			if (response.status === 409) {
				showToast('Already exempt from language checks', 'error');
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				showToast(errorData.detail || 'Failed to exempt from language checks', 'error');
				return;
			}

			// Remove language issue from item - if it only had language issue, remove it
			if (data) {
				const currentItem = data.items.find((i) => i.jellyfin_id === item.jellyfin_id);
				if (currentItem) {
					const hasOnlyLanguageIssue = currentItem.issues.length === 1 && currentItem.issues[0] === 'language';

					if (hasOnlyLanguageIssue) {
						// Only had language issue - remove completely
						const removedSize = currentItem.size_bytes || 0;
						data = {
							...data,
							items: data.items.filter((i) => i.jellyfin_id !== item.jellyfin_id),
							total_count: data.total_count - 1,
							total_size_bytes: data.total_size_bytes - removedSize,
							total_size_formatted: formatSize(data.total_size_bytes - removedSize)
						};
					} else {
						// Has other issues - just refresh to get updated state
						await fetchIssues(activeFilter);
					}
				}
			}

			showToast('Exempt from language checks', 'success');
		} catch (e) {
			showToast(e instanceof Error ? e.message : 'Failed to exempt from language checks', 'error');
		} finally {
			const newSet = new Set(languageExemptIds);
			newSet.delete(item.jellyfin_id);
			languageExemptIds = newSet;
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
			const token = localStorage.getItem('access_token');
			if (!token) {
				error = 'Not authenticated';
				return;
			}

			const filterParam = filter === 'all' ? '' : `?filter=${filter}`;
			const response = await fetch(`/api/content/issues${filterParam}`, {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (response.status === 401) {
				error = 'Session expired. Please log in again.';
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				error = errorData.detail || 'Failed to fetch issues';
				return;
			}

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
				case 'name':
					comparison = a.name.localeCompare(b.name);
					break;
				case 'size':
					comparison = (a.size_bytes || 0) - (b.size_bytes || 0);
					break;
				case 'date':
					const dateA = a.last_played_date ? new Date(a.last_played_date).getTime() : 0;
					const dateB = b.last_played_date ? new Date(b.last_played_date).getTime() : 0;
					comparison = dateA - dateB;
					break;
				case 'issues':
					comparison = a.issues.length - b.issues.length;
					break;
			}
			return sortOrder === 'asc' ? comparison : -comparison;
		});
	}

	function getIssueBadgeClass(issue: string): string {
		switch (issue) {
			case 'old':
				return 'badge-old';
			case 'large':
				return 'badge-large';
			case 'language':
				return 'badge-language';
			case 'request':
				return 'badge-request';
			default:
				return '';
		}
	}

	function getIssueLabel(issue: string): string {
		switch (issue) {
			case 'old':
				return 'Old';
			case 'large':
				return 'Large';
			case 'language':
				return 'Language';
			case 'request':
				return 'Request';
			default:
				return issue;
		}
	}

	onMount(() => {
		fetchIssues(activeFilter);
	});
</script>

<svelte:head>
	<title>Issues - Media Janitor</title>
</svelte:head>

{#if toast}
	<div class="toast toast-{toast.type}" role="alert">
		{toast.message}
	</div>
{/if}

<div class="page-container">
	<div class="page-header">
		<h1>Content Issues</h1>
		<p class="page-description">
			View and manage content with issues across your library
		</p>
	</div>

	<!-- Filter Tabs -->
	<div class="filter-tabs">
		{#each Object.entries(filterLabels) as [filter, label]}
			<button
				class="filter-tab"
				class:active={activeFilter === filter}
				onclick={() => setFilter(filter as FilterType)}
			>
				{label}
			</button>
		{/each}
	</div>

	{#if loading}
		<div class="loading-container">
			<div class="spinner" aria-label="Loading"></div>
			<p>Loading issues...</p>
		</div>
	{:else if error}
		<div class="error-container">
			<p class="error-message">{error}</p>
		</div>
	{:else if data}
		<div class="summary-bar">
			<div class="summary-stat">
				<span class="stat-label">Total Items</span>
				<span class="stat-value">{data.total_count}</span>
			</div>
			<div class="summary-stat">
				<span class="stat-label">Total Size</span>
				<span class="stat-value">{data.total_size_formatted}</span>
			</div>
		</div>

		{#if data.items.length === 0}
			<div class="empty-state">
				<p>No issues found{activeFilter !== 'all' ? ` with filter "${filterLabels[activeFilter]}"` : ''}!</p>
			</div>
		{:else}
			<div class="content-list">
				<div class="list-header">
					<span class="col-rank">#</span>
					<button class="col-name sortable" onclick={() => toggleSort('name')}>
						Name {sortField === 'name' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
					</button>
					<span class="col-type">Type</span>
					<button class="col-issues sortable" onclick={() => toggleSort('issues')}>
						Issues {sortField === 'issues' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
					</button>
					<button class="col-size sortable" onclick={() => toggleSort('size')}>
						Size {sortField === 'size' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
					</button>
					<button class="col-status sortable" onclick={() => toggleSort('date')}>
						Last Watched {sortField === 'date' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
					</button>
					<span class="col-actions">Actions</span>
				</div>
				{#each getSortedItems(data.items) as item, index}
					<div class="content-item">
						<span class="col-rank">{index + 1}</span>
						<div class="col-name">
							<span class="item-name">{item.name}</span>
							{#if item.production_year}
								<span class="item-year">({item.production_year})</span>
							{/if}
							{#if item.path}
								<span class="item-path">{formatPath(item.path)}</span>
							{/if}
						</div>
						<span class="col-type">
							<span class="type-badge type-{item.media_type.toLowerCase()}">
								{item.media_type === 'Movie' ? 'Movie' : 'Series'}
							</span>
						</span>
						<span class="col-issues">
							{#each item.issues as issue}
								<span class="issue-badge {getIssueBadgeClass(issue)}">{getIssueLabel(issue)}</span>
							{/each}
						</span>
						<span class="col-size">{item.size_formatted}</span>
						<span class="col-status" class:never-watched={wasNeverWatched(item)}>
							{formatLastWatched(item.last_played_date)}
						</span>
						<span class="col-actions">
							{#if item.issues.includes('old')}
								<button
									class="btn-protect"
									onclick={() => protectContent(item)}
									disabled={protectingIds.has(item.jellyfin_id)}
									title="Add to whitelist - protects from deletion suggestions"
								>
									{#if protectingIds.has(item.jellyfin_id)}
										<span class="btn-spinner"></span>
									{:else}
										Protect
									{/if}
								</button>
							{/if}
							{#if hasMissingEnglishAudio(item)}
								<button
									class="btn-french-only"
									onclick={() => markAsFrenchOnly(item)}
									disabled={frenchOnlyIds.has(item.jellyfin_id)}
									title="Mark as French-only - excludes from missing English audio checks"
								>
									{#if frenchOnlyIds.has(item.jellyfin_id)}
										<span class="btn-spinner"></span>
									{:else}
										FR Only
									{/if}
								</button>
							{/if}
							{#if hasLanguageIssues(item)}
								<button
									class="btn-exempt"
									onclick={() => markAsLanguageExempt(item)}
									disabled={languageExemptIds.has(item.jellyfin_id)}
									title="Exempt from all language checks"
								>
									{#if languageExemptIds.has(item.jellyfin_id)}
										<span class="btn-spinner"></span>
									{:else}
										Exempt
									{/if}
								</button>
							{/if}
						</span>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.page-container {
		padding: 1.5rem;
		max-width: 1200px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	.page-header h1 {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0 0 0.5rem 0;
	}

	.page-description {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	/* Filter Tabs */
	.filter-tabs {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
		padding: 0.25rem;
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border);
		flex-wrap: wrap;
	}

	.filter-tab {
		padding: 0.5rem 1rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text-secondary);
		background: transparent;
		border: none;
		border-radius: 0.375rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.filter-tab:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.filter-tab.active {
		color: var(--accent);
		background: var(--bg-primary);
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.loading-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		gap: 1rem;
	}

	.spinner {
		width: 2rem;
		height: 2rem;
		border: 3px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-container p {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	.error-container {
		padding: 2rem;
		background: var(--bg-secondary);
		border: 1px solid var(--danger);
		border-radius: 0.5rem;
		text-align: center;
	}

	.error-message {
		color: var(--danger);
		margin: 0;
	}

	.summary-bar {
		display: flex;
		gap: 2rem;
		padding: 1rem 1.5rem;
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border);
		margin-bottom: 1.5rem;
	}

	.summary-stat {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.stat-value {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.empty-state {
		padding: 3rem;
		text-align: center;
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border);
	}

	.empty-state p {
		color: var(--text-secondary);
		margin: 0;
	}

	.content-list {
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border);
		overflow: hidden;
	}

	.list-header {
		display: grid;
		grid-template-columns: 3rem 1fr 5rem 8rem 5rem 8rem 5rem;
		gap: 1rem;
		padding: 0.75rem 1rem;
		background: var(--bg-tertiary, var(--bg-secondary));
		border-bottom: 1px solid var(--border);
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
	}

	.sortable {
		cursor: pointer;
		background: transparent;
		border: none;
		font-size: inherit;
		font-weight: inherit;
		text-transform: inherit;
		letter-spacing: inherit;
		color: inherit;
		padding: 0;
		text-align: inherit;
	}

	.sortable:hover {
		color: var(--text-primary);
	}

	.content-item {
		display: grid;
		grid-template-columns: 3rem 1fr 5rem 8rem 5rem 8rem 5rem;
		gap: 1rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
		align-items: center;
		font-size: 0.875rem;
	}

	.content-item:last-child {
		border-bottom: none;
	}

	.content-item:hover {
		background: var(--bg-hover, rgba(0, 0, 0, 0.02));
	}

	.col-rank {
		color: var(--text-muted);
		font-weight: 500;
	}

	.col-name {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
		min-width: 0;
	}

	.item-name {
		font-weight: 500;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.item-year {
		font-weight: 400;
		color: var(--text-secondary);
		margin-left: 0.25rem;
	}

	.item-path {
		font-size: 0.75rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.col-type {
		text-align: center;
	}

	.type-badge {
		display: inline-block;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.type-movie {
		background: rgba(59, 130, 246, 0.1);
		color: rgb(59, 130, 246);
	}

	.type-series {
		background: rgba(168, 85, 247, 0.1);
		color: rgb(168, 85, 247);
	}

	.col-issues {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
	}

	.issue-badge {
		display: inline-block;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		font-size: 0.625rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	.badge-old {
		background: rgba(239, 68, 68, 0.1);
		color: #ef4444;
	}

	.badge-large {
		background: rgba(245, 158, 11, 0.1);
		color: #f59e0b;
	}

	.badge-language {
		background: rgba(59, 130, 246, 0.1);
		color: #3b82f6;
	}

	.badge-request {
		background: rgba(139, 92, 246, 0.1);
		color: #8b5cf6;
	}

	.col-size {
		color: var(--text-secondary);
		text-align: right;
	}

	.col-status {
		color: var(--text-secondary);
		font-size: 0.8125rem;
	}

	.col-status.never-watched {
		color: var(--warning, #f59e0b);
	}

	.col-actions {
		text-align: center;
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		justify-content: center;
	}

	.btn-protect {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: var(--accent, #3b82f6);
		background: transparent;
		border: 1px solid var(--accent, #3b82f6);
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.15s ease;
		min-width: 4rem;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.btn-protect:hover:not(:disabled) {
		background: var(--accent, #3b82f6);
		color: white;
	}

	.btn-protect:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-french-only {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: #8b5cf6;
		background: transparent;
		border: 1px solid #8b5cf6;
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.15s ease;
		min-width: 4rem;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.btn-french-only:hover:not(:disabled) {
		background: #8b5cf6;
		color: white;
	}

	.btn-french-only:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-exempt {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: #10b981;
		background: transparent;
		border: 1px solid #10b981;
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.15s ease;
		min-width: 4rem;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.btn-exempt:hover:not(:disabled) {
		background: #10b981;
		color: white;
	}

	.btn-exempt:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-spinner {
		width: 0.875rem;
		height: 0.875rem;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Toast notifications */
	.toast {
		position: fixed;
		bottom: 1.5rem;
		right: 1.5rem;
		padding: 0.75rem 1.25rem;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		z-index: 1000;
		animation: slideIn 0.2s ease;
	}

	.toast-success {
		background: var(--success, #22c55e);
		color: white;
	}

	.toast-error {
		background: var(--danger, #ef4444);
		color: white;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	/* Responsive design */
	@media (max-width: 900px) {
		.list-header {
			grid-template-columns: 1fr 5rem 6rem 5rem;
		}

		.content-item {
			grid-template-columns: 1fr 5rem 6rem 5rem;
		}

		.col-rank,
		.col-status {
			display: none;
		}
	}

	@media (max-width: 640px) {
		.list-header {
			display: none;
		}

		.content-item {
			grid-template-columns: 1fr;
			gap: 0.5rem;
			padding: 1rem;
		}

		.col-rank {
			display: none;
		}

		.col-name {
			order: 1;
		}

		.col-type,
		.col-issues,
		.col-size,
		.col-status {
			font-size: 0.75rem;
		}

		.col-actions {
			order: 2;
			text-align: left;
		}

		.filter-tabs {
			flex-wrap: wrap;
		}

		.filter-tab {
			flex: 1;
			text-align: center;
			min-width: 60px;
		}
	}
</style>
