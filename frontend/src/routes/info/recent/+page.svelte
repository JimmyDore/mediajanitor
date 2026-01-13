<script lang="ts">
	import { onMount } from 'svelte';

	interface RecentlyAvailableItem {
		jellyseerr_id: number;
		title: string;
		media_type: string;
		availability_date: string;
		requested_by: string | null;
	}

	interface RecentlyAvailableResponse {
		items: RecentlyAvailableItem[];
		total_count: number;
	}

	let data = $state<RecentlyAvailableResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let toastMessage = $state<string | null>(null);
	let toastType = $state<'success' | 'error'>('success');

	function formatDate(isoString: string): string {
		const date = new Date(isoString);
		return date.toLocaleDateString(undefined, {
			weekday: 'short',
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function formatMediaType(type: string): string {
		return type === 'tv' ? 'TV' : type.charAt(0).toUpperCase() + type.slice(1);
	}

	function showToast(message: string, type: 'success' | 'error') {
		toastMessage = message;
		toastType = type;
		setTimeout(() => {
			toastMessage = null;
		}, 5000);
	}

	async function copyList() {
		if (!data?.items.length) return;

		const lines = data.items.map((item) => {
			const type = item.media_type === 'tv' ? 'TV' : 'Movie';
			return `- ${item.title} (${type})`;
		});

		const text = `Recently Available Content (${data.total_count} items):\n\n${lines.join('\n')}`;

		try {
			await navigator.clipboard.writeText(text);
			showToast('Copied to clipboard!', 'success');
		} catch {
			showToast('Failed to copy to clipboard', 'error');
		}
	}

	onMount(async () => {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			const response = await fetch('/api/info/recent', {
				headers: { Authorization: `Bearer ${token}` }
			});

			if (!response.ok) {
				if (response.status === 401) {
					error = 'Session expired. Please log in again.';
				} else {
					error = 'Failed to load recently available content';
				}
				loading = false;
				return;
			}

			data = await response.json();
		} catch {
			error = 'Failed to load data';
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Recently Available - Media Janitor</title>
</svelte:head>

{#if toastMessage}
	<div class="toast toast-{toastType}" role="alert">
		{toastMessage}
	</div>
{/if}

<div class="page-container">
	<div class="page-header">
		<div class="header-text">
			<h1>Recently Available</h1>
			<p class="page-description">Content that became available in the past 7 days</p>
		</div>
		{#if data && data.total_count > 0}
			<button class="copy-button" onclick={copyList} aria-label="Copy list">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
				</svg>
				Copy List
			</button>
		{/if}
	</div>

	{#if loading}
		<div class="loading">Loading...</div>
	{:else if error}
		<div class="error">
			<p>{error}</p>
		</div>
	{:else if data}
		<div class="summary-bar">
			<span class="summary-count">{data.total_count} item{data.total_count !== 1 ? 's' : ''}</span>
		</div>

		{#if data.items.length === 0}
			<div class="empty-state">
				<p>No content became available in the past 7 days.</p>
				<a href="/" class="back-link">Back to Dashboard</a>
			</div>
		{:else}
			<div class="content-list">
				{#each data.items as item, index}
					<div class="content-item">
						<span class="item-number">{index + 1}</span>
						<div class="item-info">
							<span class="item-title">{item.title}</span>
							<div class="item-meta">
								<span class="media-type-badge {item.media_type}">{formatMediaType(item.media_type)}</span>
								<span class="item-date">{formatDate(item.availability_date)}</span>
								{#if item.requested_by}
									<span class="item-requester">Requested by {item.requested_by}</span>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.page-container {
		padding: 1.5rem;
		max-width: 1000px;
		margin: 0 auto;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.header-text h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
	}

	.page-description {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.copy-button {
		padding: 0.5rem 1rem;
		background: var(--accent);
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		transition: background-color 0.2s ease;
	}

	.copy-button:hover {
		background: var(--accent-hover, #4f46e5);
	}

	.loading {
		padding: 2rem;
		text-align: center;
		color: var(--text-secondary);
	}

	.error {
		padding: 2rem;
		background: var(--bg-secondary);
		border: 1px solid var(--danger);
		border-radius: 0.75rem;
		color: var(--danger);
	}

	.summary-bar {
		display: flex;
		justify-content: flex-start;
		padding: 0.75rem 1rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.summary-count {
		font-weight: 600;
		color: var(--text-primary);
	}

	.empty-state {
		padding: 3rem;
		text-align: center;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 0.75rem;
	}

	.empty-state p {
		color: var(--text-secondary);
		margin-bottom: 1rem;
	}

	.back-link {
		color: var(--accent);
		text-decoration: none;
	}

	.back-link:hover {
		text-decoration: underline;
	}

	.content-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.content-item {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		transition: background-color 0.2s ease;
	}

	.content-item:hover {
		background: var(--bg-hover);
	}

	.item-number {
		color: var(--text-secondary);
		font-size: 0.875rem;
		min-width: 2rem;
		text-align: right;
	}

	.item-info {
		flex: 1;
	}

	.item-title {
		font-weight: 500;
		display: block;
		margin-bottom: 0.25rem;
	}

	.item-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
		font-size: 0.875rem;
		color: var(--text-secondary);
	}

	.media-type-badge {
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.media-type-badge.movie {
		background: rgba(59, 130, 246, 0.1);
		color: #3b82f6;
	}

	.media-type-badge.tv {
		background: rgba(16, 185, 129, 0.1);
		color: #10b981;
	}

	.item-date {
		color: var(--text-secondary);
	}

	.item-requester {
		color: var(--text-secondary);
	}

	/* Toast notifications */
	.toast {
		position: fixed;
		top: 1rem;
		right: 1rem;
		padding: 1rem 1.5rem;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		z-index: 1000;
		animation: slideIn 0.3s ease;
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

	@media (max-width: 640px) {
		.page-header {
			flex-direction: column;
		}

		.item-meta {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.25rem;
		}
	}
</style>
