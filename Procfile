web: gunicorn config.wsgi --log-file -
worker: celery -A config worker -l info -O fair --without-heartbeat --without-gossip --without-mingle --concurrency=4