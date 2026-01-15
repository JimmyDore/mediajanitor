<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { auth, theme, toasts, onSessionExpired } from '$lib/stores';
	import Sidebar from '$lib/components/Sidebar.svelte';

	let { children } = $props();

	// Public routes that don't require authentication
	const publicRoutes = ['/', '/login', '/register'];

	// Check if current route is public
	let isPublicRoute = $derived(publicRoutes.includes($page.url.pathname));

	// Helper to redirect to login with optional redirect path
	function redirectToLogin(redirectPath?: string) {
		const loginUrl = redirectPath ? `/login?redirect=${encodeURIComponent(redirectPath)}` : '/login';
		goto(loginUrl);
	}

	onMount(async () => {
		// Register session expiration handler
		onSessionExpired((currentPath) => {
			toasts.add('Session expired, please log in again', 'error');
			redirectToLogin(currentPath);
		});

		// Check if user is authenticated
		const isAuthenticated = await auth.checkAuth();

		// Load theme preference if authenticated
		if (isAuthenticated) {
			await theme.loadFromApi();
		}

		// Subscribe to page changes to handle route protection
		page.subscribe(($page) => {
			const currentPath = $page.url.pathname;
			const isPublicRoute = publicRoutes.includes(currentPath);

			// Use the auth store's current state
			auth.subscribe((authState) => {
				if (!authState.isLoading) {
					if (!authState.isAuthenticated && !isPublicRoute) {
						redirectToLogin(currentPath);
					}
				}
			})();
		});
	});
</script>

{#if $auth.isLoading && !isPublicRoute}
	<!-- Only show loading for protected routes -->
	<div class="app">
		<main class="content content-centered">
			<div class="loading">Loading...</div>
		</main>
	</div>
{:else}
	<div class="app" class:with-sidebar={$auth.isAuthenticated}>
		{#if $auth.isAuthenticated}
			<Sidebar />
		{/if}
		<main class="content" class:content-centered={!$auth.isAuthenticated}>
			{@render children()}
		</main>
	</div>
{/if}

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.app.with-sidebar {
		margin-left: 220px;
	}

	.content {
		width: 100%;
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
		flex: 1;
	}

	.content-centered {
		max-width: none;
		padding: 0;
	}

	.loading {
		text-align: center;
		font-size: 1.25rem;
		color: var(--text-secondary);
	}

	/* Mobile responsive - remove sidebar margin */
	@media (max-width: 768px) {
		.app.with-sidebar {
			margin-left: 0;
			padding-top: 60px; /* Space for hamburger button */
		}
	}
</style>
