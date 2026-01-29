"""Tests for group_episodes_for_display() function in content service."""

from app.services.content_queries import (
    group_episodes_for_display,
)
from app.services.sonarr import EpisodeHistoryEntry


class TestGroupEpisodesForDisplay:
    """Test smart episode grouping logic."""

    def test_single_episode_returns_episode_format(self):
        """Single episode should return 'SXEY' format."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 2, "episode": 5, "title": "Episode 5", "added_at": "2026-01-15T10:00:00Z"},
        ]
        total_episodes_per_season = {2: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        assert result[0]["display_text"] == "S2E5"
        assert result[0]["season"] == 2
        assert result[0]["episode_numbers"] == [5]
        assert result[0]["is_full_season"] is False
        assert result[0]["added_date"] == "2026-01-15"

    def test_full_season_returns_season_format(self):
        """All episodes of a season added same day should return 'Season X'."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 2, "episode": 1, "title": "Ep 1", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 2, "episode": 2, "title": "Ep 2", "added_at": "2026-01-15T11:00:00Z"},
            {"season": 2, "episode": 3, "title": "Ep 3", "added_at": "2026-01-15T12:00:00Z"},
        ]
        total_episodes_per_season = {2: 3}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        assert result[0]["display_text"] == "Season 2"
        assert result[0]["season"] == 2
        assert result[0]["episode_numbers"] == [1, 2, 3]
        assert result[0]["is_full_season"] is True
        assert result[0]["added_date"] == "2026-01-15"

    def test_consecutive_episodes_same_day_returns_range_format(self):
        """Consecutive episodes added same day should return 'SXEY-EZ' format."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 2, "episode": 5, "title": "Ep 5", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 2, "episode": 6, "title": "Ep 6", "added_at": "2026-01-15T11:00:00Z"},
            {"season": 2, "episode": 7, "title": "Ep 7", "added_at": "2026-01-15T12:00:00Z"},
            {"season": 2, "episode": 8, "title": "Ep 8", "added_at": "2026-01-15T13:00:00Z"},
        ]
        total_episodes_per_season = {2: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        assert result[0]["display_text"] == "S2E5-E8"
        assert result[0]["season"] == 2
        assert result[0]["episode_numbers"] == [5, 6, 7, 8]
        assert result[0]["is_full_season"] is False

    def test_non_consecutive_episodes_same_day_returns_list_format(self):
        """Non-consecutive episodes added same day should return comma-separated list."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 2, "episode": 3, "title": "Ep 3", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 2, "episode": 5, "title": "Ep 5", "added_at": "2026-01-15T11:00:00Z"},
            {"season": 2, "episode": 7, "title": "Ep 7", "added_at": "2026-01-15T12:00:00Z"},
        ]
        total_episodes_per_season = {2: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        assert result[0]["display_text"] == "S2E3, S2E5, S2E7"
        assert result[0]["season"] == 2
        assert result[0]["episode_numbers"] == [3, 5, 7]
        assert result[0]["is_full_season"] is False

    def test_episodes_different_days_creates_multiple_groups(self):
        """Episodes added on different days should create separate groups."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 2, "episode": 1, "title": "Ep 1", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 2, "episode": 2, "title": "Ep 2", "added_at": "2026-01-16T10:00:00Z"},
        ]
        total_episodes_per_season = {2: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        # Should be 2 groups, one for each day
        assert len(result) == 2
        # Sorted by date descending (most recent first)
        assert result[0]["added_date"] == "2026-01-16"
        assert result[0]["display_text"] == "S2E2"
        assert result[1]["added_date"] == "2026-01-15"
        assert result[1]["display_text"] == "S2E1"

    def test_multiple_seasons_same_day_creates_separate_groups(self):
        """Episodes from different seasons same day should create separate groups."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 1, "episode": 1, "title": "Ep 1", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 2, "episode": 1, "title": "Ep 1", "added_at": "2026-01-15T11:00:00Z"},
        ]
        total_episodes_per_season = {1: 10, 2: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 2
        # Should have S1E1 and S2E1 as separate groups
        season_groups = {r["season"]: r for r in result}
        assert season_groups[1]["display_text"] == "S1E1"
        assert season_groups[2]["display_text"] == "S2E1"

    def test_empty_episodes_returns_empty_list(self):
        """Empty episode list should return empty list."""
        result = group_episodes_for_display([], {})
        assert result == []

    def test_full_season_detection_with_missing_total_episodes(self):
        """If total_episodes_per_season is missing for a season, cannot be full season."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 2, "episode": 1, "title": "Ep 1", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 2, "episode": 2, "title": "Ep 2", "added_at": "2026-01-15T11:00:00Z"},
            {"season": 2, "episode": 3, "title": "Ep 3", "added_at": "2026-01-15T12:00:00Z"},
        ]
        # Season 2 not in the map - we don't know total episodes
        total_episodes_per_season: dict[int, int] = {}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        # Without knowing total episodes, we show range format, not "Season X"
        assert result[0]["display_text"] == "S2E1-E3"
        assert result[0]["is_full_season"] is False

    def test_two_consecutive_episodes_uses_range_format(self):
        """Two consecutive episodes should use range format 'SXEY-EZ'."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 1, "episode": 3, "title": "Ep 3", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 1, "episode": 4, "title": "Ep 4", "added_at": "2026-01-15T11:00:00Z"},
        ]
        total_episodes_per_season = {1: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        assert result[0]["display_text"] == "S1E3-E4"

    def test_mixed_consecutive_and_non_consecutive_same_day(self):
        """Mix of consecutive and non-consecutive episodes same day."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 1, "episode": 1, "title": "Ep 1", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 1, "episode": 2, "title": "Ep 2", "added_at": "2026-01-15T11:00:00Z"},
            {"season": 1, "episode": 5, "title": "Ep 5", "added_at": "2026-01-15T12:00:00Z"},
        ]
        total_episodes_per_season = {1: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        # Not fully consecutive, so falls back to comma-separated list
        assert result[0]["display_text"] == "S1E1, S1E2, S1E5"
        assert result[0]["episode_numbers"] == [1, 2, 5]

    def test_duplicate_episodes_are_deduplicated(self):
        """Duplicate episode entries should be deduplicated."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 2, "episode": 5, "title": "Ep 5", "added_at": "2026-01-15T10:00:00Z"},
            {
                "season": 2,
                "episode": 5,
                "title": "Ep 5",
                "added_at": "2026-01-15T11:00:00Z",
            },  # duplicate
            {"season": 2, "episode": 6, "title": "Ep 6", "added_at": "2026-01-15T12:00:00Z"},
        ]
        total_episodes_per_season = {2: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        assert result[0]["display_text"] == "S2E5-E6"
        assert result[0]["episode_numbers"] == [5, 6]

    def test_returns_groups_sorted_by_date_descending(self):
        """Result should be sorted by date descending (most recent first)."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 1, "episode": 1, "title": "Ep 1", "added_at": "2026-01-10T10:00:00Z"},
            {"season": 1, "episode": 2, "title": "Ep 2", "added_at": "2026-01-20T10:00:00Z"},
            {"season": 1, "episode": 3, "title": "Ep 3", "added_at": "2026-01-15T10:00:00Z"},
        ]
        total_episodes_per_season = {1: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        # 3 separate days = 3 groups
        assert len(result) == 3
        # Sorted descending by date
        assert result[0]["added_date"] == "2026-01-20"
        assert result[1]["added_date"] == "2026-01-15"
        assert result[2]["added_date"] == "2026-01-10"

    def test_handles_specials_season_0(self):
        """Season 0 (specials) should be handled correctly."""
        episodes: list[EpisodeHistoryEntry] = [
            {"season": 0, "episode": 1, "title": "Special 1", "added_at": "2026-01-15T10:00:00Z"},
        ]
        total_episodes_per_season = {0: 5}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        assert len(result) == 1
        assert result[0]["display_text"] == "S0E1"
        assert result[0]["season"] == 0

    def test_complex_scenario_multiple_seasons_multiple_days(self):
        """Complex scenario with multiple seasons added on multiple days."""
        episodes: list[EpisodeHistoryEntry] = [
            # Season 1 - all on Jan 10
            {"season": 1, "episode": 1, "title": "S1E1", "added_at": "2026-01-10T10:00:00Z"},
            {"season": 1, "episode": 2, "title": "S1E2", "added_at": "2026-01-10T11:00:00Z"},
            {"season": 1, "episode": 3, "title": "S1E3", "added_at": "2026-01-10T12:00:00Z"},
            # Season 2 - partial on Jan 15
            {"season": 2, "episode": 1, "title": "S2E1", "added_at": "2026-01-15T10:00:00Z"},
            {"season": 2, "episode": 2, "title": "S2E2", "added_at": "2026-01-15T11:00:00Z"},
            # Season 2 - rest on Jan 20
            {"season": 2, "episode": 3, "title": "S2E3", "added_at": "2026-01-20T10:00:00Z"},
        ]
        total_episodes_per_season = {1: 3, 2: 10}

        result = group_episodes_for_display(episodes, total_episodes_per_season)

        # Group by (date, season): (Jan 20, S2), (Jan 15, S2), (Jan 10, S1)
        assert len(result) == 3

        # Most recent first
        jan_20_group = result[0]
        assert jan_20_group["added_date"] == "2026-01-20"
        assert jan_20_group["display_text"] == "S2E3"

        jan_15_group = result[1]
        assert jan_15_group["added_date"] == "2026-01-15"
        assert jan_15_group["display_text"] == "S2E1-E2"

        jan_10_group = result[2]
        assert jan_10_group["added_date"] == "2026-01-10"
        assert jan_10_group["display_text"] == "Season 1"  # Full season
        assert jan_10_group["is_full_season"] is True
