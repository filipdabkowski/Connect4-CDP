from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass


ROWS = 6
COLUMNS = 7
CONNECT_LENGTH = 4
EMPTY = 0
PLAYER_ONE = 1
PLAYER_TWO = 2
WIN_SCORE = 1_000_000

Board = list[list[int]]


@dataclass(frozen=True)
class MoveSuggestion:
	column: int
	score: int
	valid_moves: list[int]


def suggest_bot_move(
	board: Board,
	bot_symbol: int = PLAYER_TWO,
	depth: int = 4,
	use_multiprocessing: bool = False,
	max_workers: int | None = None,
) -> MoveSuggestion:
	board = normalize_board(board)
	bot_symbol = normalize_symbol(bot_symbol)
	depth = normalize_depth(depth)
	valid_moves = get_valid_moves(board)

	if not valid_moves:
		raise ValueError("The board is full. No valid moves are available.")

	if is_terminal_node(board):
		raise ValueError("The game is already finished.")

	ordered_moves = order_moves_by_center(valid_moves)

	if use_multiprocessing and depth > 1 and len(ordered_moves) > 1:
		column, score = evaluate_root_moves_in_processes(
			board=board,
			bot_symbol=bot_symbol,
			depth=depth,
			moves=ordered_moves,
			max_workers=max_workers,
		)
	else:
		column, score = evaluate_root_moves(
			board=board,
			bot_symbol=bot_symbol,
			depth=depth,
			moves=ordered_moves,
		)

	return MoveSuggestion(column=column, score=score, valid_moves=valid_moves)


def normalize_board(board: Board) -> Board:
	if not isinstance(board, list) or len(board) != ROWS:
		raise ValueError(f"Board must contain {ROWS} rows.")

	normalized = []
	for row in board:
		if not isinstance(row, list) or len(row) != COLUMNS:
			raise ValueError(f"Each board row must contain {COLUMNS} columns.")

		normalized_row = []
		for cell in row:
			if cell not in {EMPTY, PLAYER_ONE, PLAYER_TWO}:
				raise ValueError("Board cells must be 0, 1, or 2.")

			normalized_row.append(cell)

		normalized.append(normalized_row)

	return normalized


def normalize_symbol(symbol: int) -> int:
	try:
		symbol = int(symbol)
	except (TypeError, ValueError) as exc:
		raise ValueError("Bot symbol must be 1 or 2.") from exc

	if symbol not in {PLAYER_ONE, PLAYER_TWO}:
		raise ValueError("Bot symbol must be 1 or 2.")

	return symbol


def normalize_depth(depth: int) -> int:
	try:
		depth = int(depth)
	except (TypeError, ValueError) as exc:
		raise ValueError("Depth must be an integer.") from exc

	return max(1, min(depth, 7))


def evaluate_root_moves(board: Board, bot_symbol: int, depth: int, moves: list[int]) -> tuple[int, int]:
	best_column = moves[0]
	best_score = -WIN_SCORE * 10

	for column in moves:
		child = drop_piece(board, column, bot_symbol)
		score = minimax(
			board=child,
			depth=depth - 1,
			alpha=-WIN_SCORE * 10,
			beta=WIN_SCORE * 10,
			maximizing_player=False,
			bot_symbol=bot_symbol,
		)[1]

		if score > best_score:
			best_column = column
			best_score = score

	return best_column, best_score


def evaluate_root_moves_in_processes(
	board: Board,
	bot_symbol: int,
	depth: int,
	moves: list[int],
	max_workers: int | None = None,
) -> tuple[int, int]:
	worker_count = normalize_worker_count(max_workers, len(moves))
	scores_by_column = {}

	with ProcessPoolExecutor(max_workers=worker_count) as executor:
		futures = {
			executor.submit(score_root_move, board, column, bot_symbol, depth): column
			for column in moves
		}

		for future in as_completed(futures):
			column = futures[future]
			scores_by_column[column] = future.result()

	best_column = moves[0]
	best_score = scores_by_column[best_column]

	for column in moves[1:]:
		score = scores_by_column[column]
		if score > best_score:
			best_column = column
			best_score = score

	return best_column, best_score


def normalize_worker_count(max_workers: int | None, move_count: int) -> int:
	if max_workers is None:
		return min(move_count, COLUMNS)

	try:
		max_workers = int(max_workers)
	except (TypeError, ValueError) as exc:
		raise ValueError("maxWorkers must be an integer.") from exc

	return max(1, min(max_workers, move_count))


