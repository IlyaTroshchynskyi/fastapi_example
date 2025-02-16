"""users

Revision ID: 869afeac0e82
Revises: 77cdf6aeeebe
Create Date: 2025-02-15 17:22:38.134811

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '869afeac0e82'
down_revision: Union[str, None] = '77cdf6aeeebe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('users_pkey')),
        sa.UniqueConstraint('email', name=op.f('users_email_key')),
    )


def downgrade() -> None:
    op.drop_table('users')
