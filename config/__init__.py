from .celery import app as celery_app
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
__all__ = ('celery_app',)