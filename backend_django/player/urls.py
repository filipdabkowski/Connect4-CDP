from django.urls import path
from .views import PlayerView


urlpatterns = [
    path('<str:username>/', PlayerView.as_view(), name='detail'),
]
