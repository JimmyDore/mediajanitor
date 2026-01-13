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
	<title>Sign Up - Media Janitor</title>
</svelte:head>

<div class="auth-container">
	<div class="auth-card">
		<div class="auth-header">
			<h1>Create Account</h1>
			<p class="auth-subtitle">Start managing your media library</p>
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
					autocomplete="new-password"
					placeholder="At least 8 characters"
					minlength="8"
					class="input"
					class:input-error={passwordError}
				/>
				{#if passwordError}
					<span class="field-error">{passwordError}</span>
				{/if}
			</div>

			<button type="submit" disabled={isLoading} class="submit-button">
				{#if isLoading}
					<span class="spinner"></span>
					Creating account...
				{:else}
					Sign Up
				{/if}
			</button>
		</form>

		<p class="auth-footer">
			Already have an account? <a href="/login">Log in</a>
		</p>
	</div>
</div>

<style>
	.auth-container {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
		background: var(--bg-primary);
	}

	.auth-card {
		width: 100%;
		max-width: 400px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-8);
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

	.input-error {
		border-color: var(--danger);
	}

	.field-error {
		color: var(--danger);
		font-size: var(--font-size-sm);
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
