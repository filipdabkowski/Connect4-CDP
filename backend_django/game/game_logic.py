from dataclasses import dataclass


ROWS = 6
COLUMNS = 7
CONNECT_LENGTH = 4
EMPTY = 0
PLAYER_ONE = 1
PLAYER_TWO = 2

ROOM_STATUS_WAITING = "waiting"
ROOM_STATUS_READY = "ready"
ROOM_STATUS_FINISHED = "finished"
ROOM_STATUS_CHOICES = [
	(ROOM_STATUS_WAITING, "Waiting"),
	(ROOM_STATUS_READY, "Ready"),
	(ROOM_STATUS_FINISHED, "Finished"),
]

BOT_USERNAME = "Bot"

Board = list[list[int]]


class GameMoveError(ValueError):
	"""Raised when a requested game action would violate Connect 4 rules.

	Input: an optional error message describing the invalid move or state.
	Returns: no value; callers catch this exception to send user-facing errors.
	"""

	pass


@dataclass(frozen=True)
class MoveResult:
	"""Immutable description of a validated move and the room state it implies.

	Input: the board after the move, the played column, the active symbol, the
	next turn, optional winner/draw state, and socket message metadata.
	Returns: a dataclass instance consumed by persistence and websocket code.
	"""

	board: Board
	column: int
	player_symbol: int
	next_turn: int
	winner_symbol: int | None
	is_draw: bool
	message_type: str
	message: str | None

	@property
	def is_finished(self):
		"""Return whether this move ended the game.

		Input: no arguments; reads the result's winner and draw fields.
		Returns: True when a winner exists or the board ended in a draw.
		"""

		return self.winner_symbol is not None or self.is_draw


def create_empty_board() -> Board:
	"""Create a fresh Connect 4 board in row-major order.

	Input: no arguments.
	Returns: a 6x7 board filled with EMPTY cells.
	"""

	return [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]


def normalize_board(board: Board) -> Board:
	"""Validate and copy a board supplied by storage or a request.

	Input: a nested list expected to contain ROWS rows and COLUMNS cells per row.
	Returns: a new board list containing only EMPTY, PLAYER_ONE, or PLAYER_TWO.
	Raises: GameMoveError when shape or cell values are invalid.
	"""

	if not isinstance(board, list) or len(board) != ROWS:
		raise GameMoveError(f"Board must contain {ROWS} rows.")

	normalized = []
	for row in board:
		if not isinstance(row, list) or len(row) != COLUMNS:
			raise GameMoveError(f"Each board row must contain {COLUMNS} columns.")

		normalized_row = []
		for cell in row:
			if cell not in {EMPTY, PLAYER_ONE, PLAYER_TWO}:
				raise GameMoveError("Board cells must be 0, 1, or 2.")

			normalized_row.append(cell)

		normalized.append(normalized_row)

	return normalized


def normalize_symbol(symbol: int) -> int:
	"""Convert and validate a player symbol.

	Input: any value intended to represent PLAYER_ONE or PLAYER_TWO.
	Returns: the validated integer symbol.
	Raises: GameMoveError when the value is not 1 or 2.
	"""

	try:
		symbol = int(symbol)
	except (TypeError, ValueError) as exc:
		raise GameMoveError("Player symbol must be 1 or 2.") from exc

	if symbol not in {PLAYER_ONE, PLAYER_TWO}:
		raise GameMoveError("Player symbol must be 1 or 2.")

	return symbol


def normalize_column(column) -> int:
	"""Convert and validate a playable board column.

	Input: any value intended to represent a zero-based column index.
	Returns: the validated column integer.
	Raises: GameMoveError when the value is not inside the board.
	"""

	try:
		column = int(column)
	except (TypeError, ValueError) as exc:
		raise GameMoveError("Select a valid column.") from exc

	if column not in range(COLUMNS):
		raise GameMoveError("Selected column is outside the board.")

	return column


def get_valid_moves(board: Board) -> list[int]:
	"""List columns that can still accept a piece.

	Input: a normalized board.
	Returns: zero-based column indexes whose top cell is empty.
	"""

	return [column for column in range(COLUMNS) if board[0][column] == EMPTY]


def drop_piece(board: Board, column: int, symbol: int) -> Board:
	"""Return a new board after dropping a piece into a column.

	Input: a board, zero-based column, and player symbol.
	Returns: a copied board with the piece placed in the lowest open cell.
	Raises: GameMoveError when the column or symbol is invalid, or the column is full.
	"""

	column = normalize_column(column)
	symbol = normalize_symbol(symbol)

	if board[0][column] != EMPTY:
		raise GameMoveError("Column is full.")

	# Copy rows so callers can compare old and new state without accidental mutation.
	next_board = [row.copy() for row in board]
	for row in range(ROWS - 1, -1, -1):
		if next_board[row][column] == EMPTY:
			next_board[row][column] = symbol
			return next_board

	raise GameMoveError("Column is full.")


