from datetime import datetime

from psycopg import connect
from psycopg import sql as psycopg_sql
from sqlalchemy import Boolean, Column, Date, Float, Index, Integer, MetaData, Numeric, String, Table, Text, create_engine, inspect, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.url import make_url
from flask import current_app, g


metadata = MetaData()
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(80), nullable=False),
    Column("email", String(255), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("password_fingerprint", String(128), nullable=True),
    Column("created_at", String(40), nullable=False),
    Index("ix_users_username", "username", unique=True),
    Index("ix_users_email", "email", unique=True),
)
password_reset_tokens_table = Table(
    "password_reset_tokens",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False),
    Column("token_hash", String(128), nullable=False),
    Column("expires_at", String(40), nullable=False),
    Column("used_at", String(40), nullable=True),
    Column("created_at", String(40), nullable=False),
    Index("ix_password_reset_tokens_hash", "token_hash", unique=True),
    Index("ix_password_reset_tokens_user_id", "user_id"),
)
expenses_table = Table(
    "expenses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, server_default="1"),
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
    Column("user_id", Integer, nullable=False, server_default="1"),
    Column("monthly_budget", Numeric(12, 2), nullable=False),
    Column("monthly_income", Numeric(12, 2), nullable=False, server_default="0"),
    Index("ix_settings_user_id", "user_id", unique=True),
)
monthly_income_records_table = Table(
    "monthly_income_records",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, server_default="1"),
    Column("month_key", String(7), nullable=False),
    Column("monthly_income", Numeric(12, 2), nullable=False),
    Index("ix_monthly_income_records_user_month", "user_id", "month_key", unique=True),
)
monthly_budget_records_table = Table(
    "monthly_budget_records",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, server_default="1"),
    Column("month_key", String(7), nullable=False),
    Column("monthly_budget", Numeric(12, 2), nullable=False),
    Index("ix_monthly_budget_records_user_month", "user_id", "month_key", unique=True),
)
recurring_items_table = Table(
    "recurring_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, server_default="1"),
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
    Column("user_id", Integer, nullable=False, server_default="1"),
    Column("recurring_item_id", Integer, nullable=False),
    Column("occurrence_date", Date, nullable=False),
    Column("is_paid", Boolean, nullable=False, server_default=text("false")),
    Column("transaction_id", Integer, nullable=True),
    Column("updated_at", String(40), nullable=False),
    Index("ix_recurring_occurrence_status_item_date", "recurring_item_id", "occurrence_date"),
)
savings_goals_table = Table(
    "savings_goals",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, server_default="1"),
    Column("name", String(120), nullable=False),
    Column("target_amount", Numeric(12, 2), nullable=False),
    Column("current_amount", Numeric(12, 2), nullable=False, server_default="0"),
    Column("target_date", Date, nullable=True),
    Column("created_at", String(40), nullable=False),
    Index("ix_savings_goals_user_id", "user_id"),
)
agent_runs_table = Table(
    "agent_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, server_default="1"),
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
api_latency_records_table = Table(
    "api_latency_records",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("request_id", String(64), nullable=False),
    Column("user_id", Integer, nullable=True),
    Column("username_snapshot", String(255), nullable=True),
    Column("method", String(10), nullable=False),
    Column("path", String(500), nullable=False),
    Column("status_code", Integer, nullable=False),
    Column("duration_ms", Float, nullable=False),
    Column("ok", Boolean, nullable=False),
    Column("created_at", String(40), nullable=False),
    Index("ix_api_latency_records_request_id", "request_id"),
    Index("ix_api_latency_records_user_created", "user_id", "created_at"),
    Index("ix_api_latency_records_path", "path"),
    Index("ix_api_latency_records_created_at", "created_at"),
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
    _seed_default_user(engine)
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
        if "user_id" not in expense_columns:
            connection.execute(
                text("ALTER TABLE expenses ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )

        settings_columns = {column["name"] for column in inspector.get_columns("settings")}
        if "user_id" not in settings_columns:
            connection.execute(
                text("ALTER TABLE settings ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )
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

        monthly_income_columns = {column["name"] for column in inspector.get_columns("monthly_income_records")}
        if "user_id" not in monthly_income_columns:
            connection.execute(
                text("ALTER TABLE monthly_income_records ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )
        if dialect == "postgresql":
            connection.execute(text("DROP INDEX IF EXISTS ix_monthly_income_records_month_key"))
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_monthly_income_records_user_month "
                    "ON monthly_income_records (user_id, month_key)"
                )
            )

        monthly_budget_columns = {column["name"] for column in inspector.get_columns("monthly_budget_records")}
        if monthly_budget_columns and "user_id" not in monthly_budget_columns:
            connection.execute(
                text("ALTER TABLE monthly_budget_records ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )
        if dialect == "postgresql":
            connection.execute(text("DROP INDEX IF EXISTS ix_monthly_budget_records_month_key"))
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_monthly_budget_records_user_month "
                    "ON monthly_budget_records (user_id, month_key)"
                )
            )

        recurring_status_columns = {column["name"] for column in inspector.get_columns("recurring_occurrence_status")}
        if "user_id" not in recurring_status_columns:
            connection.execute(
                text("ALTER TABLE recurring_occurrence_status ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )
        if "transaction_id" not in recurring_status_columns:
            connection.execute(
                text(
                    "ALTER TABLE recurring_occurrence_status "
                    "ADD COLUMN transaction_id INTEGER NULL"
                )
            )

        recurring_item_columns = {column["name"] for column in inspector.get_columns("recurring_items")}
        if "user_id" not in recurring_item_columns:
            connection.execute(
                text("ALTER TABLE recurring_items ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )
        if "end_date" not in recurring_item_columns:
            connection.execute(
                text(
                    "ALTER TABLE recurring_items "
                    "ADD COLUMN end_date DATE NULL"
                )
            )

        savings_goal_columns = {column["name"] for column in inspector.get_columns("savings_goals")}
        if "user_id" not in savings_goal_columns:
            connection.execute(
                text("ALTER TABLE savings_goals ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )

        agent_run_columns = {column["name"] for column in inspector.get_columns("agent_runs")}
        if "user_id" not in agent_run_columns:
            connection.execute(
                text("ALTER TABLE agent_runs ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            )

        if dialect == "postgresql":
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_settings_user_id ON settings (user_id)"))

        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "password_fingerprint" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_fingerprint VARCHAR(128) NULL"))


def _seed_default_user(engine: Engine) -> None:
    default_username = current_app.config["AUTH_USERNAME"]
    default_email = current_app.config["AUTH_EMAIL"]
    default_password_hash = current_app.config["AUTH_PASSWORD_HASH"]
    if not default_password_hash:
        return
    created_at = datetime.now().isoformat(timespec="seconds")
    dialect = engine.dialect.name
    with engine.begin() as connection:
        any_user = connection.execute(select(users_table.c.id)).first()
        if any_user is not None:
            _sync_users_id_sequence(connection, dialect)
            return
        existing = connection.execute(
            select(users_table.c.id).where(users_table.c.id == 1)
        ).first()
        if existing is None:
            connection.execute(
                users_table.insert().values(
                    id=1,
                    username=default_username,
                    email=default_email,
                    password_hash=default_password_hash,
                    password_fingerprint=None,
                    created_at=created_at,
                )
            )
        _sync_users_id_sequence(connection, dialect)


def _sync_users_id_sequence(connection: Connection, dialect: str) -> None:
    if dialect != "postgresql":
        return
    connection.execute(
        text(
            "SELECT setval("
            "pg_get_serial_sequence('users', 'id'), "
            "COALESCE((SELECT MAX(id) FROM users), 1), "
            "true"
            ")"
        )
    )


def _seed_settings(engine: Engine) -> None:
    default_budget = round(float(current_app.config["MONTHLY_BUDGET"]), 2)
    default_income = round(float(current_app.config["MONTHLY_INCOME"]), 2)
    with engine.begin() as connection:
        user_count = connection.execute(select(users_table.c.id)).first()
        if user_count is None:
            return
        row = connection.execute(select(settings_table.c.id).where(settings_table.c.user_id == 1)).first()
        user_one = connection.execute(select(users_table.c.id).where(users_table.c.id == 1)).first()
        if row is None and user_one is not None:
            connection.execute(
                settings_table.insert().values(
                    id=1,
                    user_id=1,
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
