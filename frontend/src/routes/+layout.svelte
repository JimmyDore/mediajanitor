<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<div class="app">
	<nav class="sidebar">
		<div class="logo">
			<h1>Plex Dashboard</h1>
		</div>
		<ul class="nav-links">
			<li><a href="/">Dashboard</a></li>
			<li><a href="/content">Old/Unwatched</a></li>
			<li><a href="/language">Language Issues</a></li>
			<li><a href="/requests">Requests</a></li>
			<li><a href="/settings">Settings</a></li>
		</ul>
	</nav>
	<main class="content">
		{@render children()}
	</main>
</div>

<style>
	.app {
		display: flex;
		min-height: 100vh;
	}

	.sidebar {
		width: 240px;
		background: var(--bg-secondary);
		border-right: 1px solid var(--border);
		padding: 1rem;
	}

	.logo h1 {
		font-size: 1.25rem;
		margin-bottom: 2rem;
		color: var(--text-primary);
	}

	.nav-links {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.nav-links li {
		margin-bottom: 0.5rem;
	}

	.nav-links a {
		display: block;
		padding: 0.75rem 1rem;
		color: var(--text-secondary);
		text-decoration: none;
		border-radius: 0.5rem;
		transition: all 0.2s;
	}

	.nav-links a:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.content {
		flex: 1;
		padding: 2rem;
		overflow-y: auto;
	}
</style>
