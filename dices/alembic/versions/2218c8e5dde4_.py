"""empty message

Revision ID: 2218c8e5dde4
Revises: 90743fc38783
Create Date: 2024-10-27 23:53:56.901917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '2218c8e5dde4'
down_revision: Union[str, None] = '90743fc38783'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('join_tasks', sa.Column('bonus', sa.Integer(), nullable=True, comment='Общий бонус за подписку'))
    op.alter_column('join_tasks', 'url',
               existing_type=mysql.VARCHAR(length=253),
               comment='юрл подписки',
               existing_nullable=True)
    op.alter_column('join_tasks', 'checks',
               existing_type=mysql.INTEGER(),
               comment='колво дней в течение которых будет начисляться бонус',
               existing_nullable=True)
    op.alter_column('join_tasks', 'active',
               existing_type=mysql.TINYINT(display_width=1),
               comment='По',
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('join_tasks', 'active',
               existing_type=mysql.TINYINT(display_width=1),
               comment=None,
               existing_comment='По',
               existing_nullable=True)
    op.alter_column('join_tasks', 'checks',
               existing_type=mysql.INTEGER(),
               comment=None,
               existing_comment='колво дней в течение которых будет начисляться бонус',
               existing_nullable=True)
    op.alter_column('join_tasks', 'url',
               existing_type=mysql.VARCHAR(length=253),
               comment=None,
               existing_comment='юрл подписки',
               existing_nullable=True)
    op.drop_column('join_tasks', 'bonus')
    # ### end Alembic commands ###
