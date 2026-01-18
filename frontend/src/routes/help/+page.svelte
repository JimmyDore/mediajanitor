<script lang="ts">
	interface FAQ {
		question: string;
		answer: string;
	}

	interface FAQSection {
		title: string;
		icon: string;
		faqs: FAQ[];
	}

	const sections: FAQSection[] = [
		{
			title: 'Getting Started',
			icon: 'rocket',
			faqs: [
				{
					question: 'What is Media Janitor?',
					answer: 'Media Janitor helps you manage your Plex/Jellyfin media library by identifying content that may need attention: old unwatched content, large files that could be re-encoded, language issues, and pending media requests.'
				},
				{
					question: 'How do I connect my media server?',
					answer: 'Go to Settings and enter your Jellyfin server URL and API key. You can find your API key in Jellyfin under Dashboard > API Keys. The connection is validated before saving.'
				},
				{
					question: 'How do I connect Jellyseerr?',
					answer: 'In Settings, enter your Jellyseerr server URL and API key. The API key can be found in Jellyseerr under Settings > General. This enables request management features.'
				},
				{
					question: 'How often is my data synced?',
					answer: 'Data is synced automatically once per day. You can also trigger a manual sync from the Dashboard by clicking the Refresh button (limited to once every 5 minutes).'
				}
			]
		},
		{
			title: 'Dashboard',
			icon: 'grid',
			faqs: [
				{
					question: 'What do the numbers on the Dashboard mean?',
					answer: 'Each card shows the count of items in that category: Old/Unwatched (content not watched in X months), Large Movies (files above your size threshold), Language Issues (missing audio/subtitles), and Unavailable Requests (pending Jellyseerr requests).'
				},
				{
					question: 'Why is "Last synced" showing a long time ago?',
					answer: 'This means no automatic sync has run recently. Click the Refresh button to trigger a manual sync. Ensure your Jellyfin and Jellyseerr connections are configured in Settings.'
				},
				{
					question: 'What does "Syncing..." mean?',
					answer: 'Media Janitor is fetching the latest data from your Jellyfin and Jellyseerr servers. This may take a few minutes depending on your library size.'
				}
			]
		},
		{
			title: 'Issues',
			icon: 'alert',
			faqs: [
				{
					question: 'What is the Old/Unwatched filter?',
					answer: 'Shows content that hasn\'t been watched in X months (configurable in Settings). This helps identify content that could be removed to free up space.'
				},
				{
					question: 'What is the Large filter?',
					answer: 'Shows movies larger than your size threshold (default: 13GB). These might benefit from re-encoding to a smaller file size without noticeable quality loss.'
				},
				{
					question: 'What is the Language filter?',
					answer: 'Shows content with language issues: missing English or French audio tracks, or missing French subtitles. You can mark content as French-only or Language Exempt using the action buttons.'
				},
				{
					question: 'What is the Requests filter?',
					answer: 'Shows Jellyseerr requests that are pending or unavailable. Requests with future release dates are hidden by default (configurable in Settings).'
				},
				{
					question: 'What do the badge action buttons do?',
					answer: 'Protect (shield icon) adds content to the protected whitelist. FR marks it as French-only (no English required). The checkmark marks it as language exempt. Hide (eye-slash) hides a request from the list.'
				}
			]
		},
		{
			title: 'Whitelists',
			icon: 'shield',
			faqs: [
				{
					question: 'What are whitelists?',
					answer: 'Whitelists let you exclude content from appearing in the Issues list. There are four types: Protected (won\'t show in Old/Unwatched), French-Only (won\'t flag missing English), Language Exempt (no language checks), and Hidden Requests.'
				},
				{
					question: 'What is the difference between Permanent and Temporary whitelist?',
					answer: 'Permanent whitelist entries never expire. Temporary entries automatically expire after the selected duration (3 months, 6 months, 1 year, or a custom date). Expired entries are shown with an "Expired" badge.'
				},
				{
					question: 'How do I remove something from a whitelist?',
					answer: 'Go to the Whitelist page, find the item in the appropriate tab, and click the X button to remove it. The content will start appearing in Issues again.'
				}
			]
		},
		{
			title: 'Settings',
			icon: 'settings',
			faqs: [
				{
					question: 'What are the threshold settings?',
					answer: '"Flag content unwatched for X months" sets how long content must be unwatched to appear in Issues. "Don\'t flag content newer than X months" excludes recently added content. "Flag movies larger than X GB" sets the size threshold for large movies.'
				},
				{
					question: 'What does "Show unreleased requests" do?',
					answer: 'When enabled, requests for content that hasn\'t been released yet will appear in the Requests filter. When disabled (default), only released content requests are shown.'
				},
				{
					question: 'How do I update my API keys?',
					answer: 'Click Edit on the Jellyfin or Jellyseerr connection, enter the new API key, and click Save. The connection is validated before saving.'
				}
			]
		}
	];

	let searchQuery = $state('');
	let expandedItems = $state<Set<string>>(new Set());

	// Filter FAQs based on search query
	let filteredSections = $derived.by(() => {
		if (!searchQuery.trim()) return sections;

		const query = searchQuery.toLowerCase();
		return sections
			.map(section => ({
				...section,
				faqs: section.faqs.filter(
					faq =>
						faq.question.toLowerCase().includes(query) ||
						faq.answer.toLowerCase().includes(query)
				)
			}))
			.filter(section => section.faqs.length > 0);
	});

	function toggleItem(sectionIndex: number, faqIndex: number) {
		const key = `${sectionIndex}-${faqIndex}`;
		const newSet = new Set(expandedItems);
		if (newSet.has(key)) {
			newSet.delete(key);
		} else {
			newSet.add(key);
		}
		expandedItems = newSet;
	}

	function isExpanded(sectionIndex: number, faqIndex: number): boolean {
		return expandedItems.has(`${sectionIndex}-${faqIndex}`);
	}

	function getSectionIcon(iconName: string): string {
		const icons: Record<string, string> = {
			rocket: 'M9.315 7.584C12.195 3.883 16.695 1.5 21.75 1.5a.75.75 0 01.75.75c0 5.056-2.383 9.555-6.084 12.436A6.75 6.75 0 019.75 22.5a.75.75 0 01-.75-.75v-4.131A15.838 15.838 0 016.382 15H2.25a.75.75 0 01-.75-.75 6.75 6.75 0 017.815-6.666zM15 6.75a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5z',
			grid: 'M3 3h7v7H3V3zm11 0h7v7h-7V3zm0 11h7v7h-7v-7zm-11 0h7v7H3v-7z',
			alert: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-2h2v2h-2zm0-4V7h2v6h-2z',
			shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
			settings: 'M12 15a3 3 0 100-6 3 3 0 000 6z'
		};
		return icons[iconName] || icons.grid;
	}
