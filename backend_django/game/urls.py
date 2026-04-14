from django.urls import path
from .views import CreateRoomView, JoinRoomView

urlpatterns = [
    path("rooms/create/", CreateRoomView.as_view()),
    path("rooms/<str:code>/join/", JoinRoomView.as_view()),
]
