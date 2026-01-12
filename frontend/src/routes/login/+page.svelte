<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores';

	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let isLoading = $state(false);
	let mounted = $state(false);

	onMount(() => {
		mounted = true;
		// If already authenticated, redirect to home
		auth.subscribe((authState) => {
			if (authState.isAuthenticated && !authState.isLoading) {
				goto('/');
			}
		})();
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		isLoading = true;

		try {
			const response = await fetch('/api/auth/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password })
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Login failed');
			}

			const data = await response.json();
			// Store token in localStorage
			localStorage.setItem('access_token', data.access_token);

			// Update auth state and redirect
			await auth.checkAuth();
			goto('/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Login failed';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Log In - Plex Dashboard</title>
</svelte:head>

<div class="login-container">
	<h1>Log In</h1>

	<form onsubmit={handleSubmit} class="login-form">
		{#if error}
			<div class="error-message" role="alert">
				{error}
			</div>
		{/if}

		<div class="form-group">
			<label for="email">Email</label>
			<input
				type="email"
				id="email"
				bind:value={email}
				required
				autocomplete="email"
				placeholder="you@example.com"
			/>
		</div>

		<div class="form-group">
			<label for="password">Password</label>
			<input
				type="password"
				id="password"
				bind:value={password}
				required
				autocomplete="current-password"
				placeholder="Your password"
			/>
		</div>

		<button type="submit" disabled={isLoading} class="submit-button">
			{#if isLoading}
				Logging in...
			{:else}
				Log In
			{/if}
		</button>
	</form>

	<p class="register-link">
		Don't have an account? <a href="/register">Sign up</a>
	</p>
</div>

<style>
	.login-container {
		max-width: 400px;
		margin: 0 auto;
		padding: 2rem;
	}

	h1 {
		text-align: center;
		margin-bottom: 2rem;
		color: var(--accent);
	}

	.login-form {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	label {
		font-weight: 500;
		color: var(--text);
	}

	input {
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		font-size: 1rem;
		background: var(--bg-secondary);
		color: var(--text);
		transition: border-color 0.2s;
	}

	input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.error-message {
		padding: 1rem;
		background: var(--bg-secondary);
		border: 1px solid var(--danger);
		border-radius: 0.5rem;
		color: var(--danger);
	}

	.submit-button {
		padding: 0.875rem 1.5rem;
		background: var(--accent);
		color: white;
		border: none;
		border-radius: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.submit-button:hover:not(:disabled) {
		opacity: 0.9;
	}

	.submit-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.register-link {
		text-align: center;
		margin-top: 1.5rem;
		color: var(--text-secondary);
	}

	.register-link a {
		color: var(--accent);
		text-decoration: none;
	}

	.register-link a:hover {
		text-decoration: underline;
	}
</style>
