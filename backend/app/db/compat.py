from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def run_compat_migrations(engine: Engine) -> None:
    # Lightweight compatibility for local/single-node deployments; not a replacement for Alembic.
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_admin" in user_columns:
        return

    dialect = engine.dialect.name
    ddl = (
        "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE"
        if dialect == "postgresql"
        else "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
    )
    with engine.begin() as connection:
        connection.execute(text(ddl))
