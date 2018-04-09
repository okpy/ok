"""Adds status column to client table

Revision ID: 1266914000cd
Revises: bb816156989f
Create Date: 2018-04-08 17:47:45.001678

"""

# revision identifiers, used by Alembic.
revision = '1266914000cd'
down_revision = 'bb816156989f'

from alembic import op
import sqlalchemy as sa
import server
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('client', sa.Column('active', sa.Boolean(), default=False))

def downgrade():
    op.drop_column('client', 'active')
