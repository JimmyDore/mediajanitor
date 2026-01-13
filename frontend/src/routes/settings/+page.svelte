<script lang="ts">
	import { onMount } from 'svelte';

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

	// Expand/collapse states
	let jellyfinExpanded = $state(false);
	let jellyseerrExpanded = $state(false);

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
				// Auto-expand if not configured
				if (!hasJellyfinConfigured) jellyfinExpanded = true;
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
				// Auto-expand if not configured
				if (!hasJellyseerrConfigured) jellyseerrExpanded = true;
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

			jellyfinSuccess = 'Connected';
			hasJellyfinConfigured = true;
			currentJellyfinUrl = jellyfinUrl;
			jellyfinApiKey = '';
			jellyfinExpanded = false;
			setTimeout(() => jellyfinSuccess = null, 3000);
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

			jellyseerrSuccess = 'Connected';
			hasJellyseerrConfigured = true;
			currentJellyseerrUrl = jellyseerrUrl;
			jellyseerrApiKey = '';
			jellyseerrExpanded = false;
			setTimeout(() => jellyseerrSuccess = null, 3000);
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

			analysisSuccess = 'Saved';
			setTimeout(() => analysisSuccess = null, 3000);
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

			oldContentMonths = DEFAULT_OLD_CONTENT_MONTHS;
			minAgeMonths = DEFAULT_MIN_AGE_MONTHS;
			largeMovieSizeGb = DEFAULT_LARGE_MOVIE_SIZE_GB;

			analysisSuccess = 'Reset to defaults';
			setTimeout(() => analysisSuccess = null, 3000);
		} catch (e) {
			analysisError = e instanceof Error ? e.message : 'Failed to reset preferences';
		} finally {
			isAnalysisLoading = false;
		}
	}

	function extractDomain(url: string): string {
		try {
			return new URL(url).hostname;
		} catch {
			return url;
		}
	}
</script>

<svelte:head>
	<title>Settings - Media Janitor</title>
</svelte:head>

