"""Pydantic models for whitelist endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WhitelistItemBase(BaseModel):
    """Base model for whitelist items."""

    name: str = Field(min_length=1, max_length=500)


class WhitelistItemCreate(WhitelistItemBase):
    """Model for creating a whitelist item."""

    pass


class WhitelistItemResponse(WhitelistItemBase):
    """Model for whitelist item response."""

    id: int
    added_at: datetime

    class Config:
        from_attributes = True


class WhitelistListResponse(BaseModel):
    """Response containing list of whitelist items."""

    items: list[WhitelistItemResponse]
    total_count: int
    whitelist_type: str


class EpisodeExemptionBase(BaseModel):
    """Base model for episode exemptions."""

    show_name: str = Field(min_length=1, max_length=500)
    season: int = Field(ge=0)
    episode: int = Field(ge=0)


class EpisodeExemptionCreate(EpisodeExemptionBase):
    """Model for creating an episode exemption."""

    pass


class EpisodeExemptionResponse(EpisodeExemptionBase):
    """Model for episode exemption response."""

    id: int
    added_at: datetime

    class Config:
        from_attributes = True


class EpisodeExemptionListResponse(BaseModel):
    """Response containing list of episode exemptions."""

    items: list[EpisodeExemptionResponse]
    total_count: int


class BulkAddRequest(BaseModel):
    """Request to add multiple items to a whitelist."""

    names: list[str] = Field(min_items=1)


class BulkAddResponse(BaseModel):
    """Response after bulk adding items."""

    added_count: int
    skipped_count: int
    skipped_names: list[str] = Field(default_factory=list)


class DeleteResponse(BaseModel):
    """Response after deleting a whitelist item."""

    success: bool
    message: str
    deleted_id: Optional[int] = None
