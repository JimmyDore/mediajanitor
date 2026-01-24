"""Unit tests for nicknames service functions (US-60.4).

Tests for:
- create_nickname() success and duplicate detection
- get_nicknames() ordering
- update_nickname() success and not found case
- delete_nickname() success and not found case
"""

import pytest

from app.database import User, UserNickname
from app.services.nicknames import (
    create_nickname,
    delete_nickname,
    get_nicknames,
    update_nickname,
)
from tests.conftest import TestingAsyncSessionLocal


class TestCreateNickname:
    """Tests for create_nickname function."""

    @pytest.mark.asyncio
    async def test_creates_nickname_successfully(self) -> None:
        """Should create a new nickname mapping and return it."""
        async with TestingAsyncSessionLocal() as session:
            # Create a user
            user = User(
                email="create_nickname@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create nickname
            result = await create_nickname(
                db=session,
                user_id=user.id,
                jellyseerr_username="JohnDoe",
                display_name="John",
            )

            assert result is not None
            assert result.id is not None
            assert result.jellyseerr_username == "JohnDoe"
            assert result.display_name == "John"
            assert result.user_id == user.id
            assert result.has_jellyseerr_account is False  # Default value

    @pytest.mark.asyncio
    async def test_raises_valueerror_on_duplicate(self) -> None:
        """Should raise ValueError when username already exists for user."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="duplicate_nickname@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create first nickname
            await create_nickname(
                db=session,
                user_id=user.id,
                jellyseerr_username="JohnDoe",
                display_name="John",
            )
            await session.commit()

            # Try to create duplicate
            with pytest.raises(ValueError) as exc_info:
                await create_nickname(
                    db=session,
                    user_id=user.id,
                    jellyseerr_username="JohnDoe",
                    display_name="Different Name",
                )

            assert "already exists" in str(exc_info.value)
            assert "JohnDoe" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allows_same_username_for_different_users(self) -> None:
        """Should allow same username for different users (user isolation)."""
        async with TestingAsyncSessionLocal() as session:
            # Create two users
            user1 = User(
                email="user1_nickname@example.com",
                hashed_password="fakehash",
            )
            user2 = User(
                email="user2_nickname@example.com",
                hashed_password="fakehash",
            )
            session.add(user1)
            session.add(user2)
            await session.flush()

            # Create nickname for user1
            result1 = await create_nickname(
                db=session,
                user_id=user1.id,
                jellyseerr_username="SharedUsername",
                display_name="User1 Display",
            )
            await session.commit()

            # Create same username for user2 - should succeed
            result2 = await create_nickname(
                db=session,
                user_id=user2.id,
                jellyseerr_username="SharedUsername",
                display_name="User2 Display",
            )

            assert result1.id != result2.id
            assert result1.user_id == user1.id
            assert result2.user_id == user2.id

    @pytest.mark.asyncio
    async def test_nickname_created_at_is_set(self) -> None:
        """Should set created_at timestamp on new nickname."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="created_at_test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            result = await create_nickname(
                db=session,
                user_id=user.id,
                jellyseerr_username="TestUser",
                display_name="Test Display",
            )

            assert result.created_at is not None


class TestGetNicknames:
    """Tests for get_nicknames function."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_user_with_no_nicknames(self) -> None:
        """Should return empty list when user has no nicknames."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="no_nicknames@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            result = await get_nicknames(db=session, user_id=user.id)

            assert result.items == []
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_returns_nicknames_ordered_alphabetically(self) -> None:
        """Should return nicknames ordered by jellyseerr_username."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="ordered_nicknames@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create nicknames in non-alphabetical order
            nicknames_data = [
                ("Zoe", "Zoe Display"),
                ("Alice", "Alice Display"),
                ("Mike", "Mike Display"),
            ]
            for username, display_name in nicknames_data:
                nickname = UserNickname(
                    user_id=user.id,
                    jellyseerr_username=username,
                    display_name=display_name,
                )
                session.add(nickname)
            await session.commit()

            result = await get_nicknames(db=session, user_id=user.id)

            assert result.total_count == 3
            assert len(result.items) == 3
            # Should be alphabetically ordered
            assert result.items[0].jellyseerr_username == "Alice"
            assert result.items[1].jellyseerr_username == "Mike"
            assert result.items[2].jellyseerr_username == "Zoe"

    @pytest.mark.asyncio
    async def test_returns_only_user_specific_nicknames(self) -> None:
        """Should only return nicknames for the specified user (user isolation)."""
        async with TestingAsyncSessionLocal() as session:
            user1 = User(
                email="user1_get@example.com",
                hashed_password="fakehash",
            )
            user2 = User(
                email="user2_get@example.com",
                hashed_password="fakehash",
            )
            session.add(user1)
            session.add(user2)
            await session.flush()

            # Create nicknames for both users
            nickname1 = UserNickname(
                user_id=user1.id,
                jellyseerr_username="User1Nickname",
                display_name="User1 Display",
            )
            nickname2 = UserNickname(
                user_id=user2.id,
                jellyseerr_username="User2Nickname",
                display_name="User2 Display",
            )
            session.add(nickname1)
            session.add(nickname2)
            await session.commit()

            # Get nicknames for user1
            result = await get_nicknames(db=session, user_id=user1.id)

            assert result.total_count == 1
            assert result.items[0].jellyseerr_username == "User1Nickname"

    @pytest.mark.asyncio
    async def test_returns_nickname_item_with_all_fields(self) -> None:
        """Should return NicknameItem with all required fields."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="fields_test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="TestUser",
                display_name="Test Display",
                has_jellyseerr_account=True,
            )
            session.add(nickname)
            await session.commit()

            result = await get_nicknames(db=session, user_id=user.id)

            assert result.total_count == 1
            item = result.items[0]
            assert item.id is not None
            assert item.jellyseerr_username == "TestUser"
            assert item.display_name == "Test Display"
            assert item.has_jellyseerr_account is True
            assert item.created_at != ""  # ISO format string

    @pytest.mark.asyncio
    async def test_created_at_is_formatted_as_iso_string(self) -> None:
        """Should return created_at as ISO format string."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="iso_format@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="TestUser",
                display_name="Test Display",
            )
            session.add(nickname)
            await session.commit()

            result = await get_nicknames(db=session, user_id=user.id)

            assert result.total_count == 1
            # created_at should be a non-empty ISO format string
            assert result.items[0].created_at != ""
            # Should be parseable as ISO format (contains T separator)
            assert "T" in result.items[0].created_at


class TestUpdateNickname:
    """Tests for update_nickname function."""

    @pytest.mark.asyncio
    async def test_updates_nickname_successfully(self) -> None:
        """Should update display_name and return True."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="update_success@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="OriginalUser",
                display_name="Original Display",
            )
            session.add(nickname)
            await session.commit()
            nickname_id = nickname.id

            # Update the nickname
            result = await update_nickname(
                db=session,
                user_id=user.id,
                nickname_id=nickname_id,
                display_name="Updated Display",
            )

            assert result is True
            # Verify the update
            await session.refresh(nickname)
            assert nickname.display_name == "Updated Display"

    @pytest.mark.asyncio
    async def test_returns_false_when_nickname_not_found(self) -> None:
        """Should return False when nickname ID doesn't exist."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="update_not_found@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            result = await update_nickname(
                db=session,
                user_id=user.id,
                nickname_id=99999,  # Non-existent ID
                display_name="New Display",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_nickname_belongs_to_other_user(self) -> None:
        """Should return False when nickname belongs to a different user (user isolation)."""
        async with TestingAsyncSessionLocal() as session:
            user1 = User(
                email="user1_update@example.com",
                hashed_password="fakehash",
            )
            user2 = User(
                email="user2_update@example.com",
                hashed_password="fakehash",
            )
            session.add(user1)
            session.add(user2)
            await session.flush()

            # Create nickname for user1
            nickname = UserNickname(
                user_id=user1.id,
                jellyseerr_username="User1Nickname",
                display_name="User1 Display",
            )
            session.add(nickname)
            await session.commit()
            nickname_id = nickname.id

            # Try to update using user2's ID
            result = await update_nickname(
                db=session,
                user_id=user2.id,
                nickname_id=nickname_id,
                display_name="Hacked Display",
            )

            assert result is False
            # Verify original wasn't modified
            await session.refresh(nickname)
            assert nickname.display_name == "User1 Display"

    @pytest.mark.asyncio
    async def test_preserves_other_fields_when_updating(self) -> None:
        """Should only update display_name, preserving other fields."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="preserve_fields@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="TestUser",
                display_name="Original Display",
                has_jellyseerr_account=True,
            )
            session.add(nickname)
            await session.commit()
            nickname_id = nickname.id
            original_username = nickname.jellyseerr_username
            original_has_jellyseerr = nickname.has_jellyseerr_account

            # Update only display_name
            await update_nickname(
                db=session,
                user_id=user.id,
                nickname_id=nickname_id,
                display_name="New Display",
            )

            await session.refresh(nickname)
            assert nickname.display_name == "New Display"
            assert nickname.jellyseerr_username == original_username
            assert nickname.has_jellyseerr_account == original_has_jellyseerr


