from django.urls import path
from . import views
from .views import IndexView, ReviewDetailView, ReviewListView

app_name = "reviewzip"

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('detail/<int:pk>/', ReviewDetailView.as_view(), name='detail'),   
    path('search/', ReviewListView.as_view(), name='search'),
    path('add/request/', views.add_request, name='add_request'),
]