</script>

<svelte:head>
	<title>Help - Media Janitor</title>
</svelte:head>

<div class="help-page">
	<header class="page-header">
		<h1>Help & FAQs</h1>
		<p class="subtitle">Find answers to common questions about Media Janitor</p>
	</header>

	<!-- Search -->
	<div class="search-container">
		<svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<circle cx="11" cy="11" r="8"/>
			<line x1="21" y1="21" x2="16.65" y2="16.65"/>
		</svg>
		<input
			type="text"
			class="search-input"
			placeholder="Search FAQs..."
			bind:value={searchQuery}
		/>
		{#if searchQuery}
			<button class="search-clear" onclick={() => searchQuery = ''} aria-label="Clear search">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<line x1="18" y1="6" x2="6" y2="18"/>
					<line x1="6" y1="6" x2="18" y2="18"/>
				</svg>
			</button>
		{/if}
	</div>

	<!-- FAQ Sections -->
	{#if filteredSections.length === 0}
		<div class="no-results">
			<p>No FAQs match your search.</p>
			<button class="btn-clear" onclick={() => searchQuery = ''}>Clear search</button>
		</div>
	{:else}
		{#each filteredSections as section, sectionIndex}
			<section class="faq-section">
				<h2 class="section-title">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d={getSectionIcon(section.icon)}/>
					</svg>
					{section.title}
				</h2>

				<div class="faq-list">
					{#each section.faqs as faq, faqIndex}
						<div class="faq-item" class:expanded={isExpanded(sectionIndex, faqIndex)}>
							<button
								class="faq-question"
								onclick={() => toggleItem(sectionIndex, faqIndex)}
								aria-expanded={isExpanded(sectionIndex, faqIndex)}
							>
								<span class="question-text">{faq.question}</span>
								<svg
									class="chevron"
									class:rotated={isExpanded(sectionIndex, faqIndex)}
									width="18"
									height="18"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
								>
									<polyline points="6 9 12 15 18 9"/>
								</svg>
							</button>
							{#if isExpanded(sectionIndex, faqIndex)}
								<div class="faq-answer">
									<p>{faq.answer}</p>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</section>
		{/each}
	{/if}

	<!-- Contact Section -->
	<section class="contact-section">
		<h2>Still need help?</h2>
		<p>If you can't find what you're looking for, <a href="https://github.com/jimmydore/mediajanitor" target="_blank" rel="noopener noreferrer">view the project on GitHub</a> or <a href="https://github.com/jimmydore/mediajanitor/issues" target="_blank" rel="noopener noreferrer">report an issue</a>.</p>
	</section>
</div>

<style>
	.help-page {
		max-width: 720px;
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
		margin-bottom: var(--space-2);
	}

	.subtitle {
		color: var(--text-muted);
		font-size: var(--font-size-md);
	}

	/* Search */
	.search-container {
		position: relative;
		margin-bottom: var(--space-8);
	}

	.search-icon {
		position: absolute;
		left: var(--space-4);
		top: 50%;
		transform: translateY(-50%);
		color: var(--text-muted);
		pointer-events: none;
	}

	.search-input {
		width: 100%;
		padding: var(--space-3) var(--space-4);
		padding-left: calc(var(--space-4) + 18px + var(--space-3));
		padding-right: calc(var(--space-4) + 16px + var(--space-3));
		font-size: var(--font-size-md);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		color: var(--text-primary);
		transition: all var(--transition-fast);
	}

	.search-input:focus {
		outline: none;
		border-color: var(--accent);
		box-shadow: 0 0 0 3px var(--accent-light);
	}

	.search-input::placeholder {
		color: var(--text-muted);
	}

	.search-clear {
		position: absolute;
		right: var(--space-3);
		top: 50%;
		transform: translateY(-50%);
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		border-radius: var(--radius-sm);
		transition: all var(--transition-fast);
	}

	.search-clear:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	/* No Results */
	.no-results {
		text-align: center;
		padding: var(--space-12);
		color: var(--text-muted);
	}

	.no-results p {
		margin-bottom: var(--space-4);
	}

	.btn-clear {
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--accent);
		background: var(--accent-light);
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-clear:hover {
		background: var(--accent);
		color: white;
	}

	/* FAQ Sections */
	.faq-section {
		margin-bottom: var(--space-8);
	}

	.section-title {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		margin-bottom: var(--space-4);
	}

	.section-title svg {
		color: var(--accent);
	}

	.faq-list {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.faq-item {
		border-bottom: 1px solid var(--border);
	}

	.faq-item:last-child {
		border-bottom: none;
	}

	.faq-question {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: var(--space-4);
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
		transition: all var(--transition-fast);
	}

	.faq-question:hover {
		background: var(--bg-hover);
	}

	.question-text {
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-medium);
		color: var(--text-primary);
		flex: 1;
		padding-right: var(--space-4);
	}

	.chevron {
		color: var(--text-muted);
		transition: transform var(--transition-fast);
		flex-shrink: 0;
	}

	.chevron.rotated {
		transform: rotate(180deg);
	}

	.faq-answer {
		padding: 0 var(--space-4) var(--space-4);
		animation: slideDown 0.2s ease-out;
	}

	.faq-answer p {
		font-size: var(--font-size-md);
		color: var(--text-secondary);
		line-height: 1.6;
	}

	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* Contact Section */
	.contact-section {
		margin-top: var(--space-12);
		padding: var(--space-6);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		text-align: center;
	}

	.contact-section h2 {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		margin-bottom: var(--space-2);
	}

	.contact-section p {
		color: var(--text-secondary);
		font-size: var(--font-size-md);
	}

	.contact-section a {
		color: var(--accent);
		text-decoration: none;
	}

	.contact-section a:hover {
		text-decoration: underline;
	}

	/* Responsive */
	@media (max-width: 640px) {
		.help-page {
			padding: var(--space-4);
		}

		.question-text {
			font-size: var(--font-size-sm);
		}

		.faq-answer p {
			font-size: var(--font-size-sm);
		}
	}
</style>
