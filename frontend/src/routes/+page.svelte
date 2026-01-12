<script lang="ts">
	import { onMount } from 'svelte';
	import { auth } from '$lib/stores';

	let message = $state('Loading...');
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

	let syncStatus = $state<SyncStatus | null>(null);
	let syncLoading = $state(false);
	let toastMessage = $state<string | null>(null);
	let toastType = $state<'success' | 'error'>('success');

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

	onMount(async () => {
		try {
			const token = localStorage.getItem('access_token');
			const response = await fetch('/api/hello', {
				headers: token ? { Authorization: `Bearer ${token}` } : {}
			});
			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}
			const data = await response.json();
			message = data.message;

			// Fetch sync status
			await fetchSyncStatus();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch';
			message = '';
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
		<p class="welcome-text">Welcome back, {$auth.user.email}</p>
	{/if}
	{#if error}
		<div class="error">
			<p>Error: {error}</p>
			<p class="hint">Make sure the backend is running on port 8000</p>
		</div>
	{:else}
		<h1 class="hello-message">{message}</h1>
		<p class="subtitle">Frontend successfully connected to Backend</p>

		{#if syncStatus}
			<div class="sync-status">
				{#if syncStatus.last_synced}
					<p class="sync-time">
						Last synced: {formatDate(syncStatus.last_synced)}
					</p>
					{#if syncStatus.media_items_count !== null || syncStatus.requests_count !== null}
						<p class="sync-counts">
							{syncStatus.media_items_count ?? 0} media items, {syncStatus.requests_count ?? 0} requests
						</p>
					{/if}
				{:else}
					<p class="sync-time">Never synced</p>
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
		{/if}
	{/if}
</div>

<style>
	.dashboard-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		text-align: center;
	}

	.welcome-text {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.hello-message {
		font-size: 3rem;
		font-weight: 700;
		color: var(--accent);
		margin-bottom: 1rem;
	}

	.subtitle {
		color: var(--text-secondary);
		font-size: 1.125rem;
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

	.sync-status {
		margin-top: 2rem;
		padding: 1rem 1.5rem;
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border-color);
	}

	.sync-time {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.sync-counts {
		color: var(--text-muted);
		font-size: 0.75rem;
		margin-top: 0.25rem;
	}

	.refresh-button {
		margin-top: 1rem;
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

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

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
</style>
