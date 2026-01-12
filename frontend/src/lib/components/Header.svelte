<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/stores';

	function handleLogout() {
		auth.logout();
		window.location.href = '/login';
	}

	// Determine current route for active state
	let currentPath = $derived($page.url.pathname);
</script>

<header class="header">
	<div class="header-container">
		<a href="/" class="logo">
			<span class="logo-text">Media Janitor</span>
		</a>

		{#if $auth.isAuthenticated && $auth.user}
			<nav class="nav">
				<a
					href="/"
					class="nav-link"
					class:active={currentPath === '/'}
				>
					Dashboard
				</a>
				<a
					href="/content/old-unwatched"
					class="nav-link"
					class:active={currentPath === '/content/old-unwatched'}
				>
					Old Content
				</a>
				<a
					href="/settings"
					class="nav-link"
					class:active={currentPath === '/settings'}
				>
					Settings
				</a>
				<button onclick={handleLogout} class="logout-btn">
					Log out
				</button>
			</nav>
		{/if}
	</div>
</header>

<style>
	.header {
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.header-container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 0 1rem;
		height: 60px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.logo {
		text-decoration: none;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.logo-text {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--accent);
	}

	.nav {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.nav-link {
		padding: 0.5rem 1rem;
		color: var(--text-secondary);
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		border-radius: 0.375rem;
		transition: all 0.2s;
	}

	.nav-link:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.nav-link.active {
		color: var(--accent);
		background: rgba(0, 102, 204, 0.1);
	}

	@media (prefers-color-scheme: dark) {
		.nav-link.active {
			background: rgba(77, 166, 255, 0.1);
		}
	}

	.logout-btn {
		padding: 0.5rem 1rem;
		background: transparent;
		color: var(--danger);
		border: 1px solid var(--danger);
		border-radius: 0.375rem;
		cursor: pointer;
		font-size: 0.875rem;
		font-weight: 500;
		transition: all 0.2s;
		margin-left: 0.5rem;
	}

	.logout-btn:hover {
		background: var(--danger);
		color: white;
	}
</style>
