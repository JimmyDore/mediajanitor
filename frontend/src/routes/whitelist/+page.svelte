<script lang="ts">
	import { onMount } from 'svelte';

	interface WhitelistItem {
		id: number;
		jellyfin_id: string;
		name: string;
		media_type: string;
		created_at: string;
	}

	interface WhitelistResponse {
		items: WhitelistItem[];
		total_count: number;
	}

	let loading = $state(true);
	let error = $state<string | null>(null);
	let data = $state<WhitelistResponse | null>(null);
	let frenchOnlyData = $state<WhitelistResponse | null>(null);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let removingIds = $state<Set<number>>(new Set());
	let removingFrenchOnlyIds = $state<Set<number>>(new Set());

	function formatDate(dateStr: string): string {
		try {
			const date = new Date(dateStr);
			return date.toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric'
			});
		} catch {
			return 'Unknown';
		}
	}

	function showToast(message: string, type: 'success' | 'error') {
		toast = { message, type };
		setTimeout(() => {
			toast = null;
		}, 3000);
	}

	async function removeFromWhitelist(item: WhitelistItem) {
		const token = localStorage.getItem('access_token');
		if (!token) {
			showToast('Not authenticated', 'error');
			return;
		}

		// Add to removing set to show loading state
		removingIds = new Set([...removingIds, item.id]);

		try {
			const response = await fetch(`/api/whitelist/content/${item.id}`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (response.status === 401) {
				showToast('Session expired. Please log in again.', 'error');
				return;
			}

			if (response.status === 404) {
				showToast('Item not found in whitelist', 'error');
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				showToast(errorData.detail || 'Failed to remove from whitelist', 'error');
				return;
			}

			// Remove item from the list immediately
			if (data) {
				data = {
					...data,
					items: data.items.filter((i) => i.id !== item.id),
					total_count: data.total_count - 1
				};
			}

			showToast('Removed from whitelist', 'success');
		} catch (e) {
			showToast(e instanceof Error ? e.message : 'Failed to remove from whitelist', 'error');
		} finally {
			// Remove from removing set
			const newSet = new Set(removingIds);
			newSet.delete(item.id);
			removingIds = newSet;
		}
	}

	async function fetchWhitelist() {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) {
				error = 'Not authenticated';
				return;
			}

			const response = await fetch('/api/whitelist/content', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (response.status === 401) {
				error = 'Session expired. Please log in again.';
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				error = errorData.detail || 'Failed to fetch whitelist';
				return;
			}

			data = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch whitelist';
		} finally {
			loading = false;
		}
	}

	async function fetchFrenchOnlyWhitelist() {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) {
				return;
			}

			const response = await fetch('/api/whitelist/french-only', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (response.ok) {
				frenchOnlyData = await response.json();
			}
		} catch {
			// Silently fail for French-only - not critical
		}
	}

	async function removeFromFrenchOnlyWhitelist(item: WhitelistItem) {
		const token = localStorage.getItem('access_token');
		if (!token) {
			showToast('Not authenticated', 'error');
			return;
		}

		removingFrenchOnlyIds = new Set([...removingFrenchOnlyIds, item.id]);

		try {
			const response = await fetch(`/api/whitelist/french-only/${item.id}`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (response.status === 401) {
				showToast('Session expired. Please log in again.', 'error');
				return;
			}

			if (response.status === 404) {
				showToast('Item not found in whitelist', 'error');
				return;
			}

			if (!response.ok) {
				const errorData = await response.json();
				showToast(errorData.detail || 'Failed to remove from whitelist', 'error');
				return;
			}

			// Remove item from the list immediately
			if (frenchOnlyData) {
				frenchOnlyData = {
					...frenchOnlyData,
					items: frenchOnlyData.items.filter((i) => i.id !== item.id),
					total_count: frenchOnlyData.total_count - 1
				};
			}

			showToast('Removed from French-only whitelist', 'success');
		} catch (e) {
			showToast(e instanceof Error ? e.message : 'Failed to remove from whitelist', 'error');
		} finally {
			const newSet = new Set(removingFrenchOnlyIds);
			newSet.delete(item.id);
			removingFrenchOnlyIds = newSet;
		}
	}

	onMount(() => {
		fetchWhitelist();
		fetchFrenchOnlyWhitelist();
	});
</script>

<svelte:head>
	<title>Whitelist - Media Janitor</title>
</svelte:head>

{#if toast}
	<div class="toast toast-{toast.type}" role="alert">
		{toast.message}
	</div>
{/if}

<div class="page-container">
	<div class="page-header">
		<h1>Whitelists</h1>
		<p class="page-description">
			Manage content exempted from various issue checks
		</p>
	</div>

	{#if loading}
		<div class="loading-container">
			<div class="spinner" aria-label="Loading"></div>
			<p>Loading whitelist...</p>
		</div>
	{:else if error}
		<div class="error-container">
			<p class="error-message">{error}</p>
		</div>
	{:else if data}
		<!-- Protected Content Section -->
		<section class="whitelist-section">
			<h2 class="section-title">Protected Content</h2>
			<p class="section-description">Content protected from deletion suggestions (won't appear in old/unwatched list)</p>

			<div class="summary-bar">
				<div class="summary-stat">
					<span class="stat-label">Protected Items</span>
					<span class="stat-value">{data.total_count}</span>
				</div>
			</div>

			{#if data.items.length === 0}
				<div class="empty-state">
					<p>No content in your protected list yet.</p>
					<p class="empty-hint">
						Use the "Protect" button on the <a href="/issues?filter=old">Issues</a> page to add items.
					</p>
				</div>
			{:else}
				<div class="content-list">
					<div class="list-header">
						<span class="col-name">Name</span>
						<span class="col-type">Type</span>
						<span class="col-date">Date Added</span>
						<span class="col-actions">Actions</span>
					</div>
					{#each data.items as item}
						<div class="content-item">
							<span class="col-name item-name">{item.name}</span>
							<span class="col-type">
								<span class="type-badge type-{item.media_type.toLowerCase()}">
									{item.media_type === 'Movie' ? 'Movie' : 'Series'}
								</span>
							</span>
							<span class="col-date">{formatDate(item.created_at)}</span>
							<span class="col-actions">
								<button
									class="btn-remove"
									onclick={() => removeFromWhitelist(item)}
									disabled={removingIds.has(item.id)}
									title="Remove from whitelist - item may reappear in old content list"
								>
									{#if removingIds.has(item.id)}
										<span class="btn-spinner"></span>
									{:else}
										Remove
									{/if}
								</button>
							</span>
						</div>
					{/each}
				</div>
			{/if}
		</section>

		<!-- French-Only Section -->
		{#if frenchOnlyData}
			<section class="whitelist-section">
				<h2 class="section-title">French-Only Content</h2>
				<p class="section-description">Content that doesn't require English audio (won't flag missing EN audio)</p>

				<div class="summary-bar">
					<div class="summary-stat">
						<span class="stat-label">French-Only Items</span>
						<span class="stat-value">{frenchOnlyData.total_count}</span>
					</div>
				</div>

				{#if frenchOnlyData.items.length === 0}
					<div class="empty-state">
						<p>No French-only content yet.</p>
						<p class="empty-hint">
							Use the "FR Only" button on the <a href="/issues?filter=language">Language Issues</a> page for French films that don't need English audio.
						</p>
					</div>
				{:else}
					<div class="content-list">
						<div class="list-header">
							<span class="col-name">Name</span>
							<span class="col-type">Type</span>
							<span class="col-date">Date Added</span>
							<span class="col-actions">Actions</span>
						</div>
						{#each frenchOnlyData.items as item}
							<div class="content-item">
								<span class="col-name item-name">{item.name}</span>
								<span class="col-type">
									<span class="type-badge type-{item.media_type.toLowerCase()}">
										{item.media_type === 'Movie' ? 'Movie' : 'Series'}
									</span>
								</span>
								<span class="col-date">{formatDate(item.created_at)}</span>
								<span class="col-actions">
									<button
										class="btn-remove"
										onclick={() => removeFromFrenchOnlyWhitelist(item)}
										disabled={removingFrenchOnlyIds.has(item.id)}
										title="Remove from French-only list - item may show as missing English audio"
									>
										{#if removingFrenchOnlyIds.has(item.id)}
											<span class="btn-spinner"></span>
										{:else}
											Remove
										{/if}
									</button>
								</span>
							</div>
						{/each}
					</div>
				{/if}
			</section>
		{/if}
	{/if}
</div>

<style>
	.page-container {
		padding: 0;
	}

	.page-header {
		margin-bottom: 2rem;
	}

	.page-header h1 {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0 0 0.5rem 0;
	}

	.page-description {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.whitelist-section {
		margin-bottom: 2.5rem;
	}

	.section-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 0.25rem 0;
	}

	.section-description {
		color: var(--text-secondary);
		font-size: 0.8125rem;
		margin: 0 0 1rem 0;
	}

	.loading-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		gap: 1rem;
	}

	.spinner {
		width: 2rem;
		height: 2rem;
		border: 3px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-container p {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	.error-container {
		padding: 2rem;
		background: var(--bg-secondary);
		border: 1px solid var(--danger);
		border-radius: 0.5rem;
		text-align: center;
	}

	.error-message {
		color: var(--danger);
		margin: 0;
	}

	.summary-bar {
		display: flex;
		gap: 2rem;
		padding: 1rem 1.5rem;
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border);
		margin-bottom: 1.5rem;
	}

	.summary-stat {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.stat-value {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.empty-state {
		padding: 3rem;
		text-align: center;
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border);
	}

	.empty-state p {
		color: var(--text-secondary);
		margin: 0 0 0.5rem 0;
	}

	.empty-hint {
		font-size: 0.875rem;
	}

	.empty-hint a {
		color: var(--accent);
		text-decoration: none;
	}

	.empty-hint a:hover {
		text-decoration: underline;
	}

	.content-list {
		background: var(--bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--border);
		overflow: hidden;
	}

	.list-header {
		display: grid;
		grid-template-columns: 1fr 5rem 8rem 5rem;
		gap: 1rem;
		padding: 0.75rem 1rem;
		background: var(--bg-tertiary, var(--bg-secondary));
		border-bottom: 1px solid var(--border);
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
	}

	.content-item {
		display: grid;
		grid-template-columns: 1fr 5rem 8rem 5rem;
		gap: 1rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
		align-items: center;
		font-size: 0.875rem;
	}

	.content-item:last-child {
		border-bottom: none;
	}

	.content-item:hover {
		background: var(--bg-hover, rgba(0, 0, 0, 0.02));
	}

	.item-name {
		font-weight: 500;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.col-type {
		text-align: center;
	}

	.type-badge {
		display: inline-block;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.type-movie {
		background: rgba(59, 130, 246, 0.1);
		color: rgb(59, 130, 246);
	}

	.type-series {
		background: rgba(168, 85, 247, 0.1);
		color: rgb(168, 85, 247);
	}

	.col-date {
		color: var(--text-secondary);
		font-size: 0.8125rem;
	}

	.col-actions {
		text-align: center;
	}

	.btn-remove {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: var(--danger, #ef4444);
		background: transparent;
		border: 1px solid var(--danger, #ef4444);
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.15s ease;
		min-width: 4rem;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.btn-remove:hover:not(:disabled) {
		background: var(--danger, #ef4444);
		color: white;
	}

	.btn-remove:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-spinner {
		width: 0.875rem;
		height: 0.875rem;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Toast notifications */
	.toast {
		position: fixed;
		bottom: 1.5rem;
		right: 1.5rem;
		padding: 0.75rem 1.25rem;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		z-index: 1000;
		animation: slideIn 0.2s ease;
	}

	.toast-success {
		background: var(--success, #22c55e);
		color: white;
	}

	.toast-error {
		background: var(--danger, #ef4444);
		color: white;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	/* Responsive design */
	@media (max-width: 768px) {
		.list-header {
			display: none;
		}

		.content-item {
			grid-template-columns: 1fr;
			gap: 0.5rem;
			padding: 1rem;
		}

		.col-name {
			order: 1;
		}

		.col-type,
		.col-date {
			font-size: 0.75rem;
		}

		.col-actions {
			order: 2;
			text-align: left;
		}
	}
</style>
