import unittest
from models import PieceType, Color, Position, Piece, Board
from rules import MoveValidator

class TestXiangqiEngine(unittest.TestCase):
    def setUp(self):
        self.board = Board()
        self.validator = MoveValidator()

    def test_classic_setup(self):
        self.board.setup_classic()
        # Verify piece counts
        self.assertEqual(len(self.board.grid), 32)
        
        # Verify Generals are at standard spots
        red_gen = self.board.get_piece_at(Position(4, 0))
        self.assertIsNotNone(red_gen)
        self.assertEqual(red_gen.real_type, PieceType.GENERAL)
        self.assertEqual(red_gen.color, Color.RED)
        
        black_gen = self.board.get_piece_at(Position(4, 9))
        self.assertIsNotNone(black_gen)
        self.assertEqual(black_gen.real_type, PieceType.GENERAL)
        self.assertEqual(black_gen.color, Color.BLACK)

    def test_soldier_movement(self):
        # Red Soldier at (0, 3)
        self.board.setup_classic()
        sol_pos = Position(0, 3)
        piece = self.board.get_piece_at(sol_pos)
        self.assertEqual(piece.get_current_type(), PieceType.SOLDIER)
        
        # Before river: can only move forward 1 step
        self.assertTrue(self.validator.is_valid_move(self.board, sol_pos, Position(0, 4), Color.RED))
        self.assertFalse(self.validator.is_valid_move(self.board, sol_pos, Position(1, 3), Color.RED)) # No sideways
        self.assertFalse(self.validator.is_valid_move(self.board, sol_pos, Position(0, 2), Color.RED)) # No backward
        
        # Move soldier across the river manually
        self.board.remove_piece(sol_pos)
        crossed_pos = Position(0, 5)
        self.board.add_piece(crossed_pos, piece)
        
        # After river: can move forward or sideways 1 step
        self.assertTrue(self.validator.is_valid_move(self.board, crossed_pos, Position(0, 6), Color.RED))
        self.assertTrue(self.validator.is_valid_move(self.board, crossed_pos, Position(1, 5), Color.RED))
        self.assertFalse(self.validator.is_valid_move(self.board, crossed_pos, Position(0, 4), Color.RED)) # No backward

    def test_horse_obstacle(self):
        # Place a Horse at (4, 4)
        horse = Piece("red_horse", Color.RED, PieceType.HORSE)
        self.board.add_piece(Position(4, 4), horse)
        
        # Generals
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        
        # Permanent blocker in column 4 (e.g. at row 3) to prevent Flying General violations when horse moves
        self.board.add_piece(Position(4, 3), Piece("permanent_blocker", Color.RED, PieceType.SOLDIER))

        # Check raw moves: L-shape moves from (4, 4)
        # Destinations: (5, 6), (3, 6), (6, 5), (6, 3), (5, 2), (3, 2), (2, 3), (2, 5)
        self.assertTrue(self.validator.is_valid_move(self.board, Position(4, 4), Position(5, 6), Color.RED))
        
        # Block vertical step upwards: place a piece at (4, 5)
        blocker = Piece("blocker", Color.BLACK, PieceType.SOLDIER)
        self.board.add_piece(Position(4, 5), blocker)
        # Moves to (5, 6) and (3, 6) should now be blocked
        self.assertFalse(self.validator.is_valid_move(self.board, Position(4, 4), Position(5, 6), Color.RED))
        self.assertFalse(self.validator.is_valid_move(self.board, Position(4, 4), Position(3, 6), Color.RED))
        
        # Moves to horizontal directions should still be free
        self.assertTrue(self.validator.is_valid_move(self.board, Position(4, 4), Position(6, 5), Color.RED))

    def test_elephant_obstacle_and_river(self):
        # Elephant at (2, 0)
        elephant = Piece("red_elephant", Color.RED, PieceType.ELEPHANT)
        self.board.add_piece(Position(2, 0), elephant)
        
        # Add Generals
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        
        # Permanent blocker in column 4 (e.g. row 5) to prevent Flying General violations
        self.board.add_piece(Position(4, 5), Piece("permanent_blocker", Color.RED, PieceType.SOLDIER))

        # Move to (4, 2) is valid
        self.assertTrue(self.validator.is_valid_move(self.board, Position(2, 0), Position(4, 2), Color.RED))
        
        # Add midpoint blocker at (3, 1)
        blocker = Piece("blocker", Color.BLACK, PieceType.SOLDIER)
        self.board.add_piece(Position(3, 1), blocker)
        # Now blocked
        self.assertFalse(self.validator.is_valid_move(self.board, Position(2, 0), Position(4, 2), Color.RED))
        
        # Clear blocker, move Elephant to (4, 2)
        self.board.remove_piece(Position(3, 1))
        self.board.remove_piece(Position(2, 0))
        self.board.add_piece(Position(4, 2), elephant)
        
        # Try to cross river to (6, 4) -> should be valid (still on Red side: row 4)
        self.assertTrue(self.validator.is_valid_move(self.board, Position(4, 2), Position(6, 4), Color.RED))
        
        # Try to cross river to (2, 6) -> invalid in Classic mode
        self.board.remove_piece(Position(4, 2))
        self.board.add_piece(Position(2, 4), elephant)
        self.assertFalse(self.validator.is_valid_move(self.board, Position(2, 4), Position(0, 6), Color.RED))

    def test_advisor_palace(self):
        advisor = Piece("red_advisor", Color.RED, PieceType.ADVISOR)
        self.board.add_piece(Position(3, 0), advisor)
        
        # Generals
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        
        # Permanent blocker in column 4 (e.g. row 5)
        self.board.add_piece(Position(4, 5), Piece("permanent_blocker", Color.RED, PieceType.SOLDIER))

        # Move to (4, 1) in palace is valid
        self.assertTrue(self.validator.is_valid_move(self.board, Position(3, 0), Position(4, 1), Color.RED))
        
        # Manually move advisor to (4, 1)
        self.board.remove_piece(Position(3, 0))
        self.board.add_piece(Position(4, 1), advisor)
        
        # Try to move out of palace to (3, 2) -> valid (since (3, 2) is in palace)
        self.assertTrue(self.validator.is_valid_move(self.board, Position(4, 1), Position(3, 2), Color.RED))
        
        # Try to move out of palace to (5, 2) -> valid (since (5, 2) is in palace)
        # What if advisor is placed at (3, 2) and tries to go to (2, 3)?
        self.board.remove_piece(Position(4, 1))
        self.board.add_piece(Position(3, 2), advisor)
        self.assertFalse(self.validator.is_valid_move(self.board, Position(3, 2), Position(2, 3), Color.RED)) # (2, 3) is outside palace!

    def test_chariot_and_cannon(self):
        chariot = Piece("red_chariot", Color.RED, PieceType.CHARIOT)
        cannon = Piece("red_cannon", Color.RED, PieceType.CANNON)
        
        self.board.add_piece(Position(0, 0), chariot)
        self.board.add_piece(Position(0, 2), cannon)
        
        # Generals
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        
        # Permanent blocker in column 4 (e.g. row 5)
        self.board.add_piece(Position(4, 5), Piece("permanent_blocker", Color.RED, PieceType.SOLDIER))

        # Chariot moves horizontally to (3, 0)
        self.assertTrue(self.validator.is_valid_move(self.board, Position(0, 0), Position(3, 0), Color.RED))
        
        # Chariot tries to move vertically to (0, 3) but Cannon is at (0, 2)
        self.assertFalse(self.validator.is_valid_move(self.board, Position(0, 0), Position(0, 3), Color.RED))

        # Cannon tries to move to (0, 5) (no capture): blocked by nothing since (0, 3), (0, 4) are empty
        self.assertTrue(self.validator.is_valid_move(self.board, Position(0, 2), Position(0, 5), Color.RED))
        
        # Cannon capture test: place black piece at (0, 5)
        enemy = Piece("black_enemy", Color.BLACK, PieceType.SOLDIER)
        self.board.add_piece(Position(0, 5), enemy)
        
        # Currently Cannon is at (0, 2). Cannon capturing Enemy (0, 5):
        # Obstacles between (0, 2) and (0, 5) is 0 currently.
        # So Cannon cannot capture Enemy (0, 5) because 0 obstacles.
        self.assertFalse(self.validator.is_valid_move(self.board, Position(0, 2), Position(0, 5), Color.RED))
        
        # Add a friendly piece at (0, 3) as the "screen"
        screen = Piece("red_screen", Color.RED, PieceType.SOLDIER)
        self.board.add_piece(Position(0, 3), screen)
        # Now there is exactly 1 obstacle at (0, 3). Cannon should be able to capture at (0, 5)
        self.assertTrue(self.validator.is_valid_move(self.board, Position(0, 2), Position(0, 5), Color.RED))
        
        # If there are 2 obstacles: add another blocker at (0, 4)
        blocker2 = Piece("blocker2", Color.RED, PieceType.SOLDIER)
        self.board.add_piece(Position(0, 4), blocker2)
        # Cannot capture anymore (2 obstacles)
        self.assertFalse(self.validator.is_valid_move(self.board, Position(0, 2), Position(0, 5), Color.RED))

    def test_flying_general_rule(self):
        # Set up a board with just two Generals
        red_gen = Piece("red_gen", Color.RED, PieceType.GENERAL)
        black_gen = Piece("black_gen", Color.BLACK, PieceType.GENERAL)
        
        self.board.add_piece(Position(4, 0), red_gen)
        self.board.add_piece(Position(4, 9), black_gen)
        
        # Since they are facing each other in same column (4) with no pieces in between:
        # Red is in check, Black is in check
        self.assertTrue(self.validator.is_in_check(self.board, Color.RED))
        self.assertTrue(self.validator.is_in_check(self.board, Color.BLACK))
        
        # Place a piece in between at (4, 4)
        blocker = Piece("blocker", Color.RED, PieceType.SOLDIER)
        self.board.add_piece(Position(4, 4), blocker)
        
        # Now they are not facing each other directly
        self.assertFalse(self.validator.is_in_check(self.board, Color.RED))
        self.assertFalse(self.validator.is_in_check(self.board, Color.BLACK))
        
        # Try to move blocker away to (3, 4)
        # This move should be invalid for Red because it will result in the Generals facing each other (self-check)
        self.assertFalse(self.validator.is_valid_move(self.board, Position(4, 4), Position(3, 4), Color.RED))

    def test_checkmate_and_stalemate(self):
        # Set up a checkmate situation
        # Red General at (4, 0)
        # Black Chariots at (3, 0) and (5, 0)
        # Red Soldier at (4, 1) and Black Soldier at (4, 2) blocks the General from moving forward or the Soldier from moving.
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        self.board.add_piece(Position(4, 1), Piece("red_s1", Color.RED, PieceType.SOLDIER))
        self.board.add_piece(Position(4, 2), Piece("black_s2", Color.BLACK, PieceType.SOLDIER))
        
        self.board.add_piece(Position(3, 0), Piece("black_chariot1", Color.BLACK, PieceType.CHARIOT))
        self.board.add_piece(Position(5, 0), Piece("black_chariot2", Color.BLACK, PieceType.CHARIOT))
        
        # Red is in check
        self.assertTrue(self.validator.is_in_check(self.board, Color.RED))
        # Red legal moves should be empty
        self.assertEqual(len(self.validator.get_legal_moves(self.board, Color.RED)), 0)
        # Checkmate!
        self.assertTrue(self.validator.is_checkmate(self.board, Color.RED))
        
        # Stalemate test:
        self.board.grid.clear()
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        # Blocker for Flying General
        self.board.add_piece(Position(4, 5), Piece("blocker", Color.BLACK, PieceType.SOLDIER))
        
        # Rigid self-blockage web:
        self.board.add_piece(Position(3, 0), Piece("red_s1", Color.RED, PieceType.ADVISOR))
        self.board.add_piece(Position(5, 0), Piece("red_s2", Color.RED, PieceType.ADVISOR))
        self.board.add_piece(Position(4, 1), Piece("red_s3", Color.RED, PieceType.SOLDIER))
        self.board.add_piece(Position(4, 2), Piece("red_s4", Color.RED, PieceType.ADVISOR))
        self.board.add_piece(Position(3, 1), Piece("red_s5", Color.RED, PieceType.SOLDIER))
        self.board.add_piece(Position(5, 1), Piece("red_s6", Color.RED, PieceType.SOLDIER))
        self.board.add_piece(Position(3, 2), Piece("red_s7", Color.RED, PieceType.ADVISOR))
        self.board.add_piece(Position(5, 2), Piece("red_s8", Color.RED, PieceType.ADVISOR))
        
        # General and all friendly pieces are blocked with zero moves, and no check is active.
        self.assertFalse(self.validator.is_in_check(self.board, Color.RED))
        self.assertEqual(len(self.validator.get_legal_moves(self.board, Color.RED)), 0)
        self.assertTrue(self.validator.is_stalemate(self.board, Color.RED))

    def test_co_up_mode_logic(self):
        # Set up a Cờ Úp game
        self.board.setup_co_up()
        self.assertTrue(self.board.is_co_up)
        
        # Verify General is face-up, others are face-down
        red_gen = self.board.get_piece_at(Position(4, 0))
        self.assertIsNotNone(red_gen)
        self.assertFalse(red_gen.is_face_down)
        
        red_piece_at_horse = self.board.get_piece_at(Position(1, 0))
        self.assertIsNotNone(red_piece_at_horse)
        self.assertTrue(red_piece_at_horse.is_face_down)
        self.assertEqual(red_piece_at_horse.pseudo_type, PieceType.HORSE)
        
        # Check first move of a dark piece: should follow pseudo_type
        # Piece at (1,0) behaves as Horse, so it can move to (2, 2) or (0, 2) (provided there's no obstacle at (1, 1))
        # Let's execute the move via make_move
        res = self.validator.make_move(self.board, Position(1, 0), Position(2, 2), Color.RED)
        self.assertIsNotNone(res)
        
        # After move, the piece should be at (2, 2) and must be REVEALED (is_face_down = False)
        moved_piece = self.board.get_piece_at(Position(2, 2))
        self.assertIsNotNone(moved_piece)
        self.assertFalse(moved_piece.is_face_down)
        
        # From now on, its type is real_type
        self.assertEqual(moved_piece.get_current_type(), moved_piece.real_type)

    def test_co_up_revealed_advisor_elephant_river_crossing(self):
        self.board.is_co_up = True
        
        # Generals
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        # Permanent blocker in column 4
        self.board.add_piece(Position(4, 5), Piece("permanent_blocker", Color.RED, PieceType.SOLDIER))

        # 1. Revealed Advisor (Sĩ) can leave Palace and cross River
        advisor = Piece("red_advisor", Color.RED, PieceType.ADVISOR, is_face_down=False) # already revealed
        self.board.add_piece(Position(3, 2), advisor)
        
        # In Classic or face-down, Advisor moving from (3,2) to (2,3) is invalid (out of palace)
        # But here, as a revealed Cờ Úp Advisor, it should be VALID!
        self.assertTrue(self.validator.is_valid_move(self.board, Position(3, 2), Position(2, 3), Color.RED))
        
        # Move it to (2, 3), then try to move to (3, 4) -> (4, 5) is blocked by permanent blocker, so move to (1, 2) or (1, 4) or similar.
        # Let's place it at (3, 4) and verify it can move diagonally to (2, 5) which crosses the river!
        self.board.remove_piece(Position(3, 2))
        self.board.add_piece(Position(3, 4), advisor)
        self.assertTrue(self.validator.is_valid_move(self.board, Position(3, 4), Position(2, 5), Color.RED)) # crosses river!
        
        # 2. Revealed Elephant (Tượng) can cross River
        elephant = Piece("red_elephant", Color.RED, PieceType.ELEPHANT, is_face_down=False) # revealed
        self.board.remove_piece(Position(3, 4))
        self.board.add_piece(Position(2, 4), elephant)
        
        # Try to cross river from (2,4) to (0,6) -> should be valid since it's revealed in Cờ Úp!
        self.assertTrue(self.validator.is_valid_move(self.board, Position(2, 4), Position(0, 6), Color.RED))

if __name__ == "__main__":
    unittest.main()
