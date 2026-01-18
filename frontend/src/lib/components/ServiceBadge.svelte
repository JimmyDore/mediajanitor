<script lang="ts">
	type ServiceType = 'jellyfin' | 'jellyseerr' | 'radarr' | 'sonarr' | 'tmdb';

	interface Props {
		service: ServiceType;
		url: string;
		title: string;
	}

	let { service, url, title }: Props = $props();

	// Brand colors for each service
	const brandColors: Record<ServiceType, string> = {
		jellyfin: '#00a4dc',
		jellyseerr: '#7b68ee',
		radarr: '#ffc230',
		sonarr: '#2ecc71',
		tmdb: '#01b4e4'
	};

	// Get the color for hover effect
	const color = $derived(brandColors[service]);
</script>

<a
	href={url}
	target="_blank"
	rel="noopener noreferrer"
	class="service-badge service-badge-{service}"
	{title}
	style="--brand-color: {color}"
>
	{#if service === 'jellyfin'}
		<!-- Jellyfin icon - simplified "J" shape -->
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
			<circle cx="12" cy="12" r="10" fill={brandColors.jellyfin}/>
			<path d="M10 7h4v8c0 1.5-1.5 2.5-3 2.5S8 16.5 8 15" stroke="white" stroke-width="2" stroke-linecap="round"/>
		</svg>
	{:else if service === 'jellyseerr'}
		<!-- Jellyseerr icon - star/request shape -->
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
			<circle cx="12" cy="12" r="10" fill={brandColors.jellyseerr}/>
			<path d="M12 6l1.5 4.5H18l-3.5 2.5 1.5 4.5L12 15l-4 2.5 1.5-4.5L6 10.5h4.5L12 6z" fill="white"/>
		</svg>
	{:else if service === 'radarr'}
		<!-- Radarr icon - movie/film shape -->
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
			<circle cx="12" cy="12" r="10" fill={brandColors.radarr}/>
			<rect x="7" y="8" width="10" height="8" rx="1" stroke="#000" stroke-width="1.5" fill="none"/>
			<path d="M7 10h10M7 14h10" stroke="#000" stroke-width="1"/>
			<circle cx="9" cy="12" r="1" fill="#000"/>
			<circle cx="15" cy="12" r="1" fill="#000"/>
		</svg>
	{:else if service === 'sonarr'}
		<!-- Sonarr icon - TV/series shape -->
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
			<circle cx="12" cy="12" r="10" fill={brandColors.sonarr}/>
			<rect x="6" y="7" width="12" height="8" rx="1" stroke="#000" stroke-width="1.5" fill="none"/>
			<path d="M9 17h6M12 15v2" stroke="#000" stroke-width="1.5" stroke-linecap="round"/>
		</svg>
	{:else if service === 'tmdb'}
		<!-- TMDB icon - database/movie shape -->
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
			<circle cx="12" cy="12" r="10" fill={brandColors.tmdb}/>
			<path d="M8 8h8M8 12h8M8 16h5" stroke="white" stroke-width="2" stroke-linecap="round"/>
		</svg>
	{/if}
</a>

<style>
	.service-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 2px;
		border-radius: 4px;
		text-decoration: none;
		transition: transform 0.15s ease, opacity 0.15s ease;
		opacity: 0.9;
	}

	.service-badge:hover {
		transform: scale(1.1);
		opacity: 1;
	}

	.service-badge:focus {
		outline: 2px solid var(--brand-color);
		outline-offset: 2px;
	}

	.service-badge svg {
		display: block;
	}
</style>
