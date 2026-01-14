"""add_expires_at_to_whitelist_tables

Revision ID: ab2c099348ea
Revises: e7fd5345bfb3
Create Date: 2026-01-14 16:36:14.606586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab2c099348ea'
down_revision: Union[str, None] = 'e7fd5345bfb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('content_whitelist', sa.Column('expires_at', sa.DateTime(), nullable=True))
    op.add_column('french_only_whitelist', sa.Column('expires_at', sa.DateTime(), nullable=True))
    op.add_column('language_exempt_whitelist', sa.Column('expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('language_exempt_whitelist', 'expires_at')
    op.drop_column('french_only_whitelist', 'expires_at')
    op.drop_column('content_whitelist', 'expires_at')
