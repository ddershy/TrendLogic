from __future__ import annotations

import json
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from core.models import User, UserMemory


class Command(BaseCommand):
    help = "Upgrade fragmented user memories to one memory profile per user."

    def handle(self, *args, **options):
        existing_tables = connection.introspection.table_names()
        with connection.schema_editor() as schema_editor:
            if UserMemory._meta.db_table not in existing_tables:
                schema_editor.create_model(UserMemory)
                self.stdout.write(self.style.SUCCESS(f"Created {UserMemory._meta.db_table}"))
            elif "short_messages" not in {
                column.name
                for column in connection.introspection.get_table_description(connection.cursor(), UserMemory._meta.db_table)
            }:
                with connection.cursor() as cursor:
                    cursor.execute(f"ALTER TABLE {UserMemory._meta.db_table} ADD COLUMN short_messages text NOT NULL DEFAULT '{{}}'")
                self.stdout.write(self.style.SUCCESS(f"Added {UserMemory._meta.db_table}.short_messages"))

        for user in User.objects.all():
            UserMemory.objects.get_or_create(
                user=user,
                defaults={
                    "preferences": user.preferences or {},
                    "tags": list(user.preferences.get("preferred_categories", []) if isinstance(user.preferences, dict) else []),
                    "last_used_at": timezone.now(),
                },
            )

        if "user_memories" not in existing_tables:
            self.stdout.write(self.style.SUCCESS("No legacy user_memories table found."))
            return

        legacy_rows = self.read_legacy_rows()
        grouped = defaultdict(list)
        for row in legacy_rows:
            grouped[row["user_id"]].append(row)

        for user_id, rows in grouped.items():
            user = User.objects.filter(id=user_id).first()
            if not user:
                continue
            memory = UserMemory.objects.get(user=user)
            self.merge_legacy_rows(memory, rows)

        self.stdout.write(self.style.SUCCESS(f"Upgraded memory profiles for {len(grouped)} users."))

    def read_legacy_rows(self) -> list[dict]:
        columns = ["user_id", "memory_type", "content", "summary", "tags", "confidence", "last_used_at", "updated_at"]
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, memory_type, content, summary, tags, confidence, last_used_at, updated_at
                FROM user_memories
                ORDER BY updated_at ASC
                """
            )
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def merge_legacy_rows(self, memory: UserMemory, rows: list[dict]) -> None:
        tags = set(memory.tags or [])
        preferences = dict(memory.preferences or {})
        business_needs = list(memory.business_needs or [])
        recall_signals = list(memory.recall_signals or [])
        long_term_summary = memory.long_term_summary
        short_term_summary = memory.short_term_summary
        confidence = memory.confidence or 0.7
        last_used_at = memory.last_used_at

        for row in rows:
            row_tags = parse_tags(row.get("tags"))
            tags.update(row_tags)
            confidence = max(confidence, float(row.get("confidence") or 0))
            last_used_at = row.get("last_used_at") or last_used_at
            memory_type = row.get("memory_type")
            content = row.get("content") or ""
            summary = row.get("summary") or content[:240]

            if memory_type == "short_term":
                short_term_summary = summary
            elif memory_type == "long_term":
                long_term_summary = summary
            elif memory_type == "preference":
                preferences["legacy_summary"] = summary
                preferences["legacy_tags"] = sorted(set(preferences.get("legacy_tags", []) + row_tags))
            elif memory_type == "business_need":
                business_needs.append({"summary": summary, "content": content})
            elif memory_type == "recall_signal":
                recall_signals.append({"summary": summary, "content": content})

        memory.short_term_summary = short_term_summary
        memory.long_term_summary = long_term_summary
        memory.preferences = preferences
        memory.business_needs = business_needs[-20:]
        memory.recall_signals = recall_signals[-20:]
        memory.tags = sorted(tags)
        memory.confidence = confidence
        memory.last_used_at = last_used_at
        memory.save()


def parse_tags(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item)]
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
    return []
