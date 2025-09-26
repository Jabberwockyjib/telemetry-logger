"""add_is_active_to_sessions

Revision ID: 924dde4e403a
Revises: 37467b2aefe1
Create Date: 2025-09-26 10:56:33.575735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '924dde4e403a'
down_revision: Union[str, None] = '37467b2aefe1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_active column to sessions table
    op.add_column('sessions', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove is_active column from sessions table
    op.drop_column('sessions', 'is_active')
