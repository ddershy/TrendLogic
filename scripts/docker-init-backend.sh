#!/usr/bin/env bash
set -euo pipefail

python backend/manage.py migrate --run-syncdb
python backend/manage.py upgrade_chat_storage
python backend/manage.py upgrade_memory_storage
python backend/manage.py upgrade_rag_storage
python backend/manage.py upgrade_metrics_storage
python backend/manage.py collectstatic --noinput
python backend/manage.py check
