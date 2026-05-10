from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trendlogic_backend.settings")

from django.core.asgi import get_asgi_application

application = get_asgi_application()
