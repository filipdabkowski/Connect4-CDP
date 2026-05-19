# Connect 4 Online

Connect 4 Online is a browser-based multiplayer version of the classic Connect 4 game. Players create or join a private room, share a room code, and play on a live board that updates through WebSockets. The backend validates every move, stores the board state, detects wins and draws, and can also run a minimax-based bot opponent.

The project was built as a concurrent and distributed programming project, so the architecture intentionally uses HTTP APIs, WebSockets, Redis-backed channel communication, database locks, and multiprocessing for bot move search.

## Table of Contents

- [Game Overview](#game-overview)
- [Project Stack](#project-stack)
- [Project Structure](#project-structure)
- [Client-Server Communication](#client-server-communication)
- [Concurrency, Distribution, and Multiprocessing](#concurrency-distribution-and-multiprocessing)
- [Running the Project](#running-the-project)

## Game Overview

Connect 4 is played on a 7-column by 6-row board. Two players take turns dropping pieces into columns. A piece falls to the lowest available cell in the selected column. The first player to connect four pieces horizontally, vertically, or diagonally wins. If the board fills with no winning line, the game ends in a draw.

This implementation supports:

- user registration and login with JWT authentication
- private room creation and joining by room code
- live board synchronization with WebSockets
- server-side move validation and turn enforcement
- win and draw detection
- leaving, rejoining, and resetting rooms
- optional bot games using a minimax search
- distributed websocket communication through Redis

## Project Stack

### Backend

The backend is written in Python with Django.

| Library / framework | Role in the project |
| --- | --- |
| Django | Main backend framework, models, settings, routing, admin, and database integration. |
| Django REST Framework | REST API views and serializers for registration, login-adjacent user data, room creation, joining, leaving, reset, and bot suggestions. |
| Django Channels | WebSocket support for live game rooms. |
| Daphne | ASGI server used to serve HTTP and WebSocket traffic. |
| channels-redis | Redis channel layer backend, used so separate backend instances can broadcast to the same room groups. |

### Frontend

The frontend is written in React with TypeScript and Vite.

| Library / framework | Role in the project |
| --- | --- |
| React | UI framework for pages, forms, auth provider, and the interactive board. |
| TypeScript | Static typing for API payloads, room state, board state, and component props. |
| Vite | Development server and production build tool. |
| React Router | Public/protected routes for login, registration, and the game screen. |
| Axios | HTTP client used by the API modules. |
| Tailwind CSS | Utility-first styling for the UI. |

### Infrastructure

| Tool           | Role in the project                                                                               |
|----------------|---------------------------------------------------------------------------------------------------|
| Docker Compose | Starts PostgreSQL, Redis, two backend instances, frontend, migrations, and reverse proxy together. |
| Nginx          | Reverse proxy that serves the frontend and balances API/WebSocket traffic to backend instances.   |
| PostgreSql     | Stores main user data, room state information                                                     |
| Redis          | Used as middle layer for Django Channels                                                          |

## Project Structure

The repository is split into a Django backend and a React frontend.

```text
Connect4/
|-- backend_django/
|   |-- app_name/
|   |   |-- views.py          # REST endpoints, implemented logic
|   |   |-- consumers.py      # WebSocket consumer for live communication
|   |   |-- models.py         # Stores code representation of DB objects
|   |   |-- serializers.py    # Converts DB objects into frontend/socket payloads
|   |   |-- urls.py           # REST API routes
|   |   |-- routing.py        # WebSocket route
|   |   `-- other_file.py     # Other file with separated business logic
|   |-- configs/
|   |   |-- settings.py       # Django, database, Redis, Channels, REST, and CORS settings
|   |   |-- urls.py           # Main HTTP route configuration
|   |   `-- asgi.py           # ASGI app that combines HTTP and WebSocket handling
|   `-- manage.py
|-- frontend_react/
|   |-- src/
|   |   |-- api/
|   |   |   |-- client.ts     # Shared Axios instance and JWT request interceptor
|   |   |   |-- auth.ts       # Login, registration, refresh, and current-user API calls
|   |   |   `-- game.ts       # Room API calls and TypeScript payload types
|   |   |-- auth/
|   |   |   |-- AuthProvider.tsx  # Stores auth state and refreshes access tokens
|   |   |   |-- AuthContext.ts    # React auth context type and object
|   |   |   `-- useAuth.ts        # Hook for reading auth context
|   |   |-- components/       # Reusable UI elements such as buttons, inputs, and board
|   |   |-- pages/            # Login, registration, and main game room screens
|   |   `-- routes/           # ProtectedRoute and PublicRoute guards
|   `-- package.json
|-- docker-compose.yml
`-- README.md
```

## Client-Server Communication

The project uses two communication methods:

1. REST over HTTP for account actions and room lifecycle actions.
2. WebSockets for live game state updates and player moves inside a room.

### REST API Communication

REST is used when the client needs a clear request-response operation, such as creating or joining a room.

Important REST endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Create a new user account. |
| `POST` | `/api/auth/login` | Get access and refresh JWT tokens. |
| `POST` | `/api/auth/refresh` | Refresh the access token. |
| `GET` | `/api/player/` | Get the current player's profile. |
| `POST` | `/api/game/rooms/create/` | Create a new room. |
| `POST` | `/api/game/rooms/<code>/join/` | Join an existing room. |
| `POST` | `/api/game/rooms/<code>/leave/` | Leave a room. |
| `POST` | `/api/game/rooms/<code>/reset/` | Reset a finished room. |
| `POST` | `/api/game/rooms/<code>/bot/start/` | Start a bot game in a waiting room. |
| `POST` | `/api/game/bot/suggest-move/` | Ask the backend for a bot move suggestion. |

Example create-room request:

```http
POST /api/game/rooms/create/

{
  "code": "ROOM42"
}
```

Example room response:

```json
{
  "type": "room_state",
  "roomCode": "ROOM42",
  "status": "waiting",
  "player1": "filip",
  "player2": null,
  "board": [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0]
  ],
  "currentPlayer": {
    "symbol": 1,
    "slot": "player1",
    "username": "filip"
  },
  "isBotGame": false,
  "gameResult": null
}
```

### WebSocket Communication

After creating or joining a room, the React client opens a WebSocket connection:

```text
ws://<host>/ws/game/<roomCode>/?token=<access_token>
```

The token is passed in the query string because browser WebSocket constructors do not allow custom `Authorization` headers. The backend validates the token in `GameConsumer.connect()` and only accepts the socket if the authenticated player belongs to the room.

The most important client-to-server WebSocket message is `player_move`. It is sent when the user clicks a playable column on the board.

```json
{
  "type": "player_move",
  "player": {
    "username": "filip",
    "symbol": 1
  },
  "column": 3
}
```

The backend does not trust the player object from the client for game authority. It uses the JWT token and room membership to determine which player is moving, then validates turn order and the selected column on the server.

Example server-to-client move broadcast:

```json
{
  "type": "player_move",
  "roomCode": "ROOM42",
  "status": "ready",
  "player1": "filip",
  "player2": "nope",
  "board": [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0]
  ],
  "currentPlayer": {
    "symbol": 2,
    "slot": "player2",
    "username": "nope"
  },
  "isBotGame": false,
  "gameResult": null,
  "lastMove": {
    "player": {
      "symbol": 1,
      "slot": "player1",
      "username": "filip"
    },
    "column": 3
  }
}
```

Example error payload:

```json
{
  "type": "room_error",
  "message": "It is not your turn."
}
```

### Main Communication Flow
![alt1](/static/img1.png)

### Player Move Flow

![alt2](/static/img2.png)

## Concurrency, Distribution, and Multiprocessing

### Async WebSocket Handling

The WebSocket layer is asynchronous through Django Channels. `GameConsumer` inherits from `AsyncWebsocketConsumer`, so methods such as `connect`, `receive`, and `disconnect` run without blocking the entire server process while waiting for socket events.

Database work is synchronous in Django, so the consumer wraps database operations with `database_sync_to_async`. That allows the async WebSocket consumer to call ORM code safely without blocking the event loop directly.

Important async responsibilities:

- `connect()` authenticates the socket and adds it to the Redis-backed room group.
- `receive()` parses incoming JSON and dispatches player moves.
- `_apply_player_move()` performs the database update under a transaction.
- `broadcast_state()` and `broadcast_payload()` send serialized room state back to connected clients.

### Redis Communication Between Backend Instances

The Docker setup starts two backend containers:

- `backend1`
- `backend2`

Both are connected to the same Redis channel layer. A player can be connected to `backend1` while another player is connected to `backend2`. Without Redis, a WebSocket group broadcast would only reach sockets connected to the same backend process.

Redis solves this by acting as a shared channel layer:

![alt3](/static/img3.png)

When the backend calls:

```python
await self.channel_layer.group_send(
    self.room_name,
    {
        "type": "broadcast_payload",
        "payload": payload,
    },
)
```

Channels sends the message to Redis. Redis then delivers it to every backend instance that has sockets subscribed to that group. Each backend instance forwards the payload to its connected browsers.

### Database Locks and Move Safety

Move processing uses a database transaction and `select_for_update()`:

```python
with transaction.atomic():
    room = Room.objects.select_for_update().select_related().get(code=code)
    move_result = process_room_move(room, player_id, column)
    room.board = move_result.board
    room.save(update_fields=update_fields)
```

This is important because two players may click at nearly the same time, or the same client may retry during a network delay. The row lock ensures only one move updates a room at a time. The second move waits for the first transaction, then validates against the new board and current turn.

### Bot Multiprocessing

The bot uses a minimax search with alpha-beta pruning. Root moves can be evaluated independently, so the backend can split those root move evaluations across multiple worker processes with `multiprocessing.Pool`.

Simplified version:

```python
jobs = [(board, column, bot_symbol, depth) for column in moves]
with multiprocessing.Pool(processes=worker_count) as pool:
    scored_moves = pool.starmap(worker_score_root_move, jobs)
```

Each worker receives one possible root column, drops the bot piece in that column, and runs minimax for the remaining depth. The parent process compares the returned scores and chooses the best column.

![alt4](/static/img4.png)

Multiprocessing is used only at the root of the search tree because those branches are independent and easy to combine. Inside each branch, minimax remains recursive and uses alpha-beta pruning to skip branches that cannot improve the result.

## Running the Project

The full distributed setup can be started with Docker Compose:

```bash
docker compose up --build
```

By default, the app is exposed through the reverse proxy on:

```text
http://localhost:8080
```

For local development without Docker, run the backend and frontend separately:

```bash
cd backend_django
uv run python manage.py migrate
uv run daphne -b 0.0.0.0 -p 8000 game_server.asgi:application
```

```bash
cd frontend_react
npm install
npm run dev
```

The frontend expects an API base URL through `VITE_API_BASE_URL`. In the Docker setup this is configured to use the reverse proxy path `/api/`.

## Game Screenshots

![alt5](/static/img5.png)
