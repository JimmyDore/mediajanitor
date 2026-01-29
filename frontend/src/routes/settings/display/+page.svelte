<script lang="ts">
	import { onMount } from 'svelte';
	import { authenticatedFetch, theme, toasts, debounce, type ThemePreference } from '$lib/stores';

	// Display preferences state
	let themePreference = $state<ThemePreference>('system');
	let recentlyAvailableDays = $state(7);
	let showUnreleasedRequests = $state(false);
	let titleLanguage = $state<'en' | 'fr'>('en');

	// Loading and status state
	let isFetchingSettings = $state(true);
	let isSaving = $state(false);

	// Default values
	const DEFAULT_RECENTLY_AVAILABLE_DAYS = 7;

	onMount(async () => {
		await loadDisplayPreferences();
	});

	async function loadDisplayPreferences() {
		try {
			const response = await authenticatedFetch('/api/settings/display');

			if (response.ok) {
				const data = await response.json();
				themePreference = data.theme_preference ?? 'system';
				recentlyAvailableDays = data.recently_available_days ?? DEFAULT_RECENTLY_AVAILABLE_DAYS;
				showUnreleasedRequests = data.show_unreleased_requests ?? false;
				titleLanguage = data.title_language ?? 'en';
			}
		} catch (e) {
			console.error('Failed to load display preferences:', e);
			toasts.add('Failed to load display preferences', 'error');
		} finally {
			isFetchingSettings = false;
		}
	}

	// Track pending saves to show loading indicator after 200ms
	let loadingTimeoutId: ReturnType<typeof setTimeout> | null = null;

	async function savePreference(field: string, value: unknown) {
		// Show loading indicator after 200ms
		loadingTimeoutId = setTimeout(() => {
			isSaving = true;
		}, 200);

		try {
			const response = await authenticatedFetch('/api/settings/display', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ [field]: value })
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Failed to save preference');
			}

			// Update theme store if theme was changed
			if (field === 'theme_preference') {
				theme.setPreference(value as ThemePreference);
			}

			toasts.add('Saved', 'success');
		} catch (e) {
			console.error('Failed to save preference:', e);
			toasts.add(e instanceof Error ? e.message : 'Failed to save preference', 'error');
		} finally {
			if (loadingTimeoutId) {
				clearTimeout(loadingTimeoutId);
				loadingTimeoutId = null;
			}
			isSaving = false;
		}
	}

	function handleThemeChange(newTheme: ThemePreference) {
		if (newTheme === themePreference) return;
		themePreference = newTheme;
		savePreference('theme_preference', newTheme);
	}

	// Debounced save function for recently available days (300ms delay)
	const debouncedSaveDays = debounce((value: number) => savePreference('recently_available_days', value), 300);

	function handleDaysChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const value = parseInt(input.value, 10);
		if (value >= 1 && value <= 30) {
			recentlyAvailableDays = value;
			debouncedSaveDays(value);
		}
	}

	function handleToggleChange(event: Event) {
		const input = event.target as HTMLInputElement;
		showUnreleasedRequests = input.checked;
		savePreference('show_unreleased_requests', input.checked);
	}

	function handleLanguageChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		const value = select.value as 'en' | 'fr';
		titleLanguage = value;
		savePreference('title_language', value);
	}
</script>

