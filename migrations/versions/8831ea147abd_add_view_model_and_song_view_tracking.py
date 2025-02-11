"""Add View model and song view tracking

Revision ID: 8831ea147abd
Revises: 9f62d688f374
Create Date: 2025-02-10 22:19:24.072416

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8831ea147abd'
down_revision = '9f62d688f374'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('views',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('views')
    # ### end Alembic commands ###
