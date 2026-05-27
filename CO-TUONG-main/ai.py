import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple
from models import PieceType, Color, Position, Piece, Board
from rules import MoveValidator

# Material weights for heuristic evaluation
MATERIAL_VALUES: Dict[PieceType, float] = {
    PieceType.GENERAL: 100000.0,
    PieceType.CHARIOT: 900.0,
    PieceType.CANNON: 450.0,
    PieceType.HORSE: 400.0,
    PieceType.ELEPHANT: 200.0,
    PieceType.ADVISOR: 200.0,
    PieceType.SOLDIER: 100.0,
}

# Positional weights for pieces from RED's perspective (row 0 is baseline, row 9 is opponent's baseline)
# Columns 0 to 8, Rows 0 to 9
POSITION_BOARDS: Dict[PieceType, List[List[float]]] = {
    PieceType.SOLDIER: [
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 0 (Baseline)
        [0.0,  0.0,  0.0,  5.0,  5.0,  5.0,  0.0,  0.0,  0.0],  # Row 1
        [0.0,  0.0,  0.0, 10.0, 10.0, 10.0,  0.0,  0.0,  0.0],  # Row 2
        [2.0,  0.0,  5.0, 15.0, 20.0, 15.0,  5.0,  0.0,  2.0],  # Row 3
        [5.0,  5.0, 10.0, 20.0, 25.0, 20.0, 10.0,  5.0,  5.0],  # Row 4 (River bank)
        [10.0, 15.0, 25.0, 35.0, 40.0, 35.0, 25.0, 15.0, 10.0], # Row 5 (Crossed river)
        [20.0, 30.0, 45.0, 55.0, 60.0, 55.0, 45.0, 30.0, 20.0], # Row 6
        [30.0, 50.0, 70.0, 85.0, 90.0, 85.0, 70.0, 50.0, 30.0], # Row 7 (Palace entry)
        [40.0, 70.0, 90.0, 100.0, 110.0, 100.0, 90.0, 70.0, 40.0], # Row 8
        [10.0, 20.0, 30.0, 40.0, 40.0, 40.0, 30.0, 20.0, 10.0]  # Row 9 (Baseline)
    ],
    PieceType.HORSE: [
        [0.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0,  0.0],  # Row 0
        [-5.0,  5.0, 10.0, 10.0, 10.0, 10.0, 10.0,  5.0, -5.0],  # Row 1
        [-5.0, 10.0, 15.0, 20.0, 20.0, 20.0, 15.0, 10.0, -5.0],  # Row 2
        [-5.0, 10.0, 20.0, 25.0, 30.0, 25.0, 20.0, 10.0, -5.0],  # Row 3
        [-5.0, 15.0, 25.0, 30.0, 35.0, 30.0, 25.0, 15.0, -5.0],  # Row 4 (River)
        [-5.0, 20.0, 30.0, 35.0, 40.0, 35.0, 30.0, 20.0, -5.0],  # Row 5
        [-5.0, 25.0, 35.0, 40.0, 45.0, 40.0, 35.0, 25.0, -5.0],  # Row 6
        [-5.0, 20.0, 30.0, 35.0, 40.0, 35.0, 30.0, 20.0, -5.0],  # Row 7
        [-5.0, 10.0, 15.0, 20.0, 25.0, 20.0, 15.0, 10.0, -5.0],  # Row 8
        [0.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0,  0.0]   # Row 9
    ],
    PieceType.CHARIOT: [
        [0.0,  0.0,  0.0, 10.0, 20.0, 10.0,  0.0,  0.0,  0.0],  # Row 0
        [5.0, 15.0, 10.0, 20.0, 25.0, 20.0, 10.0, 15.0,  5.0],  # Row 1
        [0.0,  5.0,  5.0, 15.0, 20.0, 15.0,  5.0,  5.0,  0.0],  # Row 2
        [5.0, 10.0, 10.0, 20.0, 25.0, 20.0, 10.0, 10.0,  5.0],  # Row 3
        [10.0, 15.0, 15.0, 25.0, 30.0, 25.0, 15.0, 15.0, 10.0], # Row 4
        [15.0, 20.0, 20.0, 30.0, 35.0, 30.0, 20.0, 20.0, 15.0], # Row 5
        [20.0, 25.0, 25.0, 35.0, 40.0, 35.0, 25.0, 25.0, 20.0], # Row 6
        [25.0, 30.0, 30.0, 40.0, 45.0, 40.0, 30.0, 30.0, 25.0], # Row 7
        [30.0, 35.0, 35.0, 45.0, 50.0, 45.0, 35.0, 35.0, 30.0], # Row 8
        [0.0,  5.0,  5.0, 10.0, 20.0, 10.0,  5.0,  5.0,  0.0]   # Row 9
    ],
    PieceType.CANNON: [
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 0
        [5.0, 10.0,  5.0,  5.0, 10.0,  5.0,  5.0, 10.0,  5.0],  # Row 1
        [0.0,  5.0,  0.0,  0.0,  5.0,  0.0,  0.0,  5.0,  0.0],  # Row 2
        [5.0, 10.0,  5.0, 10.0, 15.0, 10.0,  5.0, 10.0,  5.0],  # Row 3
        [10.0, 15.0, 10.0, 15.0, 20.0, 15.0, 10.0, 15.0, 10.0], # Row 4
        [15.0, 20.0, 15.0, 20.0, 25.0, 20.0, 15.0, 20.0, 15.0], # Row 5
        [20.0, 25.0, 20.0, 25.0, 30.0, 25.0, 20.0, 25.0, 20.0], # Row 6
        [15.0, 20.0, 15.0, 20.0, 25.0, 20.0, 15.0, 20.0, 15.0], # Row 7
        [10.0, 15.0, 10.0, 15.0, 20.0, 15.0, 10.0, 15.0, 10.0], # Row 8
        [0.0,  5.0,  0.0,  5.0, 10.0,  5.0,  0.0,  5.0,  0.0]   # Row 9
    ],
    PieceType.ADVISOR: [
        [0.0,  0.0,  0.0,  5.0,  0.0,  5.0,  0.0,  0.0,  0.0],  # Row 0
        [0.0,  0.0,  0.0,  0.0, 10.0,  0.0,  0.0,  0.0,  0.0],  # Row 1
        [0.0,  0.0,  0.0,  5.0,  0.0,  5.0,  0.0,  0.0,  0.0],  # Row 2
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 3
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 4
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 5
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 6
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 7
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 8
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0]   # Row 9
    ],
    PieceType.ELEPHANT: [
        [0.0,  0.0,  5.0,  0.0,  0.0,  0.0,  5.0,  0.0,  0.0],  # Row 0
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 1
        [5.0,  0.0,  0.0,  0.0, 10.0,  0.0,  0.0,  0.0,  5.0],  # Row 2
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 3
        [0.0,  0.0,  5.0,  0.0,  0.0,  0.0,  5.0,  0.0,  0.0],  # Row 4
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 5
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 6
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 7
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],  # Row 8
        [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0]   # Row 9
    ]
}

