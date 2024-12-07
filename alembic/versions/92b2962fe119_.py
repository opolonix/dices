"""empty message

Revision ID: 92b2962fe119
Revises: 879e6bb3cc38
Create Date: 2024-11-28 01:21:50.071621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92b2962fe119'
down_revision: Union[str, None] = '879e6bb3cc38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('model_dice', sa.Column('avatar', sa.String(length=200), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('model_dice', 'avatar')
    # ### end Alembic commands ###
