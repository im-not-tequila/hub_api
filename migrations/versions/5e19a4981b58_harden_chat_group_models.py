"""harden_chat_group_models

Revision ID: 5e19a4981b58
Revises: 77bdda3c3a10
Create Date: 2026-06-16 11:34:41.939472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e19a4981b58'
down_revision: Union[str, Sequence[str], None] = '77bdda3c3a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat_message_reads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], name='fk_chat_message_reads_chat_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['message_id'],
            ['chat_messages.id'],
            name='fk_chat_message_reads_message_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_chat_message_reads_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', name='uq_chat_message_reads_message_user'),
    )
    op.create_index('ix_chat_message_reads_chat_id', 'chat_message_reads', ['chat_id'], unique=False)
    op.create_index('ix_chat_message_reads_message_id', 'chat_message_reads', ['message_id'], unique=False)
    op.create_index('ix_chat_message_reads_read_at', 'chat_message_reads', ['read_at'], unique=False)
    op.create_index('ix_chat_message_reads_user_id', 'chat_message_reads', ['user_id'], unique=False)

    op.add_column('chat_participants', sa.Column('removed_by_user_id', sa.Integer(), nullable=True))
    op.add_column('chat_participants', sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_chat_participants_removed_by_user_id',
        'chat_participants',
        'users',
        ['removed_by_user_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_chat_participants_removed_by_user_id',
        'chat_participants',
        ['removed_by_user_id'],
        unique=False,
    )

    op.drop_index('uq_chat_pair', table_name='chats')
    op.create_index(
        'uq_direct_chat_pair',
        'chats',
        ['user1_id', 'user2_id'],
        unique=True,
        postgresql_where=sa.text("type = 'direct'"),
    )
    op.create_check_constraint(
        'ck_chats_direct_or_group_shape',
        'chats',
        """
        (
            type = 'direct'
            AND user1_id IS NOT NULL
            AND user2_id IS NOT NULL
            AND user1_id <> user2_id
        )
        OR
        (
            type = 'group'
            AND user1_id IS NULL
            AND user2_id IS NULL
            AND title IS NOT NULL
            AND creator_user_id IS NOT NULL
        )
        """,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_chats_direct_or_group_shape', 'chats', type_='check')
    op.drop_index('uq_direct_chat_pair', table_name='chats')
    op.create_index('uq_chat_pair', 'chats', ['user1_id', 'user2_id'], unique=True)

    op.drop_index('ix_chat_participants_removed_by_user_id', table_name='chat_participants')
    op.drop_constraint('fk_chat_participants_removed_by_user_id', 'chat_participants', type_='foreignkey')
    op.drop_column('chat_participants', 'removed_at')
    op.drop_column('chat_participants', 'removed_by_user_id')

    op.drop_index('ix_chat_message_reads_user_id', table_name='chat_message_reads')
    op.drop_index('ix_chat_message_reads_read_at', table_name='chat_message_reads')
    op.drop_index('ix_chat_message_reads_message_id', table_name='chat_message_reads')
    op.drop_index('ix_chat_message_reads_chat_id', table_name='chat_message_reads')
    op.drop_table('chat_message_reads')
