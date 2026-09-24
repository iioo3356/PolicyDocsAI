from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def ensure_policy_deprecated_at_column(engine: Engine) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("policies")}
    if "deprecated_at" in columns:
        return
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE policies ADD COLUMN deprecated_at TIMESTAMP")