class TestDeleteNickname:
    """Tests for delete_nickname function."""

    @pytest.mark.asyncio
    async def test_deletes_nickname_successfully(self) -> None:
        """Should delete the nickname and return True."""
        async with TestingAsyncSessionLocal() as session:
            from sqlalchemy import select

            user = User(
                email="delete_success@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="ToBeDeleted",
                display_name="Delete Me",
            )
            session.add(nickname)
            await session.commit()
            nickname_id = nickname.id

            # Delete the nickname
            result = await delete_nickname(
                db=session,
                user_id=user.id,
                nickname_id=nickname_id,
            )

            assert result is True

            # Verify it's deleted
            await session.commit()
            query_result = await session.execute(
                select(UserNickname).where(UserNickname.id == nickname_id)
            )
            assert query_result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_returns_false_when_nickname_not_found(self) -> None:
        """Should return False when nickname ID doesn't exist."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="delete_not_found@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            result = await delete_nickname(
                db=session,
                user_id=user.id,
                nickname_id=99999,  # Non-existent ID
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_nickname_belongs_to_other_user(self) -> None:
        """Should return False when nickname belongs to a different user (user isolation)."""
        async with TestingAsyncSessionLocal() as session:
            user1 = User(
                email="user1_delete@example.com",
                hashed_password="fakehash",
            )
            user2 = User(
                email="user2_delete@example.com",
                hashed_password="fakehash",
            )
            session.add(user1)
            session.add(user2)
            await session.flush()

            # Create nickname for user1
            nickname = UserNickname(
                user_id=user1.id,
                jellyseerr_username="User1Nickname",
                display_name="User1 Display",
            )
            session.add(nickname)
            await session.commit()
            nickname_id = nickname.id

            # Try to delete using user2's ID
            result = await delete_nickname(
                db=session,
                user_id=user2.id,
                nickname_id=nickname_id,
            )

            assert result is False
            # Verify nickname still exists
            await session.refresh(nickname)
            assert nickname.id == nickname_id

    @pytest.mark.asyncio
    async def test_does_not_affect_other_users_nicknames(self) -> None:
        """Should only delete the specified nickname, not affecting others."""
        async with TestingAsyncSessionLocal() as session:
            from sqlalchemy import select

            user = User(
                email="delete_isolation@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create multiple nicknames
            nickname1 = UserNickname(
                user_id=user.id,
                jellyseerr_username="Keep1",
                display_name="Keep1 Display",
            )
            nickname2 = UserNickname(
                user_id=user.id,
                jellyseerr_username="ToDelete",
                display_name="Delete Display",
            )
            nickname3 = UserNickname(
                user_id=user.id,
                jellyseerr_username="Keep2",
                display_name="Keep2 Display",
            )
            session.add_all([nickname1, nickname2, nickname3])
            await session.commit()

            # Delete nickname2
            await delete_nickname(
                db=session,
                user_id=user.id,
                nickname_id=nickname2.id,
            )
            await session.commit()

            # Verify others still exist
            result = await session.execute(
                select(UserNickname).where(UserNickname.user_id == user.id)
            )
            remaining = result.scalars().all()
            usernames = {n.jellyseerr_username for n in remaining}

            assert len(remaining) == 2
            assert "Keep1" in usernames
            assert "Keep2" in usernames
            assert "ToDelete" not in usernames
