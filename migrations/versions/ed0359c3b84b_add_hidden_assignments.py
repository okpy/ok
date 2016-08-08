"""Add Hidden Assignments

Revision ID: ed0359c3b84b
Revises: ca9a10db0a21
Create Date: 2016-08-08 16:23:01.121388

"""

# revision identifiers, used by Alembic.
revision = 'ed0359c3b84b'
down_revision = 'ca9a10db0a21'

from alembic import op
import sqlalchemy as sa
import server
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('assignment', sa.Column('visible', sa.Boolean(), default=True))

def downgrade():
    op.drop_column('assignment', 'visible')
