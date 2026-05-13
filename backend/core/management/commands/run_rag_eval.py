from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import RAGEvaluationCase, RAGEvaluationRun
from metrics.rag_eval import evaluate_rag_cases


class Command(BaseCommand):
    help = "Run RAG retrieval evaluation using active RAGEvaluationCase rows."

    def add_arguments(self, parser):
        parser.add_argument("--top-k", type=int, default=5)
        parser.add_argument("--category", default="")

    def handle(self, *args, **options):
        top_k = int(options["top_k"])
        cases = RAGEvaluationCase.objects.filter(is_active=True)
        if options["category"]:
            cases = cases.filter(category=options["category"])
        cases = list(cases.order_by("created_at"))
        if not cases:
            self.stdout.write(self.style.WARNING("No active RAG evaluation cases. Add cases in Django admin first."))
            return

        metrics = evaluate_rag_cases(cases, top_k=top_k)
        run = RAGEvaluationRun.objects.create(
            top_k=top_k,
            case_count=metrics["case_count"],
            precision_at_k=metrics["precision_at_k"],
            recall_at_k=metrics["recall_at_k"],
            mrr=metrics["mrr"],
            avg_latency_ms=metrics["avg_latency_ms"],
            metrics=metrics,
        )
        self.stdout.write(self.style.SUCCESS(f"RAG eval run saved: {run.id}"))
        self.stdout.write(f"precision@{top_k}: {metrics['precision_at_k']}")
        self.stdout.write(f"recall@{top_k}: {metrics['recall_at_k']}")
        self.stdout.write(f"mrr: {metrics['mrr']}")
        self.stdout.write(f"avg_latency_ms: {metrics['avg_latency_ms']}")
