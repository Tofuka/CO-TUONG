import asyncio
import json
import random
import string
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from models import Board, Piece, PieceType, Color, Position
from rules import MoveValidator
from ai import get_best_move_async

app = FastAPI(title="Xiangqi Multiplatform Server", version="1.0.0")

# Enable CORS for frontend client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Serializer Helpers
# ---------------------------------------------------------------------------

def serialize_board(board: Board) -> List[dict]:
    """Converts the board grid into a list of serialized pieces for the client.
    Note: real_type is hidden for face-down pieces to prevent cheating.
    """
    serialized = []
    for pos, piece in board.grid.items():
        serialized.append({
            "col": pos.col,
            "row": pos.row,
            "id": piece.id,
            "color": piece.color.value,
            "type": piece.get_current_type().value,
            "is_face_down": piece.is_face_down
        })
    return serialized

# ---------------------------------------------------------------------------
# Connection & Room Management
# ---------------------------------------------------------------------------

class RoomSession:
    def __init__(self, room_id: str, mode: str = "classic", vs_ai: bool = False, ai_color: Color = Color.BLACK, ai_difficulty: str = "medium"):
        self.room_id = room_id
        self.mode = mode
        
        self.board = Board()
        if mode == "co_up":
            self.board.setup_co_up()
        else:
            self.board.setup_classic()
            
        self.validator = MoveValidator()
        self.current_turn = Color.RED  # Red always starts first in Xiangqi
        
        # Player mapping: session_id -> Color
        self.players: Dict[Color, str] = {}
        self.spectators: List[str] = []
        self.move_history: List[dict] = []
        
        # Undo state: maps Color of requester to active status
        self.undo_request: Optional[Color] = None
        self.state = "waiting"  # "waiting", "playing", "finished"
        self.winner: Optional[Color] = None
        
        # PvE configuration
        self.vs_ai = vs_ai
        self.ai_color = ai_color
        self.ai_difficulty = ai_difficulty

    def serialize(self) -> dict:
        return {
            "room_id": self.room_id,
            "mode": self.mode,
            "board": serialize_board(self.board),
            "turn": self.current_turn.value,
            "players": {color.value: sid for color, sid in self.players.items()},
            "state": self.state,
            "winner": self.winner.value if self.winner else None,
            "undo_request": self.undo_request.value if self.undo_request else None,
            "vs_ai": self.vs_ai,
            "ai_color": self.ai_color.value,
            "ai_difficulty": self.ai_difficulty
        }

