import multiprocessing
from dataclasses import dataclass

from .game_logic import (
	Board,
	COLUMNS,
	CONNECT_LENGTH,
	EMPTY,
	PLAYER_ONE,
	PLAYER_TWO,
	ROWS,
	create_empty_board,
	drop_piece,
	get_opponent_symbol,
	get_valid_moves,
	has_winning_line,
	is_terminal_node,
	normalize_board,
)


WIN_SCORE = 1_000_000


@dataclass(frozen=True)
class MoveSuggestion:
	"""Bot move recommendation produced by the minimax search.

	Input: the chosen column, its evaluated score, and all legal root moves.
	Returns: an immutable object passed back to HTTP and websocket callers.
	"""

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
	"""Choose the strongest legal bot move for the current board.

	Input: a board, the bot's symbol, search depth, and optional multiprocessing
	settings for root-move evaluation.
	Returns: MoveSuggestion with the selected zero-based column and score.
	Raises: ValueError when the board is invalid, full, or already terminal.
	"""

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


def normalize_symbol(symbol: int) -> int:
	"""Convert and validate the bot's player symbol.

	Input: any value intended to represent PLAYER_ONE or PLAYER_TWO.
	Returns: the validated integer symbol.
	Raises: ValueError when the value is not 1 or 2.
	"""

	try:
		symbol = int(symbol)
	except (TypeError, ValueError) as exc:
		raise ValueError("Bot symbol must be 1 or 2.") from exc

	if symbol not in {PLAYER_ONE, PLAYER_TWO}:
		raise ValueError("Bot symbol must be 1 or 2.")

	return symbol


def normalize_depth(depth: int) -> int:
	"""Clamp search depth to a practical range.

	Input: any value intended to be an integer minimax depth.
	Returns: an integer between 1 and 7.
	Raises: ValueError when the value cannot be converted to an integer.
	"""

	try:
		depth = int(depth)
	except (TypeError, ValueError) as exc:
		raise ValueError("Depth must be an integer.") from exc

	return max(1, min(depth, 7))


def evaluate_root_moves(board: Board, bot_symbol: int, depth: int, moves: list[int]) -> tuple[int, int]:
	"""Score candidate root moves in the current process.

	Input: the board, bot symbol, remaining search depth, and ordered legal moves.
	Returns: a tuple of the best column and its score.
	"""

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
	"""Score root moves in parallel worker processes.

	Input: the board, bot symbol, remaining search depth, legal root moves, and
	optional maximum worker count.
	Returns: a tuple of the best column and its score.
	"""

	worker_count = normalize_worker_count(max_workers, len(moves))

	# Every legal move can be scored independently. multiprocessing.Pool starts
	# worker processes and gives each one a root move to explore with minimax.
	jobs = [(board, column, bot_symbol, depth) for column in moves]
	with multiprocessing.Pool(processes=worker_count) as pool:
		scored_moves = pool.starmap(worker_score_root_move, jobs)

	best_column, best_score = scored_moves[0]

	for column, score in scored_moves[1:]:
		if score > best_score:
			best_column = column
			best_score = score

	return best_column, best_score


def normalize_worker_count(max_workers: int | None, move_count: int) -> int:
	"""Bound multiprocessing workers to useful legal moves.

	Input: an optional worker limit and the number of moves to evaluate.
	Returns: at least one worker and never more workers than moves.
	"""

	if max_workers is None:
		return min(move_count, COLUMNS)

	return max(1, min(max_workers, move_count))


def worker_score_root_move(board: Board, column: int, bot_symbol: int, depth: int) -> tuple[int, int]:
	"""Evaluate one root move inside a multiprocessing worker.

	Input: the board, column to test, bot symbol, and original search depth.
	Returns: the tested column and the minimax score for that move.
	"""

	child = drop_piece(board, column, bot_symbol)
	score = minimax(
		board=child,
		depth=depth - 1,
		alpha=-WIN_SCORE * 10,
		beta=WIN_SCORE * 10,
		maximizing_player=False,
		bot_symbol=bot_symbol,
	)[1]
	return column, score


def minimax(
	board: Board,
	depth: int,
	alpha: int,
	beta: int,
	maximizing_player: bool,
	bot_symbol: int,
) -> tuple[int | None, int]:
	"""Run minimax with alpha-beta pruning from the given board.

	Input: a board, remaining depth, alpha/beta bounds, whose turn the search is
	modeling, and the bot symbol.
	Returns: the best column for this node and its score; terminal leaves return
	None for the column.
	"""

	valid_moves = get_valid_moves(board)
	terminal = is_terminal_node(board)
	opponent_symbol = get_opponent_symbol(bot_symbol)

	if depth == 0 or terminal:
		if terminal:
			if has_winning_line(board, bot_symbol):
				# Earlier wins are better, so remaining depth adds urgency.
				return None, WIN_SCORE + depth
			if has_winning_line(board, opponent_symbol):
				# Earlier losses are worse, which nudges the bot to delay defeat.
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
				# The minimizing player already has a better path elsewhere.
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
			# The maximizing player already has a better path elsewhere.
			break

	return best_column, best_score


def score_position(board: Board, symbol: int) -> int:
	"""Estimate how favorable a non-terminal board is for a symbol.

	Input: a board and the symbol being evaluated.
	Returns: a heuristic score; higher values favor the supplied symbol.
	"""

	score = 0
	center_column = [board[row][COLUMNS // 2] for row in range(ROWS)]
	# Center control creates more possible four-in-a-row lines than edge play.
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
	"""Score a four-cell slice of the board.

	Input: a window of four cells and the symbol being evaluated.
	Returns: a positive score for attacking chances and a negative score when an
	opponent threat should be blocked.
	"""

	opponent_symbol = get_opponent_symbol(symbol)
	score = 0

	if window.count(symbol) == 4:
		score += WIN_SCORE
	elif window.count(symbol) == 3 and window.count(EMPTY) == 1:
		score += 100
	elif window.count(symbol) == 2 and window.count(EMPTY) == 2:
		score += 10

	if window.count(opponent_symbol) == 3 and window.count(EMPTY) == 1:
		# Blocking an immediate threat is slightly more valuable than making one.
		score -= 120

	return score


def order_moves_by_center(moves: list[int]) -> list[int]:
	"""Prefer center columns before edge columns.

	Input: legal zero-based column indexes.
	Returns: the same moves sorted by distance from the center column.
	"""

	return sorted(moves, key=lambda column: abs((COLUMNS // 2) - column))
