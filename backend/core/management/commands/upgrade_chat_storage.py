from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Upgrade chat storage from per-message rows to session-level user transcripts."

    def handle(self, *args, **options):
        existing_tables = connection.introspection.table_names()
        if "core_chatsession" not in existing_tables:
            self.stdout.write(self.style.WARNING("core_chatsession does not exist yet. Run migrate --run-syncdb first."))
            return

        with connection.cursor() as cursor:
            columns = {column.name for column in connection.introspection.get_table_description(cursor, "core_chatsession")}
        with connection.cursor() as cursor:
            if "user_transcript" not in columns:
                cursor.execute("ALTER TABLE core_chatsession ADD COLUMN user_transcript text NOT NULL DEFAULT ''")
                self.stdout.write(self.style.SUCCESS("Added core_chatsession.user_transcript"))
            if "message_count" not in columns:
                cursor.execute("ALTER TABLE core_chatsession ADD COLUMN message_count integer NOT NULL DEFAULT 0")
                self.stdout.write(self.style.SUCCESS("Added core_chatsession.message_count"))
            if "last_message_at" not in columns:
                cursor.execute("ALTER TABLE core_chatsession ADD COLUMN last_message_at datetime NULL")
                self.stdout.write(self.style.SUCCESS("Added core_chatsession.last_message_at"))

        if "core_chatmessage" not in existing_tables:
            self.stdout.write(self.style.SUCCESS("No legacy core_chatmessage table found."))
            return

        grouped_messages = defaultdict(list)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, content, created_at
                FROM core_chatmessage
                WHERE role = 'user'
                ORDER BY created_at ASC
                """
            )
            for session_id, content, created_at in cursor.fetchall():
                grouped_messages[session_id].append((content, created_at))

        with connection.cursor() as cursor:
            for session_id, messages in grouped_messages.items():
                transcript = "\n".join(f"[{created_at}] {content}" for content, created_at in messages)
                last_message_at = messages[-1][1]
                cursor.execute(
                    """
                    UPDATE core_chatsession
                    SET user_transcript = %s,
                        message_count = %s,
                        last_message_at = %s
                    WHERE id = %s AND (user_transcript = '' OR user_transcript IS NULL)
                    """,
                    [transcript, len(messages), last_message_at, session_id],
                )

        self.stdout.write(self.style.SUCCESS(f"Upgraded {len(grouped_messages)} chat sessions."))