class ConnectionManager:
    def __init__(self):
        # Maps session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Maps session_id -> room_id
        self.user_rooms: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        # We retain user_rooms mappings so players can reconnect if needed

    async def send_json(self, session_id: str, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                # Connection might be dead, handled by socket listener disconnect
                pass

    async def broadcast_to_room(self, room: RoomSession, message: dict):
        # Gather all connected player and spectator session IDs
        recipients = list(room.players.values()) + room.spectators
        for sid in recipients:
            await self.send_json(sid, message)

manager = ConnectionManager()
rooms: Dict[str, RoomSession] = {}

# ---------------------------------------------------------------------------
# AI Execution Helper
# ---------------------------------------------------------------------------

async def trigger_ai_move(room: RoomSession):
    """Calculates and executes AI's move asynchronously."""
    if not room.vs_ai or room.state != "playing" or room.current_turn != room.ai_color:
        return
        
    depth = 2
    if room.ai_difficulty == "easy":
        depth = 1
    elif room.ai_difficulty == "hard":
        depth = 3
        
    # Get best move asynchronously (keeps the event loop completely non-blocking)
    best_move = await get_best_move_async(room.board, room.ai_color, depth, room.validator)
    
    if best_move:
        from_pos, to_pos = best_move
        # Execute the move on the board
        piece = room.board.get_piece_at(from_pos)
        captured = room.board.move_piece(from_pos, to_pos)
        was_revealed = False
        if piece is not None and piece.is_face_down:
            piece.reveal()
            was_revealed = True
            
        # Store in move history (supporting undo)
        room.move_history.append({
            "from": {"col": from_pos.col, "row": from_pos.row},
            "to": {"col": to_pos.col, "row": to_pos.row},
            "captured": captured.clone() if captured else None,
            "was_revealed": was_revealed,
            "was_face_down": was_revealed # tracks if it was dark before move
        })
        
        # Broadcast move
        await manager.broadcast_to_room(room, {
            "event": "move_made",
            "from": {"col": from_pos.col, "row": from_pos.row},
            "to": {"col": to_pos.col, "row": to_pos.row},
            "captured": captured.get_current_type().value if captured else None,
            "was_revealed": was_revealed
        })
        
        # Switch turn
        room.current_turn = Color.RED if room.ai_color == Color.BLACK else Color.BLACK
        
        # Evaluate checkmate or stalemate on the opponent
        opp_color = room.current_turn
        if room.validator.is_checkmate(room.board, opp_color):
            room.state = "finished"
            room.winner = room.ai_color
            await manager.broadcast_to_room(room, {
                "event": "game_over",
                "result": "checkmate",
                "winner": room.ai_color.value
            })
        elif room.validator.is_stalemate(room.board, opp_color):
            room.state = "finished"
            room.winner = room.ai_color
            await manager.broadcast_to_room(room, {
                "event": "game_over",
                "result": "stalemate",
                "winner": room.ai_color.value
            })
        elif room.validator.is_in_check(room.board, opp_color):
            await manager.broadcast_to_room(room, {
                "event": "check",
                "color": opp_color.value
            })
            
        # Broadcast final room state
        await manager.broadcast_to_room(room, {
            "event": "room_state",
            "room": room.serialize()
        })
    else:
        # AI has no moves (should be handled by stalemate, but fallback to resign)
        room.state = "finished"
        room.winner = Color.RED if room.ai_color == Color.BLACK else Color.BLACK
        await manager.broadcast_to_room(room, {
            "event": "game_over",
            "result": "resign",
            "winner": room.winner.value
        })

# ---------------------------------------------------------------------------
# WebSocket Handler
# ---------------------------------------------------------------------------

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    # Send initial success event to player
    await manager.send_json(session_id, {
        "event": "connected",
        "session_id": session_id
    })
    
    # Handle reconnects to an active room
    if session_id in manager.user_rooms:
        room_id = manager.user_rooms[session_id]
        if room_id in rooms:
            room = rooms[room_id]
            # Send the state of the active room immediately
            await manager.send_json(session_id, {
                "event": "room_state",
                "room": room.serialize()
            })
            
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")
            
            if action == "create_room":
                # Create a new room session
                room_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                mode = message.get("mode", "classic")
                vs_ai = message.get("vs_ai", False)
                ai_difficulty = message.get("ai_difficulty", "medium")
                
                room = RoomSession(
                    room_id=room_id,
                    mode=mode,
                    vs_ai=vs_ai,
                    ai_difficulty=ai_difficulty
                )
                
                # Creator joins as Red player
                room.players[Color.RED] = session_id
                manager.user_rooms[session_id] = room_id
                rooms[room_id] = room
                
                if vs_ai:
                    # AI takes Black player
                    room.players[Color.BLACK] = "AI"
                    room.state = "playing"
                    
                await manager.send_json(session_id, {
                    "event": "room_state",
                    "room": room.serialize()
                })
                
            elif action == "join_room":
                # Join an existing room
                room_id = message.get("room_id")
                if not room_id or room_id not in rooms:
                    await manager.send_json(session_id, {
                        "event": "error",
                        "message": "Room not found."
                    })
                    continue
                    
                room = rooms[room_id]
                manager.user_rooms[session_id] = room_id
                
                # Determine assignment
                if Color.RED not in room.players:
                    room.players[Color.RED] = session_id
                elif Color.BLACK not in room.players and not room.vs_ai:
                    room.players[Color.BLACK] = session_id
                    room.state = "playing"  # Game starts when both join
                else:
                    # Join as spectator if both spots filled
                    room.spectators.append(session_id)
                    
                await manager.broadcast_to_room(room, {
                    "event": "room_state",
                    "room": room.serialize()
                })
                
            elif action == "make_move":
                # Process move action
                room_id = manager.user_rooms.get(session_id)
                if not room_id or room_id not in rooms:
                    await manager.send_json(session_id, {"event": "error", "message": "No active room."})
                    continue
                    
                room = rooms[room_id]
                if room.state != "playing":
                    await manager.send_json(session_id, {"event": "error", "message": "Game has not started or has ended."})
                    continue
                    
                # Determine player color
                player_color = None
                for color, sid in room.players.items():
                    if sid == session_id:
                        player_color = color
                        break
                        
                if not player_color or room.current_turn != player_color:
                    await manager.send_json(session_id, {"event": "error", "message": "Not your turn."})
                    continue
                    
                from_data = message.get("from")
                to_data = message.get("to")
                if not from_data or not to_data:
                    await manager.send_json(session_id, {"event": "error", "message": "Invalid move format."})
                    continue
                    
                from_pos = Position(from_data.get("col"), from_data.get("row"))
                to_pos = Position(to_data.get("col"), to_data.get("row"))
                
                # Execute move with validation
                res = room.validator.make_move(room.board, from_pos, to_pos, player_color)
                if res is None:
                    await manager.send_json(session_id, {"event": "error", "message": "Illegal move."})
                    continue
                    
                captured, was_revealed = res
                
                # Record move history (for undo feature)
                room.move_history.append({
                    "from": {"col": from_pos.col, "row": from_pos.row},
                    "to": {"col": to_pos.col, "row": to_pos.row},
                    "captured": captured.clone() if captured else None,
                    "was_revealed": was_revealed,
                    "was_face_down": was_revealed # tracks if it was dark before move
                })
                
                # Broadcast move event
                await manager.broadcast_to_room(room, {
                    "event": "move_made",
                    "from": {"col": from_pos.col, "row": from_pos.row},
                    "to": {"col": to_pos.col, "row": to_pos.row},
                    "captured": captured.get_current_type().value if captured else None,
                    "was_revealed": was_revealed
                })
                
                # Switch turn
                room.current_turn = Color.BLACK if player_color == Color.RED else Color.RED
                
                # Check for win conditions
                opp_color = room.current_turn
                if room.validator.is_checkmate(room.board, opp_color):
                    room.state = "finished"
                    room.winner = player_color
                    await manager.broadcast_to_room(room, {
                        "event": "game_over",
                        "result": "checkmate",
                        "winner": player_color.value
                    })
                elif room.validator.is_stalemate(room.board, opp_color):
                    room.state = "finished"
                    room.winner = player_color
                    await manager.broadcast_to_room(room, {
                        "event": "game_over",
                        "result": "stalemate",
                        "winner": player_color.value
                    })
                elif room.validator.is_in_check(room.board, opp_color):
                    await manager.broadcast_to_room(room, {
                        "event": "check",
                        "color": opp_color.value
                    })
                    
                # Broadcast updated room state
                await manager.broadcast_to_room(room, {
                    "event": "room_state",
                    "room": room.serialize()
                })
                
                # If vs AI and AI's turn, trigger calculations
                if room.vs_ai and room.state == "playing" and room.current_turn == room.ai_color:
                    asyncio.create_task(trigger_ai_move(room))
                    
            elif action == "request_undo":
                # Request game undo (requires opponent consent in multiplayer PvP)
                room_id = manager.user_rooms.get(session_id)
                if not room_id or room_id not in rooms:
                    continue
                room = rooms[room_id]
                if room.state != "playing" or len(room.move_history) == 0:
                    continue
                    
                player_color = None
                for color, sid in room.players.items():
                    if sid == session_id:
                        player_color = color
                        break
                        
                if not player_color:
                    continue
                    
                if room.vs_ai:
                    # In PvE, Undo is immediately approved. Undo 2 moves (AI move and player's move)
                    steps = 2 if len(room.move_history) >= 2 else 1
                    for _ in range(steps):
                        last_move = room.move_history.pop()
                        frm = Position(last_move["from"]["col"], last_move["from"]["row"])
                        to = Position(last_move["to"]["col"], last_move["to"]["row"])
                        
                        # Revert the piece
                        moved_piece = room.board.remove_piece(to)
                        if moved_piece:
                            if last_move["was_face_down"]:
                                # Unreveal
                                moved_piece.is_face_down = True
                            room.board.add_piece(frm, moved_piece)
                            
                        # Put back captured piece
                        if last_move["captured"]:
                            room.board.add_piece(to, last_move["captured"])
                            
                    # Reset current turn to player's turn
                    room.current_turn = player_color
                    await manager.broadcast_to_room(room, {
                        "event": "undo_done",
                        "room": room.serialize()
                    })
                else:
                    # In PvP, ask for opponent's permission
                    room.undo_request = player_color
                    await manager.broadcast_to_room(room, {
                        "event": "undo_requested",
                        "by": player_color.value
                    })
                    
            elif action == "respond_undo":
                # Consent response for undo request
                room_id = manager.user_rooms.get(session_id)
                if not room_id or room_id not in rooms:
                    continue
                room = rooms[room_id]
                if not room.undo_request or room.state != "playing":
                    continue
                    
                player_color = None
                for color, sid in room.players.items():
                    if sid == session_id:
                        player_color = color
                        break
                        
                # Only the opponent of the requester can respond
                if not player_color or player_color == room.undo_request:
                    continue
                    
                accept = message.get("accept", False)
                if accept:
                    # Revert exactly 1 move (back to the turn of the requester)
                    last_move = room.move_history.pop()
                    frm = Position(last_move["from"]["col"], last_move["from"]["row"])
                    to = Position(last_move["to"]["col"], last_move["to"]["row"])
                    
                    moved_piece = room.board.remove_piece(to)
                    if moved_piece:
                        if last_move["was_face_down"]:
                            moved_piece.is_face_down = True
                        room.board.add_piece(frm, moved_piece)
                        
                    if last_move["captured"]:
                        room.board.add_piece(to, last_move["captured"])
                        
                    room.current_turn = room.undo_request
                    room.undo_request = None
                    
                    await manager.broadcast_to_room(room, {
                        "event": "undo_done",
                        "room": room.serialize()
                    })
                else:
                    room.undo_request = None
                    await manager.broadcast_to_room(room, {
                        "event": "undo_rejected"
                    })
                    
            elif action == "chat":
                # Real-time room chat
                room_id = manager.user_rooms.get(session_id)
                if room_id and room_id in rooms:
                    room = rooms[room_id]
                    msg_text = message.get("message", "")
                    
                    sender_name = "Red" if room.players.get(Color.RED) == session_id else ("Black" if room.players.get(Color.BLACK) == session_id else "Spectator")
                    
                    await manager.broadcast_to_room(room, {
                        "event": "chat",
                        "sender": sender_name,
                        "message": msg_text
                    })
                    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        # Locate player's room
        room_id = manager.user_rooms.get(session_id)
        if room_id and room_id in rooms:
            room = rooms[room_id]
            # If the room is still waiting, clean it up. Otherwise, players can reconnect.
            # Broadcast disconnect notice
            await manager.broadcast_to_room(room, {
                "event": "player_disconnected",
                "session_id": session_id
            })
