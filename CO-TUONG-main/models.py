import random
from enum import Enum
from typing import Dict, Optional, Tuple

class PieceType(Enum):
    GENERAL = "general"    # Tướng (帥 / 將)
    ADVISOR = "advisor"    # Sĩ (仕 / 士)
    ELEPHANT = "elephant"  # Tượng (相 / 象)
    HORSE = "horse"        # Mã (傌 / 馬)
    CHARIOT = "chariot"    # Xe (俥 / 車)
    CANNON = "cannon"      # Pháo (炮 / 砲)
    SOLDIER = "soldier"    # Tốt (兵 / 卒)

class Color(Enum):
    RED = "red"
    BLACK = "black"

class Position:
    """Represents a coordinate on a 9x10 Xiangqi board (columns 0 to 8, rows 0 to 9)."""
    __slots__ = ("col", "row")

    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Position):
            return NotImplemented
        return self.col == other.col and self.row == other.row

    def __hash__(self) -> int:
        return hash((self.col, self.row))

    def __repr__(self) -> str:
        return f"Position(col={self.col}, row={self.row})"

    def is_valid(self) -> bool:
        """Checks if the position is within board boundaries."""
        return 0 <= self.col <= 8 and 0 <= self.row <= 9

    def is_in_palace(self, color: Color) -> bool:
        """Checks if the position is inside the respective Palace (Cung)."""
        if not (3 <= self.col <= 5):
            return False
        if color == Color.RED:
            return 0 <= self.row <= 2
        else:
            return 7 <= self.row <= 9

    def is_across_river(self, color: Color) -> bool:
        """Checks if the position is across the river for a given color."""
        if color == Color.RED:
            return self.row >= 5
        else:
            return self.row <= 4

class Piece:
    """Represents a Xiangqi piece, with supports for Classic and Cờ Úp (Blind) mode."""
    def __init__(
        self,
        piece_id: str,
        color: Color,
        real_type: PieceType,
        is_face_down: bool = False,
        pseudo_type: Optional[PieceType] = None
    ):
        self.id = piece_id
        self.color = color
        self.real_type = real_type
        self.is_face_down = is_face_down
        # If pseudo_type is not provided, default to real_type (e.g. for classic mode)
        self.pseudo_type = pseudo_type if pseudo_type is not None else real_type

    def reveal(self) -> None:
        """Flips the piece face-up."""
        self.is_face_down = False

    def get_current_type(self) -> PieceType:
        """Returns the active movement type. If face-down, it behaves as pseudo_type."""
        return self.pseudo_type if self.is_face_down else self.real_type

    def clone(self) -> 'Piece':
        """Creates a deep copy of the piece for board simulations."""
        return Piece(
            piece_id=self.id,
            color=self.color,
            real_type=self.real_type,
            is_face_down=self.is_face_down,
            pseudo_type=self.pseudo_type
        )

    def __repr__(self) -> str:
        status = "down" if self.is_face_down else "up"
        return f"{self.color.value.upper()} {self.get_current_type().name} (Real: {self.real_type.name}, {status})"

# Standard starting positions mapping (col, row) to PieceType
# Red is rows 0-3, Black is rows 6-9
STARTING_POSITIONS: Dict[Tuple[int, int], PieceType] = {
    # Red Side
    (0, 0): PieceType.CHARIOT, (8, 0): PieceType.CHARIOT,
    (1, 0): PieceType.HORSE, (7, 0): PieceType.HORSE,
    (2, 0): PieceType.ELEPHANT, (6, 0): PieceType.ELEPHANT,
    (3, 0): PieceType.ADVISOR, (5, 0): PieceType.ADVISOR,
    (4, 0): PieceType.GENERAL,
    (1, 2): PieceType.CANNON, (7, 2): PieceType.CANNON,
    (0, 3): PieceType.SOLDIER, (2, 3): PieceType.SOLDIER, (4, 3): PieceType.SOLDIER, (6, 3): PieceType.SOLDIER, (8, 3): PieceType.SOLDIER,
    
    # Black Side
    (0, 9): PieceType.CHARIOT, (8, 9): PieceType.CHARIOT,
    (1, 9): PieceType.HORSE, (7, 9): PieceType.HORSE,
    (2, 9): PieceType.ELEPHANT, (6, 9): PieceType.ELEPHANT,
    (3, 9): PieceType.ADVISOR, (5, 9): PieceType.ADVISOR,
    (4, 9): PieceType.GENERAL,
    (1, 7): PieceType.CANNON, (7, 7): PieceType.CANNON,
    (0, 6): PieceType.SOLDIER, (2, 6): PieceType.SOLDIER, (4, 6): PieceType.SOLDIER, (6, 6): PieceType.SOLDIER, (8, 6): PieceType.SOLDIER,
}

