<script lang="ts">
	import { onMount } from 'svelte';

	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state<string | null>(null);
	let isLoading = $state(false);
	let passwordError = $state<string | null>(null);
	let confirmPasswordError = $state<string | null>(null);
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

	function validatePasswordsMatch(pwd: string, confirmPwd: string): string | null {
		if (pwd !== confirmPwd) {
			return 'Passwords do not match';
		}
		return null;
	}

	type PasswordStrength = 'weak' | 'medium' | 'strong';

	function getPasswordStrength(pwd: string): PasswordStrength {
		if (pwd.length >= 12) {
			return 'strong';
		} else if (pwd.length >= 8) {
			return 'medium';
		}
		return 'weak';
	}

	function getStrengthLabel(strength: PasswordStrength): string {
		switch (strength) {
			case 'weak':
				return 'Weak';
			case 'medium':
				return 'Medium';
			case 'strong':
				return 'Strong';
		}
	}

	let passwordStrength = $derived(password.length > 0 ? getPasswordStrength(password) : null);

	// Check if passwords match - only show error when confirm field has content
	let passwordsMatchError = $derived(
		confirmPassword.length > 0 ? validatePasswordsMatch(password, confirmPassword) : null
	);

	// Disable submit when loading or passwords don't match (only when confirm has content)
	let isSubmitDisabled = $derived(
		isLoading || (confirmPassword.length > 0 && password !== confirmPassword)
	);

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = null;

		// Validate password length
		const pwdError = validatePassword(password);
		if (pwdError) {
			passwordError = pwdError;
			return;
		}
		passwordError = null;

		// Validate passwords match
		const matchError = validatePasswordsMatch(password, confirmPassword);
		if (matchError) {
			confirmPasswordError = matchError;
			return;
		}
		confirmPasswordError = null;

		isLoading = true;

		try {
			const response = await fetch('/api/auth/register', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password })
			});

			if (!response.ok) {
				const data = await response.json();
				// Check for signup disabled error
				if (response.status === 403 && data.detail === 'Sign ups are closed for now') {
					throw new Error(
						'SIGNUPS_CLOSED'
					);
				}
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
	<title>Register | Media Janitor</title>
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
			<h1>Get Started Free</h1>
			<p class="auth-subtitle">Keep your media library clean and organized</p>
		</div>

		<form onsubmit={handleSubmit} class="auth-form">
			{#if error === 'SIGNUPS_CLOSED'}
				<div class="error-message" role="alert">
					Signups are currently closed! If you're interested in using the app,
					<a href="https://github.com/JimmyDore/mediajanitor/issues/2" target="_blank" rel="noopener noreferrer">
						check out this issue
					</a> for more info. Or self-host it yourself — it's free and open source!
				</div>
			{:else if error}
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
				{#if passwordStrength}
					<div class="password-strength">
						<div class="strength-bar">
							<div
								class="strength-fill strength-{passwordStrength}"
								role="progressbar"
								aria-valuenow={passwordStrength === 'weak' ? 33 : passwordStrength === 'medium' ? 66 : 100}
								aria-valuemin={0}
								aria-valuemax={100}
								aria-label="Password strength: {getStrengthLabel(passwordStrength)}"
							></div>
						</div>
						<span class="strength-label strength-text-{passwordStrength}">{getStrengthLabel(passwordStrength)}</span>
					</div>
				{/if}
				{#if passwordError}
					<span class="field-error">{passwordError}</span>
				{/if}
			</div>

			<div class="form-group">
				<label for="confirmPassword">Confirm Password</label>
				<input
					type="password"
					id="confirmPassword"
					bind:value={confirmPassword}
					required
					autocomplete="new-password"
					placeholder="Re-enter your password"
					class="input"
					class:input-error={passwordsMatchError || confirmPasswordError}
				/>
				{#if passwordsMatchError}
					<span class="field-error">{passwordsMatchError}</span>
				{:else if confirmPasswordError}
					<span class="field-error">{confirmPasswordError}</span>
				{/if}
			</div>

			<button type="submit" disabled={isSubmitDisabled} class="submit-button">
				{#if isLoading}
					<span class="spinner"></span>
					Creating account...
				{:else}
					Create Free Account
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

	.input-error {
		border-color: var(--danger);
	}

	.field-error {
		color: var(--danger);
		font-size: var(--font-size-sm);
	}

	.password-strength {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.strength-bar {
		flex: 1;
		height: 4px;
		background: var(--border);
		border-radius: 2px;
		overflow: hidden;
	}

	.strength-fill {
		height: 100%;
		border-radius: 2px;
		transition: width var(--transition-fast), background-color var(--transition-fast);
	}

	.strength-weak {
		width: 33%;
		background-color: var(--danger);
	}

	.strength-medium {
		width: 66%;
		background-color: var(--warning);
	}

	.strength-strong {
		width: 100%;
		background-color: var(--success);
	}

	.strength-label {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		min-width: 55px;
	}

	.strength-text-weak {
		color: var(--danger);
	}

	.strength-text-medium {
		color: var(--warning);
	}

	.strength-text-strong {
		color: var(--success);
	}

	.error-message {
		padding: var(--space-3);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
		font-size: var(--font-size-base);
	}

	.error-message a {
		color: var(--danger);
		font-weight: var(--font-weight-semibold);
		text-decoration: underline;
	}

	.error-message a:hover {
		opacity: 0.8;
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
