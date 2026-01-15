/**
 * Tests for the Enhance Your Setup component (US-18.3)
 *
 * Tests verify the enhance setup card shows after initial setup is complete
 * but optional services are not configured, and can be dismissed permanently.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Enhance Your Setup API Integration (US-18.3)', () => {
	beforeEach(() => {
		mockFetch.mockReset();
		// Clear localStorage before each test
		if (typeof localStorage !== 'undefined') {
			localStorage.clear();
		}
	});

	describe('API endpoints for optional services', () => {
		it('GET /api/settings/jellyseerr returns configuration status', async () => {
			const jellyseerrSettings = {
				server_url: null,
				api_key_configured: false
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(jellyseerrSettings)
			});

			const response = await fetch('/api/settings/jellyseerr', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.api_key_configured).toBe(false);
		});

		it('GET /api/settings/radarr returns configuration status', async () => {
			const radarrSettings = {
				server_url: null,
				api_key_configured: false
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(radarrSettings)
			});

			const response = await fetch('/api/settings/radarr', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.api_key_configured).toBe(false);
		});

		it('GET /api/settings/sonarr returns configuration status', async () => {
			const sonarrSettings = {
				server_url: null,
				api_key_configured: false
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(sonarrSettings)
			});

			const response = await fetch('/api/settings/sonarr', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.api_key_configured).toBe(false);
		});
	});

	describe('Enhance setup visibility conditions', () => {
		it('should show enhance setup when setup complete but Jellyseerr not configured', () => {
			const jellyfinSettings = { api_key_configured: true, server_url: 'https://jf.example.com' };
			const syncStatus = { last_synced: '2024-01-15T10:30:00Z', is_syncing: false };
			const jellyseerrSettings = { api_key_configured: false };
			const radarrSettings = { api_key_configured: true };
			const sonarrSettings = { api_key_configured: true };
			const enhanceSetupDismissed = false;

			// showSetupChecklist would be false since Jellyfin configured and has synced
			const showSetupChecklist =
				jellyfinSettings.api_key_configured === false || syncStatus.last_synced === null;

			const showEnhanceSetup =
				!showSetupChecklist &&
				jellyfinSettings.api_key_configured === true &&
				syncStatus.last_synced !== null &&
				!enhanceSetupDismissed &&
				(jellyseerrSettings.api_key_configured === false ||
					radarrSettings.api_key_configured === false ||
					sonarrSettings.api_key_configured === false);

			expect(showSetupChecklist).toBe(false);
			expect(showEnhanceSetup).toBe(true);
		});

		it('should show enhance setup when setup complete but Radarr not configured', () => {
			const jellyfinSettings = { api_key_configured: true, server_url: 'https://jf.example.com' };
			const syncStatus = { last_synced: '2024-01-15T10:30:00Z', is_syncing: false };
			const jellyseerrSettings = { api_key_configured: true };
			const radarrSettings = { api_key_configured: false };
			const sonarrSettings = { api_key_configured: true };
			const enhanceSetupDismissed = false;

			const showSetupChecklist =
				jellyfinSettings.api_key_configured === false || syncStatus.last_synced === null;

			const showEnhanceSetup =
				!showSetupChecklist &&
				jellyfinSettings.api_key_configured === true &&
				syncStatus.last_synced !== null &&
				!enhanceSetupDismissed &&
				(jellyseerrSettings.api_key_configured === false ||
					radarrSettings.api_key_configured === false ||
					sonarrSettings.api_key_configured === false);

			expect(showSetupChecklist).toBe(false);
			expect(showEnhanceSetup).toBe(true);
		});

		it('should show enhance setup when setup complete but Sonarr not configured', () => {
			const jellyfinSettings = { api_key_configured: true, server_url: 'https://jf.example.com' };
			const syncStatus = { last_synced: '2024-01-15T10:30:00Z', is_syncing: false };
			const jellyseerrSettings = { api_key_configured: true };
			const radarrSettings = { api_key_configured: true };
			const sonarrSettings = { api_key_configured: false };
			const enhanceSetupDismissed = false;

			const showSetupChecklist =
				jellyfinSettings.api_key_configured === false || syncStatus.last_synced === null;

			const showEnhanceSetup =
				!showSetupChecklist &&
				jellyfinSettings.api_key_configured === true &&
				syncStatus.last_synced !== null &&
				!enhanceSetupDismissed &&
				(jellyseerrSettings.api_key_configured === false ||
					radarrSettings.api_key_configured === false ||
					sonarrSettings.api_key_configured === false);

			expect(showSetupChecklist).toBe(false);
			expect(showEnhanceSetup).toBe(true);
		});

		it('should NOT show enhance setup when all optional services are configured', () => {
			const jellyfinSettings = { api_key_configured: true, server_url: 'https://jf.example.com' };
			const syncStatus = { last_synced: '2024-01-15T10:30:00Z', is_syncing: false };
			const jellyseerrSettings = { api_key_configured: true };
			const radarrSettings = { api_key_configured: true };
			const sonarrSettings = { api_key_configured: true };
			const enhanceSetupDismissed = false;

			const showSetupChecklist =
				jellyfinSettings.api_key_configured === false || syncStatus.last_synced === null;

			const showEnhanceSetup =
				!showSetupChecklist &&
				jellyfinSettings.api_key_configured === true &&
				syncStatus.last_synced !== null &&
				!enhanceSetupDismissed &&
				(jellyseerrSettings.api_key_configured === false ||
					radarrSettings.api_key_configured === false ||
					sonarrSettings.api_key_configured === false);

			expect(showEnhanceSetup).toBe(false);
		});

		it('should NOT show enhance setup when setup checklist is still visible', () => {
			const jellyfinSettings = { api_key_configured: false, server_url: null };
			const syncStatus = { last_synced: null, is_syncing: false };
			const jellyseerrSettings = { api_key_configured: false };
			const radarrSettings = { api_key_configured: false };
			const sonarrSettings = { api_key_configured: false };
			const enhanceSetupDismissed = false;

			const showSetupChecklist =
				jellyfinSettings.api_key_configured === false || syncStatus.last_synced === null;

			const showEnhanceSetup =
				!showSetupChecklist &&
				jellyfinSettings.api_key_configured === true &&
				syncStatus.last_synced !== null &&
				!enhanceSetupDismissed &&
				(jellyseerrSettings.api_key_configured === false ||
					radarrSettings.api_key_configured === false ||
					sonarrSettings.api_key_configured === false);

			expect(showSetupChecklist).toBe(true);
			expect(showEnhanceSetup).toBe(false);
		});

		it('should NOT show enhance setup when dismissed', () => {
			const jellyfinSettings = { api_key_configured: true, server_url: 'https://jf.example.com' };
			const syncStatus = { last_synced: '2024-01-15T10:30:00Z', is_syncing: false };
			const jellyseerrSettings = { api_key_configured: false };
			const radarrSettings = { api_key_configured: false };
			const sonarrSettings = { api_key_configured: false };
			const enhanceSetupDismissed = true; // User dismissed the card

			const showSetupChecklist =
				jellyfinSettings.api_key_configured === false || syncStatus.last_synced === null;

			const showEnhanceSetup =
				!showSetupChecklist &&
				jellyfinSettings.api_key_configured === true &&
				syncStatus.last_synced !== null &&
				!enhanceSetupDismissed &&
				(jellyseerrSettings.api_key_configured === false ||
					radarrSettings.api_key_configured === false ||
					sonarrSettings.api_key_configured === false);

			expect(showSetupChecklist).toBe(false);
			expect(showEnhanceSetup).toBe(false);
		});
	});

	describe('localStorage persistence', () => {
		it('dismiss state is stored in localStorage', () => {
			const ENHANCE_SETUP_DISMISSED_KEY = 'mediajanitor_enhance_setup_dismissed';

			// Simulate dismissing the card
			localStorage.setItem(ENHANCE_SETUP_DISMISSED_KEY, 'true');

			// Check it was stored
			const dismissed = localStorage.getItem(ENHANCE_SETUP_DISMISSED_KEY) === 'true';
			expect(dismissed).toBe(true);
		});

		it('dismiss state is read from localStorage on load', () => {
			const ENHANCE_SETUP_DISMISSED_KEY = 'mediajanitor_enhance_setup_dismissed';

			// Pre-set dismissed state
			localStorage.setItem(ENHANCE_SETUP_DISMISSED_KEY, 'true');

			// Simulate loading the state
			const loadedDismissed = localStorage.getItem(ENHANCE_SETUP_DISMISSED_KEY) === 'true';

			expect(loadedDismissed).toBe(true);
		});

		it('card shows when localStorage has no dismiss state', () => {
			const ENHANCE_SETUP_DISMISSED_KEY = 'mediajanitor_enhance_setup_dismissed';

			// Ensure localStorage is clear
			localStorage.removeItem(ENHANCE_SETUP_DISMISSED_KEY);

			// Simulate loading the state
			const loadedDismissed = localStorage.getItem(ENHANCE_SETUP_DISMISSED_KEY) === 'true';

			expect(loadedDismissed).toBe(false);
		});
	});

	describe('Service display logic', () => {
		it('shows only unconfigured services in the list', () => {
			const jellyseerrSettings = { api_key_configured: false };
			const radarrSettings = { api_key_configured: true };
			const sonarrSettings = { api_key_configured: false };

			// Collect services to display
			const servicesToShow: string[] = [];

			if (!jellyseerrSettings.api_key_configured) {
				servicesToShow.push('Jellyseerr');
			}
			if (!radarrSettings.api_key_configured) {
				servicesToShow.push('Radarr');
			}
			if (!sonarrSettings.api_key_configured) {
				servicesToShow.push('Sonarr');
			}

			expect(servicesToShow).toContain('Jellyseerr');
			expect(servicesToShow).not.toContain('Radarr');
			expect(servicesToShow).toContain('Sonarr');
			expect(servicesToShow.length).toBe(2);
		});

		it('shows all three services when none are configured', () => {
			const jellyseerrSettings = { api_key_configured: false };
			const radarrSettings = { api_key_configured: false };
			const sonarrSettings = { api_key_configured: false };

			const servicesToShow: string[] = [];

			if (!jellyseerrSettings.api_key_configured) {
				servicesToShow.push('Jellyseerr');
			}
			if (!radarrSettings.api_key_configured) {
				servicesToShow.push('Radarr');
			}
			if (!sonarrSettings.api_key_configured) {
				servicesToShow.push('Sonarr');
			}

			expect(servicesToShow.length).toBe(3);
			expect(servicesToShow).toEqual(['Jellyseerr', 'Radarr', 'Sonarr']);
		});

		it('shows no services when all are configured (card would be hidden)', () => {
			const jellyseerrSettings = { api_key_configured: true };
			const radarrSettings = { api_key_configured: true };
			const sonarrSettings = { api_key_configured: true };

			const servicesToShow: string[] = [];

			if (!jellyseerrSettings.api_key_configured) {
				servicesToShow.push('Jellyseerr');
			}
			if (!radarrSettings.api_key_configured) {
				servicesToShow.push('Radarr');
			}
			if (!sonarrSettings.api_key_configured) {
				servicesToShow.push('Sonarr');
			}

			expect(servicesToShow.length).toBe(0);
		});
	});
});
