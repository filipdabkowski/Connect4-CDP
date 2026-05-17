from django.urls import path
from .views import BotMoveSuggestionView, CreateRoomView, JoinRoomView, LeaveRoomView, ResetRoomGameView, StartBotGameView

urlpatterns = [
    path("bot/suggest-move/", BotMoveSuggestionView.as_view()),
    path("rooms/create/", CreateRoomView.as_view()),
    path("rooms/<str:code>/join/", JoinRoomView.as_view()),
    path("rooms/<str:code>/leave/", LeaveRoomView.as_view()),
    path("rooms/<str:code>/reset/", ResetRoomGameView.as_view()),
    path("rooms/<str:code>/bot/start/", StartBotGameView.as_view()),
]
