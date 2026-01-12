<script lang="ts">
	import { onMount } from 'svelte';

	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let isLoading = $state(false);
	let passwordError = $state<string | null>(null);
	let mounted = $state(false);

	onMount(() => {
		mounted = true;
	});

	function validatePassword(pwd: string): string | null {
		if (pwd.length < 8) {
			return 'Password must be at least 8 characters';
		}
		return null;
	}

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = null;

		// Validate password
		const pwdError = validatePassword(password);
		if (pwdError) {
			passwordError = pwdError;
			return;
		}
		passwordError = null;

		isLoading = true;

		try {
			const response = await fetch('/api/auth/register', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password })
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Registration failed');
			}

			// Registration successful - redirect to login
			window.location.href = '/login';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Registration failed';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Sign Up - Plex Dashboard</title>
</svelte:head>

<div class="register-container">
	<h1>Create Account</h1>

	<form onsubmit={handleSubmit} class="register-form">
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
				autocomplete="new-password"
				placeholder="At least 8 characters"
				minlength="8"
			/>
			{#if passwordError}
				<span class="field-error">{passwordError}</span>
			{/if}
		</div>

		<button type="submit" disabled={isLoading} class="submit-button">
			{#if isLoading}
				Creating account...
			{:else}
				Sign Up
			{/if}
		</button>
	</form>

	<p class="login-link">
		Already have an account? <a href="/login">Log in</a>
	</p>
</div>

<style>
	.register-container {
		max-width: 400px;
		margin: 0 auto;
		padding: 2rem;
	}

	h1 {
		text-align: center;
		margin-bottom: 2rem;
		color: var(--accent);
	}

	.register-form {
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

	input:invalid {
		border-color: var(--danger);
	}

	.field-error {
		color: var(--danger);
		font-size: 0.875rem;
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

	.login-link {
		text-align: center;
		margin-top: 1.5rem;
		color: var(--text-secondary);
	}

	.login-link a {
		color: var(--accent);
		text-decoration: none;
	}

	.login-link a:hover {
		text-decoration: underline;
	}
</style>
