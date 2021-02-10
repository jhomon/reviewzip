web: gunicorn config.wsgi --log-file -
worker: celery -A config worker --without-heartbeat --without-gossip --without-mingle