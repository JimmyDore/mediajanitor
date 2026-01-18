<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { auth, authenticatedFetch } from '$lib/stores';
	import { goto } from '$app/navigation';
	import Landing from '$lib/components/Landing.svelte';
	import Toast from '$lib/components/Toast.svelte';

	let error = $state<string | null>(null);

	interface SyncProgressInfo {
		current_step: string | null;
		total_steps: number | null;
		current_step_progress: number | null;
		current_step_total: number | null;
		current_user_name: string | null;
	}

	interface SyncStatus {
		last_synced: string | null;
		status: string | null;
		is_syncing: boolean;
		media_items_count: number | null;
		requests_count: number | null;
		error: string | null;
		progress: SyncProgressInfo | null;
	}

	interface SyncResponse {
		status: string;
		media_items_synced: number;
		requests_synced: number;
		error: string | null;
	}

	interface IssueCategorySummary {
		count: number;
		total_size_bytes: number;
		total_size_formatted: string;
	}

	interface InfoCategorySummary {
		count: number;
	}

	interface ContentSummary {
		old_content: IssueCategorySummary;
		large_movies: IssueCategorySummary;
		language_issues: IssueCategorySummary;
		unavailable_requests: IssueCategorySummary;
		recently_available: InfoCategorySummary;
	}

	interface JellyfinSettings {
		server_url: string | null;
		api_key_configured: boolean;
	}

	interface ServiceSettings {
		api_key_configured: boolean;
	}

	const ENHANCE_SETUP_DISMISSED_KEY = 'mediajanitor_enhance_setup_dismissed';

	let syncStatus = $state<SyncStatus | null>(null);
	let syncLoading = $state(false);
	let toastMessage = $state<string | null>(null);
	let toastType = $state<'success' | 'error'>('success');
	let toastTimer: ReturnType<typeof setTimeout> | null = null;
	let contentSummary = $state<ContentSummary | null>(null);
	let summaryLoading = $state(true);
	let jellyfinSettings = $state<JellyfinSettings | null>(null);
	let jellyseerrSettings = $state<ServiceSettings | null>(null);
	let radarrSettings = $state<ServiceSettings | null>(null);
	let sonarrSettings = $state<ServiceSettings | null>(null);
	let enhanceSetupDismissed = $state(false);
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	let autoSyncTriggered = $state(false);  // Track if we've already triggered auto-sync
	const POLL_INTERVAL_MS = 2000; // Poll every 2 seconds during sync

	// Computed: Show checklist when Jellyfin not configured OR never synced
	const showSetupChecklist = $derived(
		jellyfinSettings !== null &&
			syncStatus !== null &&
			(jellyfinSettings.api_key_configured === false || syncStatus.last_synced === null)
	);

	// Computed: Show enhance setup card when setup complete but optional services not configured
	const showEnhanceSetup = $derived(
		!showSetupChecklist &&
			jellyfinSettings !== null &&
			syncStatus !== null &&
			jellyfinSettings.api_key_configured === true &&
			syncStatus.last_synced !== null &&
			!enhanceSetupDismissed &&
			jellyseerrSettings !== null &&
			radarrSettings !== null &&
			sonarrSettings !== null &&
			(jellyseerrSettings.api_key_configured === false ||
				radarrSettings.api_key_configured === false ||
				sonarrSettings.api_key_configured === false)
	);

	// Computed: Step statuses
	const jellyfinStepStatus = $derived<'pending' | 'complete'>(
		jellyfinSettings?.api_key_configured ? 'complete' : 'pending'
	);

	const syncStepStatus = $derived<'pending' | 'in-progress' | 'complete' | 'error'>(
		syncStatus?.last_synced !== null
			? 'complete'
			: syncStatus?.is_syncing
				? 'in-progress'
				: syncStatus?.status === 'failed'
					? 'error'
					: 'pending'
	);

	// Should auto-trigger sync: Jellyfin configured, never synced, not already syncing
	const shouldAutoSync = $derived(
		jellyfinSettings?.api_key_configured === true &&
		syncStatus !== null &&
		syncStatus.last_synced === null &&
		!syncStatus.is_syncing &&
		!autoSyncTriggered
	);

	// Auto-trigger first sync when conditions are met
	$effect(() => {
		if (shouldAutoSync) {
			autoSyncTriggered = true;
			triggerSync(true);  // force=true to bypass rate limit for first sync
		}
	});

	function formatDate(isoString: string): string {
		const date = new Date(isoString);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const minutes = Math.floor(diff / 60000);
		const hours = Math.floor(diff / 3600000);
		const days = Math.floor(diff / 86400000);

		if (minutes < 1) return 'Just now';
		if (minutes < 60) return `${minutes}m ago`;
		if (hours < 24) return `${hours}h ago`;
		if (days < 7) return `${days}d ago`;
		return date.toLocaleDateString();
	}

	function showToast(message: string, type: 'success' | 'error') {
		if (toastTimer) {
			clearTimeout(toastTimer);
		}
		toastMessage = message;
		toastType = type;
		toastTimer = setTimeout(() => {
			toastMessage = null;
			toastTimer = null;
		}, 3000);
	}

	function closeToast() {
		if (toastTimer) {
			clearTimeout(toastTimer);
			toastTimer = null;
		}
		toastMessage = null;
	}

	function formatProgressMessage(progress: SyncProgressInfo): string {
		if (progress.current_step === 'syncing_media') {
			if (progress.current_step_progress && progress.current_step_total) {
				const userName = progress.current_user_name || 'user';
				return `Fetching user ${progress.current_step_progress}/${progress.current_step_total}: ${userName}...`;
			}
			return 'Syncing media...';
		}
		if (progress.current_step === 'syncing_requests') {
			return 'Syncing requests...';
		}
		return 'Syncing...';
	}

	function startPolling() {
		if (pollInterval) return; // Already polling
		pollInterval = setInterval(async () => {
			await fetchSyncStatus();
			// Stop polling when sync is complete
			if (syncStatus && !syncStatus.is_syncing) {
				stopPolling();
			}
		}, POLL_INTERVAL_MS);
	}

	function stopPolling() {
		if (pollInterval) {
			clearInterval(pollInterval);
			pollInterval = null;
		}
	}

	async function fetchSyncStatus() {
		try {
			const response = await authenticatedFetch('/api/sync/status');
			if (response.ok) {
				syncStatus = await response.json();
			}
		} catch {
			// Ignore sync status errors
		}
	}

	async function fetchContentSummary() {
		try {
			const response = await authenticatedFetch('/api/content/summary');
			if (response.ok) {
				contentSummary = await response.json();
			}
		} catch {
			// Ignore summary errors
		} finally {
			summaryLoading = false;
		}
	}

	async function fetchJellyfinSettings() {
		try {
			const response = await authenticatedFetch('/api/settings/jellyfin');
			if (response.ok) {
				jellyfinSettings = await response.json();
			}
		} catch {
			// Ignore errors - will show as not configured
		}
	}

	async function fetchOptionalServicesSettings() {
		try {
			const [jellyseerrRes, radarrRes, sonarrRes] = await Promise.all([
				authenticatedFetch('/api/settings/jellyseerr'),
				authenticatedFetch('/api/settings/radarr'),
				authenticatedFetch('/api/settings/sonarr')
			]);

			if (jellyseerrRes.ok) {
				jellyseerrSettings = await jellyseerrRes.json();
			} else {
				jellyseerrSettings = { api_key_configured: false };
			}

			if (radarrRes.ok) {
				radarrSettings = await radarrRes.json();
			} else {
				radarrSettings = { api_key_configured: false };
			}

			if (sonarrRes.ok) {
				sonarrSettings = await sonarrRes.json();
			} else {
				sonarrSettings = { api_key_configured: false };
			}
		} catch {
			// Ignore errors - will show as not configured
			jellyseerrSettings = { api_key_configured: false };
			radarrSettings = { api_key_configured: false };
			sonarrSettings = { api_key_configured: false };
		}
	}

	function loadEnhanceSetupDismissed() {
		if (typeof localStorage !== 'undefined') {
			enhanceSetupDismissed = localStorage.getItem(ENHANCE_SETUP_DISMISSED_KEY) === 'true';
		}
	}

	function dismissEnhanceSetup() {
		enhanceSetupDismissed = true;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(ENHANCE_SETUP_DISMISSED_KEY, 'true');
		}
	}

	async function triggerSync(force: boolean = false) {
		if (syncLoading) return;

		syncLoading = true;
		// Start polling immediately to show progress
		startPolling();

		try {
			const response = await authenticatedFetch('/api/sync', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ force })
			});

			if (response.status === 429) {
				const data = await response.json();
				showToast(data.detail || 'Rate limited. Please wait before syncing again.', 'error');
				stopPolling();
				return;
			}

			if (!response.ok) {
				const data = await response.json();
				showToast(data.detail || 'Sync failed', 'error');
				stopPolling();
				return;
			}

			const data: SyncResponse = await response.json();
			stopPolling();
			await fetchSyncStatus();
			await fetchContentSummary();

			if (data.status === 'success') {
				showToast(
					`Synced ${data.media_items_synced} media items and ${data.requests_synced} requests`,
					'success'
				);
			} else if (data.status === 'partial') {
				showToast(`Sync completed with warnings: ${data.error}`, 'success');
			} else {
				showToast(data.error || 'Sync failed', 'error');
			}
		} catch {
			showToast('Failed to sync data', 'error');
			stopPolling();
		} finally {
			syncLoading = false;
		}
	}

	function navigateToIssues(filter: string) {
		goto(`/issues?filter=${filter}`);
	}

	function navigateToInfo(type: string) {
		goto(`/info/${type}`);
	}

	onMount(async () => {
		// Load localStorage state synchronously first
		loadEnhanceSetupDismissed();

		try {
			await Promise.all([
				fetchSyncStatus(),
				fetchContentSummary(),
				fetchJellyfinSettings(),
				fetchOptionalServicesSettings()
			]);
			// If sync is already in progress (e.g., page refresh during sync), start polling
			if (syncStatus?.is_syncing) {
				syncLoading = true;
				startPolling();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch';
		}
	});

	onDestroy(() => {
		stopPolling();
	});
</script>

<svelte:head>
	<title>{$auth.isAuthenticated ? 'Dashboard' : 'Media Janitor - Keep Your Media Library Clean'}</title>
</svelte:head>

{#if !$auth.isAuthenticated && !$auth.isLoading}
	<Landing />
{:else if $auth.isAuthenticated}
	{#if toastMessage}
		<Toast message={toastMessage} type={toastType} onclose={closeToast} />
	{/if}

	<div class="dashboard" aria-busy={summaryLoading}>
		<header class="page-header">
			<div class="header-left">
				<h1>Dashboard</h1>
				{#if syncStatus?.is_syncing && syncStatus.progress}
					<span class="sync-progress">{formatProgressMessage(syncStatus.progress)}</span>
				{:else if syncStatus?.last_synced}
					<span class="sync-time">Updated {formatDate(syncStatus.last_synced)}</span>
				{/if}
			</div>
			<button
				class="btn-refresh"
				onclick={() => triggerSync()}
				disabled={syncLoading}
				aria-label="Refresh data"
			>
				{#if syncLoading}
					<span class="spinner" role="status" aria-label="Loading"></span>
				{:else}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M23 4v6h-6M1 20v-6h6"/>
						<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
					</svg>
				{/if}
			</button>
		</header>

		{#if showSetupChecklist}
			<!-- Setup Checklist -->
			<section class="setup-checklist">
				<h2 class="section-label">Setup Checklist</h2>
				<div class="checklist-card">
					<div class="checklist-step step-{jellyfinStepStatus}">
						<span class="step-indicator">
							{#if jellyfinStepStatus === 'complete'}
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polyline points="20 6 9 17 4 12"/>
								</svg>
							{:else}
								<span class="step-number">1</span>
							{/if}
						</span>
						<div class="step-content">
							<span class="step-title">Connect Jellyfin</span>
							{#if jellyfinStepStatus === 'pending'}
								<a href="/settings" class="step-link">Go to Settings</a>
							{/if}
						</div>
					</div>
					<div class="checklist-step step-{syncStepStatus}">
						<span class="step-indicator">
							{#if syncStepStatus === 'complete'}
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polyline points="20 6 9 17 4 12"/>
								</svg>
							{:else if syncStepStatus === 'in-progress'}
								<span class="step-spinner"></span>
							{:else if syncStepStatus === 'error'}
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<line x1="18" y1="6" x2="6" y2="18"/>
									<line x1="6" y1="6" x2="18" y2="18"/>
								</svg>
							{:else}
								<span class="step-number">2</span>
							{/if}
						</span>
						<div class="step-content">
							<span class="step-title">Run First Sync</span>
							{#if syncStepStatus === 'in-progress'}
								<span class="step-status">Syncing...</span>
							{:else if syncStepStatus === 'error'}
								<div class="step-error">
									<span class="step-error-text">{syncStatus?.error || 'Sync failed'}</span>
									<button class="step-action step-retry" onclick={() => triggerSync(true)} disabled={syncLoading}>
										Retry
									</button>
								</div>
							{:else if syncStepStatus === 'pending' && jellyfinStepStatus === 'complete'}
								<button class="step-action" onclick={() => triggerSync(true)} disabled={syncLoading}>
									Start Sync
								</button>
							{/if}
						</div>
					</div>
				</div>
			</section>
		{/if}

		{#if showEnhanceSetup}
			<!-- Enhance Your Setup -->
			<section class="enhance-setup">
				<div class="enhance-card">
					<div class="enhance-header">
						<h2 class="enhance-title">Enhance your setup</h2>
						<button class="enhance-dismiss" onclick={dismissEnhanceSetup} aria-label="Dismiss">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<line x1="18" y1="6" x2="6" y2="18"/>
								<line x1="6" y1="6" x2="18" y2="18"/>
							</svg>
						</button>
					</div>
					<p class="enhance-description">Connect optional services to unlock more features</p>
					<div class="enhance-services">
						{#if jellyseerrSettings && !jellyseerrSettings.api_key_configured}
							<div class="enhance-service">
								<div class="service-info">
									<span class="service-name">Jellyseerr</span>
									<span class="service-description">Track media requests and availability</span>
								</div>
								<a href="/settings" class="service-link">Configure</a>
							</div>
						{/if}
						{#if radarrSettings && !radarrSettings.api_key_configured}
							<div class="enhance-service">
								<div class="service-info">
									<span class="service-name">Radarr</span>
									<span class="service-description">Movie collection management</span>
								</div>
								<a href="/settings" class="service-link">Configure</a>
							</div>
						{/if}
						{#if sonarrSettings && !sonarrSettings.api_key_configured}
							<div class="enhance-service">
								<div class="service-info">
									<span class="service-name">Sonarr</span>
									<span class="service-description">TV series management</span>
								</div>
								<a href="/settings" class="service-link">Configure</a>
							</div>
						{/if}
					</div>
				</div>
			</section>
		{/if}

		{#if error}
		<div class="error-banner">
			<p>Error: {error}</p>
		</div>
	{:else}
		<!-- Issue Stats -->
		<section class="stats-section">
			<h2 class="section-label">Issues</h2>

			{#if summaryLoading}
				<div class="stats-grid" role="status" aria-label="Loading content statistics">
					{#each Array(4) as _}
						<div class="stat-card skeleton"></div>
					{/each}
				</div>
			{:else}
				<div class="stats-grid" aria-live="polite">
					<button class="stat-card" onclick={() => navigateToIssues('old')}>
						<div class="stat-value">{contentSummary?.old_content.count ?? 0}</div>
						<div class="stat-label">Old Content</div>
						{#if contentSummary && contentSummary.old_content.count > 0}
							<div class="stat-meta">{contentSummary.old_content.total_size_formatted}</div>
						{/if}
					</button>

					<button class="stat-card" onclick={() => navigateToIssues('large')}>
						<div class="stat-value">{contentSummary?.large_movies.count ?? 0}</div>
						<div class="stat-label">Large Content</div>
						{#if contentSummary && contentSummary.large_movies.count > 0}
							<div class="stat-meta">{contentSummary.large_movies.total_size_formatted}</div>
						{/if}
					</button>

					<button class="stat-card" onclick={() => navigateToIssues('language')}>
						<div class="stat-value">{contentSummary?.language_issues.count ?? 0}</div>
						<div class="stat-label">Language Issues</div>
					</button>

					<button class="stat-card" onclick={() => navigateToIssues('requests')}>
						<div class="stat-value">{contentSummary?.unavailable_requests.count ?? 0}</div>
						<div class="stat-label">Unavailable Requests</div>
					</button>
				</div>
			{/if}
		</section>

		<!-- Info Links -->
		<section class="info-section">
			<h2 class="section-label">Info</h2>
			<div class="info-links">
				<button class="info-link" onclick={() => navigateToInfo('recent')}>
					<span class="info-count">{contentSummary?.recently_available?.count ?? 0}</span>
					<span class="info-text">recently available</span>
				</button>
			</div>
		</section>
		{/if}
	</div>
{/if}

<style>
	.dashboard {
		max-width: 800px;
		margin: 0 auto;
		padding: var(--space-6);
	}

	/* Responsive dashboard width for large screens */
	@media (min-width: 1440px) {
		.dashboard {
			max-width: 1000px;
		}

		.stats-grid {
			gap: var(--space-4);
		}
	}

	@media (min-width: 1920px) {
		.dashboard {
			max-width: 1200px;
		}

		.stats-grid {
			gap: var(--space-5);
		}
	}

	/* Header */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-8);
	}

	.header-left {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
	}

	.sync-time {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.sync-progress {
		font-size: var(--font-size-sm);
		color: var(--accent);
		font-weight: var(--font-weight-medium);
	}

	.btn-refresh {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-refresh:hover:not(:disabled) {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	.btn-refresh:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinner {
		width: 16px;
		height: 16px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Setup Checklist */
	.setup-checklist {
		margin-bottom: var(--space-8);
	}

	.checklist-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--space-4);
	}

	.checklist-step {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) 0;
	}

	.checklist-step:not(:last-child) {
		border-bottom: 1px solid var(--border);
	}

	.step-indicator {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.step-pending .step-indicator {
		background: var(--bg-hover);
		color: var(--text-muted);
	}

	.step-in-progress .step-indicator {
		background: var(--accent-light, rgba(59, 130, 246, 0.1));
		color: var(--accent);
	}

	.step-complete .step-indicator {
		background: var(--success-light, rgba(34, 197, 94, 0.1));
		color: var(--success, #22c55e);
	}

	.step-error .step-indicator {
		background: var(--danger-light, rgba(239, 68, 68, 0.1));
		color: var(--danger, #ef4444);
	}

	.step-number {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-semibold);
	}

	.step-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid transparent;
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.step-content {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
	}

	.step-title {
		font-size: var(--font-size-md);
		color: var(--text-primary);
	}

	.step-pending .step-title {
		color: var(--text-secondary);
	}

	.step-complete .step-title {
		color: var(--text-muted);
	}

	.step-link {
		font-size: var(--font-size-sm);
		color: var(--accent);
		text-decoration: none;
	}

	.step-link:hover {
		text-decoration: underline;
	}

	.step-action {
		font-size: var(--font-size-sm);
		padding: var(--space-1) var(--space-3);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: opacity var(--transition-fast);
	}

	.step-action:hover:not(:disabled) {
		opacity: 0.9;
	}

	.step-action:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.step-status {
		font-size: var(--font-size-sm);
		color: var(--accent);
	}

	.step-error {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.step-error-text {
		font-size: var(--font-size-sm);
		color: var(--danger, #ef4444);
	}

	.step-retry {
		background: var(--danger, #ef4444);
	}

	.step-retry:hover:not(:disabled) {
		background: var(--danger-hover, #dc2626);
	}

	/* Enhance Setup Card */
	.enhance-setup {
		margin-bottom: var(--space-8);
	}

	.enhance-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--space-4);
	}

	.enhance-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-1);
	}

	.enhance-title {
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
	}

	.enhance-dismiss {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.enhance-dismiss:hover {
		background: var(--bg-hover);
		color: var(--text-secondary);
	}

	.enhance-description {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		margin-bottom: var(--space-4);
	}

	.enhance-services {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.enhance-service {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3);
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}

	.service-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.service-name {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.service-description {
		font-size: var(--font-size-xs);
		color: var(--text-muted);
	}

	.service-link {
		font-size: var(--font-size-sm);
		color: var(--accent);
		text-decoration: none;
	}

	.service-link:hover {
		text-decoration: underline;
	}

	/* Error Banner */
	.error-banner {
		padding: var(--space-4);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
	}

	/* Stats Section */
	.stats-section {
		margin-bottom: var(--space-8);
	}

	.section-label {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: var(--space-4);
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--space-3);
	}

	.stat-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--space-4);
		text-align: left;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.stat-card:hover {
		border-color: var(--accent);
		background: var(--bg-hover);
	}

	.stat-card.skeleton {
		min-height: 88px;
		animation: pulse 1.5s ease-in-out infinite;
	}

	.stat-value {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-bold);
		font-family: var(--font-mono);
		color: var(--text-primary);
		line-height: 1;
		margin-bottom: var(--space-1);
	}

	.stat-label {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-1);
	}

	.stat-meta {
		font-size: var(--font-size-xs);
		font-family: var(--font-mono);
		color: var(--text-muted);
	}

	/* Info Section */
	.info-section {
		margin-bottom: var(--space-8);
	}

	.info-links {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.info-link {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: transparent;
		border: none;
		color: var(--text-secondary);
		font-size: var(--font-size-md);
		cursor: pointer;
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}

	.info-link:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.info-count {
		font-family: var(--font-mono);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
	}

	.info-text {
		color: inherit;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	/* Responsive */
	@media (max-width: 640px) {
		.dashboard {
			padding: var(--space-4);
		}

		.header-left {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-1);
		}

		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.info-links {
			flex-wrap: wrap;
		}
	}
</style>
