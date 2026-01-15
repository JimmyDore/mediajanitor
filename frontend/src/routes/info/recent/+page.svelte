<script lang="ts">
	import { onMount } from 'svelte';
	import { authenticatedFetch } from '$lib/stores';

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

	interface GroupedItems {
		date: string;
		dateFormatted: string;
		items: RecentlyAvailableItem[];
	}

	let data = $state<RecentlyAvailableResponse | null>(null);
	let groupedData = $state<GroupedItems[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);

	function formatDateShort(isoString: string): string {
		const date = new Date(isoString);
		const today = new Date();
		const yesterday = new Date(today);
		yesterday.setDate(yesterday.getDate() - 1);

		if (date.toDateString() === today.toDateString()) return 'Today';
		if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';

		return date.toLocaleDateString(undefined, {
			weekday: 'short',
			month: 'short',
			day: 'numeric'
		});
	}

	function getDateKey(isoString: string): string {
		const date = new Date(isoString);
		const year = date.getFullYear();
		const month = String(date.getMonth() + 1).padStart(2, '0');
		const day = String(date.getDate()).padStart(2, '0');
		return `${year}-${month}-${day}`;
	}

	function showToast(message: string, type: 'success' | 'error') {
		toast = { message, type };
		setTimeout(() => toast = null, 3000);
	}

	function groupItemsByDate(items: RecentlyAvailableItem[]): GroupedItems[] {
		const groups: Map<string, RecentlyAvailableItem[]> = new Map();

		for (const item of items) {
			const dateKey = getDateKey(item.availability_date);
			if (!groups.has(dateKey)) {
				groups.set(dateKey, []);
			}
			groups.get(dateKey)!.push(item);
		}

		return Array.from(groups.entries())
			.sort((a, b) => b[0].localeCompare(a[0]))
			.map(([date, items]) => ({
				date,
				dateFormatted: formatDateShort(items[0].availability_date),
				items
			}));
	}

	async function copyList() {
		if (!data?.items.length) return;

		const lines: string[] = [];
		for (const group of groupedData) {
			lines.push(`${group.dateFormatted}:`);
			for (const item of group.items) {
				const type = item.media_type === 'tv' ? 'TV' : 'Movie';
				lines.push(`  - ${item.title} (${type})`);
			}
			lines.push('');
		}

		const text = `Recently Available (${data.total_count} items):\n\n${lines.join('\n')}`;

		try {
			await navigator.clipboard.writeText(text);
			showToast('Copied to clipboard', 'success');
		} catch {
			showToast('Failed to copy', 'error');
		}
	}

	onMount(async () => {
		try {
			const response = await authenticatedFetch('/api/info/recent');

			if (!response.ok) {
				if (response.status === 401) {
					error = 'Session expired. Please log in again.';
				} else {
					error = 'Failed to load recently available content';
				}
				loading = false;
				return;
			}

			const result: RecentlyAvailableResponse = await response.json();
			data = result;
			groupedData = groupItemsByDate(result.items);
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

{#if toast}
	<div class="toast toast-{toast.type}" role="alert">{toast.message}</div>
{/if}

<div class="page">
	<header class="page-header">
		<div class="header-main">
			<h1>Recently Available</h1>
			{#if data && !loading}
				<span class="header-stats">{data.total_count} item{data.total_count !== 1 ? 's' : ''}</span>
			{/if}
		</div>
		{#if data && data.total_count > 0}
			<button class="copy-btn" onclick={copyList}>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
					<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
				</svg>
				Copy
			</button>
		{/if}
	</header>

	<p class="page-subtitle">Content that became available in the past 7 days</p>

	{#if loading}
		<div class="loading">
			<span class="spinner"></span>
		</div>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else if data}
		{#if data.items.length === 0}
			<div class="empty">No content became available in the past 7 days</div>
		{:else}
			<div class="table-container">
				<table class="data-table">
					<thead>
						<tr>
							<th class="col-date">Date</th>
							<th class="col-title">Title</th>
							<th class="col-type">Type</th>
							<th class="col-requester">Requested by</th>
						</tr>
					</thead>
					<tbody>
						{#each groupedData as group, groupIndex}
							{#each group.items as item, itemIndex}
								<tr>
									{#if itemIndex === 0}
										<td class="col-date" rowspan={group.items.length}>
											<span class="date-label">{group.dateFormatted}</span>
										</td>
									{/if}
									<td class="col-title">
										<span class="item-title">{item.title}</span>
									</td>
									<td class="col-type">
										<span class="type-badge type-{item.media_type}">
											{item.media_type === 'tv' ? 'TV' : 'Movie'}
										</span>
									</td>
									<td class="col-requester">
										{item.requested_by || '-'}
									</td>
								</tr>
							{/each}
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>

<style>
	.page {
		max-width: 900px;
		margin: 0 auto;
		padding: var(--space-6);
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-2);
	}

	.header-main {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
	}

	.header-stats {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		font-family: var(--font-mono);
	}

	.page-subtitle {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-6);
	}

	.copy-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.copy-btn:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	/* Loading & Error */
	.loading {
		display: flex;
		justify-content: center;
		padding: var(--space-12);
	}

	.spinner {
		width: 24px;
		height: 24px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error-box {
		padding: var(--space-4);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
	}

	.empty {
		padding: var(--space-8);
		text-align: center;
		color: var(--text-muted);
	}

	/* Table */
	.table-container {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
	}

	.data-table th,
	.data-table td {
		padding: var(--space-3) var(--space-4);
		text-align: left;
	}

	.data-table th {
		background: var(--bg-secondary);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
		border-bottom: 1px solid var(--border);
	}

	.data-table tr {
		border-bottom: 1px solid var(--border);
	}

	.data-table tr:last-child {
		border-bottom: none;
	}

	.data-table tbody tr:hover {
		background: var(--bg-hover);
	}

	/* Columns */
	.col-date {
		width: 100px;
		vertical-align: top;
		border-right: 1px solid var(--border);
	}

	.date-label {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
	}

	.col-title {
		width: 45%;
	}

	.item-title {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
	}

	.col-type {
		width: 80px;
	}

	.type-badge {
		display: inline-block;
		padding: 2px 6px;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		border-radius: var(--radius-sm);
	}

	.type-badge.type-movie {
		background: var(--info-light);
		color: var(--info);
	}

	.type-badge.type-tv {
		background: var(--success-light);
		color: var(--success);
	}

	.col-requester {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	/* Responsive */
	@media (max-width: 640px) {
		.page {
			padding: var(--space-4);
		}

		.col-requester {
			display: none;
		}

		.data-table th,
		.data-table td {
			padding: var(--space-2) var(--space-3);
		}
	}
</style>
