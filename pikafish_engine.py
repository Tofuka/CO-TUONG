import os
import queue
import subprocess
import sys
import threading
import time
from typing import Optional, Tuple

from models import Board, Color, PieceType, Position

# ---------------------------------------------------------------------------
# Engine binary discovery
# ---------------------------------------------------------------------------
_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINES_DIR = os.path.join(_DIR, "engines")

_CANDIDATES = [
    os.path.join(_ENGINES_DIR, "pikafish.exe"),      # Windows
    os.path.join(_ENGINES_DIR, "pikafish"),           # Linux / macOS
    os.path.join(_ENGINES_DIR, "Pikafish.exe"),       # capital variant
]


def _find_binary() -> Optional[str]:
    for path in _CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def is_pikafish_available() -> bool:
    """Returns True if the Pikafish binary exists in the engines/ folder."""
    return _find_binary() is not None


# ---------------------------------------------------------------------------
# Board -> Xiangqi FEN
# ---------------------------------------------------------------------------
_PT_CHAR = {
    PieceType.GENERAL:  "k",
    PieceType.ADVISOR:  "a",
    PieceType.ELEPHANT: "b",
    PieceType.HORSE:    "n",
    PieceType.CHARIOT:  "r",
    PieceType.CANNON:   "c",
    PieceType.SOLDIER:  "p",
}


def board_to_fen(board: Board, turn: Color) -> str:
    """
    Convert our Board to a Xiangqi FEN string accepted by Pikafish.

    FEN layout (standard Xiangqi):
        rank 0 (top)    = Black baseline = our row 9  (lowercase pieces)
        rank 9 (bottom) = Red   baseline = our row 0  (UPPERCASE pieces)

    IMPORTANT - Pikafish convention (opposite of chess!):
        'w' = Black to move  (plays the lowercase pieces at rank 0 side)
        'b' = Red   to move  (plays the UPPERCASE pieces at rank 9 side)

    Confirmed by direct UCI testing of the engine binary.
    """
    ranks = []
    for fen_rank in range(10):
        our_row = 9 - fen_rank   # rank 0 = our row 9 (Black home)
        empty = 0
        rank_str = ""
        for col in range(9):
            pos = Position(col, our_row)
            piece = board.grid.get(pos)
            if piece is None:
                empty += 1
            else:
                if empty:
                    rank_str += str(empty)
                    empty = 0
                ch = _PT_CHAR[piece.get_current_type()]
                if piece.color == Color.RED:
                    ch = ch.upper()   # Red = uppercase in FEN
                rank_str += ch
        if empty:
            rank_str += str(empty)
        ranks.append(rank_str)

    # Pikafish (like standard UCCI): 'w' = Red (White) to move, 'b' = Black to move
    side = "w" if turn == Color.RED else "b"
    return "/".join(ranks) + f" {side} - - 0 1"




# ---------------------------------------------------------------------------
# Move string <-> Position  conversion
# ---------------------------------------------------------------------------
def uci_to_positions(move: str) -> "Optional[Tuple[Position, Position]]":
    """
    Convert a Pikafish UCI move string (e.g. 'h9g7') to our (from_pos, to_pos).
    Pikafish rank 0 = top of board = our row 9 (Black baseline).
    Pikafish rank 9 = bottom       = our row 0 (Red  baseline).
    So: our_row = 9 - pikafish_rank  (same for both sides)
    """
    if len(move) < 4:
        return None
    try:
        fc = ord(move[0]) - ord("a")
        fr = int(move[1])
        tc = ord(move[2]) - ord("a")
        tr = int(move[3])
        return Position(fc, fr), Position(tc, tr)
    except (ValueError, IndexError):
        return None




def positions_to_uci(fp: "Position", tp: "Position") -> str:
    """Convert our positions to a UCI move string (for logging, Red view)."""
    return (
        chr(ord("a") + fp.col) + str(fp.row) +
        chr(ord("a") + tp.col) + str(tp.row)
    )


# ---------------------------------------------------------------------------
# Async line reader (non-blocking stdout consumption)
# ---------------------------------------------------------------------------
def _read_lines_async(proc: subprocess.Popen, out_queue: queue.Queue) -> None:
    """Daemon thread: reads stdout lines and puts them in a queue."""
    try:
        for line in proc.stdout:
            out_queue.put(line.rstrip())
    except Exception:
        pass
    finally:
        out_queue.put(None)   # sentinel – process ended


