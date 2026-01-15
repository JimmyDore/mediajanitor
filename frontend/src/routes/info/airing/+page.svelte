<script lang="ts">
	import { onMount } from 'svelte';
	import { authenticatedFetch } from '$lib/stores';

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
			const response = await authenticatedFetch('/api/info/airing');

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

<div class="page">
	<header class="page-header">
		<div class="header-main">
			<h1>Currently Airing</h1>
			{#if data && !loading}
				<span class="header-stats">{data.total_count} series</span>
			{/if}
		</div>
	</header>

	<p class="page-subtitle">TV series with in-progress seasons</p>

	{#if loading}
		<div class="loading">
			<span class="spinner"></span>
		</div>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else if data}
		{#if data.items.length === 0}
			<div class="empty">No currently airing series found</div>
		{:else}
			<div class="table-container">
				<table class="data-table">
					<thead>
						<tr>
							<th class="col-title">Title</th>
							<th class="col-progress">Progress</th>
						</tr>
					</thead>
					<tbody>
						{#each data.items as item}
							<tr>
								<td class="col-title">
									<span class="item-title">{item.title}</span>
								</td>
								<td class="col-progress">
									{#if item.in_progress_seasons.length > 0}
										<div class="season-list">
											{#each item.in_progress_seasons as season}
												<span class="season-badge">
													S{season.season_number}
													<span class="season-progress">{season.episodes_aired}/{season.episode_count}</span>
												</span>
											{/each}
										</div>
									{:else}
										<span class="no-data">-</span>
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

<style>
	.page {
		max-width: 800px;
		margin: 0 auto;
		padding: var(--space-6);
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-2);
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

	.page-subtitle {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-6);
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

	@keyframes spin {
		to { transform: rotate(360deg); }
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

	.data-table {
		width: 100%;
		border-collapse: collapse;
	}

	.data-table th,
	.data-table td {
		padding: var(--space-3) var(--space-4);
		text-align: left;
	}

	.data-table th {
		background: var(--bg-secondary);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
		border-bottom: 1px solid var(--border);
	}

	.data-table tr {
		border-bottom: 1px solid var(--border);
	}

	.data-table tr:last-child {
		border-bottom: none;
	}

	.data-table tbody tr:hover {
		background: var(--bg-hover);
	}

	/* Columns */
	.col-title {
		width: 50%;
	}

	.item-title {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.col-progress {
		width: 50%;
	}

	.season-list {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.season-badge {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		padding: 2px 8px;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		background: var(--accent-light);
		color: var(--accent);
		border-radius: var(--radius-sm);
	}

	.season-progress {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		opacity: 0.8;
	}

	.no-data {
		color: var(--text-muted);
	}

	/* Responsive */
	@media (max-width: 640px) {
		.page {
			padding: var(--space-4);
		}

		.data-table th,
		.data-table td {
			padding: var(--space-2) var(--space-3);
		}

		.season-list {
			flex-direction: column;
			gap: var(--space-1);
		}
	}
</style>
