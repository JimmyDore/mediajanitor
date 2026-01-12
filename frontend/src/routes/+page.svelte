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

	let syncStatus = $state<SyncStatus | null>(null);
	let syncLoading = $state(false);

	function formatDate(isoString: string): string {
		const date = new Date(isoString);
		return date.toLocaleString();
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
</style>