def has_winning_line(board: Board, symbol: int) -> bool:
	"""Check whether a symbol has four connected cells.

	Input: a board and the symbol to evaluate.
	Returns: True when a horizontal, vertical, or diagonal line exists.
	Raises: GameMoveError when the symbol is invalid.
	"""

	symbol = normalize_symbol(symbol)

	# Scan only positions that can fit a four-cell window in each direction.
	for row in range(ROWS):
		for column in range(COLUMNS - 3):
			if all(board[row][column + offset] == symbol for offset in range(CONNECT_LENGTH)):
				return True

	for column in range(COLUMNS):
		for row in range(ROWS - 3):
			if all(board[row + offset][column] == symbol for offset in range(CONNECT_LENGTH)):
				return True

	for row in range(ROWS - 3):
		for column in range(COLUMNS - 3):
			if all(board[row + offset][column + offset] == symbol for offset in range(CONNECT_LENGTH)):
				return True

	for row in range(3, ROWS):
		for column in range(COLUMNS - 3):
			if all(board[row - offset][column + offset] == symbol for offset in range(CONNECT_LENGTH)):
				return True

	return False


def is_terminal_node(board: Board) -> bool:
	"""Return whether a board has no further meaningful game states.

	Input: a board.
	Returns: True for a win by either player or a full board draw.
	"""

	return (
		has_winning_line(board, PLAYER_ONE)
		or has_winning_line(board, PLAYER_TWO)
		or not get_valid_moves(board)
	)


def get_opponent_symbol(symbol: int) -> int:
	"""Return the opposite Connect 4 player symbol.

	Input: PLAYER_ONE or PLAYER_TWO.
	Returns: PLAYER_TWO for PLAYER_ONE, otherwise PLAYER_ONE.
	Raises: GameMoveError when the input is not a valid symbol.
	"""

	return PLAYER_ONE if normalize_symbol(symbol) == PLAYER_TWO else PLAYER_TWO


def get_room_player_symbol(room, player_id) -> int:
	"""Resolve a room participant to their board symbol.

	Input: a Room-like object with player ids and an authenticated player id.
	Returns: PLAYER_ONE or PLAYER_TWO for the matching room slot.
	Raises: GameMoveError when the player is not in the room.
	"""

	if room.player_1_id == player_id:
		return PLAYER_ONE

	if room.player_2_id == player_id:
		return PLAYER_TWO

	raise GameMoveError("You are not a player in this room.")


def process_room_move(room, player_id, column) -> MoveResult:
	"""Validate and apply the human player's move rules for a room.

	Input: a Room-like object, the moving player's id, and a zero-based column.
	Returns: MoveResult describing the updated board, next turn, and end state.
	Raises: GameMoveError when authentication, room status, turn order, or column
	selection makes the move illegal.
	"""

	if not player_id:
		raise GameMoveError("You must be signed in to make a move.")

	column = normalize_column(column)

	if room.status == ROOM_STATUS_FINISHED:
		raise GameMoveError("This game is already finished.")

	if room.status != ROOM_STATUS_READY:
		raise GameMoveError("Wait for another player before making a move.")

	player_symbol = get_room_player_symbol(room, player_id)
	if room.current_turn != player_symbol:
		raise GameMoveError("It is not your turn.")

	# Room.board comes from JSON storage, so validate shape and values before using it.
	next_board = drop_piece(normalize_board(room.board), column, player_symbol)
	if has_winning_line(next_board, player_symbol):
		return MoveResult(
			board=next_board,
			column=column,
			player_symbol=player_symbol,
			next_turn=room.current_turn,
			winner_symbol=player_symbol,
			is_draw=False,
			message_type="game_over",
			message=None,
		)

	if not get_valid_moves(next_board):
		return MoveResult(
			board=next_board,
			column=column,
			player_symbol=player_symbol,
			next_turn=room.current_turn,
			winner_symbol=None,
			is_draw=True,
			message_type="game_over",
			message="Game ended in a draw.",
		)

	return MoveResult(
		board=next_board,
		column=column,
		player_symbol=player_symbol,
		next_turn=get_opponent_symbol(player_symbol),
		winner_symbol=None,
		is_draw=False,
		message_type="player_move",
		message=None,
	)
