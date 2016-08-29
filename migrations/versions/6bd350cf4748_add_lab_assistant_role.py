"""Add Lab assistant role

Revision ID: 6bd350cf4748
Revises: 6504bfe5203c
Create Date: 2016-08-28 17:43:34.671050

"""

# revision identifiers, used by Alembic.
revision = '6bd350cf4748'
down_revision = '6504bfe5203c'

from alembic import op
import sqlalchemy as sa

old = ['student', 'grader', 'staff', 'instructor']
new = ['student', 'lab assistant', 'grader', 'staff', 'instructor']

def upgrade():
    op.alter_column("enrollment", "role", existing_type=sa.types.Enum(*old, name='role'),
                                             type_=sa.types.Enum(*new, name='role'))

def downgrade():
    op.alter_column("enrollment", "role", existing_type=sa.types.Enum(*new, name='role'),
                                             type_=sa.types.Enum(*old, name='role'))
