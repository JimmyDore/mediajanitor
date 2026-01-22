<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toasts, authenticatedFetch } from '$lib/stores';

	// Jellyfin form state
	let jellyfinUrl = $state('');
	let jellyfinApiKey = $state('');
	let jellyfinError = $state<string | null>(null);
	let jellyfinSuccess = $state<string | null>(null);
	let isJellyfinLoading = $state(false);

	// Jellyfin current settings state
	let hasJellyfinConfigured = $state(false);
	let currentJellyfinUrl = $state<string | null>(null);

	// Sync status for auto-sync
	let hasNeverSynced = $state(true);

	// Jellyseerr form state
	let jellyseerrUrl = $state('');
	let jellyseerrApiKey = $state('');
	let jellyseerrError = $state<string | null>(null);
	let jellyseerrSuccess = $state<string | null>(null);
	let isJellyseerrLoading = $state(false);

	// Jellyseerr current settings state
	let hasJellyseerrConfigured = $state(false);
	let currentJellyseerrUrl = $state<string | null>(null);

	// Radarr form state
	let radarrUrl = $state('');
	let radarrApiKey = $state('');
	let radarrError = $state<string | null>(null);
	let radarrSuccess = $state<string | null>(null);
	let isRadarrLoading = $state(false);

	// Radarr current settings state
	let hasRadarrConfigured = $state(false);
	let currentRadarrUrl = $state<string | null>(null);

	// Sonarr form state
	let sonarrUrl = $state('');
	let sonarrApiKey = $state('');
	let sonarrError = $state<string | null>(null);
	let sonarrSuccess = $state<string | null>(null);
	let isSonarrLoading = $state(false);

	// Sonarr current settings state
	let hasSonarrConfigured = $state(false);
	let currentSonarrUrl = $state<string | null>(null);

	// Ultra form state
	let ultraUrl = $state('');
	let ultraApiKey = $state('');
	let ultraError = $state<string | null>(null);
	let ultraSuccess = $state<string | null>(null);
	let isUltraLoading = $state(false);

	// Ultra current settings state
	let hasUltraConfigured = $state(false);
	let currentUltraUrl = $state<string | null>(null);

	// Ultra thresholds state
	let ultraStorageWarningGb = $state(100);
	let ultraTrafficWarningPercent = $state(20);
	let ultraThresholdsError = $state<string | null>(null);
	let ultraThresholdsSuccess = $state<string | null>(null);
	let isUltraThresholdsLoading = $state(false);

	// Loading state
	let isFetchingSettings = $state(true);

	// Expand/collapse states
	let jellyfinExpanded = $state(false);
	let jellyseerrExpanded = $state(false);
	let radarrExpanded = $state(false);
	let sonarrExpanded = $state(false);
	let ultraExpanded = $state(false);

	onMount(async () => {
		await loadCurrentSettings();
	});

	async function loadCurrentSettings() {
		try {
			// Load Jellyfin settings
			const jellyfinResponse = await authenticatedFetch('/api/settings/jellyfin');

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
			const jellyseerrResponse = await authenticatedFetch('/api/settings/jellyseerr');

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

			// Load Radarr settings
			const radarrResponse = await authenticatedFetch('/api/settings/radarr');

			if (radarrResponse.ok) {
				const data = await radarrResponse.json();
				hasRadarrConfigured = data.api_key_configured;
				currentRadarrUrl = data.server_url;
				if (data.server_url) {
					radarrUrl = data.server_url;
				}
			}

			// Load Sonarr settings
			const sonarrResponse = await authenticatedFetch('/api/settings/sonarr');

			if (sonarrResponse.ok) {
				const data = await sonarrResponse.json();
				hasSonarrConfigured = data.api_key_configured;
				currentSonarrUrl = data.server_url;
				if (data.server_url) {
					sonarrUrl = data.server_url;
				}
			}

			// Load Ultra settings
			const ultraResponse = await authenticatedFetch('/api/settings/ultra');

			if (ultraResponse.ok) {
				const data = await ultraResponse.json();
				hasUltraConfigured = data.api_key_configured;
				currentUltraUrl = data.server_url;
				if (data.server_url) {
					ultraUrl = data.server_url;
				}
			}

			// Load Ultra thresholds
			const ultraThresholdsResponse = await authenticatedFetch('/api/settings/ultra/thresholds');

			if (ultraThresholdsResponse.ok) {
				const data = await ultraThresholdsResponse.json();
				ultraStorageWarningGb = data.storage_warning_gb;
				ultraTrafficWarningPercent = data.traffic_warning_percent;
			}

			// Load sync status to check if user has never synced
			const syncResponse = await authenticatedFetch('/api/sync/status');
			if (syncResponse.ok) {
				const syncData = await syncResponse.json();
				hasNeverSynced = syncData.last_synced === null;
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
			const response = await authenticatedFetch('/api/settings/jellyfin', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
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
			const wasFirstConfiguration = !hasJellyfinConfigured;
			hasJellyfinConfigured = true;
			currentJellyfinUrl = jellyfinUrl;
			jellyfinApiKey = '';
			jellyfinExpanded = false;

			// Auto-sync after first Jellyfin configuration if user has never synced
			if (wasFirstConfiguration && hasNeverSynced) {
				jellyfinSuccess = 'Connected - starting sync...';
				// Navigate to dashboard where sync will be shown in checklist
				toasts.add('Jellyfin connected! Starting first sync...', 'success');
				goto('/');
				return;
			}

			setTimeout(() => (jellyfinSuccess = null), 3000);
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
			const response = await authenticatedFetch('/api/settings/jellyseerr', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
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
			setTimeout(() => (jellyseerrSuccess = null), 3000);
		} catch (e) {
			jellyseerrError = e instanceof Error ? e.message : 'Failed to save settings';
		} finally {
			isJellyseerrLoading = false;
		}
	}

	async function handleRadarrSubmit(event: SubmitEvent) {
		event.preventDefault();
		radarrError = null;
		radarrSuccess = null;
		isRadarrLoading = true;

		try {
			const response = await authenticatedFetch('/api/settings/radarr', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					server_url: radarrUrl,
					api_key: radarrApiKey
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save settings');
			}

			radarrSuccess = 'Connected';
			hasRadarrConfigured = true;
			currentRadarrUrl = radarrUrl;
			radarrApiKey = '';
			radarrExpanded = false;
			setTimeout(() => (radarrSuccess = null), 3000);
		} catch (e) {
			radarrError = e instanceof Error ? e.message : 'Failed to save settings';
		} finally {
			isRadarrLoading = false;
		}
	}

	async function handleSonarrSubmit(event: SubmitEvent) {
		event.preventDefault();
		sonarrError = null;
		sonarrSuccess = null;
		isSonarrLoading = true;

		try {
			const response = await authenticatedFetch('/api/settings/sonarr', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					server_url: sonarrUrl,
					api_key: sonarrApiKey
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save settings');
			}

			sonarrSuccess = 'Connected';
			hasSonarrConfigured = true;
			currentSonarrUrl = sonarrUrl;
			sonarrApiKey = '';
			sonarrExpanded = false;
			setTimeout(() => (sonarrSuccess = null), 3000);
		} catch (e) {
			sonarrError = e instanceof Error ? e.message : 'Failed to save settings';
		} finally {
			isSonarrLoading = false;
		}
	}

	async function handleUltraSubmit(event: SubmitEvent) {
		event.preventDefault();
		ultraError = null;
		ultraSuccess = null;
		isUltraLoading = true;

		try {
			const response = await authenticatedFetch('/api/settings/ultra', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					server_url: ultraUrl,
					api_key: ultraApiKey
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save settings');
			}

			ultraSuccess = 'Connected';
			hasUltraConfigured = true;
			currentUltraUrl = ultraUrl;
			ultraApiKey = '';
			ultraExpanded = false;
			setTimeout(() => (ultraSuccess = null), 3000);
		} catch (e) {
			ultraError = e instanceof Error ? e.message : 'Failed to save settings';
		} finally {
			isUltraLoading = false;
		}
	}

	async function handleUltraThresholdsSubmit(event: SubmitEvent) {
		event.preventDefault();
		ultraThresholdsError = null;
		ultraThresholdsSuccess = null;
		isUltraThresholdsLoading = true;

		try {
			const response = await authenticatedFetch('/api/settings/ultra/thresholds', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					storage_warning_gb: ultraStorageWarningGb,
					traffic_warning_percent: ultraTrafficWarningPercent
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save thresholds');
			}

			ultraThresholdsSuccess = 'Saved';
			setTimeout(() => (ultraThresholdsSuccess = null), 3000);
		} catch (e) {
			ultraThresholdsError = e instanceof Error ? e.message : 'Failed to save thresholds';
		} finally {
			isUltraThresholdsLoading = false;
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

<div class="connections-page" aria-busy={isFetchingSettings}>
	<header class="page-header">
		<h1>Connections</h1>
		<p class="page-description">Connect your media services to enable syncing and monitoring.</p>
	</header>

	{#if isFetchingSettings}
		<div class="loading" role="status" aria-label="Loading connection settings">
			<span class="spinner" aria-hidden="true"></span>
		</div>
	{:else}
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
				onclick={() => (jellyfinExpanded = !jellyfinExpanded)}
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
				onclick={() => (jellyseerrExpanded = !jellyseerrExpanded)}
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

		<div class="divider"></div>

		<!-- Radarr -->
		<div class="connection-row">
			<div class="connection-info">
				<div class="connection-header">
					<span class="connection-name">Radarr</span>
					{#if hasRadarrConfigured}
						<span class="status-dot status-connected" title="Connected"></span>
					{:else}
						<span class="status-dot status-disconnected" title="Not connected"></span>
					{/if}
				</div>
				{#if hasRadarrConfigured && currentRadarrUrl}
					<span class="connection-url">{extractDomain(currentRadarrUrl)}</span>
				{:else}
					<span class="connection-url muted">Not configured</span>
				{/if}
			</div>
			<button
				class="btn-edit"
				onclick={() => (radarrExpanded = !radarrExpanded)}
				aria-expanded={radarrExpanded}
			>
				{radarrExpanded ? 'Cancel' : hasRadarrConfigured ? 'Edit' : 'Configure'}
			</button>
		</div>

		{#if radarrExpanded}
			<form onsubmit={handleRadarrSubmit} class="connection-form">
				{#if radarrError}
					<div class="inline-error">{radarrError}</div>
				{/if}
				{#if radarrSuccess}
					<div class="inline-success">{radarrSuccess}</div>
				{/if}
				<div class="form-row">
					<div class="form-field">
						<label for="radarr-url">Server URL</label>
						<input
							type="url"
							id="radarr-url"
							bind:value={radarrUrl}
							required
							placeholder="https://radarr.example.com"
						/>
					</div>
					<div class="form-field">
						<label for="radarr-key">
							API Key
							{#if hasRadarrConfigured}
								<span class="optional">(leave blank to keep)</span>
							{/if}
						</label>
						<input
							type="password"
							id="radarr-key"
							bind:value={radarrApiKey}
							required={!hasRadarrConfigured}
							placeholder={hasRadarrConfigured ? '••••••••' : 'API key'}
							autocomplete="off"
						/>
					</div>
					<button type="submit" class="btn-save" disabled={isRadarrLoading}>
						{#if isRadarrLoading}
							<span class="spinner-small"></span>
						{:else}
							Save
						{/if}
					</button>
				</div>
			</form>
		{/if}

		<div class="divider"></div>

		<!-- Sonarr -->
		<div class="connection-row">
			<div class="connection-info">
				<div class="connection-header">
					<span class="connection-name">Sonarr</span>
					{#if hasSonarrConfigured}
						<span class="status-dot status-connected" title="Connected"></span>
					{:else}
						<span class="status-dot status-disconnected" title="Not connected"></span>
					{/if}
				</div>
				{#if hasSonarrConfigured && currentSonarrUrl}
					<span class="connection-url">{extractDomain(currentSonarrUrl)}</span>
				{:else}
					<span class="connection-url muted">Not configured</span>
				{/if}
			</div>
			<button
				class="btn-edit"
				onclick={() => (sonarrExpanded = !sonarrExpanded)}
				aria-expanded={sonarrExpanded}
			>
				{sonarrExpanded ? 'Cancel' : hasSonarrConfigured ? 'Edit' : 'Configure'}
			</button>
		</div>

		{#if sonarrExpanded}
			<form onsubmit={handleSonarrSubmit} class="connection-form">
				{#if sonarrError}
					<div class="inline-error">{sonarrError}</div>
				{/if}
				{#if sonarrSuccess}
					<div class="inline-success">{sonarrSuccess}</div>
				{/if}
				<div class="form-row">
					<div class="form-field">
						<label for="sonarr-url">Server URL</label>
						<input
							type="url"
							id="sonarr-url"
							bind:value={sonarrUrl}
							required
							placeholder="https://sonarr.example.com"
						/>
					</div>
					<div class="form-field">
						<label for="sonarr-key">
							API Key
							{#if hasSonarrConfigured}
								<span class="optional">(leave blank to keep)</span>
							{/if}
						</label>
						<input
							type="password"
							id="sonarr-key"
							bind:value={sonarrApiKey}
							required={!hasSonarrConfigured}
							placeholder={hasSonarrConfigured ? '••••••••' : 'API key'}
							autocomplete="off"
						/>
					</div>
					<button type="submit" class="btn-save" disabled={isSonarrLoading}>
						{#if isSonarrLoading}
							<span class="spinner-small"></span>
						{:else}
							Save
						{/if}
					</button>
				</div>
			</form>
		{/if}

		<!-- Seedbox Monitoring Section -->
		<div class="section-header">
			<h2>Seedbox Monitoring</h2>
			<p class="section-description">Monitor your Ultra.cc seedbox storage and traffic.</p>
		</div>

		<!-- Ultra.cc -->
		<div class="connection-row">
			<div class="connection-info">
				<div class="connection-header">
					<span class="connection-name">Ultra.cc</span>
					{#if hasUltraConfigured}
						<span class="status-dot status-connected" title="Connected"></span>
					{:else}
						<span class="status-dot status-disconnected" title="Not connected"></span>
					{/if}
				</div>
				{#if hasUltraConfigured && currentUltraUrl}
					<span class="connection-url">{extractDomain(currentUltraUrl)}</span>
				{:else}
					<span class="connection-url muted">Not configured</span>
				{/if}
			</div>
			<button
				class="btn-edit"
				onclick={() => (ultraExpanded = !ultraExpanded)}
				aria-expanded={ultraExpanded}
			>
				{ultraExpanded ? 'Cancel' : hasUltraConfigured ? 'Edit' : 'Configure'}
			</button>
		</div>

		{#if ultraExpanded}
			<form onsubmit={handleUltraSubmit} class="connection-form">
				{#if ultraError}
					<div class="inline-error">{ultraError}</div>
				{/if}
				{#if ultraSuccess}
					<div class="inline-success">{ultraSuccess}</div>
				{/if}
				<div class="form-row">
					<div class="form-field">
						<label for="ultra-url">API URL</label>
						<input
							type="url"
							id="ultra-url"
							bind:value={ultraUrl}
							required
							placeholder="https://api.ultra.cc"
						/>
					</div>
					<div class="form-field">
						<label for="ultra-key">
							API Token
							{#if hasUltraConfigured}
								<span class="optional">(leave blank to keep)</span>
							{/if}
						</label>
						<input
							type="password"
							id="ultra-key"
							bind:value={ultraApiKey}
							required={!hasUltraConfigured}
							placeholder={hasUltraConfigured ? '••••••••' : 'API token'}
							autocomplete="off"
						/>
					</div>
					<button type="submit" class="btn-save" disabled={isUltraLoading}>
						{#if isUltraLoading}
							<span class="spinner-small"></span>
						{:else}
							Save
						{/if}
					</button>
				</div>
			</form>
		{/if}

		<div class="divider"></div>

		<!-- Ultra Warning Thresholds -->
		<div class="thresholds-section">
			<h3 class="thresholds-title">Warning Thresholds</h3>
			<form onsubmit={handleUltraThresholdsSubmit} class="thresholds-form">
				{#if ultraThresholdsError}
					<div class="inline-error">{ultraThresholdsError}</div>
				{/if}
				{#if ultraThresholdsSuccess}
					<div class="inline-success">{ultraThresholdsSuccess}</div>
				{/if}

				<div class="threshold-row">
					<div class="threshold-label-group">
						<label for="storage-warning">Warn when storage falls below</label>
					</div>
					<div class="threshold-input">
						<input
							type="number"
							id="storage-warning"
							bind:value={ultraStorageWarningGb}
							min="1"
							max="1000"
							required
						/>
						<span class="unit">GB</span>
					</div>
				</div>

				<div class="threshold-row">
					<div class="threshold-label-group">
						<label for="traffic-warning">Warn when traffic falls below</label>
					</div>
					<div class="threshold-input">
						<input
							type="number"
							id="traffic-warning"
							bind:value={ultraTrafficWarningPercent}
							min="1"
							max="100"
							required
						/>
						<span class="unit">%</span>
					</div>
				</div>

				<div class="threshold-actions">
					<button type="submit" class="btn-save" disabled={isUltraThresholdsLoading}>
						{#if isUltraThresholdsLoading}
							<span class="spinner-small"></span>
						{:else}
							Save
						{/if}
					</button>
				</div>
			</form>
		</div>
	{/if}
</div>

<style>
	.connections-page {
		max-width: 640px;
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

	.loading {
		display: flex;
		justify-content: center;
		padding: var(--space-12);
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
		to {
			transform: rotate(360deg);
		}
	}

	/* Section Header */
	.section-header {
		margin-top: var(--space-8);
		margin-bottom: var(--space-4);
		padding-top: var(--space-6);
		border-top: 1px solid var(--border);
	}

	.section-header h2 {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.01em;
		margin-bottom: var(--space-1);
	}

	.section-description {
		color: var(--text-muted);
		font-size: var(--font-size-sm);
	}

	/* Thresholds Section */
	.thresholds-section {
		margin-top: var(--space-2);
	}

	.thresholds-title {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		margin-bottom: var(--space-3);
	}

	.thresholds-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
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

	.threshold-label-group {
		display: flex;
		flex-direction: column;
		gap: 2px;
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
		min-width: 30px;
	}

	.threshold-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		margin-top: var(--space-3);
	}

	/* Responsive */
	@media (max-width: 600px) {
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
