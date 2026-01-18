<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	let newPassword = $state('');
	let confirmPassword = $state('');
	let showPassword = $state(false);
	let showConfirmPassword = $state(false);
	let error = $state<string | null>(null);
	let isLoading = $state(false);
	let isSuccess = $state(false);
	let passwordError = $state<string | null>(null);
	let confirmPasswordError = $state<string | null>(null);
	let token = $state<string | null>(null);
	let tokenError = $state<string | null>(null);

	onMount(() => {
		// Extract token from URL query param
		token = $page.url.searchParams.get('token');
		if (!token) {
			tokenError = 'Invalid reset link. No token provided.';
		}
	});

	function validatePassword(pwd: string): string | null {
		if (pwd.length < 8) {
			return 'Password must be at least 8 characters';
		}
		if (!/[A-Z]/.test(pwd)) {
			return 'Password must contain at least one uppercase letter';
		}
		if (!/[a-z]/.test(pwd)) {
			return 'Password must contain at least one lowercase letter';
		}
		if (!/[0-9]/.test(pwd)) {
			return 'Password must contain at least one number';
		}
		return null;
	}

	function validatePasswordsMatch(pwd: string, confirmPwd: string): string | null {
		if (pwd !== confirmPwd) {
			return 'Passwords do not match';
		}
		return null;
	}

	// Check if passwords match - only show error when confirm field has content
	let passwordsMatchError = $derived(
		confirmPassword.length > 0 ? validatePasswordsMatch(newPassword, confirmPassword) : null
	);

	// Disable submit when loading or passwords don't match (only when confirm has content)
	let isSubmitDisabled = $derived(
		isLoading || (confirmPassword.length > 0 && newPassword !== confirmPassword)
	);

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		passwordError = null;
		confirmPasswordError = null;

		// Validate password requirements
		const pwdError = validatePassword(newPassword);
		if (pwdError) {
			passwordError = pwdError;
			return;
		}

		// Validate passwords match
		const matchError = validatePasswordsMatch(newPassword, confirmPassword);
		if (matchError) {
			confirmPasswordError = matchError;
			return;
		}

		isLoading = true;

		try {
			const response = await fetch('/api/auth/reset-password', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ token, new_password: newPassword })
			});

			if (!response.ok) {
				const data = await response.json();
				if (response.status === 400) {
					throw new Error('Invalid or expired token. Please request a new reset link.');
				}
				throw new Error(data.detail || 'Password reset failed');
			}

			// Success - show message and redirect to login
			isSuccess = true;
			setTimeout(() => {
				goto('/login');
			}, 2000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Password reset failed. Please try again.';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Reset Password | Media Janitor</title>
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
			<h1>Reset Password</h1>
			<p class="auth-subtitle">Enter your new password</p>
		</div>

		{#if tokenError}
			<div class="error-message" role="alert">
				{tokenError}
			</div>
			<a href="/forgot-password" class="back-link">Request a new reset link</a>
		{:else if isSuccess}
			<div class="success-message" role="status">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
					<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
					<polyline points="22 4 12 14.01 9 11.01"/>
				</svg>
				<p>Password reset successful! Redirecting to login...</p>
			</div>
		{:else}
			<form onsubmit={handleSubmit} class="auth-form">
				{#if error}
					<div class="error-message" role="alert">
						{error}
					</div>
				{/if}

				<div class="form-group">
					<label for="newPassword">New Password</label>
					<div class="password-input-wrapper">
						<input
							type={showPassword ? 'text' : 'password'}
							id="newPassword"
							bind:value={newPassword}
							required
							autocomplete="new-password"
							placeholder="At least 8 characters"
							minlength="8"
							class="input"
							class:input-error={passwordError}
						/>
						<button
							type="button"
							class="toggle-password"
							onclick={() => showPassword = !showPassword}
							aria-label={showPassword ? 'Hide password' : 'Show password'}
						>
							{#if showPassword}
								<!-- Eye off icon -->
								<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
									<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
									<line x1="1" y1="1" x2="23" y2="23"/>
								</svg>
							{:else}
								<!-- Eye icon -->
								<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
									<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
									<circle cx="12" cy="12" r="3"/>
								</svg>
							{/if}
						</button>
					</div>
					<span class="password-hint">Must contain uppercase, lowercase, and number</span>
					{#if passwordError}
						<span class="field-error">{passwordError}</span>
					{/if}
				</div>

				<div class="form-group">
					<label for="confirmPassword">Confirm Password</label>
					<div class="password-input-wrapper">
						<input
							type={showConfirmPassword ? 'text' : 'password'}
							id="confirmPassword"
							bind:value={confirmPassword}
							required
							autocomplete="new-password"
							placeholder="Re-enter your password"
							class="input"
							class:input-error={passwordsMatchError || confirmPasswordError}
						/>
						<button
							type="button"
							class="toggle-password"
							onclick={() => showConfirmPassword = !showConfirmPassword}
							aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
						>
							{#if showConfirmPassword}
								<!-- Eye off icon -->
								<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
									<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
									<line x1="1" y1="1" x2="23" y2="23"/>
								</svg>
							{:else}
								<!-- Eye icon -->
								<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
									<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
									<circle cx="12" cy="12" r="3"/>
								</svg>
							{/if}
						</button>
					</div>
					{#if passwordsMatchError}
						<span class="field-error">{passwordsMatchError}</span>
					{:else if confirmPasswordError}
						<span class="field-error">{confirmPasswordError}</span>
					{/if}
				</div>

				<button type="submit" disabled={isSubmitDisabled} class="submit-button">
					{#if isLoading}
						<span class="spinner" aria-hidden="true"></span>
						Resetting...
					{:else}
						Reset Password
					{/if}
				</button>
			</form>

			<p class="auth-footer">
				<a href="/login">Back to login</a>
			</p>
		{/if}
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

	.password-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.input {
		width: 100%;
		padding: var(--space-3);
		padding-right: 44px;
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

	.toggle-password {
		position: absolute;
		right: 8px;
		background: none;
		border: none;
		padding: var(--space-2);
		cursor: pointer;
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-sm);
		transition: color var(--transition-fast), background-color var(--transition-fast);
	}

	.toggle-password:hover {
		color: var(--text-primary);
		background-color: var(--bg-tertiary);
	}

	.toggle-password:focus {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	.password-hint {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
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
		margin-bottom: var(--space-4);
	}

	.success-message {
		display: flex;
		align-items: flex-start;
		gap: var(--space-3);
		padding: var(--space-4);
		background: var(--success-light);
		border: 1px solid var(--success);
		border-radius: var(--radius-md);
		color: var(--success);
		font-size: var(--font-size-base);
	}

	.success-message svg {
		flex-shrink: 0;
		margin-top: 2px;
	}

	.success-message p {
		margin: 0;
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

	.back-link {
		display: block;
		text-align: center;
		color: var(--accent);
		text-decoration: none;
		font-weight: var(--font-weight-medium);
		margin-top: var(--space-4);
	}

	.back-link:hover {
		text-decoration: underline;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
