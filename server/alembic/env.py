"""
Defined environment for Alembic migrations
"""
#pylint: disable=no-member
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
from app.models import db #pylint: disable=F0401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
CONFIG = context.config

# Interpret the CONFIG file for Python logging.
# This line sets up loggers basically.
fileConfig(CONFIG.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
TARGET_METADATA = db

# other values from the CONFIG, defined by the needs of env.py,
# can be acquired:
# my_important_option = CONFIG.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = CONFIG.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=TARGET_METADATA)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(CONFIG.get_section(CONFIG.config_ini_section),
                                prefix='sqlalchemy.',
                                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(connection=connection,
                      target_metadata=TARGET_METADATA)

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

