from django.urls import path
from .views import PlayerView, PlayerMeView


urlpatterns = [
    path('<str:username>/', PlayerView.as_view(), name='detail'),
	path('', PlayerMeView.as_view(), name='index'),
]