def score_root_move(board: Board, column: int, bot_symbol: int, depth: int) -> int:
	child = drop_piece(board, column, bot_symbol)
	return minimax(
		board=child,
		depth=depth - 1,
		alpha=-WIN_SCORE * 10,
		beta=WIN_SCORE * 10,
		maximizing_player=False,
		bot_symbol=bot_symbol,
	)[1]


def minimax(
	board: Board,
	depth: int,
	alpha: int,
	beta: int,
	maximizing_player: bool,
	bot_symbol: int,
) -> tuple[int | None, int]:
	valid_moves = get_valid_moves(board)
	terminal = is_terminal_node(board)
	opponent_symbol = get_opponent_symbol(bot_symbol)

	if depth == 0 or terminal:
		if terminal:
			if has_winning_line(board, bot_symbol):
				return None, WIN_SCORE + depth
			if has_winning_line(board, opponent_symbol):
				return None, -WIN_SCORE - depth
			return None, 0

		return None, score_position(board, bot_symbol)

	ordered_moves = order_moves_by_center(valid_moves)

	if maximizing_player:
		best_score = -WIN_SCORE * 10
		best_column = ordered_moves[0]

		for column in ordered_moves:
			child = drop_piece(board, column, bot_symbol)
			score = minimax(child, depth - 1, alpha, beta, False, bot_symbol)[1]

			if score > best_score:
				best_score = score
				best_column = column

			alpha = max(alpha, best_score)
			if alpha >= beta:
				break

		return best_column, best_score

	best_score = WIN_SCORE * 10
	best_column = ordered_moves[0]

	for column in ordered_moves:
		child = drop_piece(board, column, opponent_symbol)
		score = minimax(child, depth - 1, alpha, beta, True, bot_symbol)[1]

		if score < best_score:
			best_score = score
			best_column = column

		beta = min(beta, best_score)
		if alpha >= beta:
			break

	return best_column, best_score


def get_valid_moves(board: Board) -> list[int]:
	return [column for column in range(COLUMNS) if board[0][column] == EMPTY]


def drop_piece(board: Board, column: int, symbol: int) -> Board:
	if column not in range(COLUMNS):
		raise ValueError("Column is outside the board.")

	if board[0][column] != EMPTY:
		raise ValueError("Column is full.")

	next_board = [row.copy() for row in board]
	for row in range(ROWS - 1, -1, -1):
		if next_board[row][column] == EMPTY:
			next_board[row][column] = symbol
			return next_board

	raise ValueError("Column is full.")


def has_winning_line(board: Board, symbol: int) -> bool:
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


def score_position(board: Board, symbol: int) -> int:
	score = 0
	center_column = [board[row][COLUMNS // 2] for row in range(ROWS)]
	score += center_column.count(symbol) * 6

	for row in range(ROWS):
		for column in range(COLUMNS - 3):
			window = [board[row][column + offset] for offset in range(CONNECT_LENGTH)]
			score += score_window(window, symbol)

	for column in range(COLUMNS):
		for row in range(ROWS - 3):
			window = [board[row + offset][column] for offset in range(CONNECT_LENGTH)]
			score += score_window(window, symbol)

	for row in range(ROWS - 3):
		for column in range(COLUMNS - 3):
			window = [board[row + offset][column + offset] for offset in range(CONNECT_LENGTH)]
			score += score_window(window, symbol)

	for row in range(3, ROWS):
		for column in range(COLUMNS - 3):
			window = [board[row - offset][column + offset] for offset in range(CONNECT_LENGTH)]
			score += score_window(window, symbol)

	return score


def score_window(window: list[int], symbol: int) -> int:
	opponent_symbol = get_opponent_symbol(symbol)
	score = 0

	if window.count(symbol) == 4:
		score += WIN_SCORE
	elif window.count(symbol) == 3 and window.count(EMPTY) == 1:
		score += 100
	elif window.count(symbol) == 2 and window.count(EMPTY) == 2:
		score += 10

	if window.count(opponent_symbol) == 3 and window.count(EMPTY) == 1:
		score -= 120

	return score


def get_opponent_symbol(symbol: int) -> int:
	return PLAYER_ONE if symbol == PLAYER_TWO else PLAYER_TWO


def order_moves_by_center(moves: list[int]) -> list[int]:
	return sorted(moves, key=lambda column: abs((COLUMNS // 2) - column))


def create_empty_board() -> Board:
	return [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]
