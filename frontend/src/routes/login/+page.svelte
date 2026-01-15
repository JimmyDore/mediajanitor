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
				body: JSON.stringify({ email, password }),
				credentials: 'include' // Include cookies for refresh token
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Login failed');
			}

			const data = await response.json();
			// Store token in memory (more secure than localStorage)
			// Refresh token is stored in httpOnly cookie by the server
			auth.setToken(data.access_token, data.expires_in);

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
	<title>Login | Media Janitor</title>
</svelte:head>

<div class="auth-container">
	<div class="auth-card">
		<a href="/" class="auth-logo">
			<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="logo-icon">
				<path d="M3 21h4L17.5 10.5a2.828 2.828 0 0 0-4-4L3 17v4z"/>
				<path d="M14.5 5.5l4 4"/>
				<path d="M12 22h9"/>
			</svg>
			Media Janitor
		</a>
		<div class="auth-header">
			<h1>Log In</h1>
			<p class="auth-subtitle">Sign in to your account</p>
		</div>

		<form onsubmit={handleSubmit} class="auth-form">
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
					class="input"
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
					class="input"
				/>
			</div>

			<button type="submit" disabled={isLoading} class="submit-button">
				{#if isLoading}
					<span class="spinner"></span>
					Logging in...
				{:else}
					Log In
				{/if}
			</button>
		</form>

		<p class="auth-footer">
			Don't have an account? <a href="/register">Sign up</a>
		</p>
	</div>
</div>

<style>
	.auth-container {
		min-height: 100vh;
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
		background: var(--bg-primary);
	}

	.auth-card {
		width: 400px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-8);
	}

	.auth-logo {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		font-size: var(--font-size-xl);
		font-weight: var(--font-weight-bold);
		color: var(--text-primary);
		text-decoration: none;
		margin-bottom: var(--space-6);
		letter-spacing: -0.02em;
	}

	.auth-logo:hover {
		color: var(--accent);
	}

	.logo-icon {
		flex-shrink: 0;
	}

	.auth-header {
		text-align: center;
		margin-bottom: var(--space-6);
	}

	.auth-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
		margin-bottom: var(--space-2);
		color: var(--text-primary);
	}

	.auth-subtitle {
		color: var(--text-secondary);
		font-size: var(--font-size-base);
		margin: 0;
	}

	.auth-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	label {
		font-weight: var(--font-weight-medium);
		font-size: var(--font-size-base);
		color: var(--text-primary);
	}

	.input {
		padding: var(--space-3);
		font-size: var(--font-size-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
		transition: border-color var(--transition-fast);
	}

	.input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.input::placeholder {
		color: var(--text-muted);
	}

	.error-message {
		padding: var(--space-3);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
		font-size: var(--font-size-base);
	}

	.submit-button {
		margin-top: var(--space-2);
		padding: var(--space-3);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-semibold);
		cursor: pointer;
		transition: background var(--transition-fast);
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
	}

	.submit-button:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.submit-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.auth-footer {
		text-align: center;
		margin-top: var(--space-6);
		color: var(--text-secondary);
		font-size: var(--font-size-base);
	}

	.auth-footer a {
		color: var(--accent);
		text-decoration: none;
		font-weight: var(--font-weight-medium);
	}

	.auth-footer a:hover {
		text-decoration: underline;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
