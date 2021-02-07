from django.urls import path
from .views import SentenceViewSet

app_name = 'api'

urlpatterns = [
    path('get/review/sentences', SentenceViewSet.as_view({'get': 'list'}), \
        name='get_sentences_with_keyword'),
]
