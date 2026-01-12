<script lang="ts">
	import { onMount } from 'svelte';

	interface OldUnwatchedItem {
		jellyfin_id: string;
		name: string;
		media_type: string;
		production_year: number | null;
		size_bytes: number | null;
		size_formatted: string;
		last_played_date: string | null;
		path: string | null;
	}

	interface OldUnwatchedResponse {
		items: OldUnwatchedItem[];
		total_count: number;
		total_size_bytes: number;
		total_size_formatted: string;
	}

	let loading = $state(true);
	let error = $state<string | null>(null);
	let data = $state<OldUnwatchedResponse | null>(null);

	function formatPath(path: string | null): string {
		if (!path) return '';
		const parts = path.split('/').filter((p) => p);
		if (parts.length >= 5) {
			return `${parts[3]}/${parts[4]}`;
		}
		return path;
	}

	function formatLastWatched(lastPlayed: string | null, played: boolean): string {
		if (!lastPlayed && !played) {
			return 'Never watched';
		}
		if (!lastPlayed) {
			return 'Watched (no date available)';
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

	// Check if item was never watched based on last_played_date
	function wasNeverWatched(item: OldUnwatchedItem): boolean {
		return !item.last_played_date;
	}

	async function fetchOldUnwatchedContent() {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) {
				error = 'Not authenticated';
				return;
			}

			const response = await fetch('/api/content/old-unwatched', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (response.status === 401) {
				error = 'Session expired. Please log in again.';
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				error = errorData.detail || 'Failed to fetch content';
				return;
			}

			data = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch content';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchOldUnwatchedContent();
	});
</script>

<svelte:head>
	<title>Old Content - Media Janitor</title>
</svelte:head>

<div class="page-container">
	<div class="page-header">
		<h1>Old/Unwatched Content</h1>
		<p class="page-description">
			Content not watched in 4+ months or never watched (if added 3+ months ago)
		</p>
	</div>

	{#if loading}
		<div class="loading-container">
			<div class="spinner" aria-label="Loading"></div>
			<p>Loading content...</p>
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
				<p>All your content has been watched recently!</p>
			</div>
		{:else}
			<div class="content-list">
				<div class="list-header">
					<span class="col-rank">#</span>
					<span class="col-name">Name</span>
					<span class="col-type">Type</span>
					<span class="col-year">Year</span>
					<span class="col-size">Size</span>
					<span class="col-status">Last Watched</span>
				</div>
				{#each data.items as item, index}
					<div class="content-item">
						<span class="col-rank">{index + 1}</span>
						<div class="col-name">
							<span class="item-name">{item.name}</span>
							{#if item.path}
								<span class="item-path">{formatPath(item.path)}</span>
							{/if}
						</div>
						<span class="col-type">
							<span class="type-badge type-{item.media_type.toLowerCase()}">
								{item.media_type === 'Movie' ? 'Movie' : 'Series'}
							</span>
						</span>
						<span class="col-year">{item.production_year || '-'}</span>
						<span class="col-size">{item.size_formatted}</span>
						<span class="col-status" class:never-watched={wasNeverWatched(item)}>
							{formatLastWatched(item.last_played_date, !!item.last_played_date)}
						</span>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.page-container {
		padding: 0;
	}

	.page-header {
		margin-bottom: 2rem;
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
		grid-template-columns: 3rem 1fr 5rem 4rem 5rem 8rem;
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

	.content-item {
		display: grid;
		grid-template-columns: 3rem 1fr 5rem 4rem 5rem 8rem;
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

	.col-year {
		color: var(--text-secondary);
		text-align: center;
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

	/* Responsive design */
	@media (max-width: 768px) {
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
		.col-year,
		.col-size,
		.col-status {
			font-size: 0.75rem;
		}
	}
</style>
