"""validate_jobs_status_check

Revision ID: c6eab2899afc
Revises: b182ddc16876
Create Date: 2026-08-29 16:51:03.017180

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c6eab2899afc'
down_revision = 'b182ddc16876'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE jobs VALIDATE CONSTRAINT jobs_status_check")


def downgrade() -> None:
    pass