"""permitir estoque nulo

Revision ID: ecec3f3cafeb
Revises:
Create Date: 2026-08-18 12:34:11.147921
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ecec3f3cafeb"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "stock",
            existing_type=sa.INTEGER(),
            nullable=True
        )

    op.execute(
        "UPDATE products SET stock = NULL WHERE stock = 0"
    )


def downgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "stock",
            existing_type=sa.INTEGER(),
            nullable=False
        )