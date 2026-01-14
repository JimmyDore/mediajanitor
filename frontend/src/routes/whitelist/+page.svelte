<script lang="ts">
	import { onMount } from 'svelte';

	interface WhitelistItem {
		id: number;
		jellyfin_id: string;
		name: string;
		media_type: string;
		created_at: string;
		expires_at: string | null;
	}

	interface WhitelistResponse {
		items: WhitelistItem[];
		total_count: number;
	}

	type TabType = 'protected' | 'french' | 'exempt';

	let loading = $state(true);
	let activeTab = $state<TabType>('protected');
	let protectedData = $state<WhitelistResponse | null>(null);
	let frenchOnlyData = $state<WhitelistResponse | null>(null);
	let languageExemptData = $state<WhitelistResponse | null>(null);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let removingIds = $state<Set<number>>(new Set());

	const tabLabels: Record<TabType, { label: string; desc: string }> = {
		protected: { label: 'Protected', desc: 'Won\'t appear in old/unwatched list' },
		french: { label: 'French-Only', desc: 'Won\'t flag missing English audio' },
		exempt: { label: 'Language Exempt', desc: 'Won\'t flag any language issues' }
	};

	function formatDate(dateStr: string): string {
		try {
			const date = new Date(dateStr);
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		} catch { return '?'; }
	}

	function formatExpiration(expiresAt: string | null): string {
		if (!expiresAt) return 'Permanent';
		try {
			const date = new Date(expiresAt);
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
		} catch { return '?'; }
	}

	function isExpired(expiresAt: string | null): boolean {
		if (!expiresAt) return false;
		try {
			return new Date(expiresAt) < new Date();
		} catch { return false; }
	}

	function showToast(message: string, type: 'success' | 'error') {
		toast = { message, type };
		setTimeout(() => toast = null, 3000);
	}

	function getCurrentData(): WhitelistResponse | null {
		switch (activeTab) {
			case 'protected': return protectedData;
			case 'french': return frenchOnlyData;
			case 'exempt': return languageExemptData;
		}
	}

	function getApiPath(): string {
		switch (activeTab) {
			case 'protected': return '/api/whitelist/content';
			case 'french': return '/api/whitelist/french-only';
			case 'exempt': return '/api/whitelist/language-exempt';
		}
	}

	async function removeItem(item: WhitelistItem) {
		const token = localStorage.getItem('access_token');
		if (!token) { showToast('Not authenticated', 'error'); return; }

		removingIds = new Set([...removingIds, item.id]);

		try {
			const response = await fetch(`${getApiPath()}/${item.id}`, {
				method: 'DELETE',
				headers: { Authorization: `Bearer ${token}` }
			});

			if (!response.ok) { showToast('Failed to remove', 'error'); return; }

			// Update the correct data source
			const updateData = (data: WhitelistResponse | null) => {
				if (!data) return null;
				return {
					...data,
					items: data.items.filter((i) => i.id !== item.id),
					total_count: data.total_count - 1
				};
			};

			switch (activeTab) {
				case 'protected': protectedData = updateData(protectedData); break;
				case 'french': frenchOnlyData = updateData(frenchOnlyData); break;
				case 'exempt': languageExemptData = updateData(languageExemptData); break;
			}

			showToast('Removed', 'success');
		} catch { showToast('Failed', 'error'); }
		finally {
			const newSet = new Set(removingIds);
			newSet.delete(item.id);
			removingIds = newSet;
		}
	}

	async function fetchAll() {
		const token = localStorage.getItem('access_token');
		if (!token) return;

		try {
			const [p, f, e] = await Promise.all([
				fetch('/api/whitelist/content', { headers: { Authorization: `Bearer ${token}` } }),
				fetch('/api/whitelist/french-only', { headers: { Authorization: `Bearer ${token}` } }),
				fetch('/api/whitelist/language-exempt', { headers: { Authorization: `Bearer ${token}` } })
			]);

			if (p.ok) protectedData = await p.json();
			if (f.ok) frenchOnlyData = await f.json();
			if (e.ok) languageExemptData = await e.json();
		} catch {}
		finally { loading = false; }
	}

	onMount(fetchAll);
</script>

<svelte:head>
	<title>Whitelist - Media Janitor</title>
</svelte:head>

