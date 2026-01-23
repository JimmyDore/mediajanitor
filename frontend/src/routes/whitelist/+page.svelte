<script lang="ts">
	import { onMount } from 'svelte';
	import { authenticatedFetch } from '$lib/stores';
	import Toast from '$lib/components/Toast.svelte';

	interface WhitelistItem {
		id: number;
		jellyfin_id: string;
		name: string;
		media_type: string;
		created_at: string;
		expires_at: string | null;
	}

	interface RequestWhitelistItem {
		id: number;
		jellyseerr_id: number;
		title: string;
		media_type: string;
		created_at: string;
		expires_at: string | null;
	}

	interface WhitelistResponse {
		items: WhitelistItem[];
		total_count: number;
	}

	interface RequestWhitelistResponse {
		items: RequestWhitelistItem[];
		total_count: number;
	}

	interface EpisodeExemptItem {
		id: number;
		jellyfin_id: string;
		series_name: string;
		season_number: number;
		episode_number: number;
		episode_name: string;
		identifier: string;
		created_at: string;
		expires_at: string | null;
	}

	interface EpisodeExemptResponse {
		items: EpisodeExemptItem[];
		total_count: number;
	}

	type TabType = 'protected' | 'french' | 'exempt' | 'episode' | 'large' | 'requests';

	let loading = $state(true);
	let activeTab = $state<TabType>('protected');
	let protectedData = $state<WhitelistResponse | null>(null);
	let frenchOnlyData = $state<WhitelistResponse | null>(null);
	let languageExemptData = $state<WhitelistResponse | null>(null);
	let largeContentData = $state<WhitelistResponse | null>(null);
	let episodeExemptData = $state<EpisodeExemptResponse | null>(null);
	let requestsData = $state<RequestWhitelistResponse | null>(null);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let toastTimer: ReturnType<typeof setTimeout> | null = null;
	let removingIds = $state<Set<number>>(new Set());

	const tabLabels: Record<TabType, { label: string; desc: string }> = {
		protected: { label: 'Protected', desc: 'Won\'t appear in old/unwatched list' },
		french: { label: 'French-Only', desc: 'Won\'t flag missing English audio' },
		exempt: { label: 'Language Exempt', desc: 'Won\'t flag any language issues' },
		episode: { label: 'Episode Exempt', desc: 'Individual episodes exempt from language checks' },
		large: { label: 'Large Content', desc: 'Won\'t appear in large files list' },
		requests: { label: 'Hidden Requests', desc: 'Requests hidden from the Issues view' }
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

	function isRequestItem(item: WhitelistItem | RequestWhitelistItem | EpisodeExemptItem): item is RequestWhitelistItem {
		return 'title' in item && 'jellyseerr_id' in item;
	}

	function isEpisodeExemptItem(item: WhitelistItem | RequestWhitelistItem | EpisodeExemptItem): item is EpisodeExemptItem {
		return 'series_name' in item && 'episode_name' in item;
	}

	function getItemName(item: WhitelistItem | RequestWhitelistItem | EpisodeExemptItem): string {
		if (isEpisodeExemptItem(item)) return item.series_name;
		return isRequestItem(item) ? item.title : item.name;
	}

	function getMediaTypeDisplay(item: WhitelistItem | RequestWhitelistItem | EpisodeExemptItem): string {
		if (isEpisodeExemptItem(item)) return item.identifier;
		if (isRequestItem(item)) {
			return item.media_type === 'movie' ? 'Movie' : 'TV Show';
		}
		return item.media_type === 'Movie' ? 'Movie' : 'Series';
	}

	function showToast(message: string, type: 'success' | 'error') {
		if (toastTimer) {
			clearTimeout(toastTimer);
		}
		toast = { message, type };
		toastTimer = setTimeout(() => {
			toast = null;
			toastTimer = null;
		}, 3000);
	}

	function closeToast() {
		if (toastTimer) {
			clearTimeout(toastTimer);
			toastTimer = null;
		}
		toast = null;
	}

	function getCurrentData(): WhitelistResponse | RequestWhitelistResponse | EpisodeExemptResponse | null {
		switch (activeTab) {
			case 'protected': return protectedData;
			case 'french': return frenchOnlyData;
			case 'exempt': return languageExemptData;
			case 'episode': return episodeExemptData;
			case 'large': return largeContentData;
			case 'requests': return requestsData;
		}
	}

	function getApiPath(): string {
		switch (activeTab) {
			case 'protected': return '/api/whitelist/content';
			case 'french': return '/api/whitelist/french-only';
			case 'exempt': return '/api/whitelist/language-exempt';
			case 'episode': return '/api/whitelist/episode-exempt';
			case 'large': return '/api/whitelist/large';
			case 'requests': return '/api/whitelist/requests';
		}
	}

	async function removeItem(item: WhitelistItem | RequestWhitelistItem | EpisodeExemptItem) {
		removingIds = new Set([...removingIds, item.id]);

		try {
			const response = await authenticatedFetch(`${getApiPath()}/${item.id}`, {
				method: 'DELETE'
			});

			if (!response.ok) { showToast('Failed to remove', 'error'); return; }

			// Update the correct data source
			const updateData = <T extends { id: number }>(data: { items: T[]; total_count: number } | null) => {
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
				case 'episode': episodeExemptData = updateData(episodeExemptData); break;
				case 'large': largeContentData = updateData(largeContentData); break;
				case 'requests': requestsData = updateData(requestsData); break;
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
		try {
			const [p, f, e, ep, l, r] = await Promise.all([
				authenticatedFetch('/api/whitelist/content'),
				authenticatedFetch('/api/whitelist/french-only'),
				authenticatedFetch('/api/whitelist/language-exempt'),
				authenticatedFetch('/api/whitelist/episode-exempt'),
				authenticatedFetch('/api/whitelist/large'),
				authenticatedFetch('/api/whitelist/requests')
			]);

			if (p.ok) protectedData = await p.json();
			if (f.ok) frenchOnlyData = await f.json();
			if (e.ok) languageExemptData = await e.json();
			if (ep.ok) episodeExemptData = await ep.json();
			if (l.ok) largeContentData = await l.json();
			if (r.ok) requestsData = await r.json();
		} catch {}
		finally { loading = false; }
	}

	onMount(fetchAll);
</script>

<svelte:head>
	<title>Whitelist - Media Janitor</title>
</svelte:head>

{#if toast}
	<Toast message={toast.message} type={toast.type} onclose={closeToast} />
{/if}

<div class="whitelist-page" aria-busy={loading}>
	<header class="page-header">
		<h1>Whitelists</h1>
	</header>

	<!-- Tabs -->
	<nav class="tabs">
		{#each Object.entries(tabLabels) as [tab, { label }]}
			{@const count = tab === 'protected' ? protectedData?.total_count : tab === 'french' ? frenchOnlyData?.total_count : tab === 'exempt' ? languageExemptData?.total_count : tab === 'episode' ? episodeExemptData?.total_count : tab === 'large' ? largeContentData?.total_count : requestsData?.total_count}
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
		<div class="loading" role="status" aria-label="Loading whitelist"><span class="spinner" aria-hidden="true"></span></div>
	{:else}
		{@const currentData = getCurrentData()}
		{#if !currentData || currentData.items.length === 0}
			<div class="empty" aria-live="polite">
				<p>No items in this list</p>
				<p class="empty-hint">
					{#if activeTab === 'protected'}
						Use "Protect" on the <a href="/issues?filter=old">Issues</a> page
					{:else if activeTab === 'french'}
						Use "FR" on the <a href="/issues?filter=language">Issues</a> page
					{:else if activeTab === 'exempt'}
						Use the checkmark on the <a href="/issues?filter=language">Issues</a> page
					{:else if activeTab === 'episode'}
						Use "Whitelist" on episodes in the <a href="/issues?filter=language">Issues</a> page
					{:else if activeTab === 'large'}
						Use the shield icon on the <a href="/issues?filter=large">Issues</a> page
					{:else}
						Use "Hide" on the <a href="/issues?filter=requests">Issues</a> page
					{/if}
				</p>
			</div>
		{:else}
			<div class="list">
				{#each currentData.items as item}
					<div class="list-item" class:expired={isExpired(item.expires_at)}>
						<div class="item-info">
							<span class="item-name">
								{getItemName(item)}
								{#if isExpired(item.expires_at)}
									<span class="badge-expired">Expired</span>
								{/if}
							</span>
							<span class="item-meta">
								{#if isEpisodeExemptItem(item)}
									{item.identifier} · {item.episode_name} · Added {formatDate(item.created_at)}
								{:else}
									{getMediaTypeDisplay(item)} · Added {formatDate(item.created_at)}
								{/if}
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
