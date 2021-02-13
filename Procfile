web: gunicorn config.wsgi --log-file -
worker: celery -A config worker -l info -O fair --without-heartbeat --without-gossip --without-mingle --concurrency=4
beat: celery -A config beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler