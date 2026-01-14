"""add_analysis_preferences_to_user_settings

Revision ID: e7fd5345bfb3
Revises: 782c8928d5cd
Create Date: 2026-01-14 16:27:44.941056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7fd5345bfb3'
down_revision: Union[str, None] = '782c8928d5cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_settings', sa.Column('old_content_months', sa.Integer(), nullable=True))
    op.add_column('user_settings', sa.Column('min_age_months', sa.Integer(), nullable=True))
    op.add_column('user_settings', sa.Column('large_movie_size_gb', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_settings', 'large_movie_size_gb')
    op.drop_column('user_settings', 'min_age_months')
    op.drop_column('user_settings', 'old_content_months')
