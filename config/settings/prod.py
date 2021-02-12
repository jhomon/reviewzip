from .base import *


ALLOWED_HOSTS = [
    '127.0.0.1',
    'reviewzip.herokuapp.com'
]


INSTALLED_APPS.extend( [
    'cloudinary_storage',
    'cloudinary',
] )


MIDDLEWARE.extend( [
    'whitenoise.middleware.WhiteNoiseMiddleware',
] )


# Heroku: Update database configuration from $DATABASE_URL.
import dj_database_url
db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(db_from_env)


# Whitenoise
# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Celery configuration
CELERY_BROKER_URL = os.environ.get('CLOUDAMQP_URL')
CELERY_BROKER_POOL_LIMIT = 1
CELERY_BROKER_HEARTBEAT = None
CELERY_RESULT_BACKEND = None
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_MAX_RETRIES = 3
CELERY_WORKER_CONCURRENCY = 50
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1


# cloudinary for image upload
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'drizk0ypa',
    'API_KEY': '817352748312736',
    'API_SECRET': 'zd_D9Np2pXFMNgYIh_pX7jvb_m0',
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'