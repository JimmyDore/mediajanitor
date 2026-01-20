<script lang="ts">
	type ServiceType = 'jellyfin' | 'jellyseerr' | 'radarr' | 'sonarr' | 'tmdb';

	interface Props {
		service: ServiceType;
		url: string;
		title: string;
	}

	let { service, url, title }: Props = $props();

	// Brand colors for each service (used for focus ring)
	const brandColors: Record<ServiceType, string> = {
		jellyfin: '#00a4dc',
		jellyseerr: '#7b68ee',
		radarr: '#ffc230',
		sonarr: '#00ccff',
		tmdb: '#01b4e4'
	};

	// Logo file paths (official logos)
	const logoFiles: Record<ServiceType, string> = {
		jellyfin: '/logos/jellyfin.svg',
		jellyseerr: '/logos/jellyseerr.png',
		radarr: '/logos/radarr.svg',
		sonarr: '/logos/sonarr.svg',
		tmdb: '/logos/tmdb.svg'
	};

	const color = $derived(brandColors[service]);
	const logoSrc = $derived(logoFiles[service]);
</script>

<a
	href={url}
	target="_blank"
	rel="noopener noreferrer"
	class="service-badge"
	{title}
	style="--brand-color: {color}"
>
	<img src={logoSrc} alt={service} width="16" height="16" />
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

	.service-badge img {
		display: block;
		width: 16px;
		height: 16px;
		object-fit: contain;
	}
</style>
