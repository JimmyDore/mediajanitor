<script lang="ts">
	import { onMount } from 'svelte';
	import { authenticatedFetch, toasts, debounce } from '$lib/stores';

	// Analysis preferences state
	let oldContentMonths = $state(4);
	let minAgeMonths = $state(3);
	let largeMovieSizeGb = $state(13);
	let largeSeasonSizeGb = $state(15);

	// Loading and status state
	let isFetchingSettings = $state(true);
	let isSaving = $state(false);

	// Track pending saves to show loading indicator after 200ms
	let loadingTimeoutId: ReturnType<typeof setTimeout> | null = null;

	// Default values for reset
	const DEFAULT_OLD_CONTENT_MONTHS = 4;
	const DEFAULT_MIN_AGE_MONTHS = 3;
	const DEFAULT_LARGE_MOVIE_SIZE_GB = 13;
	const DEFAULT_LARGE_SEASON_SIZE_GB = 15;

	onMount(async () => {
		await loadAnalysisPreferences();
	});

	async function loadAnalysisPreferences() {
		try {
			const response = await authenticatedFetch('/api/settings/analysis');

			if (response.ok) {
				const data = await response.json();
				oldContentMonths = data.old_content_months;
				minAgeMonths = data.min_age_months;
				largeMovieSizeGb = data.large_movie_size_gb;
				largeSeasonSizeGb = data.large_season_size_gb ?? DEFAULT_LARGE_SEASON_SIZE_GB;
			}
		} catch (e) {
			console.error('Failed to load analysis preferences:', e);
			toasts.add('Failed to load threshold settings', 'error');
		} finally {
			isFetchingSettings = false;
		}
	}

	async function savePreference(field: string, value: number) {
		// Show loading indicator after 200ms
		loadingTimeoutId = setTimeout(() => {
			isSaving = true;
		}, 200);

		try {
			const response = await authenticatedFetch('/api/settings/analysis', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ [field]: value })
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Failed to save preference');
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

	// Debounced save functions for each threshold (300ms delay)
	const debouncedSaveOldContent = debounce((value: number) => savePreference('old_content_months', value), 300);
	const debouncedSaveMinAge = debounce((value: number) => savePreference('min_age_months', value), 300);
	const debouncedSaveLargeMovie = debounce((value: number) => savePreference('large_movie_size_gb', value), 300);
	const debouncedSaveLargeSeason = debounce((value: number) => savePreference('large_season_size_gb', value), 300);

	function handleOldContentChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const value = parseInt(input.value, 10);
		if (value >= 1 && value <= 24) {
			oldContentMonths = value;
			debouncedSaveOldContent(value);
		}
	}

	function handleMinAgeChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const value = parseInt(input.value, 10);
		if (value >= 0 && value <= 12) {
			minAgeMonths = value;
			debouncedSaveMinAge(value);
		}
	}

	function handleLargeMovieChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const value = parseInt(input.value, 10);
		if (value >= 1 && value <= 100) {
			largeMovieSizeGb = value;
			debouncedSaveLargeMovie(value);
		}
	}

	function handleLargeSeasonChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const value = parseInt(input.value, 10);
		if (value >= 1 && value <= 100) {
			largeSeasonSizeGb = value;
			debouncedSaveLargeSeason(value);
		}
	}

	async function handleResetAnalysis() {
		// Show loading indicator after 200ms
		loadingTimeoutId = setTimeout(() => {
			isSaving = true;
		}, 200);

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

			toasts.add('Reset to defaults', 'success');
		} catch (e) {
			toasts.add(e instanceof Error ? e.message : 'Failed to reset preferences', 'error');
		} finally {
			if (loadingTimeoutId) {
				clearTimeout(loadingTimeoutId);
				loadingTimeoutId = null;
			}
			isSaving = false;
		}
	}
</script>

<div class="thresholds-page" aria-busy={isFetchingSettings}>
	<header class="page-header">
		<h1>Thresholds</h1>
		<p class="page-description">Configure the thresholds used to identify issues in your media library.</p>
	</header>

	{#if isFetchingSettings}
		<div class="loading" role="status" aria-label="Loading threshold settings">
			<span class="spinner" aria-hidden="true"></span>
		</div>
	{:else}
		<div class="settings-list" aria-live="polite">
			<div class="threshold-row">
				<div class="threshold-label-group">
					<label for="old-content">Flag content unwatched for</label>
					<span class="threshold-help">Used by: Old tab</span>
				</div>
				<div class="threshold-input">
					<input
						type="number"
						id="old-content"
						value={oldContentMonths}
						oninput={handleOldContentChange}
						min="1"
						max="24"
						disabled={isSaving}
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
						value={minAgeMonths}
						oninput={handleMinAgeChange}
						min="0"
						max="12"
						disabled={isSaving}
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
						value={largeMovieSizeGb}
						oninput={handleLargeMovieChange}
						min="1"
						max="100"
						disabled={isSaving}
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
						value={largeSeasonSizeGb}
						oninput={handleLargeSeasonChange}
						min="1"
						max="100"
						disabled={isSaving}
					/>
					<span class="unit">GB</span>
				</div>
			</div>

			<div class="threshold-actions">
				<button type="button" class="btn-reset" onclick={handleResetAnalysis} disabled={isSaving}>
					Reset to defaults
				</button>
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
	.thresholds-page {
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

	.threshold-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-3) 0;
		border-bottom: 1px solid var(--border);
	}

	.threshold-row:last-of-type {
		border-bottom: none;
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

	.threshold-input input:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.unit {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		min-width: 50px;
	}

	.threshold-actions {
		display: flex;
		justify-content: flex-end;
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
