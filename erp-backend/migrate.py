from sqlalchemy import text
from database import engine


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def run_migrations():
    with engine.begin() as conn:
        if not _column_exists(conn, "products", "unit_of_measure"):
            conn.execute(
                text(
                    "ALTER TABLE products "
                    "ADD COLUMN unit_of_measure VARCHAR DEFAULT 'un'"
                )
            )
            conn.execute(
                text(
                    "UPDATE products SET unit_of_measure = 'un' "
                    "WHERE unit_of_measure IS NULL"
                )
            )

        if not _column_exists(conn, "sale_items", "description"):
            conn.execute(
                text("ALTER TABLE sale_items ADD COLUMN description VARCHAR")
            )

        if not _column_exists(conn, "products", "image_path"):
            conn.execute(
                text("ALTER TABLE products ADD COLUMN image_path VARCHAR")
            )
