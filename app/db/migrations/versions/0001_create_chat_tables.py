"""create chat tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_create_chat_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    op.create_table(
        "session_state",
        sa.Column("session_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), primary_key=True),
        sa.Column("state", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute(
        """
        CREATE TRIGGER chat_sessions_set_updated_at
        BEFORE UPDATE ON chat_sessions
        FOR EACH ROW EXECUTE PROCEDURE set_updated_at();
        """
    )
    op.execute(
        """
        CREATE TRIGGER session_state_set_updated_at
        BEFORE UPDATE ON session_state
        FOR EACH ROW EXECUTE PROCEDURE set_updated_at();
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entity_documents_entity_id ON entity_documents (entity_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_entity_type_city_state ON entities (entity_type, city, state);"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS session_state_set_updated_at ON session_state;")
    op.execute("DROP TRIGGER IF EXISTS chat_sessions_set_updated_at ON chat_sessions;")
    op.drop_table("session_state")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.execute("DROP INDEX IF EXISTS ix_entity_documents_entity_id;")
    op.execute("DROP INDEX IF EXISTS ix_entities_entity_type_city_state;")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at;")
