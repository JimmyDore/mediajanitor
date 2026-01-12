<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores';

	let { children } = $props();

	// Public routes that don't require authentication
	const publicRoutes = ['/login', '/register'];

	onMount(async () => {
		// Check if user is authenticated
		const isAuthenticated = await auth.checkAuth();

		// Subscribe to page changes to handle route protection
		page.subscribe(($page) => {
			const currentPath = $page.url.pathname;
			const isPublicRoute = publicRoutes.includes(currentPath);

			// Use the auth store's current state
			auth.subscribe((authState) => {
				if (!authState.isLoading) {
					if (!authState.isAuthenticated && !isPublicRoute) {
						goto('/login');
					}
				}
			})();
		});
	});
</script>

{#if $auth.isLoading}
	<div class="app">
		<main class="content">
			<div class="loading">Loading...</div>
		</main>
	</div>
{:else}
	<div class="app">
		<main class="content">
			{@render children()}
		</main>
	</div>
{/if}

<style>
	.app {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.content {
		width: 100%;
		max-width: 800px;
		padding: 2rem;
	}

	.loading {
		text-align: center;
		font-size: 1.25rem;
		color: var(--text-secondary);
	}
</style>
