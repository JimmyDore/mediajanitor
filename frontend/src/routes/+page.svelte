<script lang="ts">
	import { onMount } from 'svelte';
	import { auth } from '$lib/stores';
	import { goto } from '$app/navigation';
	import Landing from '$lib/components/Landing.svelte';

	let error = $state<string | null>(null);

	interface SyncStatus {
		last_synced: string | null;
		status: string | null;
		media_items_count: number | null;
		requests_count: number | null;
		error: string | null;
	}

	interface SyncResponse {
		status: string;
		media_items_synced: number;
		requests_synced: number;
		error: string | null;
	}

	interface IssueCategorySummary {
		count: number;
		total_size_bytes: number;
		total_size_formatted: string;
	}

	interface InfoCategorySummary {
		count: number;
	}

	interface ContentSummary {
		old_content: IssueCategorySummary;
		large_movies: IssueCategorySummary;
		language_issues: IssueCategorySummary;
		unavailable_requests: IssueCategorySummary;
		recently_available: InfoCategorySummary;
		currently_airing: InfoCategorySummary;
	}

	let syncStatus = $state<SyncStatus | null>(null);
	let syncLoading = $state(false);
	let toastMessage = $state<string | null>(null);
	let toastType = $state<'success' | 'error'>('success');
	let contentSummary = $state<ContentSummary | null>(null);
	let summaryLoading = $state(true);

	function formatDate(isoString: string): string {
		const date = new Date(isoString);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const minutes = Math.floor(diff / 60000);
		const hours = Math.floor(diff / 3600000);
		const days = Math.floor(diff / 86400000);

		if (minutes < 1) return 'Just now';
		if (minutes < 60) return `${minutes}m ago`;
		if (hours < 24) return `${hours}h ago`;
		if (days < 7) return `${days}d ago`;
		return date.toLocaleDateString();
	}

	function showToast(message: string, type: 'success' | 'error') {
		toastMessage = message;
		toastType = type;
		setTimeout(() => {
			toastMessage = null;
		}, 5000);
	}

	async function fetchSyncStatus() {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) return;

			const response = await fetch('/api/sync/status', {
				headers: { Authorization: `Bearer ${token}` }
			});
			if (response.ok) {
				syncStatus = await response.json();
			}
		} catch {
			// Ignore sync status errors
		}
	}

	async function fetchContentSummary() {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) return;

			const response = await fetch('/api/content/summary', {
				headers: { Authorization: `Bearer ${token}` }
			});
			if (response.ok) {
				contentSummary = await response.json();
			}
		} catch {
			// Ignore summary errors
		} finally {
			summaryLoading = false;
		}
	}

	async function triggerSync() {
		if (syncLoading) return;

		syncLoading = true;
		try {
			const token = localStorage.getItem('access_token');
			if (!token) {
				showToast('Not authenticated', 'error');
				return;
			}

			const response = await fetch('/api/sync', {
				method: 'POST',
				headers: { Authorization: `Bearer ${token}` }
			});

			if (response.status === 429) {
				const data = await response.json();
				showToast(data.detail || 'Rate limited. Please wait before syncing again.', 'error');
				return;
			}

			if (!response.ok) {
				const data = await response.json();
				showToast(data.detail || 'Sync failed', 'error');
				return;
			}

			const data: SyncResponse = await response.json();
			await fetchSyncStatus();
			await fetchContentSummary();

			if (data.status === 'success') {
				showToast(
					`Synced ${data.media_items_synced} media items and ${data.requests_synced} requests`,
					'success'
				);
			} else if (data.status === 'partial') {
				showToast(`Sync completed with warnings: ${data.error}`, 'success');
			} else {
				showToast(data.error || 'Sync failed', 'error');
			}
		} catch {
			showToast('Failed to sync data', 'error');
		} finally {
			syncLoading = false;
		}
	}

	function navigateToIssues(filter: string) {
		goto(`/issues?filter=${filter}`);
	}

	function navigateToInfo(type: string) {
		goto(`/info/${type}`);
	}

	onMount(async () => {
		try {
			await Promise.all([fetchSyncStatus(), fetchContentSummary()]);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch';
		}
	});
</script>

<svelte:head>
	<title>{$auth.isAuthenticated ? 'Dashboard' : 'Media Janitor - Keep Your Media Library Clean'}</title>
</svelte:head>

