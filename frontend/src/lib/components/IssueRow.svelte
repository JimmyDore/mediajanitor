<script lang="ts">
	import ServiceBadge from './ServiceBadge.svelte';

	interface ProblematicEpisode {
		identifier: string;
		name: string;
		season: number;
		episode: number;
		missing_languages: string[];
	}

	interface ContentIssueItem {
		jellyfin_id: string;
		name: string;
		media_type: string;
		production_year: number | null;
		size_bytes: number | null;
		size_formatted: string;
		last_played_date: string | null;
		played: boolean | null;
		path: string | null;
		date_created: string | null;
		issues: string[];
		language_issues: string[] | null;
		tmdb_id: string | null;
		imdb_id: string | null;
		sonarr_title_slug: string | null;
		jellyseerr_request_id: number | null;
		largest_season_size_bytes: number | null;
		largest_season_size_formatted: string | null;
		requested_by: string | null;
		request_date: string | null;
		missing_seasons: number[] | null;
		release_date: string | null;
		problematic_episodes: ProblematicEpisode[] | null;
	}

	interface ServiceUrls {
		jellyfin_url: string | null;
		jellyseerr_url: string | null;
		radarr_url: string | null;
		sonarr_url: string | null;
	}

	type WhitelistType = 'content' | 'french-only' | 'language-exempt' | 'large' | 'request';

	interface Props {
		item: ContentIssueItem;
		activeFilter: string;
		serviceUrls: ServiceUrls | null;
		protectingIds: Set<string>;
		frenchOnlyIds: Set<string>;
		languageExemptIds: Set<string>;
		largeWhitelistIds: Set<string>;
		hidingRequestIds: Set<string>;
		deletingIds: Set<string>;
		whitelistingEpisodeIds: Set<string>;
		expanded: boolean;
		canDeleteFromArr: boolean;
		arrName: string;
		badgeTooltips: Record<string, string>;
		onopenDurationPicker: (item: ContentIssueItem, type: WhitelistType) => void;
		onopenDeleteModal: (item: ContentIssueItem) => void;
		ondeleteRequest: (item: ContentIssueItem) => void;
		ontoggleExpansion: (jellyfinId: string) => void;
		onopenEpisodeDurationPicker: (item: ContentIssueItem, episode: ProblematicEpisode) => void;
	}

	let {
		item,
		activeFilter,
		serviceUrls,
		protectingIds,
		frenchOnlyIds,
		languageExemptIds,
		largeWhitelistIds,
		hidingRequestIds,
		deletingIds,
		whitelistingEpisodeIds,
		expanded,
		canDeleteFromArr,
		arrName,
		badgeTooltips,
		onopenDurationPicker,
		onopenDeleteModal,
		ondeleteRequest,
		ontoggleExpansion,
		onopenEpisodeDurationPicker
	}: Props = $props();

	function isRequestItem(item: ContentIssueItem): boolean {
		return item.issues.includes('request');
	}

	function isSeriesItem(item: ContentIssueItem): boolean {
		const type = item.media_type.toLowerCase();
		return type === 'series' || type === 'tv';
	}

	function hasExpandableEpisodes(item: ContentIssueItem): boolean {
		return item.problematic_episodes !== null && item.problematic_episodes.length > 0;
	}

	function hasMissingEnglishAudio(item: ContentIssueItem): boolean {
		return item.language_issues?.includes('missing_en_audio') ?? false;
	}

	function formatLastWatched(lastPlayed: string | null, played: boolean | null): string {
		if (lastPlayed) {
			try {
				const date = new Date(lastPlayed);
				const now = new Date();
				const daysAgo = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
				if (daysAgo > 365) return `${Math.floor(daysAgo / 365)}y`;
				if (daysAgo > 30) return `${Math.floor(daysAgo / 30)}mo`;
				return `${daysAgo}d`;
			} catch {
				return '?';
			}
		}
		if (played) return 'Watched';
		return 'Never';
	}

	function formatRequestDate(requestDate: string | null): string {
		if (!requestDate) return '—';
		try {
			const date = new Date(requestDate);
			const now = new Date();
			const daysAgo = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
			if (daysAgo > 365) return `${Math.floor(daysAgo / 365)}y ago`;
			if (daysAgo > 30) return `${Math.floor(daysAgo / 30)}mo ago`;
			if (daysAgo === 0) return 'Today';
			if (daysAgo === 1) return 'Yesterday';
			return `${daysAgo}d ago`;
		} catch {
			return '?';
		}
	}

	function formatReleaseDate(releaseDate: string | null): string {
		if (!releaseDate) return '—';
		try {
			const date = new Date(releaseDate);
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
		} catch {
			return '?';
		}
	}

	function formatDateCreated(dateCreated: string | null): string {
		if (!dateCreated) return 'Unknown';
		try {
			const date = new Date(dateCreated);
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
		} catch {
			return '?';
		}
	}

	function isFutureRelease(releaseDate: string | null): boolean {
		if (!releaseDate) return false;
		try {
			const date = new Date(releaseDate);
			const today = new Date();
			today.setHours(0, 0, 0, 0);
			return date > today;
		} catch {
			return false;
		}
	}

	function formatLanguageBadge(lang: string): string {
		switch (lang) {
			case 'missing_en_audio': return 'EN';
			case 'missing_fr_audio': return 'FR';
			case 'missing_fr_subs': return 'FR Sub';
			default: return lang;
		}
	}

	function getTmdbUrl(item: ContentIssueItem): string | null {
		if (!item.tmdb_id) return null;
		const mediaType = item.media_type.toLowerCase() === 'movie' ? 'movie' : 'tv';
		return `https://www.themoviedb.org/${mediaType}/${item.tmdb_id}`;
	}

	function getJellyfinUrl(item: ContentIssueItem): string | null {
		if (isRequestItem(item)) return null;
		const baseUrl = serviceUrls?.jellyfin_url;
		if (!baseUrl || !item.jellyfin_id) return null;
		return `${baseUrl.replace(/\/$/, '')}/web/index.html#!/details?id=${item.jellyfin_id}`;
	}

	function getJellyseerrUrl(item: ContentIssueItem): string | null {
		const baseUrl = serviceUrls?.jellyseerr_url;
		if (!baseUrl || !item.tmdb_id) return null;
		const mediaType = item.media_type.toLowerCase() === 'movie' ? 'movie' : 'tv';
		return `${baseUrl.replace(/\/$/, '')}/${mediaType}/${item.tmdb_id}`;
	}

	function getRadarrUrl(item: ContentIssueItem): string | null {
		if (item.media_type.toLowerCase() !== 'movie') return null;
		const baseUrl = serviceUrls?.radarr_url;
		if (!baseUrl || !item.tmdb_id) return null;
		return `${baseUrl.replace(/\/$/, '')}/movie/${item.tmdb_id}`;
	}

	function getSonarrUrl(item: ContentIssueItem): string | null {
		if (item.media_type.toLowerCase() !== 'series' && item.media_type.toLowerCase() !== 'tv') return null;
		const baseUrl = serviceUrls?.sonarr_url;
		if (!baseUrl || !item.sonarr_title_slug) return null;
		return `${baseUrl.replace(/\/$/, '')}/series/${item.sonarr_title_slug}`;
	}

	function handleRowClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (hasExpandableEpisodes(item) && !target.closest('button, a, .badge-action')) {
			ontoggleExpansion(item.jellyfin_id);
		}
	}

	function handleRowKeydown(e: KeyboardEvent) {
		if (hasExpandableEpisodes(item) && (e.key === 'Enter' || e.key === ' ')) {
			e.preventDefault();
			ontoggleExpansion(item.jellyfin_id);
		}
	}