{#if toast}
	<div class="toast toast-{toast.type}" role="alert">{toast.message}</div>
{/if}

<div class="whitelist-page">
	<header class="page-header">
		<h1>Whitelists</h1>
	</header>

	<!-- Tabs -->
	<nav class="tabs">
		{#each Object.entries(tabLabels) as [tab, { label }]}
			{@const count = tab === 'protected' ? protectedData?.total_count : tab === 'french' ? frenchOnlyData?.total_count : languageExemptData?.total_count}
			<button
				class="tab"
				class:active={activeTab === tab}
				onclick={() => activeTab = tab as TabType}
			>
				{label}
				{#if count !== undefined && count > 0}
					<span class="tab-count">{count}</span>
				{/if}
			</button>
		{/each}
	</nav>

	<p class="tab-desc">{tabLabels[activeTab].desc}</p>

	{#if loading}
		<div class="loading"><span class="spinner"></span></div>
	{:else}
		{@const currentData = getCurrentData()}
		{#if !currentData || currentData.items.length === 0}
			<div class="empty">
				<p>No items in this list</p>
				<p class="empty-hint">
					{#if activeTab === 'protected'}
						Use "Protect" on the <a href="/issues?filter=old">Issues</a> page
					{:else if activeTab === 'french'}
						Use "FR" on the <a href="/issues?filter=language">Issues</a> page
					{:else}
						Use the checkmark on the <a href="/issues?filter=language">Issues</a> page
					{/if}
				</p>
			</div>
		{:else}
			<div class="list">
				{#each currentData.items as item}
					<div class="list-item" class:expired={isExpired(item.expires_at)}>
						<div class="item-info">
							<span class="item-name">
								{item.name}
								{#if isExpired(item.expires_at)}
									<span class="badge-expired">Expired</span>
								{/if}
							</span>
							<span class="item-meta">
								{item.media_type === 'Movie' ? 'Movie' : 'Series'} · Added {formatDate(item.created_at)}
							</span>
							<span class="item-expiration" class:permanent={!item.expires_at}>
								{#if item.expires_at}
									Expires: {formatExpiration(item.expires_at)}
								{:else}
									Permanent
								{/if}
							</span>
						</div>
						<button
							class="btn-remove"
							onclick={() => removeItem(item)}
							disabled={removingIds.has(item.id)}
							title="Remove"
						>
							{#if removingIds.has(item.id)}
								<span class="btn-spin"></span>
							{:else}
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<line x1="18" y1="6" x2="6" y2="18"/>
									<line x1="6" y1="6" x2="18" y2="18"/>
								</svg>
							{/if}
						</button>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.whitelist-page {
		max-width: 640px;
		margin: 0 auto;
		padding: var(--space-6);
	}

	.page-header {
		margin-bottom: var(--space-6);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.02em;
	}

	/* Tabs */
	.tabs {
		display: flex;
		gap: var(--space-1);
		border-bottom: 1px solid var(--border);
		margin-bottom: var(--space-2);
	}

	.tab {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		cursor: pointer;
		transition: all var(--transition-fast);
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.tab:hover {
		color: var(--text-primary);
	}

	.tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--accent);
	}

	.tab-count {
		background: var(--bg-tertiary);
		padding: 1px 6px;
		border-radius: 10px;
		font-size: var(--font-size-xs);
		font-family: var(--font-mono);
	}

	.tab.active .tab-count {
		background: var(--accent-light);
		color: var(--accent);
	}

	.tab-desc {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		margin-bottom: var(--space-6);
	}

	/* Loading */
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

	/* Empty */
	.empty {
		text-align: center;
		padding: var(--space-8);
		color: var(--text-muted);
	}

	.empty p {
		margin: 0 0 var(--space-2) 0;
	}

	.empty-hint {
		font-size: var(--font-size-sm);
	}

	.empty-hint a {
		color: var(--accent);
		text-decoration: none;
	}

	.empty-hint a:hover {
		text-decoration: underline;
	}

	/* List */
	.list {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.list-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.list-item:last-child {
		border-bottom: none;
	}

	.list-item:hover {
		background: var(--bg-hover);
	}

	.item-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.item-name {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.item-meta {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.item-expiration {
		font-size: var(--font-size-xs);
		color: var(--text-muted);
		font-family: var(--font-mono);
	}

	.item-expiration.permanent {
		color: var(--success);
	}

	.badge-expired {
		display: inline-block;
		padding: 1px 6px;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		background: var(--danger-light);
		color: var(--danger);
		border-radius: var(--radius-sm);
		margin-left: var(--space-2);
	}

	.list-item.expired {
		opacity: 0.6;
	}

	.list-item.expired .item-name {
		color: var(--text-muted);
	}

	.btn-remove {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
		flex-shrink: 0;
	}

	.btn-remove:hover:not(:disabled) {
		color: var(--danger);
		border-color: var(--danger);
	}

	.btn-remove:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-spin {
		width: 12px;
		height: 12px;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Responsive */
	@media (max-width: 640px) {
		.whitelist-page {
			padding: var(--space-4);
		}

		.tabs {
			overflow-x: auto;
		}
	}
</style>
