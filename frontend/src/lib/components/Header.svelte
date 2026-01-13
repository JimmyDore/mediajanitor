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
					href="/issues"
					class="nav-link"
					class:active={currentPath === '/issues' || currentPath.startsWith('/issues/')}
				>
					Issues
				</a>
				<a
					href="/whitelist"
					class="nav-link"
					class:active={currentPath === '/whitelist'}
				>
					Whitelist
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
		padding: 0 var(--space-4);
		height: 56px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.logo {
		text-decoration: none;
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.logo-text {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		letter-spacing: -0.02em;
	}

	.nav {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.nav-link {
		padding: var(--space-2) var(--space-3);
		color: var(--text-secondary);
		text-decoration: none;
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-medium);
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}

	.nav-link:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.nav-link.active {
		color: var(--accent);
		background: var(--accent-light);
	}

	.logout-btn {
		margin-left: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-medium);
		transition: all var(--transition-fast);
	}

	.logout-btn:hover {
		color: var(--danger);
		border-color: var(--danger);
		background: var(--danger-light);
	}

	@media (max-width: 640px) {
		.header-container {
			padding: 0 var(--space-3);
		}

		.nav-link {
			padding: var(--space-2);
			font-size: var(--font-size-sm);
		}

		.logout-btn {
			padding: var(--space-2);
			font-size: var(--font-size-sm);
		}
	}
</style>
