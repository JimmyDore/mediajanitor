<script lang="ts">
	import { onMount } from 'svelte';

	let stats = $state({
		oldUnwatched: 0,
		largeMovies: 0,
		languageIssues: 0,
		unavailableRequests: 0,
		loading: true,
		error: null as string | null
	});

	onMount(async () => {
		// TODO: Fetch actual stats from API
		// For now, show placeholder
		stats.loading = false;
	});
</script>

<svelte:head>
	<title>Dashboard - Plex Dashboard</title>
</svelte:head>

<div class="dashboard">
	<header class="flex justify-between items-center mb-4">
		<h1>Dashboard</h1>
		<button class="btn btn-primary" disabled={stats.loading}>
			Refresh
		</button>
	</header>

	{#if stats.loading}
		<p class="text-muted">Loading...</p>
	{:else if stats.error}
		<div class="card" style="border-color: var(--danger);">
			<p style="color: var(--danger);">{stats.error}</p>
		</div>
	{:else}
		<div class="stats-grid">
			<a href="/content" class="card stat-card">
				<h3 class="stat-value">{stats.oldUnwatched}</h3>
				<p class="stat-label">Old/Unwatched</p>
				<p class="text-sm text-muted">Content to review</p>
			</a>

			<a href="/content?filter=large" class="card stat-card">
				<h3 class="stat-value">{stats.largeMovies}</h3>
				<p class="stat-label">Large Movies</p>
				<p class="text-sm text-muted">&gt;13GB files</p>
			</a>

			<a href="/language" class="card stat-card">
				<h3 class="stat-value">{stats.languageIssues}</h3>
				<p class="stat-label">Language Issues</p>
				<p class="text-sm text-muted">Missing audio/subs</p>
			</a>

			<a href="/requests" class="card stat-card">
				<h3 class="stat-value">{stats.unavailableRequests}</h3>
				<p class="stat-label">Unavailable</p>
				<p class="text-sm text-muted">Pending requests</p>
			</a>
		</div>

		<section class="mt-8">
			<h2 class="mb-4">Quick Actions</h2>
			<div class="flex gap-4">
				<a href="/content" class="btn btn-ghost">Review content</a>
				<a href="/settings" class="btn btn-ghost">Settings</a>
			</div>
		</section>
	{/if}
</div>

<style>
	.dashboard {
		max-width: 1200px;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.stat-card {
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.stat-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.stat-value {
		font-size: 2.5rem;
		font-weight: 700;
		color: var(--accent);
		margin-bottom: 0.25rem;
	}

	.stat-label {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
	}

	.mt-8 {
		margin-top: 2rem;
	}
</style>
