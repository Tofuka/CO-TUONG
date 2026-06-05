"""
Xiangqi AI Engine – Dual-Engine Architecture
=============================================
Primary:   Pikafish UCI engine (strongest open-source Xiangqi AI)
           → Auto-detected from  engines/pikafish.exe
           → Falls back to custom engine if binary is absent

Fallback:  Custom iterative-deepening Alpha-Beta engine
  Techniques:
  • Iterative Deepening (ID-IDDFS) with hard time limit
  • Alpha-Beta Pruning + Transposition Table (Zobrist hashing)
  • Killer-Move & History Heuristics
  • Quiescence Search, Null-Move Pruning, Late Move Reductions
  • Fast material + PST static evaluation
"""

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from models import Board, Color, Piece, PieceType, Position
from rules import MoveValidator

# ---------------------------------------------------------------------------
# Material values
# ---------------------------------------------------------------------------
MATERIAL: Dict[PieceType, int] = {
    PieceType.GENERAL:  100_000,
    PieceType.CHARIOT:    1_000,
    PieceType.CANNON:       450,
    PieceType.HORSE:        400,
    PieceType.ELEPHANT:     200,
    PieceType.ADVISOR:      200,
    PieceType.SOLDIER:      100,
}

# ---------------------------------------------------------------------------
# Piece-Square Tables (from RED's perspective, row 0 = red baseline)
# ---------------------------------------------------------------------------
PST: Dict[PieceType, List[List[int]]] = {
    PieceType.SOLDIER: [
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  5,  5,  5,  0,  0,  0],
        [  0,  0,  0, 10, 10, 10,  0,  0,  0],
        [  2,  0,  5, 15, 20, 15,  5,  0,  2],
        [  5,  5, 10, 20, 25, 20, 10,  5,  5],
        [ 15, 20, 35, 45, 50, 45, 35, 20, 15],
        [ 30, 40, 55, 65, 70, 65, 55, 40, 30],
        [ 50, 65, 80, 95,100, 95, 80, 65, 50],
        [ 60, 80,100,115,120,115,100, 80, 60],
        [ 15, 25, 40, 50, 50, 50, 40, 25, 15],
    ],
    PieceType.HORSE: [
        [  0, -5, -5, -5, -5, -5, -5, -5,  0],
        [ -5,  5, 10, 10, 10, 10, 10,  5, -5],
        [ -5, 10, 20, 25, 25, 25, 20, 10, -5],
        [ -5, 15, 25, 30, 35, 30, 25, 15, -5],
        [ -5, 20, 30, 35, 40, 35, 30, 20, -5],
        [ -5, 25, 35, 40, 45, 40, 35, 25, -5],
        [ -5, 25, 35, 40, 45, 40, 35, 25, -5],
        [ -5, 20, 30, 35, 40, 35, 30, 20, -5],
        [ -5, 10, 20, 25, 30, 25, 20, 10, -5],
        [  0, -5, -5, -5, -5, -5, -5, -5,  0],
    ],
    PieceType.CHARIOT: [
        [  0,  5,  5, 10, 20, 10,  5,  5,  0],
        [ 10, 20, 15, 25, 30, 25, 15, 20, 10],
        [  5, 10, 10, 20, 25, 20, 10, 10,  5],
        [ 10, 15, 15, 25, 30, 25, 15, 15, 10],
        [ 15, 20, 20, 30, 35, 30, 20, 20, 15],
        [ 20, 25, 25, 35, 40, 35, 25, 25, 20],
        [ 25, 30, 30, 40, 45, 40, 30, 30, 25],
        [ 30, 35, 35, 45, 50, 45, 35, 35, 30],
        [ 35, 40, 40, 50, 55, 50, 40, 40, 35],
        [  5, 10, 10, 15, 25, 15, 10, 10,  5],
    ],
    PieceType.CANNON: [
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  5, 10,  5,  5, 10,  5,  5, 10,  5],
        [  0,  5,  0,  0,  5,  0,  0,  5,  0],
        [  5, 10,  5, 10, 15, 10,  5, 10,  5],
        [ 10, 15, 10, 15, 20, 15, 10, 15, 10],
        [ 15, 20, 15, 20, 25, 20, 15, 20, 15],
        [ 20, 25, 20, 25, 30, 25, 20, 25, 20],
        [ 15, 20, 15, 20, 25, 20, 15, 20, 15],
        [ 10, 15, 10, 15, 20, 15, 10, 15, 10],
        [  0,  5,  0,  5, 10,  5,  0,  5,  0],
    ],
    PieceType.ADVISOR: [
        [  0,  0,  0,  5,  0,  5,  0,  0,  0],
        [  0,  0,  0,  0, 10,  0,  0,  0,  0],
        [  0,  0,  0,  5,  0,  5,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    ],
    PieceType.ELEPHANT: [
        [  0,  0,  5,  0,  0,  0,  5,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  5,  0,  0,  0, 10,  0,  0,  0,  5],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  5,  0,  0,  0,  5,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    ],
    PieceType.GENERAL: [
        [  0,  0,  0, -5,  0, -5,  0,  0,  0],
        [  0,  0,  0,  0,  5,  0,  0,  0,  0],
        [  0,  0,  0, -5,  0, -5,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
        [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    ],
}

# ---------------------------------------------------------------------------
# Zobrist Hashing
# ---------------------------------------------------------------------------
_PIECE_IDX: Dict[PieceType, int] = {pt: i for i, pt in enumerate(PieceType)}
_COLOR_IDX: Dict[Color, int] = {Color.RED: 0, Color.BLACK: 1}

_rng = random.Random(0xDEADBEEF_CAFE)
ZOBRIST: List[List[List[List[int]]]] = [
    [
        [[_rng.getrandbits(64) for _ in range(9)] for _ in range(10)]
        for _ in range(7)
    ]
    for _ in range(2)
]
ZOBRIST_TURN = _rng.getrandbits(64)


def _compute_hash(board: Board, turn_is_red: bool) -> int:
    h = ZOBRIST_TURN if turn_is_red else 0
    for pos, piece in board.grid.items():
        ci = _COLOR_IDX[piece.color]
        pi = _PIECE_IDX[piece.get_current_type()]
        h ^= ZOBRIST[ci][pi][pos.row][pos.col]
    return h


# ---------------------------------------------------------------------------
# Transposition Table
# ---------------------------------------------------------------------------
TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2

_TT_SIZE = 1 << 19   # 524 288 buckets (smaller = faster cache)
_tt_key   = [0]   * _TT_SIZE
_tt_depth = [-1]  * _TT_SIZE
_tt_flag  = [0]   * _TT_SIZE
_tt_score = [0]   * _TT_SIZE
_tt_move  = [None] * _TT_SIZE   # type: List[Optional[Tuple[Position,Position]]]


def _tt_probe(key: int, depth: int, alpha: int, beta: int
              ) -> Tuple[bool, int, Optional[Tuple[Position, Position]]]:
    idx = key & (_TT_SIZE - 1)
    if _tt_key[idx] != key or _tt_depth[idx] < depth:
        return False, 0, _tt_move[idx]   # still return stored best-move hint
    flag  = _tt_flag[idx]
    score = _tt_score[idx]
    if flag == TT_EXACT:
        return True, score, _tt_move[idx]
    if flag == TT_LOWER and score >= beta:
        return True, score, _tt_move[idx]
    if flag == TT_UPPER and score <= alpha:
        return True, score, _tt_move[idx]
    return False, 0, _tt_move[idx]


def _tt_store(key: int, depth: int, flag: int, score: int,
              move: Optional[Tuple[Position, Position]]) -> None:
    idx = key & (_TT_SIZE - 1)
    if _tt_depth[idx] <= depth:
        _tt_key[idx]   = key
        _tt_depth[idx] = depth
        _tt_flag[idx]  = flag
        _tt_score[idx] = score
        _tt_move[idx]  = move


# ---------------------------------------------------------------------------
# Fast Static Evaluation  (material + PST only – NO legal-move generation)
# ---------------------------------------------------------------------------
def _pst(pt: PieceType, row: int, col: int, color: Color) -> int:
    if color == Color.BLACK:
        row = 9 - row
        col = 8 - col
    t = PST.get(pt)
    return t[row][col] if t else 0


def evaluate(board: Board, color: Color) -> int:
    """Pure material+PST evaluation.  O(pieces) – no legal-move generation."""
    score = 0
    for pos, piece in board.grid.items():
        pt  = piece.get_current_type()
        val = MATERIAL[pt] + _pst(pt, pos.row, pos.col, piece.color)
        if piece.color == color:
            score += val
        else:
            score -= val
    return score


# ---------------------------------------------------------------------------
# Move Ordering
# ---------------------------------------------------------------------------
_MAX_PLY = 64
_killers: List[List[Optional[Tuple[Position, Position]]]] = [
    [None, None] for _ in range(_MAX_PLY)
]
_history: Dict[Tuple[int, int, int, int], int] = {}


def _mvv_lva(board: Board, fp: Position, tp: Position) -> int:
    victim = board.grid.get(tp)
    if victim is None:
        return 0
    attacker = board.grid.get(fp)
    if attacker is None:
        return 0
    return MATERIAL[victim.get_current_type()] - MATERIAL[attacker.get_current_type()] // 10


def _order_moves(
    board: Board,
    moves: List[Tuple[Position, Position]],
    ply: int,
    tt_move: Optional[Tuple[Position, Position]],
) -> None:
    """Sort moves in-place (descending priority)."""
    k = _killers[ply] if ply < _MAX_PLY else [None, None]

    def score(m: Tuple[Position, Position]) -> int:
        if m == tt_move:
            return 1_000_000
        cap = _mvv_lva(board, m[0], m[1])
        if cap > 0:
            return 100_000 + cap
        if m == k[0]:
            return 9_000
        if m == k[1]:
            return 8_000
        key = (m[0].col, m[0].row, m[1].col, m[1].row)
        return _history.get(key, 0)

    moves.sort(key=score, reverse=True)


# ---------------------------------------------------------------------------
# Quiescence Search (captures only)
# ---------------------------------------------------------------------------
_Q_LIMIT = 3
_INF = 10_000_000


def quiescence(
    board: Board,
    alpha: int,
    beta: int,
    color: Color,
    validator: MoveValidator,
    qdepth: int = 0,
) -> int:
    stand_pat = evaluate(board, color)
    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat
    if qdepth >= _Q_LIMIT:
        return alpha

    opp = Color.BLACK if color == Color.RED else Color.RED
    moves = validator.get_legal_moves(board, color)
    captures = [(fp, tp) for fp, tp in moves if board.grid.get(tp) is not None]
    captures.sort(key=lambda m: _mvv_lva(board, m[0], m[1]), reverse=True)

    for fp, tp in captures:
        b2 = board.clone()
        p  = b2.get_piece_at(fp)
        b2.move_piece(fp, tp)
        if p and p.is_face_down:
            p.reveal()
        sc = -quiescence(b2, -beta, -alpha, opp, validator, qdepth + 1)
        if sc >= beta:
            return beta
        if sc > alpha:
            alpha = sc
    return alpha


# ---------------------------------------------------------------------------
# Alpha-Beta with TT / killers / history / null-move / LMR
# ---------------------------------------------------------------------------
_search_deadline: float = 0.0   # module-level deadline set before each ID call
_search_aborted: bool   = False  # set True when deadline exceeded


def alpha_beta(
    board: Board,
    depth: int,
    alpha: int,
    beta: int,
    color: Color,       # root maximizing color
    turn: Color,        # whose turn NOW
    validator: MoveValidator,
    ply: int,
    hkey: int,
    allow_null: bool = True,
) -> Tuple[int, Optional[Tuple[Position, Position]]]:
    global _search_aborted

    # Time check (every call at shallow nodes too)
    if ply % 4 == 0 and time.monotonic() >= _search_deadline:
        _search_aborted = True

    if _search_aborted:
        return evaluate(board, color), None

    orig_alpha = alpha
    opp = Color.BLACK if turn == Color.RED else Color.RED

    # TT probe
    hit, tt_sc, tt_move = _tt_probe(hkey, depth, alpha, beta)
    if hit:
        return tt_sc, tt_move

    # Terminal states
    if validator.is_checkmate(board, turn):
        sc = -(_INF - ply) if turn == color else (_INF - ply)
        return sc, None
    if validator.is_stalemate(board, turn):
        sc = -(_INF - ply) if turn == color else (_INF - ply)
        return sc, None

    # Leaf node → quiescence
    if depth == 0:
        sc = quiescence(board, alpha, beta, color, validator)
        _tt_store(hkey, 0, TT_EXACT, sc, None)
        return sc, None

    # Null-move pruning
    NULL_R = 2
    in_check = validator.is_in_check(board, turn)
    if (allow_null and not in_check and depth >= NULL_R + 1):
        piece_count = sum(
            1 for p in board.grid.values()
            if p.get_current_type() not in (PieceType.SOLDIER, PieceType.GENERAL)
        )
        if piece_count > 6:
            null_hash = hkey ^ ZOBRIST_TURN
            null_sc, _ = alpha_beta(
                board, depth - NULL_R - 1, -beta, -beta + 1,
                color, opp, validator, ply + 1, null_hash, allow_null=False
            )
            if -null_sc >= beta:
                return beta, None

    # Generate & order moves
    moves = validator.get_legal_moves(board, turn)
    if not moves:
        sc = -(_INF - ply) if turn == color else (_INF - ply)
        return sc, None

    _order_moves(board, moves, ply, tt_move)

    best_move: Optional[Tuple[Position, Position]] = None
    best_score = -_INF

    for idx, (fp, tp) in enumerate(moves):
        # Make move
        b2 = board.clone()
        piece = b2.get_piece_at(fp)
        captured = b2.move_piece(fp, tp)
        if piece and piece.is_face_down:
            piece.reveal()

        # Incremental hash update
        new_hkey = hkey ^ ZOBRIST_TURN
        if piece:
            ci = _COLOR_IDX[piece.color]
            pi = _PIECE_IDX[piece.get_current_type()]
            new_hkey ^= ZOBRIST[ci][pi][fp.row][fp.col]
            new_hkey ^= ZOBRIST[ci][pi][tp.row][tp.col]
        if captured:
            ci2 = _COLOR_IDX[captured.color]
            pi2 = _PIECE_IDX[captured.get_current_type()]
            new_hkey ^= ZOBRIST[ci2][pi2][tp.row][tp.col]

        # LMR
        reduction = 0
        if idx >= 4 and depth >= 3 and captured is None and not in_check:
            reduction = 1

        sc, _ = alpha_beta(
            b2, depth - 1 - reduction, -beta, -alpha,
            color, opp, validator, ply + 1, new_hkey
        )
        sc = -sc

        # Re-search at full depth if LMR raised alpha
        if reduction and sc > alpha:
            sc, _ = alpha_beta(
                b2, depth - 1, -beta, -alpha,
                color, opp, validator, ply + 1, new_hkey
            )
            sc = -sc

        if _search_aborted:
            break

        if sc > best_score:
            best_score = sc
            best_move  = (fp, tp)

        alpha = max(alpha, sc)
        if alpha >= beta:
            # Beta cut – update killers & history
            if captured is None and ply < _MAX_PLY:
                km = (fp, tp)
                kl = _killers[ply]
                if km != kl[0]:
                    kl[1] = kl[0]
                    kl[0] = km
                key = (fp.col, fp.row, tp.col, tp.row)
                _history[key] = _history.get(key, 0) + depth * depth
            break

    if not _search_aborted and best_move:
        flag = TT_EXACT
        if best_score <= orig_alpha:
            flag = TT_UPPER
        elif best_score >= beta:
            flag = TT_LOWER
        _tt_store(hkey, depth, flag, best_score, best_move)

    return best_score, best_move


# ---------------------------------------------------------------------------
# Iterative Deepening  (returns best move within time budget)
# ---------------------------------------------------------------------------
DIFFICULTY_PARAMS = {
    "easy":   {"max_depth": 2, "time_limit_ms":  800},
    "medium": {"max_depth": 5, "time_limit_ms": 2000},
    "hard":   {"max_depth": 7, "time_limit_ms": 5000},
}


def iterative_deepening(
    board: Board,
    color: Color,
    validator: MoveValidator,
    max_depth: int = 5,
    time_limit_ms: float = 2000,
) -> Optional[Tuple[Position, Position]]:
    global _killers, _history, _search_deadline, _search_aborted

    _killers = [[None, None] for _ in range(_MAX_PLY)]
    _history.clear()
    _search_deadline = time.monotonic() + time_limit_ms / 1000.0
    _search_aborted  = False

    hkey = _compute_hash(board, color == Color.RED)
    best_move: Optional[Tuple[Position, Position]] = None
    best_score = -_INF

    for depth in range(1, max_depth + 1):
        if time.monotonic() >= _search_deadline:
            break

        _search_aborted = False
        sc, mv = alpha_beta(board, depth, -_INF, _INF, color, color, validator, 0, hkey)

        if not _search_aborted and mv:
            best_move  = mv
            best_score = sc

        if best_score >= _INF - 100:
            break  # Forced mate found

    return best_move


def get_best_move(
    board: Board,
    color: Color,
    validator: MoveValidator,
    difficulty: str = "medium",
) -> Optional[Tuple[Position, Position]]:
    """
    Primary PvE entry point.
    Uses Pikafish if the binary is present; falls back to the custom engine.
    """
    # -- 1. Try Pikafish (strongest) -------------------------------------------
    try:
        from pikafish_engine import is_pikafish_available, get_pikafish_move
        if is_pikafish_available():
            move = get_pikafish_move(board, color, difficulty)
            if move is not None:
                return move
    except Exception as exc:
        print(f"[AI] Pikafish error ({exc}), falling back to custom engine.")

    # -- 2. Fallback: custom iterative-deepening engine -----------------------
    p = DIFFICULTY_PARAMS.get(difficulty, DIFFICULTY_PARAMS["medium"])
    return iterative_deepening(board, color, validator, p["max_depth"], p["time_limit_ms"])


# ---------------------------------------------------------------------------
# Legacy shim (backward compat)
# ---------------------------------------------------------------------------
def minimax(
    board: Board,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    color: Color,
    validator: MoveValidator,
) -> Tuple[float, Optional[Tuple[Position, Position]]]:
    d_map = {1: "easy", 2: "easy", 3: "medium"}
    move  = get_best_move(board, color, validator, d_map.get(depth, "medium"))
    return float(evaluate(board, color)), move


# ---------------------------------------------------------------------------
# Async wrapper for FastAPI / server.py
# ---------------------------------------------------------------------------
executor = ThreadPoolExecutor(max_workers=4)


async def get_best_move_async(
    board: Board,
    color: Color,
    depth: int,
    validator: MoveValidator,
) -> Optional[Tuple[Position, Position]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        executor, get_best_move, board, color, validator, "hard"
    )
