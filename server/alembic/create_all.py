from app.models import db

db.create_all()

# then, load the Alembic configuration and generate the
# version table, "stamping" it with the most recent rev:
from alembic.config import Config
from alembic import command
alembic_cfg = Config("alembic.ini")
command.stamp(alembic_cfg, "head")
