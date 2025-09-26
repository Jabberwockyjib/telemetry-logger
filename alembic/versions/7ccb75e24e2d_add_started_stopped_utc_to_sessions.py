"""add_started_stopped_utc_to_sessions

Revision ID: 7ccb75e24e2d
Revises: ec1b6b326a9f
Create Date: 2025-09-26 11:19:22.422813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ccb75e24e2d'
down_revision: Union[str, None] = 'ec1b6b326a9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add started_utc and stopped_utc columns to sessions table
    op.add_column('sessions', sa.Column('started_utc', sa.DateTime(timezone=True), nullable=True))
    op.add_column('sessions', sa.Column('stopped_utc', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove started_utc and stopped_utc columns from sessions table
    op.drop_column('sessions', 'stopped_utc')
    op.drop_column('sessions', 'started_utc')
