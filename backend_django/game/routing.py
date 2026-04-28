from django.urls import re_path

from .consumers import GameConsumer

websocket_urlpatterns = [
    re_path(r"^ws/game/(?P<room_code>[A-Za-z0-9_-]+)/$", GameConsumer.as_asgi()),
]
