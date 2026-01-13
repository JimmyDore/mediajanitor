<script lang="ts">
	import { onMount } from 'svelte';
	import { auth } from '$lib/stores';
	import { goto } from '$app/navigation';

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
		return date.toLocaleString();
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
			// Fetch sync status and content summary in parallel
			await Promise.all([fetchSyncStatus(), fetchContentSummary()]);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch';
		}
	});
</script>

<svelte:head>
	<title>Dashboard - Media Janitor</title>
</svelte:head>

{#if toastMessage}
	<div class="toast toast-{toastType}" role="alert">
		{toastMessage}
	</div>
{/if}

<div class="page-container">
	{#if $auth.isAuthenticated && $auth.user}
		<div class="page-header">
			<div class="header-content">
				<h1>Dashboard</h1>
				<p class="page-subtitle">Welcome back, {$auth.user.email}</p>
			</div>
			<div class="sync-controls">
				{#if syncStatus}
					<div class="sync-info">
						{#if syncStatus.last_synced}
							<span class="sync-time">Last synced: <span class="text-mono">{formatDate(syncStatus.last_synced)}</span></span>
						{:else}
							<span class="sync-time">Never synced</span>
						{/if}
					</div>
				{/if}
				<button
					class="refresh-button"
					onclick={triggerSync}
					disabled={syncLoading}
					aria-label="Refresh data"
				>
					{#if syncLoading}
						<span class="spinner" aria-hidden="true"></span>
						Syncing...
					{:else}
						Refresh
					{/if}
				</button>
			</div>
		</div>
	{/if}

	{#if error}
		<div class="error-box">
			<p>Error: {error}</p>
			<p class="error-hint">Make sure the backend is running on port 8000</p>
		</div>
	{:else}
		<section class="section">
			<h2 class="section-title">Issues</h2>
			<div class="card-grid">
				<!-- Old Content Card -->
				<button
					class="issue-card"
					onclick={() => navigateToIssues('old')}
					aria-label="View old content"
				>
					{#if summaryLoading}
						<div class="skeleton-content">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon icon-old">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
								<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/>
							</svg>
						</div>
						<div class="card-body">
							<span class="card-label">Old Content</span>
							<span class="card-value text-mono">{contentSummary?.old_content.count ?? 0}</span>
							{#if contentSummary && contentSummary.old_content.count > 0}
								<span class="card-meta text-mono">{contentSummary.old_content.total_size_formatted}</span>
							{/if}
						</div>
					{/if}
				</button>

				<!-- Large Movies Card -->
				<button
					class="issue-card"
					onclick={() => navigateToIssues('large')}
					aria-label="View large movies"
				>
					{#if summaryLoading}
						<div class="skeleton-content">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon icon-large">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
								<path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12zM6 10h2v2H6v-2zm0 4h8v2H6v-2zm10 0h2v2h-2v-2zm-6-4h8v2h-8v-2z"/>
							</svg>
						</div>
						<div class="card-body">
							<span class="card-label">Large Movies</span>
							<span class="card-value text-mono">{contentSummary?.large_movies.count ?? 0}</span>
							{#if contentSummary && contentSummary.large_movies.count > 0}
								<span class="card-meta text-mono">{contentSummary.large_movies.total_size_formatted}</span>
							{/if}
						</div>
					{/if}
				</button>

				<!-- Language Issues Card -->
				<button
					class="issue-card"
					onclick={() => navigateToIssues('language')}
					aria-label="View language issues"
				>
					{#if summaryLoading}
						<div class="skeleton-content">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon icon-language">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
								<path d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
							</svg>
						</div>
						<div class="card-body">
							<span class="card-label">Language Issues</span>
							<span class="card-value text-mono">{contentSummary?.language_issues.count ?? 0}</span>
						</div>
					{/if}
				</button>

				<!-- Unavailable Requests Card -->
				<button
					class="issue-card"
					onclick={() => navigateToIssues('requests')}
					aria-label="View unavailable requests"
				>
					{#if summaryLoading}
						<div class="skeleton-content">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon icon-requests">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
								<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
							</svg>
						</div>
						<div class="card-body">
							<span class="card-label">Unavailable Requests</span>
							<span class="card-value text-mono">{contentSummary?.unavailable_requests.count ?? 0}</span>
						</div>
					{/if}
				</button>
			</div>
		</section>

		<!-- Info Section -->
		<section class="section">
			<h2 class="section-title">Info</h2>
			<div class="card-grid card-grid-2">
				<!-- Recently Available Card -->
				<button
					class="info-card"
					onclick={() => navigateToInfo('recent')}
					aria-label="View recently available content"
				>
					{#if summaryLoading}
						<div class="skeleton-content">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon icon-recent">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
								<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
							</svg>
						</div>
						<div class="card-body">
							<span class="card-label">Recently Available</span>
							<span class="card-value text-mono">{contentSummary?.recently_available?.count ?? 0}</span>
							<span class="card-meta">Past 7 days</span>
						</div>
					{/if}
				</button>

				<!-- Currently Airing Card -->
				<button
					class="info-card"
					onclick={() => navigateToInfo('airing')}
					aria-label="View currently airing series"
				>
					{#if summaryLoading}
						<div class="skeleton-content">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon icon-airing">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
								<path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 10l7 4-7 4z"/>
							</svg>
						</div>
						<div class="card-body">
							<span class="card-label">Currently Airing</span>
							<span class="card-value text-mono">{contentSummary?.currently_airing?.count ?? 0}</span>
							<span class="card-meta">In-progress series</span>
						</div>
					{/if}
				</button>
			</div>
		</section>
	{/if}
</div>

<style>
	.page-container {
		padding: var(--space-6);
		max-width: 1200px;
		margin: 0 auto;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: var(--space-8);
		flex-wrap: wrap;
		gap: var(--space-4);
	}

	.header-content h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
		margin-bottom: var(--space-1);
	}

	.page-subtitle {
		color: var(--text-secondary);
		font-size: var(--font-size-base);
		margin: 0;
	}

	.sync-controls {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.sync-info {
		text-align: right;
	}

	.sync-time {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	.text-mono {
		font-family: var(--font-mono);
		font-variant-numeric: tabular-nums;
	}

	.refresh-button {
		padding: var(--space-2) var(--space-4);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		transition: background var(--transition-fast);
	}

	.refresh-button:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.refresh-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.error-box {
		padding: var(--space-6);
		background: var(--bg-secondary);
		border: 1px solid var(--danger);
		border-radius: var(--radius-lg);
	}

	.error-box p {
		color: var(--danger);
		margin-bottom: var(--space-2);
	}

	.error-hint {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	/* Sections */
	.section {
		margin-bottom: var(--space-8);
	}

	.section-title {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		margin-bottom: var(--space-4);
		color: var(--text-primary);
	}

	/* Card Grid */
	.card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: var(--space-4);
	}

	.card-grid-2 {
		max-width: 480px;
	}

	/* Issue Cards */
	.issue-card,
	.info-card {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		padding: var(--space-4);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		cursor: pointer;
		transition: border-color var(--transition-fast);
		text-align: left;
		width: 100%;
	}

	.issue-card:hover,
	.info-card:hover {
		border-color: var(--accent);
	}

	/* Info cards have a left accent border */
	.info-card {
		border-left: 3px solid var(--success);
	}

	.card-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: var(--radius-md);
		flex-shrink: 0;
	}

	.icon-old {
		background: var(--danger-light);
		color: var(--danger);
	}

	.icon-large {
		background: var(--warning-light);
		color: var(--warning);
	}

	.icon-language {
		background: var(--info-light);
		color: var(--info);
	}

	.icon-requests {
		background: rgba(139, 92, 246, 0.1);
		color: #8b5cf6;
	}

	.icon-recent,
	.icon-airing {
		background: var(--success-light);
		color: var(--success);
	}

	.card-body {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.card-label {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		font-weight: var(--font-weight-medium);
	}

	.card-value {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-bold);
		color: var(--text-primary);
		line-height: 1.2;
	}

	.card-meta {
		font-size: var(--font-size-xs);
		color: var(--text-muted);
	}

	/* Loading skeleton */
	.skeleton-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		width: 100%;
	}

	.skeleton-line {
		height: 1rem;
		background: linear-gradient(90deg, var(--bg-hover) 25%, var(--bg-secondary) 50%, var(--bg-hover) 75%);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
		border-radius: var(--radius-sm);
	}

	.skeleton-line.short {
		width: 60%;
	}

	.skeleton-line.long {
		width: 100%;
	}

	/* Toast - using global styles */

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@keyframes shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}

	/* Responsive */
	@media (max-width: 640px) {
		.page-container {
			padding: var(--space-4);
		}

		.page-header {
			flex-direction: column;
		}

		.sync-controls {
			width: 100%;
			justify-content: space-between;
		}

		.card-grid {
			grid-template-columns: 1fr;
		}

		.card-grid-2 {
			max-width: none;
		}
	}
</style>
