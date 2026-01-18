<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/stores';

	let showUserMenu = $state(false);
	let mobileMenuOpen = $state(false);

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

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
	}

	// Determine current route for active state
	let currentPath = $derived($page.url.pathname);
</script>

<svelte:window onclick={closeUserMenu} />

<!-- Mobile hamburger button -->
<button class="mobile-menu-btn" onclick={toggleMobileMenu} aria-label="Toggle menu">
	<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
		{#if mobileMenuOpen}
			<line x1="18" y1="6" x2="6" y2="18"/>
			<line x1="6" y1="6" x2="18" y2="18"/>
		{:else}
			<line x1="3" y1="12" x2="21" y2="12"/>
			<line x1="3" y1="6" x2="21" y2="6"/>
			<line x1="3" y1="18" x2="21" y2="18"/>
		{/if}
	</svg>
</button>

<!-- Mobile backdrop -->
{#if mobileMenuOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="mobile-backdrop" onclick={closeMobileMenu}></div>
{/if}

<aside class="sidebar" class:open={mobileMenuOpen}>
	<!-- Logo -->
	<div class="sidebar-header">
		<a href="/" class="logo" onclick={closeMobileMenu}>
			<span class="logo-text">Media Janitor</span>
		</a>
	</div>

	<!-- Navigation -->
	{#if $auth.isAuthenticated && $auth.user}
		<nav class="sidebar-nav">
			<a
				href="/"
				class="nav-item"
				class:active={currentPath === '/'}
				onclick={closeMobileMenu}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="3" y="3" width="7" height="7"/>
					<rect x="14" y="3" width="7" height="7"/>
					<rect x="14" y="14" width="7" height="7"/>
					<rect x="3" y="14" width="7" height="7"/>
				</svg>
				Dashboard
			</a>
			<a
				href="/issues"
				class="nav-item"
				class:active={currentPath === '/issues' || currentPath.startsWith('/issues/')}
				onclick={closeMobileMenu}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="12" cy="12" r="10"/>
					<line x1="12" y1="8" x2="12" y2="12"/>
					<line x1="12" y1="16" x2="12.01" y2="16"/>
				</svg>
				Issues
			</a>
			<a
				href="/library"
				class="nav-item"
				class:active={currentPath === '/library'}
				onclick={closeMobileMenu}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
					<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
				</svg>
				Library
			</a>
			<a
				href="/whitelist"
				class="nav-item"
				class:active={currentPath === '/whitelist'}
				onclick={closeMobileMenu}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
				</svg>
				Whitelist
			</a>
			<a
				href="/settings"
				class="nav-item"
				class:active={currentPath === '/settings'}
				onclick={closeMobileMenu}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="12" cy="12" r="3"/>
					<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
				</svg>
				Settings
			</a>
			<a
				href="/help"
				class="nav-item"
				class:active={currentPath === '/help'}
				onclick={closeMobileMenu}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="12" cy="12" r="10"/>
					<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
					<line x1="12" y1="17" x2="12.01" y2="17"/>
				</svg>
				Help
			</a>
		</nav>

		<!-- User section -->
		<div class="sidebar-footer">
			<div class="user-section">
				<button
					class="user-btn"
					onclick={(e) => { e.stopPropagation(); toggleUserMenu(); }}
					aria-expanded={showUserMenu}
					aria-haspopup="true"
				>
					<span class="user-avatar">{$auth.user.email.charAt(0).toUpperCase()}</span>
					<span class="user-email">{$auth.user.email}</span>
					<svg class="chevron" class:open={showUserMenu} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="6 9 12 15 18 9"/>
					</svg>
				</button>

				{#if showUserMenu}
					<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
					<div class="user-dropdown" onclick={(e) => e.stopPropagation()}>
						<button onclick={handleLogout} class="dropdown-item dropdown-item-danger">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
								<polyline points="16 17 21 12 16 7"/>
								<line x1="21" y1="12" x2="9" y2="12"/>
							</svg>
							Sign out
						</button>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</aside>

<style>
	/* Mobile menu button */
	.mobile-menu-btn {
		display: none;
		position: fixed;
		top: var(--space-4);
		left: var(--space-4);
		z-index: 300;
		width: 40px;
		height: 40px;
		align-items: center;
		justify-content: center;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		color: var(--text-primary);
	}

	.mobile-backdrop {
		display: none;
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 150;
	}

	/* Sidebar */
	.sidebar {
		position: fixed;
		left: 0;
		top: 0;
		bottom: 0;
		width: var(--sidebar-width);
		background: var(--bg-secondary);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		z-index: 200;
	}

	.sidebar-header {
		padding: var(--space-5) var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.logo {
		text-decoration: none;
		display: flex;
		align-items: center;
	}

	.logo-text {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-bold);
		color: var(--text-primary);
		letter-spacing: -0.02em;
	}

	/* Navigation */
	.sidebar-nav {
		flex: 1;
		padding: var(--space-3);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		overflow-y: auto;
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-3);
		color: var(--text-secondary);
		text-decoration: none;
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-medium);
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}

	.nav-item:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.nav-item.active {
		color: var(--accent);
		background: var(--accent-light);
	}

	.nav-item svg {
		flex-shrink: 0;
	}

	/* Footer / User section */
	.sidebar-footer {
		padding: var(--space-3);
		border-top: 1px solid var(--border);
	}

	.user-section {
		position: relative;
	}

	.user-btn {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		width: 100%;
		padding: var(--space-3);
		background: transparent;
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
		text-align: left;
	}

	.user-btn:hover {
		background: var(--bg-hover);
	}

	.user-avatar {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--accent-light);
		color: var(--accent);
		border-radius: 50%;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-semibold);
		flex-shrink: 0;
	}

	.user-email {
		flex: 1;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.chevron {
		color: var(--text-muted);
		transition: transform var(--transition-fast);
		flex-shrink: 0;
	}

	.chevron.open {
		transform: rotate(180deg);
	}

	.user-dropdown {
		position: absolute;
		bottom: calc(100% + var(--space-2));
		left: 0;
		right: 0;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		overflow: hidden;
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

	/* Mobile responsive */
	@media (max-width: 768px) {
		.mobile-menu-btn {
			display: flex;
		}

		.mobile-backdrop {
			display: block;
		}

		.sidebar {
			transform: translateX(-100%);
			visibility: hidden;
			transition: transform var(--transition-base), visibility var(--transition-base);
		}

		.sidebar.open {
			transform: translateX(0);
			visibility: visible;
		}
	}
</style>
