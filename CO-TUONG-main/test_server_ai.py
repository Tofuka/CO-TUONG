import asyncio
import json
import unittest
from fastapi.testclient import TestClient
from models import Board, Piece, PieceType, Color, Position
from rules import MoveValidator
from ai import get_best_move_async, evaluate_board, minimax
from server import app

class TestAIAndServer(unittest.TestCase):
    def setUp(self):
        self.board = Board()
        self.validator = MoveValidator()

    def test_ai_evaluation_balance(self):
        # Fresh board should have exactly equal material and positional balance (0.0)
        self.board.setup_classic()
        red_score = evaluate_board(self.board, Color.RED)
        black_score = evaluate_board(self.board, Color.BLACK)
        
        # Red score relative to Red and Black score relative to Black should be identical
        self.assertEqual(red_score, black_score)
        self.assertEqual(red_score, 0.0)

    def test_ai_mate_in_one(self):
        # Construct a mate-in-one scenario for Black
        # Black Chariot at (4, 1) and Red General at (4, 0).
        # Red General has friendly blockers at (3,0) and (5,0), but (4,1) is occupied by the attacking Black Chariot.
        # Wait, if Black Chariot is at (4,1), it is directly checking the Red General at (4,0) and the General cannot escape or capture it!
        # If Black to move, Black Chariot is already at (4, 1), checking. So Red is already mated or in check.
        # Let's set up a move where Black can deliver immediate checkmate:
        # Black Chariot at (3, 5). Red General at (4, 0) with advisors at (3, 0) and (5, 0).
        # Red Palace has friendly blocker at (4, 1) to prevent general moving forward.
        # Black Chariot at (3, 5) can move to (3, 0) to checkmate?
        # If Black Chariot moves to (3, 0):
        # It lands adjacent to the Red General, but General is at (4, 0).
        # Chariot at (3, 0) can capture the Advisor at (3, 0). From (3, 0), it attacks (4, 0) horizontally.
        # General cannot capture the Chariot at (3, 0) because it is protected by, say, a Black Horse?
        # Actually, simpler:
        # Let's set up a scenario where Black has a Chariot at (4, 5).
        # Column 4 is empty between row 0 and row 5 except the Chariot.
        # Red General at (4, 0).
        # Red General's escape squares are: (3, 0) and (5, 0) which are blocked by friendly Advisors,
        # and (4, 1) which is currently empty!
        # If Black moves Chariot from (4, 5) to (4, 0) -> this captures Red General (checkmate/mate-in-1!).
        # Let's verify that Minimax at depth 1 or 2 finds the capture (winning move)!
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        self.board.add_piece(Position(3, 0), Piece("red_s1", Color.RED, PieceType.ADVISOR))
        self.board.add_piece(Position(5, 0), Piece("red_s2", Color.RED, PieceType.ADVISOR))
        
        # Black Chariot at (4, 5)
        black_chariot = Piece("black_chariot", Color.BLACK, PieceType.CHARIOT)
        self.board.add_piece(Position(4, 5), black_chariot)
        
        # Black to move: best move should be (4, 5) -> (4, 0) to capture General
        _, best_move = minimax(self.board, 2, -float('inf'), float('inf'), True, Color.BLACK, self.validator)
        
        self.assertIsNotNone(best_move)
        frm, to = best_move
        self.assertEqual(frm, Position(4, 5))
        self.assertEqual(to, Position(4, 0))

    def test_ai_escapes_check(self):
        # Red General at (4, 0) under check by Black Chariot at (4, 5)
        # General is the only Red piece, so any legal move must start from (4, 0).
        self.board.add_piece(Position(4, 0), Piece("red_gen", Color.RED, PieceType.GENERAL))
        self.board.add_piece(Position(4, 9), Piece("black_gen", Color.BLACK, PieceType.GENERAL))
        
        # Black Chariot checking at (4, 5)
        self.board.add_piece(Position(4, 5), Piece("black_chariot", Color.BLACK, PieceType.CHARIOT))
        
        # Red is currently in check
        self.assertTrue(self.validator.is_in_check(self.board, Color.RED))
        
        # Red to move: best move must be the General escaping to one of the empty squares: (3, 0), (5, 0), or (4, 1)
        _, best_move = minimax(self.board, 2, -float('inf'), float('inf'), True, Color.RED, self.validator)
        
        self.assertIsNotNone(best_move)
        frm, to = best_move
        self.assertEqual(frm, Position(4, 0))
        self.assertIn(to, [Position(3, 0), Position(5, 0), Position(4, 1)])

    def test_websocket_server_multiplayer(self):
        # Test client connections and room transitions
        client1 = TestClient(app)
        client2 = TestClient(app)
        
        with client1.websocket_connect("/ws/player1") as ws1:
            # 1. Connect and receive confirmation
            data = ws1.receive_json()
            self.assertEqual(data["event"], "connected")
            self.assertEqual(data["session_id"], "player1")
            
            # 2. Create room
            ws1.send_json({"action": "create_room", "mode": "classic", "vs_ai": False})
            room_data = ws1.receive_json()
            self.assertEqual(room_data["event"], "room_state")
            room_state = room_data["room"]
            room_id = room_state["room_id"]
            self.assertEqual(room_state["mode"], "classic")
            self.assertEqual(room_state["state"], "waiting")
            self.assertEqual(room_state["players"]["red"], "player1")
            
            # 3. Join room as Player 2
            with client2.websocket_connect("/ws/player2") as ws2:
                # Player 2 connection confirmation
                data2 = ws2.receive_json()
                self.assertEqual(data2["event"], "connected")
                
                # Join existing room
                ws2.send_json({"action": "join_room", "room_id": room_id})
                
                # Player 2 receives updated room_state
                state_p2 = ws2.receive_json()
                self.assertEqual(state_p2["event"], "room_state")
                self.assertEqual(state_p2["room"]["state"], "playing")
                self.assertEqual(state_p2["room"]["players"]["black"], "player2")
                
                # Player 1 receives updated room_state as well (via broadcast)
                state_p1 = ws1.receive_json()
                self.assertEqual(state_p1["event"], "room_state")
                self.assertEqual(state_p1["room"]["state"], "playing")
                
                # 4. Make a valid move: Red Soldier at (0, 3) to (0, 4)
                ws1.send_json({
                    "action": "make_move",
                    "from": {"col": 0, "row": 3},
                    "to": {"col": 0, "row": 4}
                })
                
                # Verify move event is broadcast to both players
                move_p1 = ws1.receive_json()
                self.assertEqual(move_p1["event"], "move_made")
                self.assertEqual(move_p1["from"], {"col": 0, "row": 3})
                self.assertEqual(move_p1["to"], {"col": 0, "row": 4})
                self.assertIsNone(move_p1["captured"])
                
                # Player 2 receives move too
                move_p2 = ws2.receive_json()
                self.assertEqual(move_p2["event"], "move_made")
                
                # Recipient states are broadcast
                room_state_p1 = ws1.receive_json()
                self.assertEqual(room_state_p1["event"], "room_state")
                self.assertEqual(room_state_p1["room"]["turn"], "black") # turn shifts to Black

if __name__ == "__main__":
    unittest.main()
