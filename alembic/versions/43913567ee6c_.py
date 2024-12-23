"""empty message

Revision ID: 43913567ee6c
Revises: d70cd8f7da55
Create Date: 2024-11-26 15:27:01.965240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43913567ee6c'
down_revision: Union[str, None] = 'd70cd8f7da55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('model_dice', sa.Column('title', sa.Text(), nullable=True))
    op.add_column('model_dice', sa.Column('description', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('model_dice', 'description')
    op.drop_column('model_dice', 'title')
    # ### end Alembic commands ###
