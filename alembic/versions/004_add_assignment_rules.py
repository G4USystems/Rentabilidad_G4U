"""Add assignment_rules table

Revision ID: 004
Revises: 003
Create Date: 2024-01-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create assignment_rules table
    op.create_table(
        'assignment_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('counterparty', sa.String(length=200), nullable=True),
        sa.Column('counterparty_pattern', sa.String(length=200), nullable=True),
        sa.Column('client_name_suggested', sa.String(length=200), nullable=True),
        sa.Column('project_id_suggested', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['project_id_suggested'],
            ['projects.id'],
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create index for faster queries
    op.create_index('ix_assignment_rules_active', 'assignment_rules', ['is_active'])
    op.create_index('ix_assignment_rules_priority', 'assignment_rules', ['priority'])


def downgrade() -> None:
    op.drop_index('ix_assignment_rules_priority', 'assignment_rules')
    op.drop_index('ix_assignment_rules_active', 'assignment_rules')
    op.drop_table('assignment_rules')
