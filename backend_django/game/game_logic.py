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
	pass


@dataclass(frozen=True)
class MoveResult:
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
		return self.winner_symbol is not None or self.is_draw


def create_empty_board() -> Board:
	return [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]


def normalize_board(board: Board) -> Board:
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
	try:
		symbol = int(symbol)
	except (TypeError, ValueError) as exc:
		raise GameMoveError("Player symbol must be 1 or 2.") from exc

	if symbol not in {PLAYER_ONE, PLAYER_TWO}:
		raise GameMoveError("Player symbol must be 1 or 2.")

	return symbol


def normalize_column(column) -> int:
	try:
		column = int(column)
	except (TypeError, ValueError) as exc:
		raise GameMoveError("Select a valid column.") from exc

	if column not in range(COLUMNS):
		raise GameMoveError("Selected column is outside the board.")

	return column


def get_valid_moves(board: Board) -> list[int]:
	return [column for column in range(COLUMNS) if board[0][column] == EMPTY]


def drop_piece(board: Board, column: int, symbol: int) -> Board:
	column = normalize_column(column)
	symbol = normalize_symbol(symbol)

	if board[0][column] != EMPTY:
		raise GameMoveError("Column is full.")

	next_board = [row.copy() for row in board]
	for row in range(ROWS - 1, -1, -1):
		if next_board[row][column] == EMPTY:
			next_board[row][column] = symbol
			return next_board

	raise GameMoveError("Column is full.")


def has_winning_line(board: Board, symbol: int) -> bool:
	symbol = normalize_symbol(symbol)

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
	return (
		has_winning_line(board, PLAYER_ONE)
		or has_winning_line(board, PLAYER_TWO)
		or not get_valid_moves(board)
	)


def get_opponent_symbol(symbol: int) -> int:
	return PLAYER_ONE if normalize_symbol(symbol) == PLAYER_TWO else PLAYER_TWO


def get_room_player_symbol(room, player_id) -> int:
	if room.player_1_id == player_id:
		return PLAYER_ONE

	if room.player_2_id == player_id:
		return PLAYER_TWO

	raise GameMoveError("You are not a player in this room.")


def process_room_move(room, player_id, column) -> MoveResult:
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
