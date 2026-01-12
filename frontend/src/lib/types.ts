/**
 * TypeScript types for Plex Dashboard
 */

// Content types
export interface ContentItem {
	id: string;
	name: string;
	type: 'Movie' | 'Series';
	year?: number;
	dateCreated: string;
	lastPlayed?: string;
	played: boolean;
	playCount: number;
	size: number;
	path: string;
	isAllowlisted: boolean;
}

export interface OldUnwatchedResponse {
	items: ContentItem[];
	totalCount: number;
	totalSize: number;
	protectedCount: number;
}

export interface LargeMoviesResponse {
	items: ContentItem[];
	totalCount: number;
	totalSize: number;
	threshold: number;
}

// Language types
export interface AudioTrack {
	language: string;
	title: string;
	codec: string;
	channels: number;
	isDefault: boolean;
}

export interface LanguageIssue {
	id: string;
	name: string;
	type: 'Movie' | 'Series';
	year?: number;
	dateCreated: string;
	hasEnglish: boolean;
	hasFrench: boolean;
	hasFrenchSubs: boolean;
	audioLanguages: string[];
	subtitleLanguages: string[];
	path: string;
	// For series
	totalEpisodes?: number;
	problematicEpisodes?: ProblematicEpisode[];
}

export interface ProblematicEpisode {
	identifier: string;
	name: string;
	season: number;
	episode: number;
	missingLanguages: string[];
	availableLanguages: string[];
	hasFrenchSubs: boolean;
}

// Jellyseerr types
export interface JellyseerrRequest {
	id: number;
	status: number;
	title: string;
	type: 'movie' | 'tv';
	releaseDate?: string;
	requestedBy: string;
	createdAt: string;
	// For TV
	seasonAnalysis?: SeasonAnalysis;
}

export interface SeasonAnalysis {
	analysisAvailable: boolean;
	missingSeasonsCount: number;
	availableSeasonsCount: number;
	futureSeasonsCount: number;
	inProgressSeasonsCount: number;
	isCompleteForReleased: boolean;
	summary: string;
}

export interface InProgressRequest extends JellyseerrRequest {
	inProgressSeasons: InProgressSeason[];
}

export interface InProgressSeason {
	seasonNumber: number;
	episodesAired: number;
	totalEpisodes: number;
}

// Whitelist types
export type WhitelistType =
	| 'content'
	| 'french_only'
	| 'french_subs_only'
	| 'language_exempt'
	| 'episode_exempt';

export interface WhitelistItem {
	id: number;
	name: string;
	addedAt: string;
}

export interface EpisodeExemption {
	id: number;
	showName: string;
	season: number;
	episodes: number[];
	addedAt: string;
}

// Settings types
export interface Settings {
	oldContentMonthsCutoff: number;
	minAgeMonths: number;
	largeMovieSizeThresholdGb: number;
	recentItemsDaysBack: number;
	filterFutureReleases: boolean;
	filterRecentReleases: boolean;
	recentReleaseMonthsCutoff: number;
}

// API response types
export interface ApiResponse<T> {
	data: T;
	success: boolean;
	error?: string;
}

export interface ApiStats {
	oldUnwatched: number;
	largeMovies: number;
	languageIssues: number;
	unavailableRequests: number;
	inProgressRequests: number;
}

// Authentication types
export interface AuthUser {
	id: number;
	email: string;
}

export interface AuthState {
	isAuthenticated: boolean;
	user: AuthUser | null;
	isLoading: boolean;
}
