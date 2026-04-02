from psycopg import connect
from psycopg import sql as psycopg_sql
from sqlalchemy import Boolean, Column, Date, Index, Integer, MetaData, Numeric, String, Table, Text, create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.url import make_url
from flask import current_app, g


metadata = MetaData()
expenses_table = Table(
    "expenses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("date", Date, nullable=False),
    Column("category", String(100), nullable=False),
    Column("description", String(255), nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("entry_type", String(20), nullable=False, server_default="expense"),
    Index("ix_expenses_date", "date"),
    Index("ix_expenses_category", "category"),
    Index("ix_expenses_entry_type", "entry_type"),
)
settings_table = Table(
    "settings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("monthly_budget", Numeric(12, 2), nullable=False),
    Column("monthly_income", Numeric(12, 2), nullable=False, server_default="0"),
)
monthly_income_records_table = Table(
    "monthly_income_records",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("month_key", String(7), nullable=False),
    Column("monthly_income", Numeric(12, 2), nullable=False),
    Index("ix_monthly_income_records_month_key", "month_key", unique=True),
)
recurring_items_table = Table(
    "recurring_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("category", String(100), nullable=False),
    Column("description", String(255), nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("entry_type", String(20), nullable=False, server_default="expense"),
    Column("frequency", String(20), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=True),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    Index("ix_recurring_items_start_date", "start_date"),
    Index("ix_recurring_items_end_date", "end_date"),
    Index("ix_recurring_items_active", "active"),
)
recurring_occurrence_status_table = Table(
    "recurring_occurrence_status",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("recurring_item_id", Integer, nullable=False),
    Column("occurrence_date", Date, nullable=False),
    Column("is_paid", Boolean, nullable=False, server_default=text("false")),
    Column("transaction_id", Integer, nullable=True),
    Column("updated_at", String(40), nullable=False),
    Index("ix_recurring_occurrence_status_item_date", "recurring_item_id", "occurrence_date"),
)
agent_runs_table = Table(
    "agent_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workflow_name", String(100), nullable=False),
    Column("workflow_label", String(160), nullable=False),
    Column("status", String(20), nullable=False),
    Column("headline", String(255), nullable=False),
    Column("summary", Text, nullable=False),
    Column("risk_level", String(20), nullable=False),
    Column("recommended_actions", Text, nullable=False),
    Column("automated_actions", Text, nullable=False),
    Column("email_subject", String(255), nullable=False),
    Column("email_draft", Text, nullable=False),
    Column("task", Text, nullable=False),
    Column("model", String(80), nullable=False),
    Column("tools_used", Text, nullable=False),
    Column("report_download_url", String(255), nullable=True),
    Column("generated_at", String(40), nullable=False),
    Index("ix_agent_runs_workflow_name", "workflow_name"),
    Index("ix_agent_runs_generated_at", "generated_at"),
)


def get_engine() -> Engine:
    engine = current_app.extensions.get("db_engine")
    if engine is None:
        engine = create_engine(
            current_app.config["DATABASE_URL"],
            future=True,
            pool_pre_ping=True,
        )
        current_app.extensions["db_engine"] = engine
    return engine


def get_db() -> Connection:
    if "db" not in g:
        g.db = get_engine().connect()
    return g.db


def close_db(_: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    _ensure_database_exists()
    engine = get_engine()
    metadata.create_all(engine)
    _migrate_schema(engine)
    _seed_settings(engine)


def _migrate_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    dialect = engine.dialect.name
    expense_columns = {column["name"] for column in inspector.get_columns("expenses")}
    with engine.begin() as connection:
        if "entry_type" not in expense_columns:
            connection.execute(
                text(
                    "ALTER TABLE expenses "
                    "ADD COLUMN entry_type VARCHAR(20) NOT NULL DEFAULT 'expense'"
                )
            )
            if dialect == "postgresql":
                connection.execute(
                    text("ALTER TABLE expenses ALTER COLUMN entry_type DROP DEFAULT")
                )

        settings_columns = {column["name"] for column in inspector.get_columns("settings")}
        if "monthly_income" not in settings_columns:
            connection.execute(
                text(
                    "ALTER TABLE settings "
                    "ADD COLUMN monthly_income NUMERIC(12, 2) NOT NULL DEFAULT 0"
                )
            )
            if dialect == "postgresql":
                connection.execute(
                    text("ALTER TABLE settings ALTER COLUMN monthly_income DROP DEFAULT")
                )

        recurring_status_columns = {column["name"] for column in inspector.get_columns("recurring_occurrence_status")}
        if "transaction_id" not in recurring_status_columns:
            connection.execute(
                text(
                    "ALTER TABLE recurring_occurrence_status "
                    "ADD COLUMN transaction_id INTEGER NULL"
                )
            )

        recurring_item_columns = {column["name"] for column in inspector.get_columns("recurring_items")}
        if "end_date" not in recurring_item_columns:
            connection.execute(
                text(
                    "ALTER TABLE recurring_items "
                    "ADD COLUMN end_date DATE NULL"
                )
            )


def _seed_settings(engine: Engine) -> None:
    default_budget = round(float(current_app.config["MONTHLY_BUDGET"]), 2)
    default_income = round(float(current_app.config["MONTHLY_INCOME"]), 2)
    with engine.begin() as connection:
        row = connection.execute(text("SELECT COUNT(*) FROM settings")).scalar_one()
        if row == 0:
            connection.execute(
                settings_table.insert().values(
                    id=1,
                    monthly_budget=default_budget,
                    monthly_income=default_income,
                )
            )


def _ensure_database_exists() -> None:
    database_url = current_app.config["DATABASE_URL"]
    parsed_url = make_url(database_url)
    if not parsed_url.drivername.startswith("postgresql"):
        return

    database_name = parsed_url.database
    if not database_name:
        return

    maintenance_db = current_app.config.get("POSTGRES_MAINTENANCE_DB", "postgres")
    with connect(
        dbname=maintenance_db,
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.host,
        port=parsed_url.port or 5432,
        autocommit=True,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    psycopg_sql.SQL("CREATE DATABASE {}").format(
                        psycopg_sql.Identifier(database_name)
                    )
                )