<div class="settings-page">
	<header class="page-header">
		<h1>Settings</h1>
	</header>

	{#if isFetchingSettings}
		<div class="loading">
			<span class="spinner"></span>
		</div>
	{:else}
		<!-- Connections Section -->
		<section class="section">
			<h2 class="section-title">Connections</h2>

			<!-- Jellyfin -->
			<div class="connection-row">
				<div class="connection-info">
					<div class="connection-header">
						<span class="connection-name">Jellyfin</span>
						{#if hasJellyfinConfigured}
							<span class="status-dot status-connected" title="Connected"></span>
						{:else}
							<span class="status-dot status-disconnected" title="Not connected"></span>
						{/if}
					</div>
					{#if hasJellyfinConfigured && currentJellyfinUrl}
						<span class="connection-url">{extractDomain(currentJellyfinUrl)}</span>
					{:else}
						<span class="connection-url muted">Not configured</span>
					{/if}
				</div>
				<button
					class="btn-edit"
					onclick={() => jellyfinExpanded = !jellyfinExpanded}
					aria-expanded={jellyfinExpanded}
				>
					{jellyfinExpanded ? 'Cancel' : hasJellyfinConfigured ? 'Edit' : 'Configure'}
				</button>
			</div>

			{#if jellyfinExpanded}
				<form onsubmit={handleJellyfinSubmit} class="connection-form">
					{#if jellyfinError}
						<div class="inline-error">{jellyfinError}</div>
					{/if}
					{#if jellyfinSuccess}
						<div class="inline-success">{jellyfinSuccess}</div>
					{/if}
					<div class="form-row">
						<div class="form-field">
							<label for="jellyfin-url">Server URL</label>
							<input
								type="url"
								id="jellyfin-url"
								bind:value={jellyfinUrl}
								required
								placeholder="https://jellyfin.example.com"
							/>
						</div>
						<div class="form-field">
							<label for="jellyfin-key">
								API Key
								{#if hasJellyfinConfigured}
									<span class="optional">(leave blank to keep)</span>
								{/if}
							</label>
							<input
								type="password"
								id="jellyfin-key"
								bind:value={jellyfinApiKey}
								required={!hasJellyfinConfigured}
								placeholder={hasJellyfinConfigured ? '••••••••' : 'API key'}
								autocomplete="off"
							/>
						</div>
						<button type="submit" class="btn-save" disabled={isJellyfinLoading}>
							{#if isJellyfinLoading}
								<span class="spinner-small"></span>
							{:else}
								Save
							{/if}
						</button>
					</div>
				</form>
			{/if}

			<div class="divider"></div>

			<!-- Jellyseerr -->
			<div class="connection-row">
				<div class="connection-info">
					<div class="connection-header">
						<span class="connection-name">Jellyseerr</span>
						{#if hasJellyseerrConfigured}
							<span class="status-dot status-connected" title="Connected"></span>
						{:else}
							<span class="status-dot status-disconnected" title="Not connected"></span>
						{/if}
					</div>
					{#if hasJellyseerrConfigured && currentJellyseerrUrl}
						<span class="connection-url">{extractDomain(currentJellyseerrUrl)}</span>
					{:else}
						<span class="connection-url muted">Not configured</span>
					{/if}
				</div>
				<button
					class="btn-edit"
					onclick={() => jellyseerrExpanded = !jellyseerrExpanded}
					aria-expanded={jellyseerrExpanded}
				>
					{jellyseerrExpanded ? 'Cancel' : hasJellyseerrConfigured ? 'Edit' : 'Configure'}
				</button>
			</div>

			{#if jellyseerrExpanded}
				<form onsubmit={handleJellyseerrSubmit} class="connection-form">
					{#if jellyseerrError}
						<div class="inline-error">{jellyseerrError}</div>
					{/if}
					{#if jellyseerrSuccess}
						<div class="inline-success">{jellyseerrSuccess}</div>
					{/if}
					<div class="form-row">
						<div class="form-field">
							<label for="jellyseerr-url">Server URL</label>
							<input
								type="url"
								id="jellyseerr-url"
								bind:value={jellyseerrUrl}
								required
								placeholder="https://jellyseerr.example.com"
							/>
						</div>
						<div class="form-field">
							<label for="jellyseerr-key">
								API Key
								{#if hasJellyseerrConfigured}
									<span class="optional">(leave blank to keep)</span>
								{/if}
							</label>
							<input
								type="password"
								id="jellyseerr-key"
								bind:value={jellyseerrApiKey}
								required={!hasJellyseerrConfigured}
								placeholder={hasJellyseerrConfigured ? '••••••••' : 'API key'}
								autocomplete="off"
							/>
						</div>
						<button type="submit" class="btn-save" disabled={isJellyseerrLoading}>
							{#if isJellyseerrLoading}
								<span class="spinner-small"></span>
							{:else}
								Save
							{/if}
						</button>
					</div>
				</form>
			{/if}
		</section>

		<!-- Thresholds Section -->
		<section class="section">
			<h2 class="section-title">Thresholds</h2>

			<form onsubmit={handleAnalysisSubmit} class="thresholds-form">
				{#if analysisError}
					<div class="inline-error">{analysisError}</div>
				{/if}
				{#if analysisSuccess}
					<div class="inline-success">{analysisSuccess}</div>
				{/if}

				<div class="threshold-row">
					<label for="old-content">Flag content unwatched for</label>
					<div class="threshold-input">
						<input
							type="number"
							id="old-content"
							bind:value={oldContentMonths}
							min="1"
							max="24"
							required
						/>
						<span class="unit">months</span>
					</div>
				</div>

				<div class="threshold-row">
					<label for="min-age">Don't flag content newer than</label>
					<div class="threshold-input">
						<input
							type="number"
							id="min-age"
							bind:value={minAgeMonths}
							min="0"
							max="12"
							required
						/>
						<span class="unit">months</span>
					</div>
				</div>

				<div class="threshold-row">
					<label for="large-size">Flag movies larger than</label>
					<div class="threshold-input">
						<input
							type="number"
							id="large-size"
							bind:value={largeMovieSizeGb}
							min="1"
							max="100"
							required
						/>
						<span class="unit">GB</span>
					</div>
				</div>

				<div class="threshold-actions">
					<button type="button" class="btn-reset" onclick={handleResetAnalysis} disabled={isAnalysisLoading}>
						Reset
					</button>
					<button type="submit" class="btn-save" disabled={isAnalysisLoading}>
						{#if isAnalysisLoading}
							<span class="spinner-small"></span>
						{:else}
							Save
						{/if}
					</button>
				</div>
			</form>
		</section>
	{/if}
</div>

<style>
	.settings-page {
		max-width: 640px;
		margin: 0 auto;
		padding: var(--space-6);
	}

	.page-header {
		margin-bottom: var(--space-8);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
	}

	.loading {
		display: flex;
		justify-content: center;
		padding: var(--space-12);
	}

	/* Section */
	.section {
		margin-bottom: var(--space-10);
	}

	.section-title {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: var(--space-4);
	}

	.divider {
		height: 1px;
		background: var(--border);
		margin: var(--space-4) 0;
	}

	/* Connection Row */
	.connection-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) 0;
	}

	.connection-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.connection-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.connection-name {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}

	.status-connected {
		background: var(--success);
	}

	.status-disconnected {
		background: var(--text-muted);
	}

	.connection-url {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.connection-url.muted {
		color: var(--text-muted);
	}

	.btn-edit {
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-edit:hover {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	/* Connection Form */
	.connection-form {
		padding: var(--space-4) 0;
		padding-left: var(--space-4);
		border-left: 2px solid var(--border);
		margin-left: var(--space-1);
		margin-top: var(--space-2);
	}

	.form-row {
		display: flex;
		gap: var(--space-3);
		align-items: flex-end;
		flex-wrap: wrap;
	}

	.form-field {
		flex: 1;
		min-width: 160px;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.form-field label {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		font-weight: var(--font-weight-medium);
	}

	.optional {
		font-weight: var(--font-weight-normal);
		color: var(--text-muted);
	}

	.form-field input {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
		transition: border-color var(--transition-fast);
	}

	.form-field input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.form-field input::placeholder {
		color: var(--text-muted);
	}

	.btn-save {
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-size-sm);
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
		min-width: 60px;
		height: 34px;
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
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		margin-bottom: var(--space-3);
	}

	.inline-error {
		background: var(--danger-light);
		color: var(--danger);
	}

	.inline-success {
		background: var(--success-light);
		color: var(--success);
	}

	/* Thresholds */
	.thresholds-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.threshold-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-2) 0;
	}

	.threshold-row label {
		font-size: var(--font-size-md);
		color: var(--text-primary);
	}

	.threshold-input {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.threshold-input input {
		width: 64px;
		padding: var(--space-2);
		font-size: var(--font-size-md);
		font-family: var(--font-mono);
		text-align: center;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
	}

	.threshold-input input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.unit {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		min-width: 50px;
	}

	.threshold-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		margin-top: var(--space-4);
		padding-top: var(--space-4);
		border-top: 1px solid var(--border);
	}

	.btn-reset {
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-reset:hover:not(:disabled) {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	.btn-reset:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Spinners */
	.spinner {
		width: 24px;
		height: 24px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.spinner-small {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Responsive */
	@media (max-width: 600px) {
		.settings-page {
			padding: var(--space-4);
		}

		.form-row {
			flex-direction: column;
			align-items: stretch;
		}

		.form-field {
			min-width: 100%;
		}

		.btn-save {
			width: 100%;
		}

		.threshold-row {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-2);
		}

		.threshold-input {
			width: 100%;
		}

		.threshold-input input {
			flex: 1;
		}
	}
</style>
