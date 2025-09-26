"""add_notes_to_sessions

Revision ID: ec1b6b326a9f
Revises: 924dde4e403a
Create Date: 2025-09-26 11:18:39.606278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec1b6b326a9f'
down_revision: Union[str, None] = '924dde4e403a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add notes column to sessions table
    op.add_column('sessions', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove notes column from sessions table
    op.drop_column('sessions', 'notes')