class Board:
    """Represents the 9x10 grid and manages pieces."""
    def __init__(self):
        self.grid: Dict[Position, Piece] = {}
        self.is_co_up: bool = False

    def get_piece_at(self, pos: Position) -> Optional[Piece]:
        return self.grid.get(pos)

    def move_piece(self, from_pos: Position, to_pos: Position) -> Optional[Piece]:
        """Moves a piece from one position to another. Captures opponent piece if present.
        
        Returns the captured piece, or None if the destination was empty.
        """
        if from_pos not in self.grid:
            return None
        piece = self.grid.pop(from_pos)
        captured = self.grid.pop(to_pos, None)  # Remove captured piece from board
        self.grid[to_pos] = piece
        return captured

    def remove_piece(self, pos: Position) -> Optional[Piece]:
        """Removes a piece from the board at the given position."""
        return self.grid.pop(pos, None)

    def add_piece(self, pos: Position, piece: Piece) -> None:
        """Adds a piece to the board at the given position."""
        self.grid[pos] = piece

    def clone(self) -> 'Board':
        """Deep clones the board representation."""
        new_board = Board()
        new_board.is_co_up = self.is_co_up
        for pos, piece in self.grid.items():
            # Create a new position and clone the piece
            new_pos = Position(pos.col, pos.row)
            new_board.grid[new_pos] = piece.clone()
        return new_board

    def setup_classic(self) -> None:
        """Sets up the board for standard Xiangqi."""
        self.grid.clear()
        self.is_co_up = False
        for (col, row), piece_type in STARTING_POSITIONS.items():
            pos = Position(col, row)
            color = Color.RED if row <= 4 else Color.BLACK
            piece_id = f"{color.value}_{piece_type.value}_{col}_{row}"
            self.grid[pos] = Piece(
                piece_id=piece_id,
                color=color,
                real_type=piece_type,
                is_face_down=False
            )

    def setup_co_up(self) -> None:
        """Sets up the board for Cờ Úp (Blind/Mystery Xiangqi).
        
        Generals start face-up in their standard positions.
        All other 15 pieces of each color are shuffled and placed face-down
        in their standard starting positions, receiving their pseudo_type
        from their standard position.
        """
        self.grid.clear()
        self.is_co_up = True
        
        # Standard piece pool for one player, excluding GENERAL
        base_pool = [
            PieceType.CHARIOT, PieceType.CHARIOT,
            PieceType.HORSE, PieceType.HORSE,
            PieceType.ELEPHANT, PieceType.ELEPHANT,
            PieceType.ADVISOR, PieceType.ADVISOR,
            PieceType.CANNON, PieceType.CANNON,
            PieceType.SOLDIER, PieceType.SOLDIER, PieceType.SOLDIER, PieceType.SOLDIER, PieceType.SOLDIER
        ]
        
        red_pool = list(base_pool)
        random.shuffle(red_pool)
        
        black_pool = list(base_pool)
        random.shuffle(black_pool)
        
        red_idx = 0
        black_idx = 0
        
        for (col, row), pseudo_type in STARTING_POSITIONS.items():
            pos = Position(col, row)
            color = Color.RED if row <= 4 else Color.BLACK
            
            if pseudo_type == PieceType.GENERAL:
                # General is always face-up and standard
                piece_id = f"{color.value}_general_{col}_{row}"
                self.grid[pos] = Piece(
                    piece_id=piece_id,
                    color=color,
                    real_type=PieceType.GENERAL,
                    is_face_down=False,
                    pseudo_type=PieceType.GENERAL
                )
            else:
                if color == Color.RED:
                    real_type = red_pool[red_idx]
                    red_idx += 1
                else:
                    real_type = black_pool[black_idx]
                    black_idx += 1
                
                piece_id = f"{color.value}_dark_{col}_{row}"
                self.grid[pos] = Piece(
                    piece_id=piece_id,
                    color=color,
                    real_type=real_type,
                    is_face_down=True,
                    pseudo_type=pseudo_type
                )