</script>

<tr
	class:expandable={hasExpandableEpisodes(item)}
	class:expanded={expanded}
	onclick={handleRowClick}
	role={hasExpandableEpisodes(item) ? 'button' : undefined}
	tabindex={hasExpandableEpisodes(item) ? 0 : undefined}
	aria-expanded={hasExpandableEpisodes(item) ? expanded : undefined}
	onkeydown={handleRowKeydown}
>
	<td class="col-name">
		<div class="name-cell">
			<div class="title-row">
				{#if hasExpandableEpisodes(item)}
					<span class="expand-icon" aria-hidden="true">
						{#if expanded}
							<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
								<polyline points="6 9 12 15 18 9"/>
							</svg>
						{:else}
							<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
								<polyline points="9 18 15 12 9 6"/>
							</svg>
						{/if}
					</span>
				{/if}
				<span class="item-name" title={item.name}>{item.name}</span>
				<span class="item-year">{item.production_year ?? '—'}</span>
				{#if hasExpandableEpisodes(item)}
					<span class="episode-count" title="Episodes with language issues">
						{item.problematic_episodes?.length} {item.problematic_episodes?.length === 1 ? 'episode' : 'episodes'}
					</span>
				{/if}
				{#if isRequestItem(item) && item.missing_seasons && item.missing_seasons.length > 0}
					<span class="missing-seasons" title="Missing seasons">
						S{item.missing_seasons.join(', S')}
					</span>
				{/if}
			</div>
			<span class="external-links">
				{#if getJellyfinUrl(item)}
					<ServiceBadge service="jellyfin" url={getJellyfinUrl(item) ?? ''} title="View in Jellyfin" />
				{/if}
				{#if getJellyseerrUrl(item)}
					<ServiceBadge service="jellyseerr" url={getJellyseerrUrl(item) ?? ''} title="View in Jellyseerr" />
				{/if}
				{#if getRadarrUrl(item)}
					<ServiceBadge service="radarr" url={getRadarrUrl(item) ?? ''} title="View in Radarr" />
				{/if}
				{#if getSonarrUrl(item)}
					<ServiceBadge service="sonarr" url={getSonarrUrl(item) ?? ''} title="View in Sonarr" />
				{/if}
				{#if getTmdbUrl(item)}
					<ServiceBadge service="tmdb" url={getTmdbUrl(item) ?? ''} title="View on TMDB" />
				{/if}
			</span>
		</div>
	</td>
	{#if activeFilter === 'requests'}
		<td class="col-requester">
			{item.requested_by ?? '—'}
		</td>
	{/if}
	{#if activeFilter !== 'requests'}
	<td class="col-issues">
		<div class="badge-groups">
			{#each item.issues as issue}
				{#if issue === 'old'}
					<span class="badge-group">
						<span class="badge badge-old">old</span>
						<button
							class="badge-action"
							onclick={() => onopenDurationPicker(item, 'content')}
							disabled={protectingIds.has(item.jellyfin_id)}
							title="Protect from deletion"
						>
							{#if protectingIds.has(item.jellyfin_id)}
								<span class="badge-spin"></span>
							{:else}
								<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
									<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
								</svg>
							{/if}
						</button>
					</span>
				{:else if issue === 'language'}
					<span class="badge-group">
						<span class="badge badge-language">language</span>
						{#if hasMissingEnglishAudio(item)}
							<button
								class="badge-action"
								onclick={() => onopenDurationPicker(item, 'french-only')}
								disabled={frenchOnlyIds.has(item.jellyfin_id)}
								title="Mark as French-only"
							>
								{#if frenchOnlyIds.has(item.jellyfin_id)}
									<span class="badge-spin"></span>
								{:else}
									FR
								{/if}
							</button>
						{/if}
						<button
							class="badge-action"
							onclick={() => onopenDurationPicker(item, 'language-exempt')}
							disabled={languageExemptIds.has(item.jellyfin_id)}
							title="Exempt from language checks"
						>
							{#if languageExemptIds.has(item.jellyfin_id)}
								<span class="badge-spin"></span>
							{:else}
								<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
									<polyline points="20 6 9 17 4 12"/>
								</svg>
							{/if}
						</button>
					</span>
				{:else if issue === 'large'}
					<span class="badge-group">
						<span class="badge badge-large" title={badgeTooltips.large}>large</span>
						<button
							class="badge-action"
							onclick={() => onopenDurationPicker(item, 'large')}
							disabled={largeWhitelistIds.has(item.jellyfin_id)}
							title="Keep in high quality"
						>
							{#if largeWhitelistIds.has(item.jellyfin_id)}
								<span class="badge-spin"></span>
							{:else}
								<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
									<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
								</svg>
							{/if}
						</button>
					</span>
				{:else if issue === 'request'}
					<span class="badge-group">
						<span class="badge badge-request" title={badgeTooltips.request}>request</span>
						<button
							class="badge-action"
							onclick={() => onopenDurationPicker(item, 'request')}
							disabled={hidingRequestIds.has(item.jellyfin_id)}
							title="Hide this request"
						>
							{#if hidingRequestIds.has(item.jellyfin_id)}
								<span class="badge-spin"></span>
							{:else}
								<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
									<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
									<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
									<line x1="1" y1="1" x2="23" y2="23"/>
								</svg>
							{/if}
						</button>
					</span>
				{:else}
					<span class="badge badge-{issue}">{issue}</span>
				{/if}
			{/each}
		</div>
	</td>
	{/if}
	<td class="col-size">
		{#if isRequestItem(item)}
			<span class="text-muted">—</span>
		{:else if isSeriesItem(item) && item.largest_season_size_formatted}
			<span class="size-with-label" title="Largest season size">
				<span class="size-label">Largest season:</span>
				<span class="size-value">{item.largest_season_size_formatted}</span>
			</span>
		{:else}
			{item.size_formatted}
		{/if}
	</td>
	<td class="col-added">
		{#if isRequestItem(item)}
			<span class="text-muted">—</span>
		{:else}
			{formatDateCreated(item.date_created)}
		{/if}
	</td>
	{#if activeFilter === 'requests'}
		<td class="col-release" class:future={isFutureRelease(item.release_date)}>
			{formatReleaseDate(item.release_date)}
		</td>
	{/if}
	<td class="col-watched" class:never={!isRequestItem(item) && !item.last_played_date && !item.played}>
		{#if isRequestItem(item)}
			{formatRequestDate(item.request_date)}
		{:else}
			{formatLastWatched(item.last_played_date, item.played)}
		{/if}
	</td>
	<td class="col-actions">
		{#if isRequestItem(item)}
			<div class="action-buttons">
				<button
					class="btn-action btn-whitelist"
					onclick={() => onopenDurationPicker(item, 'request')}
					disabled={hidingRequestIds.has(item.jellyfin_id)}
					title="Hide this request"
				>
					{#if hidingRequestIds.has(item.jellyfin_id)}
						<span class="btn-spinner"></span>
					{:else}
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
							<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
							<line x1="1" y1="1" x2="23" y2="23"/>
						</svg>
					{/if}
				</button>
				<button
					class="btn-action btn-delete"
					onclick={() => ondeleteRequest(item)}
					disabled={deletingIds.has(item.jellyfin_id)}
					title="Delete request from Jellyseerr"
				>
					{#if deletingIds.has(item.jellyfin_id)}
						<span class="btn-spinner"></span>
					{:else}
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<polyline points="3 6 5 6 21 6"/>
							<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
						</svg>
					{/if}
				</button>
			</div>
		{:else}
			<button
				class="btn-delete"
				onclick={() => onopenDeleteModal(item)}
				disabled={deletingIds.has(item.jellyfin_id) || !item.tmdb_id || !canDeleteFromArr}
				title={!item.tmdb_id ? 'No TMDB ID' : !canDeleteFromArr ? `${arrName} not configured` : `Delete from ${arrName}`}
			>
				{#if deletingIds.has(item.jellyfin_id)}
					<span class="btn-spinner"></span>
				{:else}
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="3 6 5 6 21 6"/>
						<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
					</svg>
				{/if}
			</button>
		{/if}
	</td>
</tr>
{#if hasExpandableEpisodes(item) && expanded}
	<tr class="episode-row">
		<td colspan={activeFilter === 'requests' ? 7 : 6}>
			<div class="episode-list">
				{#each item.problematic_episodes ?? [] as episode}
					{@const episodeKey = `${item.jellyfin_id}-${episode.season}-${episode.episode}`}
					<div class="episode-item">
						<span class="episode-identifier">{episode.identifier}</span>
						<span class="episode-name" title={episode.name}>{episode.name}</span>
						<div class="episode-badges">
							{#each episode.missing_languages as lang}
								<span class="episode-badge badge-missing-{lang.replace('missing_', '').replace('_', '-')}">
									{formatLanguageBadge(lang)}
								</span>
							{/each}
						</div>
						<button
							class="btn-whitelist-episode"
							onclick={(e) => {
								e.stopPropagation();
								onopenEpisodeDurationPicker(item, episode);
							}}
							disabled={whitelistingEpisodeIds.has(episodeKey)}
							title="Whitelist this episode"
						>
							{#if whitelistingEpisodeIds.has(episodeKey)}
								<span class="btn-spinner"></span>
							{:else}
								Whitelist
							{/if}
						</button>
					</div>
				{/each}
			</div>
		</td>
	</tr>
{/if}

<style>
	/* Row styling */
	tr.expandable {
		cursor: pointer;
	}

	tr.expandable:hover {
		background: var(--bg-hover);
	}

	tr.expanded {
		background: var(--bg-secondary);
	}

	/* Name cell */
	.col-name {
		width: 32%;
		min-width: 180px;
	}

	.name-cell {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
		flex: 1;
	}

	.expand-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		margin-right: var(--space-1);
		color: var(--text-muted);
		flex-shrink: 0;
	}

	.item-name {
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 60px;
		flex: 1 1 auto;
	}

	.item-year {
		font-size: var(--font-size-sm);
		font-family: var(--font-mono);
		color: var(--text-muted);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.episode-count {
		font-size: var(--font-size-xs);
		color: var(--info);
		font-weight: var(--font-weight-medium);
		padding: 1px 6px;
		background: var(--info-light);
		border-radius: var(--radius-sm);
		white-space: nowrap;
	}

	.missing-seasons {
		font-size: var(--font-size-xs);
		color: var(--warning);
		font-weight: var(--font-weight-medium);
	}

	.external-links {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		flex-shrink: 0;
	}

	.text-muted {
		color: var(--text-muted);
	}

	/* Column styles */
	.col-requester {
		width: 10%;
		min-width: 80px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.col-issues {
		width: 28%;
		min-width: 140px;
	}

	.col-size {
		width: 10%;
		min-width: 80px;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.size-with-label {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 1px;
		line-height: 1.2;
	}

	.size-label {
		font-size: var(--font-size-xs);
		font-family: var(--font-sans);
		color: var(--text-muted);
	}

	.size-value {
		font-family: var(--font-mono);
	}

	.col-added {
		width: 10%;
		min-width: 80px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-release {
		width: 10%;
		min-width: 80px;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-release.future {
		color: var(--warning);
		font-weight: var(--font-weight-medium);
	}

	.col-watched {
		width: 10%;
		min-width: 70px;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		text-align: right;
	}

	.col-watched.never {
		color: var(--warning);
	}

	.col-actions {
		width: 48px;
		text-align: center;
	}

	/* Badge styles */
	.badge-groups {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.badge-group {
		display: inline-flex;
		align-items: center;
		gap: 0;
	}

	.badge {
		display: inline-flex;
		align-items: center;
		padding: 2px 6px;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		border-radius: var(--radius-sm);
		cursor: default;
	}

	.badge-group .badge {
		border-radius: var(--radius-sm) 0 0 var(--radius-sm);
	}

	.badge-old {
		background: var(--danger-light);
		color: var(--danger);
	}

	.badge-large {
		background: var(--warning-light);
		color: var(--warning);
		cursor: help;
	}

	.badge-language {
		background: var(--info-light);
		color: var(--info);
	}

	.badge-request {
		background: rgba(139, 92, 246, 0.1);
		color: #8b5cf6;
		cursor: help;
	}

	.badge-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 22px;
		height: 20px;
		padding: 0 4px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-left: none;
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
		font-size: 9px;
		font-weight: var(--font-weight-bold);
	}

	.badge-action:first-of-type {
		border-left: 1px solid var(--border);
	}

	.badge-action:last-child {
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
	}

	.badge-action:hover:not(:disabled) {
		color: var(--text-primary);
		background: var(--bg-hover);
		border-color: var(--text-muted);
	}

	.badge-action:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.badge-spin {
		width: 10px;
		height: 10px;
		border: 1.5px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Action buttons */
	.action-buttons {
		display: inline-flex;
		gap: var(--space-1);
	}

	.btn-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		padding: 0;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-action:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-whitelist:hover:not(:disabled) {
		color: var(--accent);
		border-color: var(--accent);
		background: var(--accent-light);
	}

	.btn-delete {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		padding: 0;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-delete:hover:not(:disabled) {
		color: var(--danger);
		border-color: var(--danger);
		background: var(--danger-light);
	}

	.btn-delete:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-spinner {
		width: 12px;
		height: 12px;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Episode row styles */
	tr.episode-row {
		background: var(--bg-secondary);
	}

	tr.episode-row:hover {
		background: var(--bg-secondary);
	}

	tr.episode-row td {
		padding: 0;
	}

	.episode-list {
		padding: var(--space-3) var(--space-4);
		padding-left: calc(var(--space-4) + 24px);
		border-top: 1px solid var(--border);
	}

	.episode-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) var(--space-3);
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		margin-bottom: var(--space-2);
	}

	.episode-item:last-child {
		margin-bottom: 0;
	}

	.episode-identifier {
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		min-width: 60px;
	}

	.episode-name {
		flex: 1;
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.episode-badges {
		display: flex;
		gap: var(--space-1);
		flex-shrink: 0;
	}

	.episode-badge {
		display: inline-flex;
		align-items: center;
		padding: 1px 6px;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		border-radius: var(--radius-sm);
	}

	.badge-missing-en-audio {
		background: var(--danger-light);
		color: var(--danger);
	}

	.badge-missing-fr-audio {
		background: var(--warning-light);
		color: var(--warning);
	}

	.badge-missing-fr-subs {
		background: var(--info-light);
		color: var(--info);
	}

	.btn-whitelist-episode {
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
		flex-shrink: 0;
		min-width: 75px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.btn-whitelist-episode:hover:not(:disabled) {
		color: var(--accent);
		border-color: var(--accent);
		background: var(--accent-light);
	}

	.btn-whitelist-episode:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Responsive styles - keeping mobile adaptations at component level is complex */
	/* The parent page handles the responsive table layout transforms */
</style>
