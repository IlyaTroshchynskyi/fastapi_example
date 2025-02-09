"""init

Revision ID: 77cdf6aeeebe
Revises:
Create Date: 2025-02-09 14:35:43.460343

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '77cdf6aeeebe'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'genres',
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('genres_pkey')),
    )
    op.create_index(op.f('genres_name_idx'), 'genres', ['name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('genres_name_idx'), table_name='genres')
    op.drop_table('genres')
