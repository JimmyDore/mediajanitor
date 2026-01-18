<script lang="ts">
	import { page } from '$app/stores';

	let { children } = $props();

	const navItems = [
		{ href: '/settings/connections', label: 'Connections', icon: 'plug' },
		{ href: '/settings/thresholds', label: 'Thresholds', icon: 'sliders' },
		{ href: '/settings/users', label: 'Users', icon: 'users' },
		{ href: '/settings/display', label: 'Display', icon: 'monitor' },
		{ href: '/settings/security', label: 'Security', icon: 'lock' }
	];

	// Get current section name for breadcrumb
	let currentSection = $derived(() => {
		const path = $page.url.pathname;
		const item = navItems.find((item) => path.startsWith(item.href));
		return item?.label || 'Settings';
	});
</script>

<svelte:head>
	<title>{currentSection()} - Settings - Media Janitor</title>
</svelte:head>

<div class="settings-layout">
	<!-- Breadcrumb -->
	<nav class="breadcrumb" aria-label="Breadcrumb">
		<ol>
			<li>
				<a href="/">Dashboard</a>
				<span class="separator" aria-hidden="true">/</span>
			</li>
			<li>
				<a href="/settings/connections">Settings</a>
				<span class="separator" aria-hidden="true">/</span>
			</li>
			<li aria-current="page">{currentSection()}</li>
		</ol>
	</nav>

	<div class="settings-content">
		<!-- Sidebar Navigation -->
		<aside class="settings-sidebar" role="navigation" aria-label="Settings navigation">
			<nav>
				<ul class="nav-list">
					{#each navItems as item}
						<li>
							<a
								href={item.href}
								class="nav-item"
								class:active={$page.url.pathname.startsWith(item.href)}
								aria-current={$page.url.pathname.startsWith(item.href) ? 'page' : undefined}
							>
								{#if item.icon === 'plug'}
									<svg
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										aria-hidden="true"
									>
										<path d="M12 22v-5" />
										<path d="M9 8V2" />
										<path d="M15 8V2" />
										<path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" />
									</svg>
								{:else if item.icon === 'sliders'}
									<svg
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										aria-hidden="true"
									>
										<line x1="4" y1="21" x2="4" y2="14" />
										<line x1="4" y1="10" x2="4" y2="3" />
										<line x1="12" y1="21" x2="12" y2="12" />
										<line x1="12" y1="8" x2="12" y2="3" />
										<line x1="20" y1="21" x2="20" y2="16" />
										<line x1="20" y1="12" x2="20" y2="3" />
										<line x1="1" y1="14" x2="7" y2="14" />
										<line x1="9" y1="8" x2="15" y2="8" />
										<line x1="17" y1="16" x2="23" y2="16" />
									</svg>
								{:else if item.icon === 'users'}
									<svg
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										aria-hidden="true"
									>
										<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
										<circle cx="9" cy="7" r="4" />
										<path d="M23 21v-2a4 4 0 0 0-3-3.87" />
										<path d="M16 3.13a4 4 0 0 1 0 7.75" />
									</svg>
								{:else if item.icon === 'monitor'}
									<svg
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										aria-hidden="true"
									>
										<rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
										<line x1="8" y1="21" x2="16" y2="21" />
										<line x1="12" y1="17" x2="12" y2="21" />
									</svg>
								{:else if item.icon === 'lock'}
									<svg
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										aria-hidden="true"
									>
										<rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
										<path d="M7 11V7a5 5 0 0 1 10 0v4" />
									</svg>
								{/if}
								<span>{item.label}</span>
							</a>
						</li>
					{/each}
				</ul>
			</nav>
		</aside>

		<!-- Main Content -->
		<main class="settings-main">
			{@render children()}
		</main>
	</div>
</div>

<style>
	.settings-layout {
		max-width: 1000px;
		margin: 0 auto;
		padding: var(--space-6);
	}

	/* Breadcrumb */
	.breadcrumb {
		margin-bottom: var(--space-6);
	}

	.breadcrumb ol {
		display: flex;
		align-items: center;
		list-style: none;
		padding: 0;
		margin: 0;
		font-size: var(--font-size-sm);
	}

	.breadcrumb li {
		display: flex;
		align-items: center;
	}

	.breadcrumb a {
		color: var(--text-secondary);
		text-decoration: none;
		transition: color var(--transition-fast);
	}

	.breadcrumb a:hover {
		color: var(--text-primary);
	}

	.breadcrumb .separator {
		margin: 0 var(--space-2);
		color: var(--text-muted);
	}

	.breadcrumb li[aria-current='page'] {
		color: var(--text-primary);
		font-weight: var(--font-weight-medium);
	}

	/* Settings Content Layout */
	.settings-content {
		display: flex;
		gap: var(--space-8);
	}

	/* Sidebar */
	.settings-sidebar {
		flex-shrink: 0;
		width: 200px;
	}

	.nav-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-4);
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		text-decoration: none;
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}

	.nav-item:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.nav-item.active {
		background: var(--accent-light);
		color: var(--accent);
	}

	.nav-item svg {
		flex-shrink: 0;
	}

	/* Main Content */
	.settings-main {
		flex: 1;
		min-width: 0;
	}

	/* Mobile: Horizontal tabs */
	@media (max-width: 768px) {
		.settings-layout {
			padding: var(--space-4);
		}

		.settings-content {
			flex-direction: column;
			gap: var(--space-4);
		}

		.settings-sidebar {
			width: 100%;
		}

		.nav-list {
			flex-direction: row;
			overflow-x: auto;
			-webkit-overflow-scrolling: touch;
			gap: var(--space-2);
			padding-bottom: var(--space-2);
		}

		.nav-item {
			flex-shrink: 0;
			padding: var(--space-2) var(--space-3);
			white-space: nowrap;
		}

		/* On mobile, hide icon text, show only icon */
		.nav-item span {
			display: inline;
		}

		/* Add border under tabs on mobile */
		.settings-sidebar {
			border-bottom: 1px solid var(--border);
			padding-bottom: var(--space-2);
		}
	}

	/* Very small screens */
	@media (max-width: 480px) {
		.breadcrumb {
			font-size: var(--font-size-xs);
		}

		.nav-item {
			padding: var(--space-2);
		}

		.nav-item svg {
			width: 16px;
			height: 16px;
		}
	}
</style>