{#if !$auth.isAuthenticated && !$auth.isLoading}
	<Landing />
{:else if $auth.isAuthenticated}
	{#if toastMessage}
		<div class="toast toast-{toastType}" role="alert">
			{toastMessage}
		</div>
	{/if}

	<div class="dashboard">
		<header class="page-header">
			<div class="header-left">
				<h1>Dashboard</h1>
				{#if syncStatus?.last_synced}
					<span class="sync-time">Updated {formatDate(syncStatus.last_synced)}</span>
				{/if}
			</div>
			<button
				class="btn-refresh"
				onclick={triggerSync}
				disabled={syncLoading}
				aria-label="Refresh data"
			>
				{#if syncLoading}
					<span class="spinner"></span>
				{:else}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M23 4v6h-6M1 20v-6h6"/>
						<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
					</svg>
				{/if}
			</button>
		</header>

		{#if error}
		<div class="error-banner">
			<p>Error: {error}</p>
		</div>
	{:else}
		<!-- Issue Stats -->
		<section class="stats-section">
			<h2 class="section-label">Issues</h2>

			{#if summaryLoading}
				<div class="stats-grid">
					{#each Array(4) as _}
						<div class="stat-card skeleton"></div>
					{/each}
				</div>
			{:else}
				<div class="stats-grid">
					<button class="stat-card" onclick={() => navigateToIssues('old')}>
						<div class="stat-value">{contentSummary?.old_content.count ?? 0}</div>
						<div class="stat-label">Old Content</div>
						{#if contentSummary && contentSummary.old_content.count > 0}
							<div class="stat-meta">{contentSummary.old_content.total_size_formatted}</div>
						{/if}
					</button>

					<button class="stat-card" onclick={() => navigateToIssues('large')}>
						<div class="stat-value">{contentSummary?.large_movies.count ?? 0}</div>
						<div class="stat-label">Large Movies</div>
						{#if contentSummary && contentSummary.large_movies.count > 0}
							<div class="stat-meta">{contentSummary.large_movies.total_size_formatted}</div>
						{/if}
					</button>

					<button class="stat-card" onclick={() => navigateToIssues('language')}>
						<div class="stat-value">{contentSummary?.language_issues.count ?? 0}</div>
						<div class="stat-label">Language Issues</div>
					</button>

					<button class="stat-card" onclick={() => navigateToIssues('requests')}>
						<div class="stat-value">{contentSummary?.unavailable_requests.count ?? 0}</div>
						<div class="stat-label">Unavailable Requests</div>
					</button>
				</div>
			{/if}
		</section>

		<!-- Info Links -->
		<section class="info-section">
			<h2 class="section-label">Info</h2>
			<div class="info-links">
				<button class="info-link" onclick={() => navigateToInfo('recent')}>
					<span class="info-count">{contentSummary?.recently_available?.count ?? 0}</span>
					<span class="info-text">recently available</span>
				</button>
				<span class="info-separator">·</span>
				<button class="info-link" onclick={() => navigateToInfo('airing')}>
					<span class="info-count">{contentSummary?.currently_airing?.count ?? 0}</span>
					<span class="info-text">currently airing</span>
				</button>
			</div>
		</section>
		{/if}
	</div>
{/if}

<style>
	.dashboard {
		max-width: 800px;
		margin: 0 auto;
		padding: var(--space-6);
	}

	/* Header */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-8);
	}

	.header-left {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
	}

	.sync-time {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.btn-refresh {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-refresh:hover:not(:disabled) {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	.btn-refresh:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinner {
		width: 16px;
		height: 16px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Error Banner */
	.error-banner {
		padding: var(--space-4);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
	}

	/* Stats Section */
	.stats-section {
		margin-bottom: var(--space-8);
	}

	.section-label {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: var(--space-4);
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--space-3);
	}

	.stat-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--space-4);
		text-align: left;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.stat-card:hover {
		border-color: var(--accent);
		background: var(--bg-hover);
	}

	.stat-card.skeleton {
		min-height: 88px;
		animation: pulse 1.5s ease-in-out infinite;
	}

	.stat-value {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-bold);
		font-family: var(--font-mono);
		color: var(--text-primary);
		line-height: 1;
		margin-bottom: var(--space-1);
	}

	.stat-label {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-1);
	}

	.stat-meta {
		font-size: var(--font-size-xs);
		font-family: var(--font-mono);
		color: var(--text-muted);
	}

	/* Info Section */
	.info-section {
		margin-bottom: var(--space-8);
	}

	.info-links {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.info-link {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: transparent;
		border: none;
		color: var(--text-secondary);
		font-size: var(--font-size-md);
		cursor: pointer;
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}

	.info-link:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.info-count {
		font-family: var(--font-mono);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
	}

	.info-text {
		color: inherit;
	}

	.info-separator {
		color: var(--text-muted);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	/* Responsive */
	@media (max-width: 640px) {
		.dashboard {
			padding: var(--space-4);
		}

		.header-left {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-1);
		}

		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.info-links {
			flex-wrap: wrap;
		}
	}
</style>
