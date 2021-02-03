from django.urls import path
from .views import add_review
from .views import IndexView, ReviewDetailView, ReviewListView

app_name = "reviewzip"

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('detail/<int:pk>', ReviewDetailView.as_view(), name='detail'),   
    path('search', ReviewListView.as_view(), name='search'),
    path('add/request', add_review, name='add_request'),
]