# ---------------------------------------------------------------------------
# PikafishEngine  (persistent process, thread-safe)
# ---------------------------------------------------------------------------
class PikafishEngine:
    """
    Manages a single persistent Pikafish subprocess.
    Thread-safe via _lock; the caller should never invoke from the GUI thread
    (use a background thread just as with the custom AI).
    """

    def __init__(self):
        self._proc:   Optional[subprocess.Popen] = None
        self._queue:  queue.Queue = queue.Queue()
        self._lock    = threading.Lock()
        self._ready   = False

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #
    def _send(self, cmd: str) -> None:
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.write(cmd + "\n")
                self._proc.stdin.flush()
            except OSError:
                pass

    def _wait_token(self, token: str, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is None:
                return False        # process died
            if token in line:
                return True
        return False

    def _drain(self) -> None:
        """Discard all buffered output."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #
    def start(self) -> bool:
        binary = _find_binary()
        if binary is None:
            return False
        try:
            self._proc = subprocess.Popen(
                [binary],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                cwd=_ENGINES_DIR,       # NNUE file must be in same dir
                creationflags=subprocess.CREATE_NO_WINDOW,  # Windows: suppress console popup
            )
        except (OSError, FileNotFoundError) as exc:
            print(f"[Pikafish] Cannot launch binary: {exc}")
            return False

        # Start async reader
        threading.Thread(
            target=_read_lines_async,
            args=(self._proc, self._queue),
            daemon=True,
        ).start()

        # UCI handshake
        self._send("uci")
        if not self._wait_token("uciok", timeout=8.0):
            print("[Pikafish] uciok not received – engine may be incompatible.")
            return False

        self._send("setoption name Threads value 2")
        self._send("setoption name Hash value 128")
        self._send("isready")
        if not self._wait_token("readyok", timeout=8.0):
            print("[Pikafish] readyok not received.")
            return False

        self._ready = True
        print("[Pikafish] Engine ready.")
        return True


    def stop(self) -> None:
        with self._lock:
            if self._proc:
                try:
                    self._send("quit")
                    self._proc.wait(timeout=3)
                except Exception:
                    self._proc.kill()
                finally:
                    self._proc = None
                    self._ready = False

    # ------------------------------------------------------------------ #
    #  Query                                                               #
    # ------------------------------------------------------------------ #
    def get_best_move(
        self,
        board: Board,
        turn: Color,
        difficulty: str = "medium",
    ) -> Optional[Tuple[Position, Position]]:
        """
        Ask Pikafish for the best move.
        Returns (from_pos, to_pos) in our coordinate system, or None on error.
        """
        movetime_ms = {"easy": 300, "medium": 1500, "hard": 4000}.get(difficulty, 1500)

        with self._lock:
            if not self._ready:
                if not self.start():
                    return None

            self._drain()

            fen = board_to_fen(board, turn)
            self._send(f"position fen {fen}")
            self._send(f"go movetime {movetime_ms}")

            timeout = movetime_ms / 1000.0 + 4.0
            deadline = time.monotonic() + timeout

            while time.monotonic() < deadline:
                try:
                    line = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if line is None:
                    print("[Pikafish] Process terminated unexpectedly.")
                    self._ready = False
                    return None

                if line.startswith("bestmove"):
                    parts = line.split()
                    move_str = parts[1] if len(parts) >= 2 else "(none)"
                    if move_str == "(none)":
                        return None
                    result = uci_to_positions(move_str)
                    if result:
                        fp, tp = result
                        print(f"[Pikafish] {move_str} -> {fp} -> {tp}")
                    return result


            print("[Pikafish] Timed out waiting for bestmove.")
            self._send("stop")
            return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_instance: Optional[PikafishEngine] = None
_instance_lock = threading.Lock()


def _get_instance() -> PikafishEngine:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = PikafishEngine()
    return _instance


def get_pikafish_move(
    board: Board,
    turn: Color,
    difficulty: str = "medium",
) -> Optional[Tuple[Position, Position]]:
    """
    Public API used by ai.py.
    Returns (from_pos, to_pos) or None if Pikafish is unavailable/fails.
    """
    return _get_instance().get_best_move(board, turn, difficulty)


def shutdown_pikafish() -> None:
    """Call this when the game exits to gracefully quit the engine process."""
    global _instance
    with _instance_lock:
        if _instance:
            _instance.stop()
            _instance = None
