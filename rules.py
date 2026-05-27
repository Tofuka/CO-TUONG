from typing import List, Tuple, Optional
from models import PieceType, Color, Position, Piece, Board

class MoveValidator:
    """Handles movement validation, check, checkmate, stalemate, and special rules 
    for both Classic and Cờ Úp Xiangqi.
    """
    
    def is_valid_move(self, board: Board, from_pos: Position, to_pos: Position, current_player: Color) -> bool:
        """Validates if a move is fully legal, checking boundaries, piece movement rules, 
        obstacle clearance, and ensuring it does not result in self-check.
        """
        # 1. Boundaries and coordinate validity
        if not from_pos.is_valid() or not to_pos.is_valid():
            return False
            
        # 2. Cannot move to the same square
        if from_pos == to_pos:
            return False
            
        # 3. Source piece must exist and belong to the current player
        piece = board.get_piece_at(from_pos)
        if piece is None or piece.color != current_player:
            return False
            
        # 4. Destination cannot contain a friendly piece
        dest_piece = board.get_piece_at(to_pos)
        if dest_piece is not None and dest_piece.color == current_player:
            return False
            
        # 5. Check raw movement mechanics and obstacles
        if not self._validate_raw_move(board, piece, from_pos, to_pos):
            return False
            
        # 6. Check that the move does not leave/put the player's own General in check (self-check protection)
        board_clone = board.clone()
        # Simulate move
        board_clone.move_piece(from_pos, to_pos)
        # Flip the piece if it was face down on the simulated board to ensure accurate subsequent check verification
        sim_piece = board_clone.get_piece_at(to_pos)
        if sim_piece is not None and sim_piece.is_face_down:
            sim_piece.reveal()
            
        if self.is_in_check(board_clone, current_player):
            return False
            
        return True

    def make_move(self, board: Board, from_pos: Position, to_pos: Position, current_player: Color) -> Optional[Tuple[Optional[Piece], bool]]:
        """Validates and executes a move on the board.
        
        If the move is valid, executes it, reveals the piece if it was face-down,
        and returns a tuple: (captured_piece, was_revealed).
        If the move is invalid, returns None.
        """
        if not self.is_valid_move(board, from_pos, to_pos, current_player):
            return None
            
        piece = board.get_piece_at(from_pos)
        captured = board.move_piece(from_pos, to_pos)
        
        was_revealed = False
        if piece is not None and piece.is_face_down:
            piece.reveal()
            was_revealed = True
            
        return captured, was_revealed

    def _validate_raw_move(self, board: Board, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        """Determines if a move matches the piece's raw movement pattern and handles obstacle checks.
        Uses pseudo_type if the piece is face-down, and real_type if face-up.
        """
        piece_type = piece.get_current_type()
        
        if piece_type == PieceType.GENERAL:
            return self._validate_general(piece, from_pos, to_pos)
        elif piece_type == PieceType.ADVISOR:
            return self._validate_advisor(board, piece, from_pos, to_pos)
        elif piece_type == PieceType.ELEPHANT:
            return self._validate_elephant(board, piece, from_pos, to_pos)
        elif piece_type == PieceType.HORSE:
            return self._validate_horse(board, piece, from_pos, to_pos)
        elif piece_type == PieceType.CHARIOT:
            return self._validate_chariot(board, piece, from_pos, to_pos)
        elif piece_type == PieceType.CANNON:
            return self._validate_cannon(board, piece, from_pos, to_pos)
        elif piece_type == PieceType.SOLDIER:
            return self._validate_soldier(piece, from_pos, to_pos)
            
        return False

    def _validate_general(self, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        d_col = to_pos.col - from_pos.col
        d_row = to_pos.row - from_pos.row
        
        # General moves 1 step orthogonally
        if abs(d_col) + abs(d_row) != 1:
            return False
            
        # Must stay inside its own Palace
        return to_pos.is_in_palace(piece.color)

    def _validate_advisor(self, board: Board, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        d_col = to_pos.col - from_pos.col
        d_row = to_pos.row - from_pos.row
        
        # Advisor moves 1 step diagonally
        if abs(d_col) != 1 or abs(d_row) != 1:
            return False
            
        # Palace restriction:
        # In Classic mode OR if the piece is still face-down, it must stay in the Palace.
        is_co_up = getattr(board, "is_co_up", False)
        if not is_co_up or piece.is_face_down:
            return to_pos.is_in_palace(piece.color)
            
        # In Cờ Úp, once revealed, the Advisor is allowed to cross the river and leave the Palace.
        return True

    def _validate_elephant(self, board: Board, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        d_col = to_pos.col - from_pos.col
        d_row = to_pos.row - from_pos.row
        
        # Elephant moves exactly 2 steps diagonally
        if abs(d_col) != 2 or abs(d_row) != 2:
            return False
            
        # Check midpoint obstacle (cản mắt Tượng)
        mid_col = from_pos.col + d_col // 2
        mid_row = from_pos.row + d_row // 2
        if board.get_piece_at(Position(mid_col, mid_row)) is not None:
            return False
            
        # River restriction:
        # In Classic mode OR if the piece is still face-down, it cannot cross the river.
        is_co_up = getattr(board, "is_co_up", False)
        if not is_co_up or piece.is_face_down:
            if piece.color == Color.RED:
                return to_pos.row <= 4
            else:
                return to_pos.row >= 5
                
        # In Cờ Úp, once revealed, the Elephant is allowed to cross the river.
        return True

    def _validate_horse(self, board: Board, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        d_col = to_pos.col - from_pos.col
        d_row = to_pos.row - from_pos.row
        
        # Horse moves in an L-shape: (1 orthogonal, then 1 diagonal outwards)
        if abs(d_col) == 1 and abs(d_row) == 2:
            # Moving vertically. Obstacle is 1 step vertically from start (cản chân Mã)
            obs_pos = Position(from_pos.col, from_pos.row + (d_row // 2))
            return board.get_piece_at(obs_pos) is None
        elif abs(d_col) == 2 and abs(d_row) == 1:
            # Moving horizontally. Obstacle is 1 step horizontally from start (cản chân Mã)
            obs_pos = Position(from_pos.col + (d_col // 2), from_pos.row)
            return board.get_piece_at(obs_pos) is None
            
        return False

    def _validate_chariot(self, board: Board, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        d_col = to_pos.col - from_pos.col
        d_row = to_pos.row - from_pos.row
        
        # Chariot moves orthogonally
        if d_col != 0 and d_row != 0:
            return False
            
        # Path must be completely clear of obstacles
        if d_col != 0:
            step = 1 if d_col > 0 else -1
            for c in range(from_pos.col + step, to_pos.col, step):
                if board.get_piece_at(Position(c, from_pos.row)) is not None:
                    return False
        else:
            step = 1 if d_row > 0 else -1
            for r in range(from_pos.row + step, to_pos.row, step):
                if board.get_piece_at(Position(from_pos.col, r)) is not None:
                    return False
                    
        return True

    def _validate_cannon(self, board: Board, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        d_col = to_pos.col - from_pos.col
        d_row = to_pos.row - from_pos.row
        
        # Cannon moves orthogonally
        if d_col != 0 and d_row != 0:
            return False
            
        obstacles = self._count_obstacles_between(board, from_pos, to_pos)
        dest_piece = board.get_piece_at(to_pos)
        
        if dest_piece is None:
            # Non-capturing move: must have 0 obstacles in between
            return obstacles == 0
        else:
            # Capturing move: must have exactly 1 obstacle in between (the screen/ngòi)
            return obstacles == 1

    def _count_obstacles_between(self, board: Board, p1: Position, p2: Position) -> int:
        d_col = p2.col - p1.col
        d_row = p2.row - p1.row
        
        count = 0
        if d_col != 0:
            step = 1 if d_col > 0 else -1
            for c in range(p1.col + step, p2.col, step):
                if board.get_piece_at(Position(c, p1.row)) is not None:
                    count += 1
        else:
            step = 1 if d_row > 0 else -1
            for r in range(p1.row + step, p2.row, step):
                if board.get_piece_at(Position(p1.col, r)) is not None:
                    count += 1
        return count

    def _validate_soldier(self, piece: Piece, from_pos: Position, to_pos: Position) -> bool:
        d_col = to_pos.col - from_pos.col
        d_row = to_pos.row - from_pos.row
        
        # Soldier moves exactly 1 step orthogonally
        if abs(d_col) + abs(d_row) != 1:
            return False
            
        if piece.color == Color.RED:
            # Red Soldier can never move backwards
            if d_row < 0:
                return False
            # Before crossing river (row <= 4): can only move forward
            if from_pos.row <= 4:
                return d_row == 1 and d_col == 0
            # After crossing river (row >= 5): can move forward or sideways
            else:
                return (d_row == 1 and d_col == 0) or (d_row == 0 and abs(d_col) == 1)
        else:
            # Black Soldier can never move backwards
            if d_row > 0:
                return False
            # Before crossing river (row >= 5): can only move forward
            if from_pos.row >= 5:
                return d_row == -1 and d_col == 0
            # After crossing river (row <= 4): can move forward or sideways
            else:
                return (d_row == -1 and d_col == 0) or (d_row == 0 and abs(d_col) == 1)

    def _are_generals_facing(self, board: Board) -> bool:
        """Checks if the Red General and Black General are facing each other directly 
        in the same column without any intervening pieces.
        """
        red_pos = None
        black_pos = None
        for pos, piece in board.grid.items():
            if piece.get_current_type() == PieceType.GENERAL:
                if piece.color == Color.RED:
                    red_pos = pos
                else:
                    black_pos = pos
                    
        if red_pos is None or black_pos is None:
            return False
            
        if red_pos.col != black_pos.col:
            return False
            
        col = red_pos.col
        start_row = min(red_pos.row, black_pos.row) + 1
        end_row = max(red_pos.row, black_pos.row)
        
        for r in range(start_row, end_row):
            if board.get_piece_at(Position(col, r)) is not None:
                return False
                
        return True

    def is_in_check(self, board: Board, color: Color) -> bool:
        """Returns True if the General of the specified color is under threat 
        of being captured in the next turn, or if the Flying General rule is triggered.
        """
        general_pos = None
        for pos, piece in board.grid.items():
            if piece.color == color and piece.get_current_type() == PieceType.GENERAL:
                general_pos = pos
                break
                
        if general_pos is None:
            return False
            
        opp_color = Color.BLACK if color == Color.RED else Color.RED
        
        # Check if any opponent piece can capture the General
        for pos, piece in board.grid.items():
            if piece.color == opp_color:
                if self._validate_raw_move(board, piece, pos, general_pos):
                    return True
                    
        # Check if Generals face each other (Flying General rule)
        if self._are_generals_facing(board):
            return True
            
        return False

    def get_legal_moves(self, board: Board, color: Color) -> List[Tuple[Position, Position]]:
        """Returns a list of all legal moves for a given player color as (from_pos, to_pos)."""
        legal_moves = []
        
        # Collect all pieces of the given color
        friendly_pieces = [(pos, p) for pos, p in board.grid.items() if p.color == color]
        
        # Brute-force scan over the board
        for from_pos, piece in friendly_pieces:
            for c in range(9):
                for r in range(10):
                    to_pos = Position(c, r)
                    if self.is_valid_move(board, from_pos, to_pos, color):
                        legal_moves.append((from_pos, to_pos))
                        
        return legal_moves

    def is_checkmate(self, board: Board, color: Color) -> bool:
        """Returns True if the player of `color` is in check and has no legal moves."""
        return self.is_in_check(board, color) and len(self.get_legal_moves(board, color)) == 0

    def is_stalemate(self, board: Board, color: Color) -> bool:
        """Returns True if the player of `color` has no legal moves but is NOT currently in check.
        In standard Xiangqi, this results in a loss for the stalemated player.
        """
        return not self.is_in_check(board, color) and len(self.get_legal_moves(board, color)) == 0
