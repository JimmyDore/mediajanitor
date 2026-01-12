<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
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

	function handleBack() {
		goto('/');
	}
</script>

<svelte:head>
	<title>Settings - Plex Dashboard</title>
</svelte:head>

<div class="settings-container">
	<div class="header">
		<button onclick={handleBack} class="back-button">
			&larr; Back to Dashboard
		</button>
		<h1>Settings</h1>
	</div>

	{#if isFetchingSettings}
		<div class="loading">Loading settings...</div>
	{:else}
		<section class="settings-section">
			<h2>Jellyfin Connection</h2>
			<p class="section-description">
				Connect your Jellyfin server to analyze your media library.
			</p>

			{#if hasJellyfinConfigured}
				<div class="status-badge connected">
					Connected to {currentJellyfinUrl}
				</div>
			{:else}
				<div class="status-badge not-connected">
					Not connected
				</div>
			{/if}

			<form onsubmit={handleJellyfinSubmit} class="settings-form">
				{#if jellyfinError}
					<div class="message error-message" role="alert">
						{jellyfinError}
					</div>
				{/if}

				{#if jellyfinSuccess}
					<div class="message success-message" role="status">
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
					/>
					<span class="hint">The full URL to your Jellyfin server</span>
				</div>

				<div class="form-group">
					<label for="jellyfin-api-key">
						API Key
						{#if hasJellyfinConfigured}
							<span class="optional">(leave blank to keep current)</span>
						{/if}
					</label>
					<input
						type="password"
						id="jellyfin-api-key"
						bind:value={jellyfinApiKey}
						required={!hasJellyfinConfigured}
						placeholder={hasJellyfinConfigured ? '••••••••••••••••' : 'Enter your API key'}
						autocomplete="off"
					/>
					<span class="hint">
						Find this in Jellyfin Dashboard → API Keys
					</span>
				</div>

				<button type="submit" disabled={isJellyfinLoading} class="submit-button">
					{#if isJellyfinLoading}
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
			<h2>Jellyseerr Connection</h2>
			<p class="section-description">
				Connect your Jellyseerr server to track media requests.
			</p>

			{#if hasJellyseerrConfigured}
				<div class="status-badge connected">
					Connected to {currentJellyseerrUrl}
				</div>
			{:else}
				<div class="status-badge not-connected">
					Not connected
				</div>
			{/if}

			<form onsubmit={handleJellyseerrSubmit} class="settings-form">
				{#if jellyseerrError}
					<div class="message error-message" role="alert">
						{jellyseerrError}
					</div>
				{/if}

				{#if jellyseerrSuccess}
					<div class="message success-message" role="status">
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
					/>
					<span class="hint">The full URL to your Jellyseerr server</span>
				</div>

				<div class="form-group">
					<label for="jellyseerr-api-key">
						API Key
						{#if hasJellyseerrConfigured}
							<span class="optional">(leave blank to keep current)</span>
						{/if}
					</label>
					<input
						type="password"
						id="jellyseerr-api-key"
						bind:value={jellyseerrApiKey}
						required={!hasJellyseerrConfigured}
						placeholder={hasJellyseerrConfigured ? '••••••••••••••••' : 'Enter your API key'}
						autocomplete="off"
					/>
					<span class="hint">
						Find this in Jellyseerr Settings → General → API Key
					</span>
				</div>

				<button type="submit" disabled={isJellyseerrLoading} class="submit-button">
					{#if isJellyseerrLoading}
						Validating connection...
					{:else if hasJellyseerrConfigured}
						Update Connection
					{:else}
						Connect to Jellyseerr
					{/if}
				</button>
			</form>
		</section>
	{/if}
</div>

<style>
	.settings-container {
		max-width: 600px;
		margin: 0 auto;
		padding: 1rem;
	}

	.header {
		margin-bottom: 2rem;
	}

	.back-button {
		background: none;
		border: none;
		color: var(--accent);
		cursor: pointer;
		padding: 0.5rem 0;
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.back-button:hover {
		text-decoration: underline;
	}

	h1 {
		color: var(--text);
		font-size: 2rem;
		font-weight: 700;
		margin: 0;
	}

	.loading {
		text-align: center;
		color: var(--text-secondary);
		padding: 2rem;
	}

	.settings-section {
		background: var(--bg-secondary);
		border-radius: 0.75rem;
		padding: 1.5rem;
		border: 1px solid var(--border);
		margin-bottom: 1.5rem;
	}

	.settings-section:last-child {
		margin-bottom: 0;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text);
	}

	.section-description {
		color: var(--text-secondary);
		margin: 0 0 1rem 0;
		font-size: 0.875rem;
	}

	.status-badge {
		display: inline-block;
		padding: 0.5rem 1rem;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		margin-bottom: 1.5rem;
	}

	.status-badge.connected {
		background: rgba(16, 185, 129, 0.1);
		color: #10b981;
		border: 1px solid rgba(16, 185, 129, 0.3);
	}

	.status-badge.not-connected {
		background: rgba(245, 158, 11, 0.1);
		color: #f59e0b;
		border: 1px solid rgba(245, 158, 11, 0.3);
	}

	.settings-form {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	label {
		font-weight: 500;
		color: var(--text);
		font-size: 0.875rem;
	}

	.optional {
		font-weight: 400;
		color: var(--text-secondary);
		font-size: 0.75rem;
	}

	input {
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		font-size: 1rem;
		background: var(--bg-primary);
		color: var(--text);
		transition: border-color 0.2s;
	}

	input:focus {
		outline: none;
		border-color: var(--accent);
	}

	input::placeholder {
		color: var(--text-secondary);
		opacity: 0.6;
	}

	.hint {
		color: var(--text-secondary);
		font-size: 0.75rem;
	}

	.message {
		padding: 1rem;
		border-radius: 0.5rem;
	}

	.error-message {
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.3);
		color: var(--danger);
	}

	.success-message {
		background: rgba(16, 185, 129, 0.1);
		border: 1px solid rgba(16, 185, 129, 0.3);
		color: #10b981;
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
		margin-top: 0.5rem;
	}

	.submit-button:hover:not(:disabled) {
		opacity: 0.9;
	}

	.submit-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
