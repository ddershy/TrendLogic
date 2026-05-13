from __future__ import annotations

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Create missing metric and RAG evaluation tables."

    def handle(self, *args, **options):
        existing_tables = set(connection.introspection.table_names())
        model_names = ["MetricEvent", "RAGEvaluationCase", "RAGEvaluationRun"]
        with connection.schema_editor() as schema_editor:
            for model_name in model_names:
                model = apps.get_model("core", model_name)
                if model._meta.db_table in existing_tables:
                    self.stdout.write(f"{model._meta.db_table} already exists.")
                    continue
                schema_editor.create_model(model)
                self.stdout.write(self.style.SUCCESS(f"Created {model._meta.db_table}."))
