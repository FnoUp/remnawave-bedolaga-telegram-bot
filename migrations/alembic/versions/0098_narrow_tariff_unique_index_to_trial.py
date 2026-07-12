"""narrow tariff unique active index to trial subscriptions only

Revision ID: 0098
Revises: 0097
Create Date: 2026-07-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0098'
down_revision: Union[str, None] = '0097'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Allow a user to buy multiple parallel PAID subscriptions of the same
    # tariff. The trial-uniqueness race guard (UQ_TRIAL_CONSTRAINT in
    # app/database/crud/subscription.py) reuses this same index name, so we
    # narrow the predicate to is_trial=true instead of dropping it — trial
    # double-creation is still blocked, paid duplicates are now allowed.
    op.execute(sa.text('DROP INDEX IF EXISTS uq_subscriptions_user_tariff_active'))
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_subscriptions_user_tariff_active
            ON subscriptions (user_id, tariff_id)
            WHERE tariff_id IS NOT NULL AND status IN ('active', 'trial', 'limited')
                  AND is_trial = true
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text('DROP INDEX IF EXISTS uq_subscriptions_user_tariff_active'))
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_subscriptions_user_tariff_active
            ON subscriptions (user_id, tariff_id)
            WHERE tariff_id IS NOT NULL AND status IN ('active', 'trial', 'limited')
            """
        )
    )
