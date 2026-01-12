<script lang="ts">
	import { onMount } from 'svelte';

	let message = $state('Loading...');
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			const response = await fetch('/api/hello');
			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}
			const data = await response.json();
			message = data.message;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch';
			message = '';
		}
	});
</script>

<svelte:head>
	<title>Plex Dashboard</title>
</svelte:head>

<div class="hello-container">
	{#if error}
		<div class="error">
			<p>Error: {error}</p>
			<p class="hint">Make sure the backend is running on port 8000</p>
		</div>
	{:else}
		<h1 class="hello-message">{message}</h1>
		<p class="subtitle">Frontend successfully connected to Backend</p>
	{/if}
</div>

<style>
	.hello-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		text-align: center;
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
</style>
