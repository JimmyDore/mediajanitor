<script lang="ts">
	import { onMount } from 'svelte';
	import { auth } from '$lib/stores';

	// Jellyfin form state
	let jellyfinUrl = $state('');
	let jellyfinApiKey = $state('');
	let jellyfinError = $state<string | null>(null);
	let jellyfinSuccess = $state<string | null>(null);
	let isJellyfinLoading = $state(false);
	let isFetchingSettings = $state(true);

	// Jellyfin current settings state
	let hasJellyfinConfigured = $state(false);
	let currentJellyfinUrl = $state<string | null>(null);

	// Jellyseerr form state
	let jellyseerrUrl = $state('');
	let jellyseerrApiKey = $state('');
	let jellyseerrError = $state<string | null>(null);
	let jellyseerrSuccess = $state<string | null>(null);
	let isJellyseerrLoading = $state(false);

	// Jellyseerr current settings state
	let hasJellyseerrConfigured = $state(false);
	let currentJellyseerrUrl = $state<string | null>(null);

	// Analysis preferences state
	let oldContentMonths = $state(4);
	let minAgeMonths = $state(3);
	let largeMovieSizeGb = $state(13);
	let analysisError = $state<string | null>(null);
	let analysisSuccess = $state<string | null>(null);
	let isAnalysisLoading = $state(false);

	// Default values for reset
	const DEFAULT_OLD_CONTENT_MONTHS = 4;
	const DEFAULT_MIN_AGE_MONTHS = 3;
	const DEFAULT_LARGE_MOVIE_SIZE_GB = 13;

	onMount(async () => {
		await loadCurrentSettings();
	});

	async function loadCurrentSettings() {
		try {
			const token = localStorage.getItem('access_token');

			// Load Jellyfin settings
			const jellyfinResponse = await fetch('/api/settings/jellyfin', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (jellyfinResponse.ok) {
				const data = await jellyfinResponse.json();
				hasJellyfinConfigured = data.api_key_configured;
				currentJellyfinUrl = data.server_url;
				if (data.server_url) {
					jellyfinUrl = data.server_url;
				}
			}

			// Load Jellyseerr settings
			const jellyseerrResponse = await fetch('/api/settings/jellyseerr', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (jellyseerrResponse.ok) {
				const data = await jellyseerrResponse.json();
				hasJellyseerrConfigured = data.api_key_configured;
				currentJellyseerrUrl = data.server_url;
				if (data.server_url) {
					jellyseerrUrl = data.server_url;
				}
			}

			// Load analysis preferences
			const analysisResponse = await fetch('/api/settings/analysis', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (analysisResponse.ok) {
				const data = await analysisResponse.json();
				oldContentMonths = data.old_content_months;
				minAgeMonths = data.min_age_months;
				largeMovieSizeGb = data.large_movie_size_gb;
			}
		} catch (e) {
			console.error('Failed to load settings:', e);
		} finally {
			isFetchingSettings = false;
		}
	}

	async function handleJellyfinSubmit(event: SubmitEvent) {
		event.preventDefault();
		jellyfinError = null;
		jellyfinSuccess = null;
		isJellyfinLoading = true;

		try {
			const token = localStorage.getItem('access_token');
			const response = await fetch('/api/settings/jellyfin', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					server_url: jellyfinUrl,
					api_key: jellyfinApiKey
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save settings');
			}

			jellyfinSuccess = data.message || 'Settings saved successfully!';
			hasJellyfinConfigured = true;
			currentJellyfinUrl = jellyfinUrl;
			jellyfinApiKey = ''; // Clear the API key field after successful save
		} catch (e) {
			jellyfinError = e instanceof Error ? e.message : 'Failed to save settings';
		} finally {
			isJellyfinLoading = false;
		}
	}

	async function handleJellyseerrSubmit(event: SubmitEvent) {
		event.preventDefault();
		jellyseerrError = null;
		jellyseerrSuccess = null;
		isJellyseerrLoading = true;

		try {
			const token = localStorage.getItem('access_token');
			const response = await fetch('/api/settings/jellyseerr', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					server_url: jellyseerrUrl,
					api_key: jellyseerrApiKey
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save settings');
			}

			jellyseerrSuccess = data.message || 'Jellyseerr connected successfully!';
			hasJellyseerrConfigured = true;
			currentJellyseerrUrl = jellyseerrUrl;
			jellyseerrApiKey = ''; // Clear the API key field after successful save
		} catch (e) {
			jellyseerrError = e instanceof Error ? e.message : 'Failed to save settings';
		} finally {
			isJellyseerrLoading = false;
		}
	}

	async function handleAnalysisSubmit(event: SubmitEvent) {
		event.preventDefault();
		analysisError = null;
		analysisSuccess = null;
		isAnalysisLoading = true;

		try {
			const token = localStorage.getItem('access_token');
			const response = await fetch('/api/settings/analysis', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					old_content_months: oldContentMonths,
					min_age_months: minAgeMonths,
					large_movie_size_gb: largeMovieSizeGb
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save preferences');
			}

			analysisSuccess = data.message || 'Preferences saved successfully!';
		} catch (e) {
			analysisError = e instanceof Error ? e.message : 'Failed to save preferences';
		} finally {
			isAnalysisLoading = false;
		}
	}

	async function handleResetAnalysis() {
		analysisError = null;
		analysisSuccess = null;
		isAnalysisLoading = true;

		try {
			const token = localStorage.getItem('access_token');
			const response = await fetch('/api/settings/analysis', {
				method: 'DELETE',
				headers: { Authorization: `Bearer ${token}` }
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to reset preferences');
			}

			// Reset to default values
			oldContentMonths = DEFAULT_OLD_CONTENT_MONTHS;
			minAgeMonths = DEFAULT_MIN_AGE_MONTHS;
			largeMovieSizeGb = DEFAULT_LARGE_MOVIE_SIZE_GB;

			analysisSuccess = 'Preferences reset to defaults!';
		} catch (e) {
			analysisError = e instanceof Error ? e.message : 'Failed to reset preferences';
		} finally {
			isAnalysisLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Settings - Media Janitor</title>
</svelte:head>

<div class="page-container">
	<div class="page-header">
		<h1>Settings</h1>
		<p class="page-subtitle">Configure your media server connections and preferences.</p>
	</div>

	{#if isFetchingSettings}
		<div class="loading-state">
			<span class="spinner"></span>
			<span>Loading settings...</span>
		</div>
	{:else}
		<section class="settings-section">
			<div class="section-header">
				<h2>Jellyfin Connection</h2>
				<p class="section-description">Connect your Jellyfin server to analyze your media library.</p>
			</div>

			{#if hasJellyfinConfigured}
				<div class="status-badge status-connected">
					Connected to {currentJellyfinUrl}
				</div>
			{:else}
				<div class="status-badge status-disconnected">
					Not connected
				</div>
			{/if}

			<form onsubmit={handleJellyfinSubmit} class="settings-form">
				{#if jellyfinError}
					<div class="message message-error" role="alert">
						{jellyfinError}
					</div>
				{/if}

				{#if jellyfinSuccess}
					<div class="message message-success" role="status">
						{jellyfinSuccess}
					</div>
				{/if}

				<div class="form-group">
					<label for="jellyfin-url">Server URL</label>
					<input
						type="url"
						id="jellyfin-url"
						bind:value={jellyfinUrl}
						required
						placeholder="https://your-jellyfin-server.com"
						class="input"
					/>
					<span class="hint">The full URL to your Jellyfin server</span>
				</div>

				<div class="form-group">
					<label for="jellyfin-api-key">
						API Key
						{#if hasJellyfinConfigured}
							<span class="label-hint">(leave blank to keep current)</span>
						{/if}
					</label>
					<input
						type="password"
						id="jellyfin-api-key"
						bind:value={jellyfinApiKey}
						required={!hasJellyfinConfigured}
						placeholder={hasJellyfinConfigured ? '••••••••••••••••' : 'Enter your API key'}
						autocomplete="off"
						class="input"
					/>
					<span class="hint">Find this in Jellyfin Dashboard → API Keys</span>
				</div>

				<button type="submit" disabled={isJellyfinLoading} class="btn-primary">
					{#if isJellyfinLoading}
						<span class="spinner"></span>
						Validating connection...
					{:else if hasJellyfinConfigured}
						Update Connection
					{:else}
						Connect to Jellyfin
					{/if}
				</button>
			</form>
		</section>

		<section class="settings-section">
			<div class="section-header">
				<h2>Jellyseerr Connection</h2>
				<p class="section-description">Connect your Jellyseerr server to track media requests.</p>
			</div>

			{#if hasJellyseerrConfigured}
				<div class="status-badge status-connected">
					Connected to {currentJellyseerrUrl}
				</div>
			{:else}
				<div class="status-badge status-disconnected">
					Not connected
				</div>
			{/if}

			<form onsubmit={handleJellyseerrSubmit} class="settings-form">
				{#if jellyseerrError}
					<div class="message message-error" role="alert">
						{jellyseerrError}
					</div>
				{/if}

				{#if jellyseerrSuccess}
					<div class="message message-success" role="status">
						{jellyseerrSuccess}
					</div>
				{/if}

				<div class="form-group">
					<label for="jellyseerr-url">Server URL</label>
					<input
						type="url"
						id="jellyseerr-url"
						bind:value={jellyseerrUrl}
						required
						placeholder="https://your-jellyseerr-server.com"
						class="input"
					/>
					<span class="hint">The full URL to your Jellyseerr server</span>
				</div>

				<div class="form-group">
					<label for="jellyseerr-api-key">
						API Key
						{#if hasJellyseerrConfigured}
							<span class="label-hint">(leave blank to keep current)</span>
						{/if}
					</label>
					<input
						type="password"
						id="jellyseerr-api-key"
						bind:value={jellyseerrApiKey}
						required={!hasJellyseerrConfigured}
						placeholder={hasJellyseerrConfigured ? '••••••••••••••••' : 'Enter your API key'}
						autocomplete="off"
						class="input"
					/>
					<span class="hint">Find this in Jellyseerr Settings → General → API Key</span>
				</div>

				<button type="submit" disabled={isJellyseerrLoading} class="btn-primary">
					{#if isJellyseerrLoading}
						<span class="spinner"></span>
						Validating connection...
					{:else if hasJellyseerrConfigured}
						Update Connection
					{:else}
						Connect to Jellyseerr
					{/if}
				</button>
			</form>
		</section>

		<section class="settings-section">
			<div class="section-header">
				<h2>Analysis Preferences</h2>
				<p class="section-description">Customize thresholds for content analysis.</p>
			</div>

			<form onsubmit={handleAnalysisSubmit} class="settings-form">
				{#if analysisError}
					<div class="message message-error" role="alert">
						{analysisError}
					</div>
				{/if}

				{#if analysisSuccess}
					<div class="message message-success" role="status">
						{analysisSuccess}
					</div>
				{/if}

				<div class="form-group">
					<label for="old-content-months">Old Content Threshold (months)</label>
					<input
						type="number"
						id="old-content-months"
						bind:value={oldContentMonths}
						min="1"
						max="24"
						required
						class="input input-number"
					/>
					<span class="hint">Flag content not watched in this many months (default: <span class="text-mono">4</span>)</span>
				</div>

				<div class="form-group">
					<label for="min-age-months">Minimum Age (months)</label>
					<input
						type="number"
						id="min-age-months"
						bind:value={minAgeMonths}
						min="0"
						max="12"
						required
						class="input input-number"
					/>
					<span class="hint">Don't flag recently added content (default: <span class="text-mono">3</span>)</span>
				</div>

				<div class="form-group">
					<label for="large-movie-size">Large Movie Size (GB)</label>
					<input
						type="number"
						id="large-movie-size"
						bind:value={largeMovieSizeGb}
						min="1"
						max="100"
						required
						class="input input-number"
					/>
					<span class="hint">Movies larger than this are flagged (default: <span class="text-mono">13</span>)</span>
				</div>

				<div class="button-row">
					<button type="submit" disabled={isAnalysisLoading} class="btn-primary">
						{#if isAnalysisLoading}
							<span class="spinner"></span>
							Saving...
						{:else}
							Save Preferences
						{/if}
					</button>
					<button
						type="button"
						onclick={handleResetAnalysis}
						disabled={isAnalysisLoading}
						class="btn-secondary"
					>
						Reset to Defaults
					</button>
				</div>
			</form>
		</section>
	{/if}
</div>

<style>
	.page-container {
		padding: var(--space-6);
		max-width: 640px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: var(--space-8);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
		margin-bottom: var(--space-2);
	}

	.page-subtitle {
		color: var(--text-secondary);
		font-size: var(--font-size-base);
		margin: 0;
	}

	.loading-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		padding: var(--space-8);
		color: var(--text-secondary);
	}

	/* Settings Section */
	.settings-section {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
		margin-bottom: var(--space-6);
	}

	.settings-section:last-child {
		margin-bottom: 0;
	}

	.section-header {
		margin-bottom: var(--space-4);
	}

	.section-header h2 {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		margin-bottom: var(--space-1);
	}

	.section-description {
		color: var(--text-secondary);
		font-size: var(--font-size-base);
		margin: 0;
	}

	/* Status Badge */
	.status-badge {
		display: inline-flex;
		align-items: center;
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		margin-bottom: var(--space-4);
	}

	.status-connected {
		background: var(--success-light);
		color: var(--success);
		border: 1px solid var(--success);
	}

	.status-disconnected {
		background: var(--warning-light);
		color: var(--warning);
		border: 1px solid var(--warning);
	}

	/* Form */
	.settings-form {
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

	.label-hint {
		font-weight: var(--font-weight-normal);
		color: var(--text-muted);
		font-size: var(--font-size-sm);
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

	.input-number {
		font-family: var(--font-mono);
		font-variant-numeric: tabular-nums;
	}

	.hint {
		color: var(--text-muted);
		font-size: var(--font-size-sm);
	}

	.text-mono {
		font-family: var(--font-mono);
	}

	/* Messages */
	.message {
		padding: var(--space-3);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
	}

	.message-error {
		background: var(--danger-light);
		border: 1px solid var(--danger);
		color: var(--danger);
	}

	.message-success {
		background: var(--success-light);
		border: 1px solid var(--success);
		color: var(--success);
	}

	/* Buttons */
	.btn-primary,
	.btn-secondary {
		padding: var(--space-3) var(--space-4);
		border-radius: var(--radius-md);
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-semibold);
		cursor: pointer;
		transition: all var(--transition-fast);
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
	}

	.btn-primary {
		background: var(--accent);
		color: white;
		border: none;
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.btn-secondary {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
	}

	.btn-secondary:hover:not(:disabled) {
		background: var(--bg-hover);
		border-color: var(--text-secondary);
	}

	.btn-primary:disabled,
	.btn-secondary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.button-row {
		display: flex;
		gap: var(--space-3);
		flex-wrap: wrap;
		margin-top: var(--space-2);
	}

	.button-row .btn-primary,
	.button-row .btn-secondary {
		flex: 1;
		min-width: 140px;
	}

	.spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.btn-primary .spinner {
		border-color: rgba(255, 255, 255, 0.3);
		border-top-color: white;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@media (max-width: 640px) {
		.page-container {
			padding: var(--space-4);
		}

		.settings-section {
			padding: var(--space-4);
		}

		.button-row {
			flex-direction: column;
		}

		.button-row .btn-primary,
		.button-row .btn-secondary {
			width: 100%;
		}
	}
</style>
