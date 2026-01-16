<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { theme, toasts, authenticatedFetch, type ThemePreference } from '$lib/stores';

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

	// Analysis preferences state
	let oldContentMonths = $state(4);
	let minAgeMonths = $state(3);
	let largeMovieSizeGb = $state(13);
	let largeSeasonSizeGb = $state(15);
	let analysisError = $state<string | null>(null);
	let analysisSuccess = $state<string | null>(null);
	let isAnalysisLoading = $state(false);

	// Display preferences state
	let showUnreleasedRequests = $state(false);
	let recentlyAvailableDays = $state(7);
	let currentTheme = $state<ThemePreference>('system');
	let titleLanguage = $state<'en' | 'fr'>('en');
	let displayError = $state<string | null>(null);
	let displaySuccess = $state<string | null>(null);
	let isDisplayLoading = $state(false);
	let isThemeLoading = $state(false);
	let isRecentDaysLoading = $state(false);
	let isTitleLanguageLoading = $state(false);

	// Nickname state
	interface NicknameItem {
		id: number;
		jellyseerr_username: string;
		display_name: string;
		created_at: string;
	}
	let nicknames = $state<NicknameItem[]>([]);
	let isNicknamesLoading = $state(false);
	let showAddNicknameForm = $state(false);
	let newNicknameUsername = $state('');
	let newNicknameDisplayName = $state('');
	let isAddingNickname = $state(false);
	let editingNicknameId = $state<number | null>(null);
	let editingDisplayName = $state('');
	let isSavingEdit = $state(false);
	let deleteConfirmId = $state<number | null>(null);
	let isDeletingNickname = $state(false);
	let isRefreshingUsers = $state(false);

	// Expand/collapse states
	let jellyfinExpanded = $state(false);
	let jellyseerrExpanded = $state(false);
	let radarrExpanded = $state(false);
	let sonarrExpanded = $state(false);

	// Default values for reset
	const DEFAULT_OLD_CONTENT_MONTHS = 4;
	const DEFAULT_MIN_AGE_MONTHS = 3;
	const DEFAULT_LARGE_MOVIE_SIZE_GB = 13;
	const DEFAULT_LARGE_SEASON_SIZE_GB = 15;

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

			// Load analysis preferences
			const analysisResponse = await authenticatedFetch('/api/settings/analysis');

			if (analysisResponse.ok) {
				const data = await analysisResponse.json();
				oldContentMonths = data.old_content_months;
				minAgeMonths = data.min_age_months;
				largeMovieSizeGb = data.large_movie_size_gb;
				largeSeasonSizeGb = data.large_season_size_gb ?? 15;
			}

			// Load display preferences
			const displayResponse = await authenticatedFetch('/api/settings/display');

			if (displayResponse.ok) {
				const data = await displayResponse.json();
				showUnreleasedRequests = data.show_unreleased_requests;
				recentlyAvailableDays = data.recently_available_days ?? 7;
				currentTheme = data.theme_preference || 'system';
				titleLanguage = data.title_language || 'en';
			}

			// Load nicknames
			await loadNicknames();

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

	async function loadNicknames() {
		isNicknamesLoading = true;
		try {
			const response = await authenticatedFetch('/api/settings/nicknames');
			if (response.ok) {
				const data = await response.json();
				nicknames = data.items;
			}
		} catch (e) {
			console.error('Failed to load nicknames:', e);
		} finally {
			isNicknamesLoading = false;
		}
	}

	async function handleRefreshUsers() {
		isRefreshingUsers = true;

		try {
			const response = await authenticatedFetch('/api/settings/nicknames/refresh', {
				method: 'POST'
			});

			if (!response.ok) {
				const data = await response.json();
				toasts.add(data.detail || 'Failed to refresh users', 'error');
				return;
			}

			const data = await response.json();
			toasts.add(data.message, 'success');
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to refresh users', 'error');
		} finally {
			isRefreshingUsers = false;
		}
	}

	async function handleAddNickname(event: SubmitEvent) {
		event.preventDefault();
		isAddingNickname = true;

		try {
			const response = await authenticatedFetch('/api/settings/nicknames', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					jellyseerr_username: newNicknameUsername.trim(),
					display_name: newNicknameDisplayName.trim()
				})
			});

			if (!response.ok) {
				const data = await response.json();
				if (response.status === 409) {
					toasts.add('This username already has a nickname', 'error');
				} else {
					toasts.add(data.detail || 'Failed to add nickname', 'error');
				}
				return;
			}

			toasts.add('Nickname added', 'success');
			newNicknameUsername = '';
			newNicknameDisplayName = '';
			showAddNicknameForm = false;
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to add nickname', 'error');
		} finally {
			isAddingNickname = false;
		}
	}

	function startEditNickname(nickname: NicknameItem) {
		editingNicknameId = nickname.id;
		editingDisplayName = nickname.display_name;
	}

	function cancelEditNickname() {
		editingNicknameId = null;
		editingDisplayName = '';
	}

	async function saveEditNickname(id: number) {
		isSavingEdit = true;

		try {
			const response = await authenticatedFetch(`/api/settings/nicknames/${id}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					display_name: editingDisplayName.trim()
				})
			});

			if (!response.ok) {
				const data = await response.json();
				toasts.add(data.detail || 'Failed to update nickname', 'error');
				return;
			}

			toasts.add('Nickname updated', 'success');
			editingNicknameId = null;
			editingDisplayName = '';
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to update nickname', 'error');
		} finally {
			isSavingEdit = false;
		}
	}

	async function confirmDeleteNickname(id: number) {
		isDeletingNickname = true;

		try {
			const response = await authenticatedFetch(`/api/settings/nicknames/${id}`, {
				method: 'DELETE'
			});

			if (!response.ok) {
				const data = await response.json();
				toasts.add(data.detail || 'Failed to delete nickname', 'error');
				return;
			}

			toasts.add('Nickname removed', 'success');
			deleteConfirmId = null;
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to delete nickname', 'error');
		} finally {
			isDeletingNickname = false;
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
			setTimeout(() => jellyseerrSuccess = null, 3000);
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
			setTimeout(() => radarrSuccess = null, 3000);
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
			setTimeout(() => sonarrSuccess = null, 3000);
		} catch (e) {
			sonarrError = e instanceof Error ? e.message : 'Failed to save settings';
		} finally {
			isSonarrLoading = false;
		}
	}

	async function handleAnalysisSubmit(event: SubmitEvent) {
		event.preventDefault();
		analysisError = null;
		analysisSuccess = null;
		isAnalysisLoading = true;

		try {
			const response = await authenticatedFetch('/api/settings/analysis', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					old_content_months: oldContentMonths,
					min_age_months: minAgeMonths,
					large_movie_size_gb: largeMovieSizeGb,
					large_season_size_gb: largeSeasonSizeGb
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
			const response = await authenticatedFetch('/api/settings/analysis', {
				method: 'DELETE'
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to reset preferences');
			}

			oldContentMonths = DEFAULT_OLD_CONTENT_MONTHS;
			minAgeMonths = DEFAULT_MIN_AGE_MONTHS;
			largeMovieSizeGb = DEFAULT_LARGE_MOVIE_SIZE_GB;
			largeSeasonSizeGb = DEFAULT_LARGE_SEASON_SIZE_GB;

			analysisSuccess = 'Reset to defaults';
			setTimeout(() => analysisSuccess = null, 3000);
		} catch (e) {
			analysisError = e instanceof Error ? e.message : 'Failed to reset preferences';
		} finally {
			isAnalysisLoading = false;
		}
	}

	async function handleDisplayToggle() {
		displayError = null;
		displaySuccess = null;
		isDisplayLoading = true;

		// Toggle the value optimistically
		showUnreleasedRequests = !showUnreleasedRequests;

		try {
			const response = await authenticatedFetch('/api/settings/display', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					show_unreleased_requests: showUnreleasedRequests
				})
			});

			const data = await response.json();

			if (!response.ok) {
				// Revert on error
				showUnreleasedRequests = !showUnreleasedRequests;
				throw new Error(data.detail || 'Failed to save setting');
			}

			displaySuccess = 'Saved';
			setTimeout(() => displaySuccess = null, 3000);
		} catch (e) {
			displayError = e instanceof Error ? e.message : 'Failed to save setting';
		} finally {
			isDisplayLoading = false;
		}
	}

	async function handleThemeChange(newTheme: ThemePreference) {
		if (newTheme === currentTheme) return;

		isThemeLoading = true;
		const success = await theme.saveToApi(newTheme);

		if (success) {
			currentTheme = newTheme;
			toasts.add('Theme updated', 'success');
		} else {
			toasts.add('Failed to save theme preference', 'error');
		}

		isThemeLoading = false;
	}

	async function handleRecentDaysChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const newValue = parseInt(input.value, 10);

		if (isNaN(newValue) || newValue < 1 || newValue > 30) {
			return;
		}

		isRecentDaysLoading = true;
		displayError = null;
		displaySuccess = null;

		try {
			const response = await authenticatedFetch('/api/settings/display', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					recently_available_days: newValue
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save setting');
			}

			recentlyAvailableDays = newValue;
			displaySuccess = 'Saved';
			setTimeout(() => displaySuccess = null, 3000);
		} catch (e) {
			displayError = e instanceof Error ? e.message : 'Failed to save setting';
		} finally {
			isRecentDaysLoading = false;
		}
	}

	async function handleTitleLanguageChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		const newValue = select.value as 'en' | 'fr';

		if (newValue === titleLanguage) return;

		isTitleLanguageLoading = true;
		displayError = null;
		displaySuccess = null;

		try {
			const response = await authenticatedFetch('/api/settings/display', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					title_language: newValue
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to save setting');
			}

			titleLanguage = newValue;
			displaySuccess = 'Saved';
			setTimeout(() => displaySuccess = null, 3000);
		} catch (e) {
			displayError = e instanceof Error ? e.message : 'Failed to save setting';
		} finally {
			isTitleLanguageLoading = false;
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
					onclick={() => radarrExpanded = !radarrExpanded}
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
					onclick={() => sonarrExpanded = !sonarrExpanded}
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
		</section>

		<!-- User Nicknames Section -->
		<section class="section">
			<div class="section-header">
				<h2 class="section-title">User Nicknames</h2>
				{#if hasJellyfinConfigured}
					<button
						class="btn-refresh"
						onclick={handleRefreshUsers}
						disabled={isRefreshingUsers}
						title="Fetch Jellyfin users to populate nickname list"
					>
						{#if isRefreshingUsers}
							<span class="spinner-small spinner-inline"></span>
							Refreshing...
						{:else}
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M23 4v6h-6"/>
								<path d="M1 20v-6h6"/>
								<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
							</svg>
							Refresh users
						{/if}
					</button>
				{/if}
			</div>

			{#if isNicknamesLoading}
				<div class="nicknames-loading">
					<span class="spinner-small spinner-inline"></span>
					<span>Loading nicknames...</span>
				</div>
			{:else if nicknames.length === 0 && !showAddNicknameForm}
				<div class="nicknames-empty">
					<p>No nicknames configured. Add nicknames to customize how requesters appear in notifications.</p>
					<button class="btn-add" onclick={() => showAddNicknameForm = true}>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="12" y1="5" x2="12" y2="19"/>
							<line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
						Add nickname
					</button>
				</div>
			{:else}
				<!-- Nicknames Table -->
				{#if nicknames.length > 0}
					<div class="nicknames-table">
						<div class="nicknames-header">
							<span class="col-username">Jellyseerr Username</span>
							<span class="col-arrow">→</span>
							<span class="col-displayname">Display Name</span>
							<span class="col-actions">Actions</span>
						</div>
						{#each nicknames as nickname (nickname.id)}
							<div class="nickname-row">
								{#if editingNicknameId === nickname.id}
									<!-- Editing mode -->
									<span class="col-username nickname-value">{nickname.jellyseerr_username}</span>
									<span class="col-arrow">→</span>
									<input
										type="text"
										class="col-displayname edit-input"
										bind:value={editingDisplayName}
										placeholder="Display name"
										disabled={isSavingEdit}
									/>
									<span class="col-actions">
										<button
											class="btn-icon btn-save-icon"
											onclick={() => saveEditNickname(nickname.id)}
											disabled={isSavingEdit || !editingDisplayName.trim()}
											title="Save"
										>
											{#if isSavingEdit}
												<span class="spinner-small spinner-inline"></span>
											{:else}
												<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
													<polyline points="20 6 9 17 4 12"/>
												</svg>
											{/if}
										</button>
										<button
											class="btn-icon btn-cancel-icon"
											onclick={cancelEditNickname}
											disabled={isSavingEdit}
											title="Cancel"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<line x1="18" y1="6" x2="6" y2="18"/>
												<line x1="6" y1="6" x2="18" y2="18"/>
											</svg>
										</button>
									</span>
								{:else if deleteConfirmId === nickname.id}
									<!-- Delete confirmation mode -->
									<span class="col-username nickname-value">{nickname.jellyseerr_username}</span>
									<span class="col-arrow">→</span>
									<span class="col-displayname delete-confirm-text">Delete this nickname?</span>
									<span class="col-actions">
										<button
											class="btn-icon btn-confirm-delete"
											onclick={() => confirmDeleteNickname(nickname.id)}
											disabled={isDeletingNickname}
											title="Confirm delete"
										>
											{#if isDeletingNickname}
												<span class="spinner-small spinner-inline"></span>
											{:else}
												<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
													<polyline points="20 6 9 17 4 12"/>
												</svg>
											{/if}
										</button>
										<button
											class="btn-icon btn-cancel-icon"
											onclick={() => deleteConfirmId = null}
											disabled={isDeletingNickname}
											title="Cancel"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<line x1="18" y1="6" x2="6" y2="18"/>
												<line x1="6" y1="6" x2="18" y2="18"/>
											</svg>
										</button>
									</span>
								{:else}
									<!-- Normal display mode -->
									<span class="col-username nickname-value">{nickname.jellyseerr_username}</span>
									<span class="col-arrow">→</span>
									<span class="col-displayname nickname-value">{nickname.display_name}</span>
									<span class="col-actions">
										<button
											class="btn-icon btn-edit-icon"
											onclick={() => startEditNickname(nickname)}
											title="Edit"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
												<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
											</svg>
										</button>
										<button
											class="btn-icon btn-delete-icon"
											onclick={() => deleteConfirmId = nickname.id}
											title="Delete"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<polyline points="3 6 5 6 21 6"/>
												<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
											</svg>
										</button>
									</span>
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				<!-- Add Nickname Form -->
				{#if showAddNicknameForm}
					<form onsubmit={handleAddNickname} class="add-nickname-form">
						<div class="add-nickname-row">
							<input
								type="text"
								class="add-input"
								bind:value={newNicknameUsername}
								placeholder="Jellyseerr username"
								disabled={isAddingNickname}
								required
							/>
							<span class="add-arrow">→</span>
							<input
								type="text"
								class="add-input"
								bind:value={newNicknameDisplayName}
								placeholder="Display name"
								disabled={isAddingNickname}
								required
							/>
							<button
								type="submit"
								class="btn-icon btn-save-icon"
								disabled={isAddingNickname || !newNicknameUsername.trim() || !newNicknameDisplayName.trim()}
								title="Add"
							>
								{#if isAddingNickname}
									<span class="spinner-small spinner-inline"></span>
								{:else}
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<polyline points="20 6 9 17 4 12"/>
									</svg>
								{/if}
							</button>
							<button
								type="button"
								class="btn-icon btn-cancel-icon"
								onclick={() => { showAddNicknameForm = false; newNicknameUsername = ''; newNicknameDisplayName = ''; }}
								disabled={isAddingNickname}
								title="Cancel"
							>
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<line x1="18" y1="6" x2="6" y2="18"/>
									<line x1="6" y1="6" x2="18" y2="18"/>
								</svg>
							</button>
						</div>
					</form>
				{:else if nicknames.length > 0}
					<button class="btn-add btn-add-more" onclick={() => showAddNicknameForm = true}>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="12" y1="5" x2="12" y2="19"/>
							<line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
						Add nickname
					</button>
				{/if}
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
					<div class="threshold-label-group">
						<label for="old-content">Flag content unwatched for</label>
						<span class="threshold-help">Used by: Old tab</span>
					</div>
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
					<div class="threshold-label-group">
						<label for="min-age">Don't flag content newer than</label>
						<span class="threshold-help">Used by: Old tab (for never-watched items)</span>
					</div>
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
					<div class="threshold-label-group">
						<label for="large-size">Flag movies larger than</label>
						<span class="threshold-help">Used by: Large tab</span>
					</div>
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

				<div class="threshold-row">
					<div class="threshold-label-group">
						<label for="large-season-size">Flag TV series if any season exceeds</label>
						<span class="threshold-help">Used by: Large tab</span>
					</div>
					<div class="threshold-input">
						<input
							type="number"
							id="large-season-size"
							bind:value={largeSeasonSizeGb}
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

		<!-- Display Preferences Section -->
		<section class="section">
			<h2 class="section-title">Display</h2>

			{#if displayError}
				<div class="inline-error">{displayError}</div>
			{/if}
			{#if displaySuccess}
				<div class="inline-success">{displaySuccess}</div>
			{/if}

			<!-- Theme Selector -->
			<div class="theme-row">
				<div class="theme-info">
					<span class="theme-label">Theme</span>
					<span class="theme-description">Choose your preferred color scheme</span>
				</div>
				<div class="theme-selector" class:loading={isThemeLoading}>
					<button
						class="theme-option"
						class:active={currentTheme === 'light'}
						onclick={() => handleThemeChange('light')}
						disabled={isThemeLoading}
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<circle cx="12" cy="12" r="5"/>
							<line x1="12" y1="1" x2="12" y2="3"/>
							<line x1="12" y1="21" x2="12" y2="23"/>
							<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
							<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
							<line x1="1" y1="12" x2="3" y2="12"/>
							<line x1="21" y1="12" x2="23" y2="12"/>
							<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
							<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
						</svg>
						Light
					</button>
					<button
						class="theme-option"
						class:active={currentTheme === 'dark'}
						onclick={() => handleThemeChange('dark')}
						disabled={isThemeLoading}
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
						</svg>
						Dark
					</button>
					<button
						class="theme-option"
						class:active={currentTheme === 'system'}
						onclick={() => handleThemeChange('system')}
						disabled={isThemeLoading}
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
							<line x1="8" y1="21" x2="16" y2="21"/>
							<line x1="12" y1="17" x2="12" y2="21"/>
						</svg>
						System
					</button>
				</div>
			</div>

			<div class="divider"></div>

			<!-- Recently Available Days -->
			<div class="threshold-row">
				<div class="threshold-label-group">
					<label for="recent-days">Recently available days</label>
					<span class="threshold-help">Show content that became available in the past N days</span>
				</div>
				<div class="threshold-input">
					<input
						type="number"
						id="recent-days"
						bind:value={recentlyAvailableDays}
						min="1"
						max="30"
						onchange={handleRecentDaysChange}
						disabled={isRecentDaysLoading}
					/>
					<span class="unit">days</span>
					{#if isRecentDaysLoading}
						<span class="spinner-small spinner-inline"></span>
					{/if}
				</div>
			</div>

			<div class="divider"></div>

			<!-- Title Language -->
			<div class="select-row">
				<div class="select-info">
					<span class="select-label">Title language</span>
					<span class="select-description">Preferred language for content titles</span>
				</div>
				<div class="select-wrapper">
					<select
						id="title-language"
						value={titleLanguage}
						onchange={handleTitleLanguageChange}
						disabled={isTitleLanguageLoading}
						class="language-select"
					>
						<option value="en">English</option>
						<option value="fr">French</option>
					</select>
					{#if isTitleLanguageLoading}
						<span class="spinner-small spinner-inline"></span>
					{/if}
				</div>
			</div>

			<div class="divider"></div>

			<div class="toggle-row">
				<div class="toggle-info">
					<span class="toggle-label">Show unreleased requests</span>
					<span class="toggle-description">Include requests for content that hasn't been released yet</span>
				</div>
				<button
					class="toggle-switch"
					class:active={showUnreleasedRequests}
					onclick={handleDisplayToggle}
					disabled={isDisplayLoading}
					role="switch"
					aria-checked={showUnreleasedRequests}
				>
					{#if isDisplayLoading}
						<span class="toggle-spinner"></span>
					{:else}
						<span class="toggle-knob"></span>
					{/if}
				</button>
			</div>
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

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-4);
	}

	.section-header .section-title {
		margin-bottom: 0;
	}

	.section-title {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: var(--space-4);
	}

	.btn-refresh {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
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

	.btn-refresh:hover:not(:disabled) {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	.btn-refresh:disabled {
		opacity: 0.6;
		cursor: not-allowed;
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

	.threshold-label-group {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.threshold-help {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
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

	.spinner-inline {
		border-color: var(--border);
		border-top-color: var(--accent);
		flex-shrink: 0;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Toggle Row */
	.toggle-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) 0;
	}

	.toggle-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.toggle-label {
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.toggle-description {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.toggle-switch {
		position: relative;
		width: 44px;
		height: 24px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 12px;
		cursor: pointer;
		transition: all var(--transition-fast);
		padding: 0;
		flex-shrink: 0;
	}

	.toggle-switch:hover:not(:disabled) {
		border-color: var(--text-muted);
	}

	.toggle-switch.active {
		background: var(--accent);
		border-color: var(--accent);
	}

	.toggle-switch:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.toggle-knob {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 18px;
		height: 18px;
		background: white;
		border-radius: 50%;
		transition: transform var(--transition-fast);
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
	}

	.toggle-switch.active .toggle-knob {
		transform: translateX(20px);
	}

	.toggle-spinner {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 14px;
		height: 14px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Select Row (Language selector) */
	.select-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) 0;
	}

	.select-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.select-label {
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.select-description {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.select-wrapper {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.language-select {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: border-color var(--transition-fast);
		min-width: 110px;
	}

	.language-select:hover:not(:disabled) {
		border-color: var(--text-muted);
	}

	.language-select:focus {
		outline: none;
		border-color: var(--accent);
	}

	.language-select:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* Theme Selector */
	.theme-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) 0;
		gap: var(--space-4);
	}

	.theme-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.theme-label {
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.theme-description {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.theme-selector {
		display: flex;
		background: var(--bg-tertiary);
		border-radius: var(--radius-md);
		padding: 3px;
		gap: 2px;
	}

	.theme-selector.loading {
		opacity: 0.6;
		pointer-events: none;
	}

	.theme-option {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
		white-space: nowrap;
	}

	.theme-option:hover:not(:disabled) {
		color: var(--text-primary);
	}

	.theme-option.active {
		background: var(--bg-primary);
		color: var(--text-primary);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
	}

	.theme-option:disabled {
		cursor: not-allowed;
	}

	.theme-option svg {
		flex-shrink: 0;
	}

	/* Nicknames */
	.nicknames-loading {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--text-muted);
		font-size: var(--font-size-sm);
		padding: var(--space-4) 0;
	}

	.nicknames-empty {
		padding: var(--space-4) 0;
	}

	.nicknames-empty p {
		color: var(--text-muted);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-3);
	}

	.btn-add {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-add:hover {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	.btn-add-more {
		margin-top: var(--space-3);
	}

	.nicknames-table {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.nicknames-header {
		display: grid;
		grid-template-columns: 1fr 24px 1fr 80px;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
	}

	.nickname-row {
		display: grid;
		grid-template-columns: 1fr 24px 1fr 80px;
		gap: var(--space-2);
		padding: var(--space-3);
		border-bottom: 1px solid var(--border);
		align-items: center;
	}

	.nickname-row:last-child {
		border-bottom: none;
	}

	.col-arrow {
		color: var(--text-muted);
		text-align: center;
	}

	.col-actions {
		display: flex;
		gap: var(--space-1);
		justify-content: flex-end;
	}

	.nickname-value {
		font-size: var(--font-size-sm);
		color: var(--text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.edit-input {
		padding: var(--space-1) var(--space-2);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-primary);
		color: var(--text-primary);
		width: 100%;
	}

	.edit-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.delete-confirm-text {
		font-size: var(--font-size-sm);
		color: var(--danger);
		font-weight: var(--font-weight-medium);
	}

	.btn-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		padding: 0;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
		color: var(--text-secondary);
	}

	.btn-icon:hover:not(:disabled) {
		border-color: var(--text-muted);
		color: var(--text-primary);
	}

	.btn-icon:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-save-icon {
		color: var(--success);
		border-color: var(--success);
	}

	.btn-save-icon:hover:not(:disabled) {
		background: var(--success);
		color: white;
		border-color: var(--success);
	}

	.btn-cancel-icon {
		color: var(--text-muted);
	}

	.btn-edit-icon:hover:not(:disabled) {
		color: var(--accent);
		border-color: var(--accent);
	}

	.btn-delete-icon:hover:not(:disabled) {
		color: var(--danger);
		border-color: var(--danger);
	}

	.btn-confirm-delete {
		color: var(--danger);
		border-color: var(--danger);
	}

	.btn-confirm-delete:hover:not(:disabled) {
		background: var(--danger);
		color: white;
	}

	/* Add Nickname Form */
	.add-nickname-form {
		margin-top: var(--space-3);
	}

	.add-nickname-row {
		display: flex;
		gap: var(--space-2);
		align-items: center;
	}

	.add-input {
		flex: 1;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
	}

	.add-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.add-input::placeholder {
		color: var(--text-muted);
	}

	.add-arrow {
		color: var(--text-muted);
		flex-shrink: 0;
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

		.theme-row {
			flex-direction: column;
			align-items: flex-start;
		}

		.theme-selector {
			width: 100%;
			justify-content: space-between;
		}

		.theme-option {
			flex: 1;
			justify-content: center;
		}

		.nicknames-header {
			display: none;
		}

		.nickname-row {
			grid-template-columns: 1fr;
			gap: var(--space-2);
		}

		.nickname-row .col-arrow {
			display: none;
		}

		.nickname-row .col-username {
			font-weight: var(--font-weight-medium);
		}

		.nickname-row .col-displayname::before {
			content: '→ ';
			color: var(--text-muted);
		}

		.nickname-row .col-actions {
			margin-top: var(--space-1);
		}

		.add-nickname-row {
			flex-wrap: wrap;
		}

		.add-nickname-row .add-input {
			flex: 1 1 100%;
		}

		.add-nickname-row .add-arrow {
			display: none;
		}

		.add-nickname-row .btn-icon {
			flex-shrink: 0;
		}
	}
</style>
