"""Review to student view

Revision ID: 8308ba12c9b5
Revises: ef84eeb16962
Create Date: 2016-02-11 02:02:32.620471

"""

# revision identifiers, used by Alembic.
revision = '8308ba12c9b5'
down_revision = 'ef84eeb16962'

from alembic import op
import sqlalchemy as sa
import server
from sqlalchemy.dialects import mysql

import textwrap

def upgrade():
    conn = op.get_bind()

    update_submit = textwrap.dedent("""\
    UPDATE backup AS b
    JOIN submission AS s ON b.id = s.backup_id
    LEFT JOIN final_submission AS fs ON s.id = fs.submission_id
    SET submit = 1, flagged = (fs.id IS NOT NULL)
    """)
    conn.execute(sa.text(update_submit))

    delete_degenerate_groups = textwrap.dedent("""\
    DELETE g, group_member
    FROM `group` AS g JOIN group_member JOIN (
        SELECT g.id AS group_id, max(group_member.id) AS group_member_id
        FROM `group` AS g JOIN group_member ON g.id = group_member.group_id
        GROUP BY g.id
        HAVING count(group_member.id) = 1
    ) AS r
    WHERE g.id = r.group_id AND group_member.id = r.group_member_id
    """)
    conn.execute(sa.text(delete_degenerate_groups))

    op.create_foreign_key(op.f('fk_backup_assignment_id_assignment'), 'backup', 'assignment', ['assignment_id'], ['id'])
    op.create_foreign_key(op.f('fk_backup_submitter_id_user'), 'backup', 'user', ['submitter_id'], ['id'])
    op.create_foreign_key(op.f('fk_enrollment_user_id_user'), 'enrollment', 'user', ['user_id'], ['id'])
    op.create_foreign_key(op.f('fk_enrollment_course_id_course'), 'enrollment', 'course', ['course_id'], ['id'])
    op.create_foreign_key(op.f('fk_group_assignment_id_assignment'), 'group', 'assignment', ['assignment_id'], ['id'])
    op.create_foreign_key(op.f('fk_group_member_assignment_id_assignment'), 'group_member', 'assignment', ['assignment_id'], ['id'])
    op.create_foreign_key(op.f('fk_group_member_group_id_group'), 'group_member', 'group', ['group_id'], ['id'])
    op.create_foreign_key(op.f('fk_group_member_user_id_user'), 'group_member', 'user', ['user_id'], ['id'])
    op.create_foreign_key(op.f('fk_message_backup_id_backup'), 'message', 'backup', ['backup_id'], ['id'])

    op.create_primary_key(
        'pk_enrollment', 'user_enrollment',
        ['user_id', 'course_id']
    )
    op.create_primary_key(
        'pk_group_member', 'group_member',
        ['user_id', 'assignment_id']
    )

    op.drop_column('enrollment', 'id')
    op.drop_column('group_member', 'id')

    op.drop_table('submission')
    op.drop_table('final_submission')

def downgrade():
    op.drop_constraint(op.f('fk_message_backup_id_backup'), 'message', type_='foreignkey')
    op.add_column('group_member', sa.Column('id', mysql.BIGINT(display_width=20), nullable=False))
    op.drop_constraint(op.f('fk_group_member_user_id_user'), 'group_member', type_='foreignkey')
    op.drop_constraint(op.f('fk_group_member_group_id_group'), 'group_member', type_='foreignkey')
    op.drop_constraint(op.f('fk_group_member_assignment_id_assignment'), 'group_member', type_='foreignkey')
    op.drop_constraint(op.f('fk_group_assignment_id_assignment'), 'group', type_='foreignkey')
    op.add_column('enrollment', sa.Column('id', mysql.BIGINT(display_width=20), nullable=False))
    op.drop_constraint(op.f('fk_enrollment_course_id_course'), 'enrollment', type_='foreignkey')
    op.drop_constraint(op.f('fk_enrollment_user_id_user'), 'enrollment', type_='foreignkey')
    op.drop_constraint(op.f('fk_backup_submitter_id_user'), 'backup', type_='foreignkey')
    op.drop_constraint(op.f('fk_backup_assignment_id_assignment'), 'backup', type_='foreignkey')

    drop_constraint('pk_enrollment', 'enrollment', type_='primary')
    drop_constraint('pk_group_member', 'group_member', type_='primary')

    op.create_table('final_submission',
        sa.Column('created', mysql.DATETIME(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('id', mysql.BIGINT(display_width=20), nullable=False),
        sa.Column('submission', mysql.BIGINT(display_width=20), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_default_charset='utf8',
        mysql_engine='InnoDB'
    )
    op.create_table('submission',
    sa.Column('created', mysql.DATETIME(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('id', mysql.BIGINT(display_width=20), nullable=False),
        sa.Column('backup', mysql.BIGINT(display_width=20), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_default_charset='utf8',
        mysql_engine='InnoDB'
    )