<div class="display-page" aria-busy={isFetchingSettings}>
	<header class="page-header">
		<h1>Display</h1>
		<p class="page-description">Customize your viewing experience and preferences.</p>
	</header>

	{#if isFetchingSettings}
		<div class="loading" role="status" aria-label="Loading display settings">
			<span class="spinner" aria-hidden="true"></span>
		</div>
	{:else}
		<div class="settings-list" aria-live="polite">
			<!-- Theme selector -->
			<div class="setting-row theme-row">
				<div class="setting-label-group">
					<label>Theme</label>
					<span class="setting-help">Choose how Media Janitor looks</span>
				</div>
				<div class="theme-selector" class:loading={isSaving}>
					<button
						type="button"
						class="theme-option"
						class:active={themePreference === 'light'}
						onclick={() => handleThemeChange('light')}
						disabled={isSaving}
						aria-pressed={themePreference === 'light'}
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
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
						type="button"
						class="theme-option"
						class:active={themePreference === 'dark'}
						onclick={() => handleThemeChange('dark')}
						disabled={isSaving}
						aria-pressed={themePreference === 'dark'}
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
							<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
						</svg>
						Dark
					</button>
					<button
						type="button"
						class="theme-option"
						class:active={themePreference === 'system'}
						onclick={() => handleThemeChange('system')}
						disabled={isSaving}
						aria-pressed={themePreference === 'system'}
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
							<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
							<line x1="8" y1="21" x2="16" y2="21"/>
							<line x1="12" y1="17" x2="12" y2="21"/>
						</svg>
						System
					</button>
				</div>
			</div>

			<!-- Title language -->
			<div class="setting-row">
				<div class="setting-label-group">
					<label for="language-select">Title language</label>
					<span class="setting-help">Language for content titles</span>
				</div>
				<div class="setting-control">
					<select
						id="language-select"
						value={titleLanguage}
						onchange={handleLanguageChange}
						disabled={isSaving}
					>
						<option value="en">English</option>
						<option value="fr">French</option>
					</select>
				</div>
			</div>

			<!-- Recently available days -->
			<div class="setting-row">
				<div class="setting-label-group">
					<label for="recent-days">Recently available</label>
					<span class="setting-help">Show content added in the last N days</span>
				</div>
				<div class="setting-control">
					<input
						type="number"
						id="recent-days"
						value={recentlyAvailableDays}
						oninput={handleDaysChange}
						min="1"
						max="30"
						disabled={isSaving}
					/>
					<span class="unit">days</span>
				</div>
			</div>

			<!-- Show unreleased requests toggle -->
			<div class="setting-row">
				<div class="setting-label-group">
					<label for="unreleased-toggle">Show unreleased requests</label>
					<span class="setting-help">Include requests for content not yet released</span>
				</div>
				<div class="setting-control">
					<label class="toggle">
						<input
							type="checkbox"
							id="unreleased-toggle"
							checked={showUnreleasedRequests}
							onchange={handleToggleChange}
							disabled={isSaving}
						/>
						<span class="toggle-slider"></span>
					</label>
				</div>
			</div>
		</div>

		{#if isSaving}
			<div class="saving-indicator" role="status">
				<span class="spinner-small" aria-hidden="true"></span>
				<span>Saving...</span>
			</div>
		{/if}
	{/if}
</div>

<style>
	.display-page {
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

	/* Settings list */
	.settings-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.setting-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-3) 0;
		border-bottom: 1px solid var(--border);
	}

	.setting-row:last-child {
		border-bottom: none;
	}

	.setting-label-group {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.setting-label-group label {
		font-size: var(--font-size-md);
		color: var(--text-primary);
		font-weight: var(--font-weight-medium);
	}

	.setting-help {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.setting-control {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	/* Theme Selector */
	.theme-row .setting-label-group {
		flex-shrink: 0;
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

	/* Select inputs */
	.setting-control select {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
		cursor: pointer;
		min-width: 120px;
	}

	.setting-control select:focus {
		outline: none;
		border-color: var(--accent);
	}

	.setting-control select:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Number input */
	.setting-control input[type='number'] {
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

	.setting-control input[type='number']:focus {
		outline: none;
		border-color: var(--accent);
	}

	.setting-control input[type='number']:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.unit {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	/* Toggle switch */
	.toggle {
		position: relative;
		display: inline-block;
		width: 44px;
		height: 24px;
	}

	.toggle input {
		opacity: 0;
		width: 0;
		height: 0;
	}

	.toggle-slider {
		position: absolute;
		cursor: pointer;
		inset: 0;
		background-color: var(--border);
		border-radius: 24px;
		transition: background-color var(--transition-fast);
	}

	.toggle-slider::before {
		position: absolute;
		content: '';
		height: 18px;
		width: 18px;
		left: 3px;
		bottom: 3px;
		background-color: white;
		border-radius: 50%;
		transition: transform var(--transition-fast);
	}

	.toggle input:checked + .toggle-slider {
		background-color: var(--accent);
	}

	.toggle input:checked + .toggle-slider::before {
		transform: translateX(20px);
	}

	.toggle input:focus + .toggle-slider {
		box-shadow: 0 0 0 2px var(--accent-light);
	}

	.toggle input:disabled + .toggle-slider {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Saving indicator */
	.saving-indicator {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin-top: var(--space-4);
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		background: var(--bg-secondary);
		border-radius: var(--radius-md);
		width: fit-content;
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
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Responsive */
	@media (max-width: 600px) {
		.setting-row {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-2);
		}

		.setting-control {
			width: 100%;
		}

		.setting-control select {
			width: 100%;
		}

		.theme-selector {
			width: 100%;
			justify-content: space-between;
		}

		.theme-option {
			flex: 1;
			justify-content: center;
		}
	}
</style>
