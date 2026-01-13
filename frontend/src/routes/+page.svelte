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

<div class="dashboard-container">
	{#if $auth.isAuthenticated && $auth.user}
		<div class="dashboard-header">
			<div class="header-text">
				<h1>Dashboard</h1>
				<p class="welcome-text">Welcome back, {$auth.user.email}</p>
			</div>
			<div class="sync-controls">
				{#if syncStatus}
					<div class="sync-info">
						{#if syncStatus.last_synced}
							<span class="sync-time">Last synced: {formatDate(syncStatus.last_synced)}</span>
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
		<div class="error">
			<p>Error: {error}</p>
			<p class="hint">Make sure the backend is running on port 8000</p>
		</div>
	{:else}
		<section class="issues-section">
			<h2 class="section-title">Issues</h2>
			<div class="summary-cards">
				<!-- Old Content Card -->
				<button
					class="summary-card"
					onclick={() => navigateToIssues('old')}
					aria-label="View old content"
				>
					{#if summaryLoading}
						<div class="card-skeleton">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon old">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
								<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/>
							</svg>
						</div>
						<div class="card-content">
							<span class="card-label">Old Content</span>
							<span class="card-count">{contentSummary?.old_content.count ?? 0}</span>
							{#if contentSummary && contentSummary.old_content.count > 0}
								<span class="card-size">{contentSummary.old_content.total_size_formatted}</span>
							{/if}
						</div>
					{/if}
				</button>

				<!-- Large Movies Card -->
				<button
					class="summary-card"
					onclick={() => navigateToIssues('large')}
					aria-label="View large movies"
				>
					{#if summaryLoading}
						<div class="card-skeleton">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon large">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
								<path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12zM6 10h2v2H6v-2zm0 4h8v2H6v-2zm10 0h2v2h-2v-2zm-6-4h8v2h-8v-2z"/>
							</svg>
						</div>
						<div class="card-content">
							<span class="card-label">Large Movies</span>
							<span class="card-count">{contentSummary?.large_movies.count ?? 0}</span>
							{#if contentSummary && contentSummary.large_movies.count > 0}
								<span class="card-size">{contentSummary.large_movies.total_size_formatted}</span>
							{/if}
						</div>
					{/if}
				</button>

				<!-- Language Issues Card -->
				<button
					class="summary-card"
					onclick={() => navigateToIssues('language')}
					aria-label="View language issues"
				>
					{#if summaryLoading}
						<div class="card-skeleton">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon language">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
								<path d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
							</svg>
						</div>
						<div class="card-content">
							<span class="card-label">Language Issues</span>
							<span class="card-count">{contentSummary?.language_issues.count ?? 0}</span>
						</div>
					{/if}
				</button>

				<!-- Unavailable Requests Card -->
				<button
					class="summary-card"
					onclick={() => navigateToIssues('requests')}
					aria-label="View unavailable requests"
				>
					{#if summaryLoading}
						<div class="card-skeleton">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon requests">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
								<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
							</svg>
						</div>
						<div class="card-content">
							<span class="card-label">Unavailable Requests</span>
							<span class="card-count">{contentSummary?.unavailable_requests.count ?? 0}</span>
						</div>
					{/if}
				</button>
			</div>
		</section>

		<!-- Info Section -->
		<section class="info-section">
			<h2 class="section-title">Info</h2>
			<div class="info-cards">
				<!-- Recently Available Card -->
				<button
					class="info-card"
					onclick={() => navigateToInfo('recent')}
					aria-label="View recently available content"
				>
					{#if summaryLoading}
						<div class="card-skeleton">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon recent">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
								<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
							</svg>
						</div>
						<div class="card-content">
							<span class="card-label">Recently Available</span>
							<span class="card-count">{contentSummary?.recently_available?.count ?? 0}</span>
							<span class="card-subtitle">Past 7 days</span>
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
						<div class="card-skeleton">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line long"></div>
						</div>
					{:else}
						<div class="card-icon airing">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
								<path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 10l7 4-7 4z"/>
							</svg>
						</div>
						<div class="card-content">
							<span class="card-label">Currently Airing</span>
							<span class="card-count">{contentSummary?.currently_airing?.count ?? 0}</span>
							<span class="card-subtitle">In-progress series</span>
						</div>
					{/if}
				</button>
			</div>
		</section>
	{/if}
</div>

<style>
	.dashboard-container {
		padding: 1.5rem;
		max-width: 1200px;
		margin: 0 auto;
	}

	.dashboard-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 2rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.header-text h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
	}

	.welcome-text {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.sync-controls {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.sync-info {
		text-align: right;
	}

	.sync-time {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	.refresh-button {
		padding: 0.5rem 1rem;
		background: var(--accent);
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		transition: background-color 0.2s ease;
	}

	.refresh-button:hover:not(:disabled) {
		background: var(--accent-hover, #4f46e5);
	}

	.refresh-button:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.error {
		padding: 2rem;
		background: var(--bg-secondary);
		border: 1px solid var(--danger);
		border-radius: 0.75rem;
	}

	.error p {
		color: var(--danger);
		margin-bottom: 0.5rem;
	}

	.error .hint {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	/* Issues Section */
	.issues-section {
		margin-bottom: 2rem;
	}

	/* Info Section - distinct from issues */
	.info-section {
		margin-bottom: 2rem;
	}

	.info-cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
		max-width: 520px; /* Limit to 2 cards */
	}

	.info-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1.25rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-left: 4px solid #10b981; /* Green accent border for info cards */
		border-radius: 0.75rem;
		cursor: pointer;
		transition: all 0.2s ease;
		text-align: left;
		width: 100%;
	}

	.info-card:hover {
		border-color: #10b981;
		background: var(--bg-hover);
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.card-subtitle {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin-top: 0.125rem;
	}

	.section-title {
		font-size: 1.125rem;
		font-weight: 600;
		margin-bottom: 1rem;
		color: var(--text-primary);
	}

	.summary-cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.summary-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1.25rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 0.75rem;
		cursor: pointer;
		transition: all 0.2s ease;
		text-align: left;
		width: 100%;
	}

	.summary-card:hover {
		border-color: var(--accent);
		background: var(--bg-hover);
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.card-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		border-radius: 0.5rem;
		flex-shrink: 0;
	}

	.card-icon.old {
		background: rgba(239, 68, 68, 0.1);
		color: #ef4444;
	}

	.card-icon.large {
		background: rgba(245, 158, 11, 0.1);
		color: #f59e0b;
	}

	.card-icon.language {
		background: rgba(59, 130, 246, 0.1);
		color: #3b82f6;
	}

	.card-icon.requests {
		background: rgba(139, 92, 246, 0.1);
		color: #8b5cf6;
	}

	/* Info card icons - green/teal theme to distinguish from issues */
	.card-icon.recent {
		background: rgba(16, 185, 129, 0.1);
		color: #10b981;
	}

	.card-icon.airing {
		background: rgba(20, 184, 166, 0.1);
		color: #14b8a6;
	}

	.card-content {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.card-label {
		font-size: 0.875rem;
		color: var(--text-secondary);
		font-weight: 500;
	}

	.card-count {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1.2;
	}

	.card-size {
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	/* Loading skeleton */
	.card-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		width: 100%;
	}

	.skeleton-line {
		height: 1rem;
		background: linear-gradient(90deg, var(--bg-hover) 25%, var(--bg-secondary) 50%, var(--bg-hover) 75%);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
		border-radius: 0.25rem;
	}

	.skeleton-line.short {
		width: 60%;
	}

	.skeleton-line.long {
		width: 100%;
	}

	/* Toast notifications */
	.toast {
		position: fixed;
		top: 1rem;
		right: 1rem;
		padding: 1rem 1.5rem;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		z-index: 1000;
		animation: slideIn 0.3s ease;
	}

	.toast-success {
		background: var(--success, #22c55e);
		color: white;
	}

	.toast-error {
		background: var(--danger, #ef4444);
		color: white;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
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
		.dashboard-header {
			flex-direction: column;
		}

		.sync-controls {
			width: 100%;
			justify-content: space-between;
		}

		.summary-cards {
			grid-template-columns: 1fr;
		}
	}
</style>
