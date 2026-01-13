<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/stores';

	let showUserMenu = $state(false);

	function handleLogout() {
		auth.logout();
		window.location.href = '/login';
	}

	function toggleUserMenu() {
		showUserMenu = !showUserMenu;
	}

	function closeUserMenu() {
		showUserMenu = false;
	}

	// Determine current route for active state
	let currentPath = $derived($page.url.pathname);
</script>

<svelte:window onclick={closeUserMenu} />

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

				<div class="user-menu-container">
					<button
						class="user-btn"
						onclick={(e) => { e.stopPropagation(); toggleUserMenu(); }}
						aria-expanded={showUserMenu}
						aria-haspopup="true"
					>
						<span class="user-avatar">{$auth.user.email.charAt(0).toUpperCase()}</span>
					</button>

					{#if showUserMenu}
						<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
						<div class="user-dropdown" onclick={(e) => e.stopPropagation()}>
							<div class="user-info">
								<span class="user-email">{$auth.user.email}</span>
							</div>
							<div class="dropdown-divider"></div>
							<button onclick={handleLogout} class="dropdown-item dropdown-item-danger">
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
									<polyline points="16 17 21 12 16 7"/>
									<line x1="21" y1="12" x2="9" y2="12"/>
								</svg>
								Sign out
							</button>
						</div>
					{/if}
				</div>
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

	/* User menu */
	.user-menu-container {
		position: relative;
		margin-left: var(--space-2);
	}

	.user-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		padding: 0;
		background: var(--bg-hover);
		border: 1px solid var(--border);
		border-radius: 50%;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.user-btn:hover {
		border-color: var(--text-muted);
	}

	.user-avatar {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-semibold);
		color: var(--text-secondary);
	}

	.user-dropdown {
		position: absolute;
		top: calc(100% + var(--space-2));
		right: 0;
		min-width: 200px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		z-index: 200;
		overflow: hidden;
	}

	.user-info {
		padding: var(--space-3) var(--space-4);
	}

	.user-email {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		word-break: break-all;
	}

	.dropdown-divider {
		height: 1px;
		background: var(--border);
	}

	.dropdown-item {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-3) var(--space-4);
		background: transparent;
		border: none;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all var(--transition-fast);
		text-align: left;
	}

	.dropdown-item:hover {
		background: var(--bg-hover);
	}

	.dropdown-item-danger {
		color: var(--danger);
	}

	.dropdown-item-danger:hover {
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
	}
</style>
