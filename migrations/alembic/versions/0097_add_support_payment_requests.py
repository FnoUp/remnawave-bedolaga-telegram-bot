"""support_payment_requests: оплата через поддержку

Revision ID: 0097
Revises: 0096
Create Date: 2026-07-01

Создаёт таблицу ``support_payment_requests`` для заявок на оплату через
поддержку (пополнение баланса или покупка подписки) с подтверждением админом.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0097'
down_revision: Union[str, None] = '0096'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'support_payment_requests' in inspector.get_table_names():
        return

    op.create_table(
        'support_payment_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'ticket_id',
            sa.Integer(),
            sa.ForeignKey('tickets.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('request_type', sa.String(length=20), nullable=False, server_default='balance'),
        sa.Column('amount_kopeks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_by', sa.BigInteger(), nullable=True),
    )
    op.create_index(
        'ix_support_payment_requests_user_id',
        'support_payment_requests',
        ['user_id'],
    )
    op.create_index(
        'ix_support_payment_requests_status',
        'support_payment_requests',
        ['status'],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'support_payment_requests' not in inspector.get_table_names():
        return
    op.drop_index('ix_support_payment_requests_status', table_name='support_payment_requests')
    op.drop_index('ix_support_payment_requests_user_id', table_name='support_payment_requests')
    op.drop_table('support_payment_requests')
