<script lang="ts">
	import { authenticatedFetch } from '$lib/stores';

	// Password change state
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// Show/hide password toggles
	let showCurrentPassword = $state(false);
	let showNewPassword = $state(false);
	let showConfirmPassword = $state(false);

	// Password validation
	const minLength = 8;
	let passwordErrors = $derived(() => {
		const errors: string[] = [];
		if (newPassword.length > 0) {
			if (newPassword.length < minLength) {
				errors.push('Must be at least 8 characters');
			}
			if (!/[A-Z]/.test(newPassword)) {
				errors.push('Must contain an uppercase letter');
			}
			if (!/[a-z]/.test(newPassword)) {
				errors.push('Must contain a lowercase letter');
			}
			if (!/[0-9]/.test(newPassword)) {
				errors.push('Must contain a number');
			}
		}
		return errors;
	});

	let passwordsMatch = $derived(() => {
		if (confirmPassword.length === 0) return true;
		return newPassword === confirmPassword;
	});

	let isFormValid = $derived(() => {
		return (
			currentPassword.length > 0 &&
			newPassword.length >= minLength &&
			passwordErrors().length === 0 &&
			confirmPassword.length > 0 &&
			passwordsMatch()
		);
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		success = null;

		if (!isFormValid()) {
			error = 'Please fill in all fields correctly';
			return;
		}

		isLoading = true;

		try {
			const response = await authenticatedFetch('/api/auth/change-password', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					current_password: currentPassword,
					new_password: newPassword
				})
			});

			const data = await response.json();

			if (!response.ok) {
				if (response.status === 400) {
					throw new Error(data.detail || 'Current password is incorrect');
				} else if (response.status === 422) {
					throw new Error('New password does not meet requirements');
				}
				throw new Error(data.detail || 'Failed to change password');
			}

			success = 'Password changed successfully';
			// Clear form
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to change password';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="security-page">
	<header class="page-header">
		<h1>Security</h1>
		<p class="page-description">Manage your account security settings.</p>
	</header>

	<section class="security-section">
		<h2>Change Password</h2>
		<p class="section-description">Update your password to keep your account secure.</p>

		<form onsubmit={handleSubmit} class="password-form">
			{#if error}
				<div class="inline-error" role="alert">{error}</div>
			{/if}
			{#if success}
				<div class="inline-success" role="status">{success}</div>
			{/if}

			<div class="form-group">
				<label for="current-password">Current Password</label>
				<div class="password-input-wrapper">
					<input
						type={showCurrentPassword ? 'text' : 'password'}
						id="current-password"
						bind:value={currentPassword}
						autocomplete="current-password"
						required
					/>
					<button
						type="button"
						class="password-toggle"
						onclick={() => (showCurrentPassword = !showCurrentPassword)}
						aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
					>
						{#if showCurrentPassword}
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
								<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
								<line x1="1" y1="1" x2="23" y2="23" />
							</svg>
						{:else}
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
								<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
								<circle cx="12" cy="12" r="3" />
							</svg>
						{/if}
					</button>
				</div>
			</div>

			<div class="form-group">
				<label for="new-password">New Password</label>
				<div class="password-input-wrapper">
					<input
						type={showNewPassword ? 'text' : 'password'}
						id="new-password"
						bind:value={newPassword}
						autocomplete="new-password"
						required
						minlength={minLength}
					/>
					<button
						type="button"
						class="password-toggle"
						onclick={() => (showNewPassword = !showNewPassword)}
						aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
					>
						{#if showNewPassword}
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
								<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
								<line x1="1" y1="1" x2="23" y2="23" />
							</svg>
						{:else}
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
								<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
								<circle cx="12" cy="12" r="3" />
							</svg>
						{/if}
					</button>
				</div>
				{#if passwordErrors().length > 0}
					<ul class="password-requirements" role="alert">
						{#each passwordErrors() as err}
							<li class="requirement-error">{err}</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="form-group">
				<label for="confirm-password">Confirm New Password</label>
				<div class="password-input-wrapper">
					<input
						type={showConfirmPassword ? 'text' : 'password'}
						id="confirm-password"
						bind:value={confirmPassword}
						autocomplete="new-password"
						required
					/>
					<button
						type="button"
						class="password-toggle"
						onclick={() => (showConfirmPassword = !showConfirmPassword)}
						aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
					>
						{#if showConfirmPassword}
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
								<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
								<line x1="1" y1="1" x2="23" y2="23" />
							</svg>
						{:else}
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
								<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
								<circle cx="12" cy="12" r="3" />
							</svg>
						{/if}
					</button>
				</div>
				{#if !passwordsMatch() && confirmPassword.length > 0}
					<p class="password-mismatch" role="alert">Passwords do not match</p>
				{/if}
			</div>

			<div class="form-actions">
				<button type="submit" class="btn-save" disabled={isLoading || !isFormValid()}>
					{#if isLoading}
						<span class="spinner-small"></span>
					{:else}
						Change Password
					{/if}
				</button>
			</div>
		</form>
	</section>
</div>

<style>
	.security-page {
		max-width: 480px;
	}

	.page-header {
		margin-bottom: var(--space-6);
	}

	.page-header h1 {
		font-size: var(--font-size-xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
		margin-bottom: var(--space-2);
	}

	.page-description {
		color: var(--text-muted);
		font-size: var(--font-size-sm);
	}

	.security-section {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
	}

	.security-section h2 {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		margin-bottom: var(--space-1);
	}

	.section-description {
		color: var(--text-muted);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-6);
	}

	.password-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.form-group label {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.password-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.password-input-wrapper input {
		width: 100%;
		padding: var(--space-3);
		padding-right: 44px;
		font-size: var(--font-size-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
	}

	.password-input-wrapper input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.password-toggle {
		position: absolute;
		right: var(--space-2);
		padding: var(--space-2);
		background: transparent;
		border: none;
		cursor: pointer;
		color: var(--text-muted);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.password-toggle:hover {
		color: var(--text-primary);
	}

	.password-requirements {
		list-style: none;
		padding: 0;
		margin: 0;
		font-size: var(--font-size-sm);
	}

	.requirement-error {
		color: var(--danger);
		padding-left: var(--space-3);
		position: relative;
	}

	.requirement-error::before {
		content: '•';
		position: absolute;
		left: 0;
	}

	.password-mismatch {
		color: var(--danger);
		font-size: var(--font-size-sm);
		margin: 0;
	}

	.form-actions {
		padding-top: var(--space-4);
		border-top: 1px solid var(--border);
		margin-top: var(--space-2);
	}

	.btn-save {
		width: 100%;
		padding: var(--space-3);
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-medium);
		color: white;
		background: var(--accent);
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: background var(--transition-fast);
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 44px;
	}

	.btn-save:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.btn-save:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* Inline messages */
	.inline-error,
	.inline-success {
		font-size: var(--font-size-sm);
		padding: var(--space-3);
		border-radius: var(--radius-md);
	}

	.inline-error {
		background: var(--danger-light);
		color: var(--danger);
	}

	.inline-success {
		background: var(--success-light);
		color: var(--success);
	}

	/* Spinner */
	.spinner-small {
		width: 18px;
		height: 18px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Responsive */
	@media (max-width: 480px) {
		.security-section {
			padding: var(--space-4);
		}
	}
</style>
