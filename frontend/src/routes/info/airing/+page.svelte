<script lang="ts">
	import { onMount } from 'svelte';

	interface InProgressSeason {
		season_number: number;
		name: string;
		episodes_aired: number;
		episode_count: number;
	}

	interface CurrentlyAiringItem {
		jellyseerr_id: number;
		title: string;
		in_progress_seasons: InProgressSeason[];
	}

	interface CurrentlyAiringResponse {
		items: CurrentlyAiringItem[];
		total_count: number;
	}

	let data = $state<CurrentlyAiringResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function formatSeasonProgress(seasons: InProgressSeason[]): string {
		return seasons
			.map((s) => `S${s.season_number} (${s.episodes_aired}/${s.episode_count})`)
			.join(', ');
	}

	onMount(async () => {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			const response = await fetch('/api/info/airing', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (!response.ok) {
				if (response.status === 401) {
					error = 'Session expired. Please log in again.';
				} else {
					error = 'Failed to load currently airing series';
				}
				loading = false;
				return;
			}

			data = await response.json();
		} catch {
			error = 'Failed to load data';
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Currently Airing - Media Janitor</title>
</svelte:head>

<div class="page-container">
	<div class="page-header">
		<h1>Currently Airing</h1>
		<p class="page-description">TV series with in-progress seasons</p>
	</div>

	{#if loading}
		<div class="loading">Loading...</div>
	{:else if error}
		<div class="error">
			<p>{error}</p>
		</div>
	{:else if data}
		<div class="summary-bar">
			<span class="summary-count">{data.total_count} series</span>
		</div>

		{#if data.items.length === 0}
			<div class="empty-state">
				<p>No currently airing series found.</p>
				<p class="hint">This feature will show series with episodes still to air.</p>
				<a href="/" class="back-link">Back to Dashboard</a>
			</div>
		{:else}
			<div class="content-list">
				{#each data.items as item, index}
					<div class="content-item">
						<span class="item-number">{index + 1}</span>
						<div class="item-info">
							<span class="item-title">{item.title}</span>
							<div class="item-meta">
								<span class="airing-badge">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
										<path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 10l7 4-7 4z"/>
									</svg>
									Currently Airing
								</span>
								{#if item.in_progress_seasons.length > 0}
									<span class="season-progress">{formatSeasonProgress(item.in_progress_seasons)}</span>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.page-container {
		padding: 1.5rem;
		max-width: 1000px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	.page-header h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
	}

	.page-description {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.loading {
		padding: 2rem;
		text-align: center;
		color: var(--text-secondary);
	}

	.error {
		padding: 2rem;
		background: var(--bg-secondary);
		border: 1px solid var(--danger);
		border-radius: 0.75rem;
		color: var(--danger);
	}

	.summary-bar {
		display: flex;
		justify-content: flex-start;
		padding: 0.75rem 1rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.summary-count {
		font-weight: 600;
		color: var(--text-primary);
	}

	.empty-state {
		padding: 3rem;
		text-align: center;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 0.75rem;
	}

	.empty-state p {
		color: var(--text-secondary);
		margin-bottom: 0.5rem;
	}

	.empty-state .hint {
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.back-link {
		color: var(--accent);
		text-decoration: none;
	}

	.back-link:hover {
		text-decoration: underline;
	}

	.content-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.content-item {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		transition: background-color 0.2s ease;
	}

	.content-item:hover {
		background: var(--bg-hover);
	}

	.item-number {
		color: var(--text-secondary);
		font-size: 0.875rem;
		min-width: 2rem;
		text-align: right;
	}

	.item-info {
		flex: 1;
	}

	.item-title {
		font-weight: 500;
		display: block;
		margin-bottom: 0.25rem;
	}

	.item-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
		font-size: 0.875rem;
		color: var(--text-secondary);
	}

	.airing-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.5rem;
		background: rgba(20, 184, 166, 0.1);
		color: #14b8a6;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.season-progress {
		color: var(--text-secondary);
	}

	@media (max-width: 640px) {
		.item-meta {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.25rem;
		}
	}
</style>
