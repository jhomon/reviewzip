from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

app_name = 'api'

urlpatterns = [
    path('get/review/sentences', views.get_sentences_with_keyword, \
        name='get_sentences_with_keyword'),
]

urlpatterns = format_suffix_patterns(urlpatterns)