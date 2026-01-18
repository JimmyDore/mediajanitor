<script lang="ts">
	import { onMount } from 'svelte';
	import { authenticatedFetch } from '$lib/stores';

	// Analysis preferences state
	let oldContentMonths = $state(4);
	let minAgeMonths = $state(3);
	let largeMovieSizeGb = $state(13);
	let largeSeasonSizeGb = $state(15);
	let analysisError = $state<string | null>(null);
	let analysisSuccess = $state<string | null>(null);
	let isAnalysisLoading = $state(false);

	// Loading state
	let isFetchingSettings = $state(true);

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
		} finally {
			isFetchingSettings = false;
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
			setTimeout(() => (analysisSuccess = null), 3000);
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
			setTimeout(() => (analysisSuccess = null), 3000);
		} catch (e) {
			analysisError = e instanceof Error ? e.message : 'Failed to reset preferences';
		} finally {
			isAnalysisLoading = false;
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

	/* Thresholds Form */
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
