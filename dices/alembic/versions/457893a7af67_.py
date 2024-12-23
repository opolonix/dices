"""empty message

Revision ID: 457893a7af67
Revises: 94a1fa9a27e8
Create Date: 2024-11-11 01:50:11.464713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '457893a7af67'
down_revision: Union[str, None] = '94a1fa9a27e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('rooms', sa.Column('stage', sa.Integer(), nullable=True))
    op.drop_column('rooms', 'started')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('rooms', sa.Column('started', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    op.drop_column('rooms', 'stage')
    # ### end Alembic commands ###
