from __future__ import annotations

from django.core.management.base import BaseCommand

from core.views import seed_default_categories


class Command(BaseCommand):
    help = "Seed default TrendLogic data."

    def handle(self, *args, **options):
        seed_default_categories()
        self.stdout.write(self.style.SUCCESS("TrendLogic default categories seeded."))
