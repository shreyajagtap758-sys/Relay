from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b182ddc16876'
down_revision = '12570994dc89'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('jobs_status_check', 'jobs', type_='check')
    op.create_check_constraint(
        'jobs_status_check',
        'jobs',
        "status IN ('pending', 'running', 'succeeded', 'failed', 'dead_letter')",
        postgresql_not_valid=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('jobs_status_check', 'jobs', type_='check')
    op.create_check_constraint(
        'jobs_status_check',
        'jobs',
        "status IN ('pending', 'running', 'succeeded', 'failed')",
    )