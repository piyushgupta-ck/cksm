"""add approver_id to approval_requests

Revision ID: 217a2e0fea79
Revises: 9d879dbed828
Create Date: 2026-05-14 15:48:17.703438

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '217a2e0fea79'
down_revision = '9d879dbed828'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('approval_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('approver_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_approval_approver', 'users', ['approver_id'], ['id'])


def downgrade():
    with op.batch_alter_table('approval_requests', schema=None) as batch_op:
        batch_op.drop_constraint('fk_approval_approver', type_='foreignkey')
        batch_op.drop_column('approver_id')
