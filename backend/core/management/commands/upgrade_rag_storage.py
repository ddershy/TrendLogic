from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Upgrade RAG-related database metadata columns."

    def handle(self, *args, **options):
        table_name = "core_uploadeddocument"
        existing_tables = set(connection.introspection.table_names())
        if table_name not in existing_tables:
            self.stdout.write(self.style.WARNING(f"{table_name} does not exist, skipped."))
            return

        columns = {column.name for column in connection.introspection.get_table_description(connection.cursor(), table_name)}
        if "chunk_count" not in columns:
            with connection.cursor() as cursor:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN chunk_count integer NOT NULL DEFAULT 0")
            self.stdout.write(self.style.SUCCESS("Added core_uploadeddocument.chunk_count."))
        else:
            self.stdout.write("core_uploadeddocument.chunk_count already exists.")
