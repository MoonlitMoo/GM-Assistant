"""adding song table

Revision ID: 8672ab67dc22
Revises: 7726828eb595
Create Date: 2025-10-05 11:59:01.520449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8672ab67dc22'
down_revision: Union[str, Sequence[str], None] = '7726828eb595'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('song',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('artist', sa.String(length=255), nullable=False),
    sa.Column('album', sa.String(length=255), nullable=True),
    sa.Column('source', sa.Enum('spotify', 'file', 'url', name='songsource'), nullable=False),
    sa.Column('source_id', sa.String(length=128), nullable=True),
    sa.Column('source_url', sa.String(length=512), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('local_path', sa.String(length=1024), nullable=True),
    sa.Column('added_at', sa.DateTime(), nullable=False),
    sa.Column('play_count', sa.Integer(), nullable=False),
    sa.Column('last_played_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("(source != 'file') OR (local_path IS NOT NULL)", name=op.f('ck_song_ck_song_file_has_path')),
    sa.CheckConstraint('duration_ms IS NULL OR duration_ms >= 0', name=op.f('ck_song_ck_song_duration_nonneg')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_song')),
    sa.UniqueConstraint('source', 'source_id', name='uq_song_source_sourceid')
    )
    with op.batch_alter_table('song', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_song_song_artist'), ['artist'], unique=False)
        batch_op.create_index(batch_op.f('ix_song_song_source'), ['source'], unique=False)
        batch_op.create_index(batch_op.f('ix_song_song_title'), ['title'], unique=False)
        batch_op.create_index('ix_song_title_artist', ['title', 'artist'], unique=False)

    op.create_table('song_tag',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['song_id'], ['song.id'], name=op.f('fk_song_tag_song_id_song'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], name=op.f('fk_song_tag_tag_id_tag'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_song_tag')),
    sa.UniqueConstraint('song_id', 'tag_id', name='uq_song_tag_song_tag')
    )
    with op.batch_alter_table('song_tag', schema=None) as batch_op:
        batch_op.create_index('ix_song_tag_song_id', ['song_id'], unique=False)
        batch_op.create_index('ix_song_tag_tag_id', ['tag_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table('song_tag', schema=None) as batch_op:
        batch_op.drop_index('ix_song_tag_tag_id')
        batch_op.drop_index('ix_song_tag_song_id')

    op.drop_table('song_tag')
    with op.batch_alter_table('song', schema=None) as batch_op:
        batch_op.drop_index('ix_song_title_artist')
        batch_op.drop_index(batch_op.f('ix_song_song_title'))
        batch_op.drop_index(batch_op.f('ix_song_song_source'))
        batch_op.drop_index(batch_op.f('ix_song_song_artist'))

    op.drop_table('song')

    try:
        sa.Enum(name='songsource').drop(op.get_bind(), checkfirst=False)
    except Exception:
        pass
