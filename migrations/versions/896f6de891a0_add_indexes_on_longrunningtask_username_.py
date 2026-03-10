"""add indexes on longrunningtask username_owner and finished_at

Revision ID: 896f6de891a0
Revises:
Create Date: 2026-03-10 12:03:20.554733

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "896f6de891a0"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use IF NOT EXISTS for idempotency — this is the first Alembic migration in the
    # project and the table is created by the application (SQLModel.metadata.create_all),
    # not by the migration chain.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_longrunningtask_username_owner "
        "ON longrunningtask (username_owner)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_longrunningtask_finished_at "
        "ON longrunningtask (finished_at)"
    )


def downgrade() -> None:
    op.drop_index("ix_longrunningtask_finished_at", table_name="longrunningtask")
    op.drop_index("ix_longrunningtask_username_owner", table_name="longrunningtask")