def evaluate_board(board: Board, color: Color) -> float:
    """Evaluates the board from the perspective of the specified color.
    
    Score = (Friendly Material + Friendly Positional) - (Enemy Material + Enemy Positional)
    """
    score = 0.0
    for pos, piece in board.grid.items():
        piece_type = piece.get_current_type()
        val = MATERIAL_VALUES.get(piece_type, 0.0)
        
        pos_val = 0.0
        if piece_type in POSITION_BOARDS:
            col, row = pos.col, pos.row
            # Flip coordinates vertically (and horizontally) for Black pieces
            if piece.color == Color.BLACK:
                row = 9 - row
                col = 8 - col
            pos_val = POSITION_BOARDS[piece_type][row][col]
            
        total_val = val + pos_val
        
        if piece.color == color:
            score += total_val
        else:
            score -= total_val
            
    return score

def minimax(
    board: Board,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    color: Color,
    validator: MoveValidator
) -> Tuple[float, Optional[Tuple[Position, Position]]]:
    """Calculates the best move using Minimax with Alpha-Beta pruning."""
    opp_color = Color.BLACK if color == Color.RED else Color.RED
    
    # 1. Terminal Node Check (Checkmate / Stalemate)
    if validator.is_checkmate(board, color):
        # Current player is checkmated (loses). Prefer longer paths when losing.
        return -1000000.0 + (5 - depth), None
    if validator.is_checkmate(board, opp_color):
        # Opponent is checkmated (wins). Prefer shorter paths when winning.
        return 1000000.0 - (5 - depth), None
        
    if validator.is_stalemate(board, color):
        # Stalemate is a loss in Xiangqi
        return -1000000.0 + (5 - depth), None
    if validator.is_stalemate(board, opp_color):
        return 1000000.0 - (5 - depth), None
        
    # 2. Maximum depth reached
    if depth == 0:
        return evaluate_board(board, color), None
        
    active_color = color if maximizing else opp_color
    moves = validator.get_legal_moves(board, active_color)
    
    # Stalemate fallback
    if not moves:
        return (-1000000.0 + (5 - depth) if maximizing else 1000000.0 - (5 - depth)), None
        
    # 3. Move Ordering: evaluate captures first for efficient pruning
    def move_priority(move: Tuple[Position, Position]) -> float:
        from_pos, to_pos = move
        dest_piece = board.grid.get(to_pos)
        if dest_piece is not None:
            # MVV-LVA (Most Valuable Victim - Least Valuable Assailant) heuristic
            victim_val = MATERIAL_VALUES.get(dest_piece.get_current_type(), 0.0)
            attacker_val = MATERIAL_VALUES.get(board.grid[from_pos].get_current_type(), 0.0)
            return victim_val - (attacker_val / 100.0)
        return -999999.0
        
    moves.sort(key=move_priority, reverse=True)
    
    best_move = None
    if maximizing:
        max_eval = -float('inf')
        for move in moves:
            from_pos, to_pos = move
            
            # Simulate move
            board_clone = board.clone()
            piece = board_clone.get_piece_at(from_pos)
            board_clone.move_piece(from_pos, to_pos)
            if piece is not None and piece.is_face_down:
                piece.reveal()
                
            eval_score, _ = minimax(board_clone, depth - 1, alpha, beta, False, color, validator)
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
                
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Beta cutoff
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in moves:
            from_pos, to_pos = move
            
            # Simulate move
            board_clone = board.clone()
            piece = board_clone.get_piece_at(from_pos)
            board_clone.move_piece(from_pos, to_pos)
            if piece is not None and piece.is_face_down:
                piece.reveal()
                
            eval_score, _ = minimax(board_clone, depth - 1, alpha, beta, True, color, validator)
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
                
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha cutoff
        return min_eval, best_move

# Thread pool for asynchronous execution of CPU-bound minimax operations
executor = ThreadPoolExecutor(max_workers=4)

async def get_best_move_async(
    board: Board,
    color: Color,
    depth: int,
    validator: MoveValidator
) -> Optional[Tuple[Position, Position]]:
    """Runs the Minimax calculation in a separate thread pool to keep the 
    FastAPI event loop completely non-blocking.
    """
    loop = asyncio.get_running_loop()
    _, best_move = await loop.run_in_executor(
        executor,
        minimax,
        board,
        depth,
        -float('inf'),
        float('inf'),
        True,
        color,
        validator
    )
    return best_move
