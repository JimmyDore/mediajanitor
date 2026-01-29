<script lang="ts">
	import SearchInput from './SearchInput.svelte';

	type FilterType = 'all' | 'old' | 'large' | 'language' | 'requests';
	type LargeSubFilter = 'all' | 'movies' | 'series';

	interface Props {
		activeFilter: FilterType;
		largeSubFilter: LargeSubFilter;
		searchQuery: string;
		totalCount: number | null;
		totalSizeFormatted: string | null;
		filteredCount: number | null;
		filteredSizeFormatted: string | null;
		isFiltered: boolean;
		loading: boolean;
		onfilterChange: (filter: FilterType) => void;
		onsubFilterChange: (subFilter: LargeSubFilter) => void;
		onsearchInput: (event: Event) => void;
		onsearchClear: () => void;
	}

	let {
		activeFilter,
		largeSubFilter,
		searchQuery,
		totalCount,
		totalSizeFormatted,
		filteredCount,
		filteredSizeFormatted,
		isFiltered,
		loading,
		onfilterChange,
		onsubFilterChange,
		onsearchInput,
		onsearchClear
	}: Props = $props();

	const filterLabels: Record<FilterType, string> = {
		all: 'All',
		old: 'Old',
		large: 'Large',
		language: 'Language',
		requests: 'Unavailable'
	};
</script>

<header class="page-header">
	<div class="header-main">
		<h1>Issues</h1>
		{#if totalCount !== null && !loading}
			<span class="header-stats">
				{#if isFiltered}
					{filteredCount} of {totalCount} items · {filteredSizeFormatted}
				{:else}
					{totalCount} items · {totalSizeFormatted}
				{/if}
			</span>
		{/if}
	</div>
	<SearchInput
		value={searchQuery}
		placeholder="Search by title, year..."
		aria-label="Search issues by title or year"
		oninput={onsearchInput}
		onclear={onsearchClear}
	/>
</header>

<nav class="filter-nav">
	{#each Object.entries(filterLabels) as [filter, label]}
		<button
			class="filter-tab"
			class:active={activeFilter === filter}
			onclick={() => onfilterChange(filter as FilterType)}
		>
			{label}
		</button>
	{/each}
</nav>

{#if activeFilter === 'large'}
	<div class="sub-filter-nav">
		<button
			class="sub-filter-btn"
			class:active={largeSubFilter === 'all'}
			onclick={() => onsubFilterChange('all')}
		>
			All
		</button>
		<button
			class="sub-filter-btn"
			class:active={largeSubFilter === 'movies'}
			onclick={() => onsubFilterChange('movies')}
		>
			Movies
		</button>
		<button
			class="sub-filter-btn"
			class:active={largeSubFilter === 'series'}
			onclick={() => onsubFilterChange('series')}
		>
			Series
		</button>
	</div>
{/if}

<style>
	.page-header {
		margin-bottom: var(--space-6);
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

	/* Filter nav - underline style */
	.filter-nav {
		display: flex;
		gap: var(--space-1);
		border-bottom: 1px solid var(--border);
		margin-bottom: var(--space-6);
	}

	.filter-tab {
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
	}

	.filter-tab:hover {
		color: var(--text-primary);
	}

	.filter-tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--accent);
	}

	/* Sub-filter nav for Large tab */
	.sub-filter-nav {
		display: flex;
		gap: var(--space-2);
		margin-bottom: var(--space-4);
	}

	.sub-filter-btn {
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.sub-filter-btn:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.sub-filter-btn.active {
		background: var(--accent);
		color: white;
		border-color: var(--accent);
	}

	@media (max-width: 640px) {
		.filter-nav {
			overflow-x: auto;
			-webkit-overflow-scrolling: touch;
		}
	}

	@media (max-width: 380px) {
		.filter-nav {
			gap: 0;
		}

		.filter-tab {
			padding: var(--space-2) var(--space-2);
			font-size: var(--font-size-xs);
		}
	}
</style>
