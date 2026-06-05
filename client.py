import math
import array
import json
import queue
import random
import string
import threading
import time
from typing import Dict, List, Optional, Tuple
import pygame
from models import Board, Piece, PieceType, Color, Position
from rules import MoveValidator

# Initialize Pygame and Mixer
pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass  # Fallback if audio system is unavailable

# ---------------------------------------------------------------------------
# Global Styling Constants
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 750

# Colors (HSL-based premium palette converted to RGB)
COLOR_BACKGROUND = (35, 30, 25)       # Rich dark obsidian
COLOR_WOOD_DARK = (139, 90, 43)       # Cherry/Mahogany wood
COLOR_WOOD_LIGHT = (205, 133, 63)     # Sandalwood/Bamboo wood
COLOR_BOARD_LINE = (50, 40, 30)       # Deep charcoal for sharp lines
COLOR_TEXT_LIGHT = (230, 220, 210)    # Soft parchment white
COLOR_TEXT_MUTED = (140, 130, 120)    # Muted slate grey
COLOR_RED_PIECE = (180, 40, 40)       # Crimson Red
COLOR_BLACK_PIECE = (40, 80, 60)      # Emerald/Dark Jade Green
COLOR_GOLD = (212, 175, 55)           # Golden Accent
COLOR_SEL_GLOW = (240, 200, 80)       # Selected Piece Aura
COLOR_CHECK_GLOW = (255, 50, 50)      # Danger Check warning

# Dimensions
BOARD_LEFT = 50
BOARD_TOP = 50
GRID_CELL_SIZE = 64
PIECE_RADIUS = 26

# Character mappings (Calligraphy representations)
CHARACTERS = {
    "red": {
        "general": "帥", "advisor": "仕", "elephant": "相",
        "horse": "傌", "chariot": "俥", "cannon": "炮", "soldier": "兵"
    },
    "black": {
        "general": "將", "advisor": "士", "elephant": "象",
        "horse": "馬", "chariot": "車", "cannon": "砲", "soldier": "卒"
    }
}

# ---------------------------------------------------------------------------
# Bilingual Text Dictionary
# ---------------------------------------------------------------------------
LANG = {
    "vi": {
        # Menu
        "title":            "CỜ TƯỚNG & CỜ ÚP",
        "btn_pve":          "[*]  ĐẤU VỚI MÁY  (PvE)",
        "btn_pvp":          "[~]  ĐẤU MẠNG  (PvP)",
        "btn_rules":        "[?]  HƯỚNG DẪN CHƠI",
        "btn_exit":         "[X]  THOÁT GAME",
        # Rules page
        "rules_title":      "HƯỚNG DẪN LUẬT CHƠI",
        "rules_back":       "QUAY LẠI MENU CHÍNH",
        "rules_lines": [
            "1. CỜ TƯỚNG TRUYỀN THỐNG:",
            "   - Xe: Đi và ăn ngang dọc không giới hạn khoảng cách, miễn là không bị chắn.",
            "   - Pháo: Đi ngang dọc; khi ăn quân bắt buộc phải nhảy qua đúng 1 quân cản.",
            "   - Mã: Di chuyển hình chữ L (tiến 1 chéo 1). Bị cản chân nếu có quân liền kề.",
            "   - Tượng: Đi chéo 2 ô; bị cản mắt nếu có quân ở giữa. Không được qua sông.",
            "   - Sĩ: Đi chéo 1 ô bên trong phạm vi Cung (Cung rộng 3x3 ô ở đáy).",
            "   - Tướng: Đi ngang hoặc dọc 1 ô bên trong phạm vi Cung.",
            "   - Tốt: Đi thẳng 1 ô. Sau khi qua sông được đi thẳng hoặc ngang 1 ô.",
            "   - Lộ Mặt Tướng: Hai Tướng không được đối mặt trực tiếp trên cùng một cột.",
            "",
            "2. CHẾ ĐỘ CHƠI CỜ ÚP (MYSTERY CHESS):",
            "   - Chỉ có Tướng đặt ngửa. 15 quân còn lại bị úp mặt, xáo trộn ngẫu nhiên.",
            "   - Nước đầu tiên của quân úp theo luật vị trí giả định đang đứng.",
            "   - Sau nước đầu tiên, quân úp lật ngửa lộ danh tính thật.",
            "   - Từ nước thứ hai trở đi, di chuyển theo luật thật của chính nó.",
            "   - Luật đặc biệt: Sĩ và Tượng Cờ Úp sau khi ngửa ĐƯỢC PHÉP QUA SÔNG!"
        ],
        # Sidebar
        "sidebar_title":    "CỜ TƯỚNG & CỜ ÚP",
        "btn_menu":         "MENU",
        "btn_vs_ai":        "Đấu với Máy",
        "btn_online":       "Đấu Mạng",
        "label_mode":       "Chế Độ:",
        "btn_classic":      "Truyền Thống",
        "btn_co_up":        "Cờ Úp",
        "label_diff":       "Độ Khó:",
        "btn_connect":      "[>>]  KẾT NỐI SERVER",
        "placeholder_room": "MÃ PHÒNG",
        "btn_create_room":  "TẠO PHÒNG",
        "btn_join_room":    "VÀO PHÒNG THEO MÃ CODE",
        "label_chat":       "Kênh Trò Chuyện:",
        "placeholder_chat": "NHẬP TIN NHẮN...",
        "btn_undo":         "<<  QUAY LẠI",
        "btn_reset":        "[o]  ĐẦU HÀNG / RESET",
        # Game over
        "win_title":        "*** THẮNG ***",
        "lose_title":       "--- THUA ---",
        "win_label":        "BẠN ĐÃ THẮNG!",
        "lose_label":       "BẠN ĐÃ THUA!",
        "win_sub":          "{color} đã chiếu hết!",
        "lose_sub":         "{color} đã bị chiếu hết!",
        "rematch_btn":      ">> ĐẤU LẠI <<",
        "color_red":        "ĐỎ",
        "color_black":      "ĐEN",
        # Status messages
        "status_ready":     "Sẵn sàng! (Bạn: ĐỎ)",
        "status_offline":   "Server ngoại tuyến. Kết nối để bắt đầu.",
        "status_ai_think":  "Máy đang suy nghĩ...",
        "status_your_turn": "Lượt của bạn.",
        "status_illegal":   "Nước đi không hợp lệ.",
        "status_new_match": "Ván mới bắt đầu! (Bạn: ĐỎ)",
        "status_undo":      "Đã hoàn tác.",
        "status_reset":     "Đã đặt lại ván cờ.",
        "status_check_b":   "CẢNH BÁO: TƯỚNG ĐEN bị chiếu!",
        "status_check_r":   "CẢNH BÁO: TƯỚNG ĐỎ bị chiếu!",
        "status_mate_r":    "Chiếu hết! ĐỎ thắng!",
        "status_mate_b":    "Chiếu hết! MÁY thắng!",
    },
    "en": {
        # Menu
        "title":            "XIANGQI & MYSTERY CHESS",
        "btn_pve":          "[*]  PLAY VS AI  (PvE)",
        "btn_pvp":          "[~]  PLAY ONLINE  (PvP)",
        "btn_rules":        "[?]  HOW TO PLAY",
        "btn_exit":         "[X]  EXIT GAME",
        # Rules page
        "rules_title":      "GAME RULES",
        "rules_back":       "BACK TO MAIN MENU",
        "rules_lines": [
            "1. CLASSIC XIANGQI:",
            "   - Chariot (Rook): Moves any number of squares horizontally or vertically.",
            "   - Cannon: Moves like Chariot; captures by jumping over exactly 1 piece.",
            "   - Horse: Moves in an L-shape (1 ortho + 1 diagonal). Blocked by adjacent piece.",
            "   - Elephant: Moves 2 squares diagonally; blocked if middle square is occupied.",
            "   - Advisor: Moves 1 square diagonally inside the palace (3x3 area).",
            "   - General (King): Moves 1 square orthogonally inside the palace.",
            "   - Soldier (Pawn): Moves 1 square forward; after river can also move sideways.",
            "   - Flying General: Two Generals cannot face each other on same file with no piece between.",
            "",
            "2. MYSTERY CHESS (CO UP) MODE:",
            "   - Only the General is placed face-up. The other 15 pieces are shuffled face-down.",
            "   - First move of a face-down piece follows the rule of its assumed position.",
            "   - After the first move the piece is flipped face-up revealing its true identity.",
            "   - From the second move onward, the piece follows its own real movement rules.",
            "   - Special rule: Advisor & Elephant in Co Up mode may cross the river once revealed!"
        ],
        # Sidebar
        "sidebar_title":    "XIANGQI & MYSTERY CHESS",
        "btn_menu":         "MENU",
        "btn_vs_ai":        "VS Computer",
        "btn_online":       "Online PvP",
        "label_mode":       "Mode:",
        "btn_classic":      "Classic",
        "btn_co_up":        "Mystery",
        "label_diff":       "Difficulty:",
        "btn_connect":      "[>>]  CONNECT TO SERVER",
        "placeholder_room": "ROOM CODE",
        "btn_create_room":  "CREATE ROOM",
        "btn_join_room":    "JOIN ROOM BY CODE",
        "label_chat":       "Chat Channel:",
        "placeholder_chat": "TYPE A MESSAGE...",
        "btn_undo":         "<<  UNDO",
        "btn_reset":        "[o]  RESIGN / RESET",
        # Game over
        "win_title":        "*** YOU WIN ***",
        "lose_title":       "--- YOU LOSE ---",
        "win_label":        "YOU WON!",
        "lose_label":       "YOU LOST!",
        "win_sub":          "{color} has been checkmated!",
        "lose_sub":         "{color} has been checkmated!",
        "rematch_btn":      ">> REMATCH <<",
        "color_red":        "RED",
        "color_black":      "BLACK",
        # Status messages
        "status_ready":     "Game Ready! (You: RED)",
        "status_offline":   "Server offline. Connect to start.",
        "status_ai_think":  "AI is thinking...",
        "status_your_turn": "Your turn.",
        "status_illegal":   "Illegal move.",
        "status_new_match": "New match started! (You: RED)",
        "status_undo":      "Undo complete.",
        "status_reset":     "Game reset.",
        "status_check_b":   "WARNING: BLACK General is in check!",
        "status_check_r":   "WARNING: RED General is in check!",
        "status_mate_r":    "Checkmate! RED wins!",
        "status_mate_b":    "Checkmate! AI wins!",
    }
}

# ---------------------------------------------------------------------------
# Native Procedural Sound Synthesis
# ---------------------------------------------------------------------------

def play_sound(freq: float, duration_ms: float, volume: float = 0.5):
    """Synthesizes a clean sine wave with exponential decay programmatically.
    Creates a warm, skeuomorphic wooden block click.
    """
    try:
        sample_rate = 44100
        n_samples = int(sample_rate * (duration_ms / 1000.0))
        # 16-bit signed integer buffer
        buf = array.array('h', [0] * n_samples)
        
        for i in range(n_samples):
            t = i / sample_rate
            # Exponential pluck decay
            decay = math.exp(-8 * t)
            val = math.sin(2 * math.pi * freq * t) * decay * volume
            buf[i] = int(val * 32767)
            
        sound = pygame.mixer.Sound(buffer=buf)
        sound.play()
    except Exception:
        pass  # Fail silently if mixer fails

# ---------------------------------------------------------------------------
# Thread-safe WebSocket Background Thread
# ---------------------------------------------------------------------------

class WebSocketClientThread(threading.Thread):
    def __init__(self, session_id: str, server_url: str):
        super().__init__()
        self.session_id = session_id
        self.server_url = server_url
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()
        self.running = True
        self.daemon = True

    def run(self):
        # We import here to keep the main thread load fast
        import websocket # type: ignore
        ws_url = f"{self.server_url}/ws/{self.session_id}"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.receive_queue.put(data)
            except Exception:
                pass
                
        def on_error(ws, error):
            pass
            
        def on_close(ws, close_status_code, close_msg):
            self.receive_queue.put({"event": "disconnected"})
            
        def on_open(ws):
            # Start a sender thread
            def sender():
                while self.running:
                    try:
                        msg = self.send_queue.get(timeout=1.0)
                        ws.send(json.dumps(msg))
                    except queue.Empty:
                        continue
                    except Exception:
                        break
            threading.Thread(target=sender, daemon=True).start()

        # Connect synchronously in this background thread
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()

# ---------------------------------------------------------------------------
# Graphics Drawing & Animations
# ---------------------------------------------------------------------------

class GraphicsEngine:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen

        # --- Menu / UI fonts: ưu tiên Segoe UI, Arial... (hỗ trợ tốt tiếng Việt) ---
        self.font_menu_title = self.get_menu_font(52)   # Tiêu đề to trên màn menu
        self.font_title      = self.get_menu_font(24)
        self.font_medium     = self.get_menu_font(19)
        self.font_ui         = self.get_menu_font(15)

        # --- Piece / Calligraphy fonts: ưu tiên font CJK (chữ Hán trên quân cờ) ---
        self.font_calligraphy      = self.get_piece_font(36)
        self.font_calligraphy_dark = self.get_piece_font(34)
        self.font_river            = self.get_piece_font(27)  # "漢楚爭雄" trên sông
        
        # Cache for procedural wood background
        self.wood_surface = None
        self.wood_rect = None

    # ------------------------------------------------------------------
    # Font loader: Menu / UI  (Vietnamese-first, broad Unicode)
    # ------------------------------------------------------------------
    def get_menu_font(self, size: int) -> pygame.font.Font:
        """Loads a font optimised for Vietnamese + Latin text (menu, labels, status bar)."""
        import os

        # Priority 1 – direct Windows font file paths
        win_paths = [
            r"C:\Windows\Fonts\segoeui.ttf",   # Segoe UI – best Vietnamese coverage
            r"C:\Windows\Fonts\segoeuib.ttf",  # Segoe UI Bold
            r"C:\Windows\Fonts\arial.ttf",     # Arial
            r"C:\Windows\Fonts\tahoma.ttf",    # Tahoma
            r"C:\Windows\Fonts\verdana.ttf",   # Verdana
            r"C:\Windows\Fonts\calibri.ttf",   # Calibri
            r"C:\Windows\Fonts\msjh.ttc",      # MS JhengHei (also good for Viet)
            r"C:\Windows\Fonts\msyh.ttc",      # MS YaHei
        ]
        for path in win_paths:
            if os.path.isfile(path):
                try:
                    return pygame.font.Font(path, size)
                except Exception:
                    continue

        # Priority 2 – SysFont lookup
        candidates = [
            "segoeuivariable", "segoeui", "arial", "tahoma", "verdana", "calibri",
            "dejavusans", "liberationsans", "freesans",
            "microsoftyahei", "msjhenghei",
        ]
        try:
            available = set(f.lower() for f in pygame.font.get_fonts())
            for name in candidates:
                if name.lower() in available:
                    return pygame.font.SysFont(name, size)
        except Exception:
            pass

        return pygame.font.Font(None, size)  # ultimate fallback

    # ------------------------------------------------------------------
    # Font loader: Piece / Calligraphy  (CJK-first, for Chinese characters)
    # ------------------------------------------------------------------
    def get_piece_font(self, size: int) -> pygame.font.Font:
        """Loads a font optimised for CJK (Chinese) characters on chess pieces."""
        import os

        # Priority 1 – direct Windows CJK font file paths
        # Ordered: best CJK coverage first, then broad-Unicode fallbacks
        win_paths = [
            r"C:\Windows\Fonts\msyh.ttc",       # Microsoft YaHei – excellent CJK
            r"C:\Windows\Fonts\msjh.ttc",       # Microsoft JhengHei – Traditional CJK
            r"C:\Windows\Fonts\simsun.ttc",     # SimSun – classic Song typeface
            r"C:\Windows\Fonts\simhei.ttf",     # SimHei – bold CJK
            r"C:\Windows\Fonts\mingliu.ttc",    # MingLiU – Traditional CJK
            r"C:\Windows\Fonts\kaiu.ttf",       # KaiTi / KaiU – calligraphy style
            r"C:\Windows\Fonts\STKAITI.TTF",    # STKaiTi – brushstroke calligraphy
            r"C:\Windows\Fonts\STFANGSO.TTF",   # STFangsong – elegant serif CJK
            r"C:\Windows\Fonts\STXINGKA.TTF",   # STXingKai – seal-script style
            r"C:\Windows\Fonts\segoeui.ttf",    # Segoe UI (fallback)
            r"C:\Windows\Fonts\arial.ttf",      # Arial (last resort)
        ]
        for path in win_paths:
            if os.path.isfile(path):
                try:
                    return pygame.font.Font(path, size)
                except Exception:
                    continue

        # Priority 2 – SysFont lookup (CJK-first)
        candidates = [
            "microsoftyahei", "microsoftyaheiui",
            "msjhenghei", "msjhengheiui",
            "simsun", "simhei", "nsimsun",
            "notoserifcjktc", "notoserifcjksc",
            "notosanscjksc", "notosanscjktc",
            "mingliu", "pmingliuextb",
            # broad-Unicode fallbacks
            "segoeui", "arial", "dejavusans",
        ]
        try:
            available = set(f.lower() for f in pygame.font.get_fonts())
            for name in candidates:
                if name.lower() in available:
                    return pygame.font.SysFont(name, size)
        except Exception:
            pass

        return pygame.font.Font(None, size)  # ultimate fallback

    # kept for backward compatibility (used by river labels)
    def get_chinese_font(self, size: int) -> pygame.font.Font:
        """Alias → get_piece_font (backward compat)."""
        return self.get_piece_font(size)

    def draw_wood_background(self, rect: pygame.Rect):
        """Generates a procedural, premium wood grain texture dynamically."""
        if self.wood_surface is None or self.wood_rect != rect:
            self.wood_surface = pygame.Surface((rect.width, rect.height))
            self.wood_rect = rect
            
            # Base wood color fill
            pygame.draw.rect(self.wood_surface, COLOR_WOOD_DARK, self.wood_surface.get_rect())
            
            # Procedural vertical grain fibers
            state = random.getstate()
            random.seed(42)  # Maintain stable grain texture
            
            for x in range(0, rect.width, 3):
                # Draw subtle vertical lines of varying brown shades
                shade = random.randint(-15, 15)
                r = max(0, min(255, COLOR_WOOD_DARK[0] + shade))
                g = max(0, min(255, COLOR_WOOD_DARK[1] + shade - 5))
                b = max(0, min(255, COLOR_WOOD_DARK[2] + shade - 10))
                
                # Subtle vertical alpha line
                pygame.draw.line(self.wood_surface, (r, g, b), (x, 0), (x, rect.height), 1)
                
            # Draw soft bevel / inner frame
            pygame.draw.rect(self.wood_surface, COLOR_BOARD_LINE, self.wood_surface.get_rect(), 4)
            random.setstate(state)
            
        self.screen.blit(self.wood_surface, (rect.left, rect.top))

    def draw_board(self, board_rect: pygame.Rect):
        """Draws a premium wooden Xiangqi board layout."""
        self.draw_wood_background(board_rect)
        
        # Grid lines (columns 0 to 8, rows 0 to 9)
        # Vertical columns
        for c in range(9):
            x = BOARD_LEFT + c * GRID_CELL_SIZE
            # Draw split lines (sông/river interrupts vertical lines)
            y_start_red = BOARD_TOP
            y_end_red = BOARD_TOP + 4 * GRID_CELL_SIZE
            y_start_black = BOARD_TOP + 5 * GRID_CELL_SIZE
            y_end_black = BOARD_TOP + 9 * GRID_CELL_SIZE
            
            # Leftmost and rightmost columns run all the way down
            if c == 0 or c == 8:
                pygame.draw.line(self.screen, COLOR_BOARD_LINE, (x, BOARD_TOP), (x, BOARD_TOP + 9 * GRID_CELL_SIZE), 2)
            else:
                pygame.draw.line(self.screen, COLOR_BOARD_LINE, (x, y_start_red), (x, y_end_red), 1)
                pygame.draw.line(self.screen, COLOR_BOARD_LINE, (x, y_start_black), (x, y_end_black), 1)
                
        # Horizontal rows
        for r in range(10):
            y = BOARD_TOP + r * GRID_CELL_SIZE
            pygame.draw.line(self.screen, COLOR_BOARD_LINE, (BOARD_LEFT, y), (BOARD_LEFT + 8 * GRID_CELL_SIZE, y), 1 if r not in (0, 9) else 2)
            
        # Draw Palaces (Cung) diagonals
        # Red Palace (Columns 3-5, Rows 0-2)
        p1_r = (BOARD_LEFT + 3 * GRID_CELL_SIZE, BOARD_TOP)
        p2_r = (BOARD_LEFT + 5 * GRID_CELL_SIZE, BOARD_TOP + 2 * GRID_CELL_SIZE)
        pygame.draw.line(self.screen, COLOR_BOARD_LINE, p1_r, p2_r, 1)
        
        p3_r = (BOARD_LEFT + 5 * GRID_CELL_SIZE, BOARD_TOP)
        p4_r = (BOARD_LEFT + 3 * GRID_CELL_SIZE, BOARD_TOP + 2 * GRID_CELL_SIZE)
        pygame.draw.line(self.screen, COLOR_BOARD_LINE, p3_r, p4_r, 1)
        
        # Black Palace (Columns 3-5, Rows 7-9)
        p1_b = (BOARD_LEFT + 3 * GRID_CELL_SIZE, BOARD_TOP + 7 * GRID_CELL_SIZE)
        p2_b = (BOARD_LEFT + 5 * GRID_CELL_SIZE, BOARD_TOP + 9 * GRID_CELL_SIZE)
        pygame.draw.line(self.screen, COLOR_BOARD_LINE, p1_b, p2_b, 1)
        
        p3_b = (BOARD_LEFT + 5 * GRID_CELL_SIZE, BOARD_TOP + 7 * GRID_CELL_SIZE)
        p4_b = (BOARD_LEFT + 3 * GRID_CELL_SIZE, BOARD_TOP + 9 * GRID_CELL_SIZE)
        pygame.draw.line(self.screen, COLOR_BOARD_LINE, p3_b, p4_b, 1)
        
        # River (Chu Hà / Hán Giới)
        river_y = BOARD_TOP + 4 * GRID_CELL_SIZE
        river_h = GRID_CELL_SIZE
        
        # Calligraphy text for River – "漢楚爭雄" (Hán Sở Tranh Hùng)
        river_cx = BOARD_LEFT + 4 * GRID_CELL_SIZE   # x-center of board
        river_cy = river_y + GRID_CELL_SIZE // 2      # y-center of river strip
        # Left half: "漢 楚"
        txt_left  = self.font_river.render("漢 楚", True, COLOR_BOARD_LINE)
        rect_left = txt_left.get_rect(center=(BOARD_LEFT + 2 * GRID_CELL_SIZE, river_cy))
        self.screen.blit(txt_left, rect_left)
        # Right half: "爭 雄"
        txt_right  = self.font_river.render("爭 雄", True, COLOR_BOARD_LINE)
        rect_right = txt_right.get_rect(center=(BOARD_LEFT + 6 * GRID_CELL_SIZE, river_cy))
        self.screen.blit(txt_right, rect_right)

    def draw_3d_piece(self, x: int, y: int, color_val: str, piece_type: str, is_face_down: bool, is_selected: bool, is_checked: bool):
        """Draws an extremely polished, skeuomorphic 3D circular piece with drop shadows."""
        # 1. Drop shadow (offset slightly down-right)
        pygame.draw.circle(self.screen, (20, 18, 15), (x + 3, y + 4), PIECE_RADIUS)
        
        # 2. Outer rim selection/check glows
        if is_checked:
            pygame.draw.circle(self.screen, COLOR_CHECK_GLOW, (x, y), PIECE_RADIUS + 3, 3)
        elif is_selected:
            pygame.draw.circle(self.screen, COLOR_SEL_GLOW, (x, y), PIECE_RADIUS + 3, 3)
            
        # 3. Base piece cap (Ivory-white for Red, Dark Obsidian-mahogany for Black)
        base_color = COLOR_WOOD_LIGHT if color_val == "red" else (60, 50, 45)
        pygame.draw.circle(self.screen, base_color, (x, y), PIECE_RADIUS)
        
        # 4. Skeuomorphic Bevel Edge (darker bottom-right, lighter top-left)
        pygame.draw.circle(self.screen, (20, 15, 10) if color_val == "black" else (160, 110, 70), (x, y), PIECE_RADIUS, 2)
        
        # 5. Inner polished recess
        pygame.draw.circle(self.screen, base_color, (x, y), PIECE_RADIUS - 2)
        
        # 6. Character drawing
        if is_face_down:
            # Mysterious dark piece with golden spiral pattern for Cờ Úp
            pygame.draw.circle(self.screen, (40, 35, 30), (x, y), PIECE_RADIUS - 4)
            # Golden decorative spiral rim
            pygame.draw.circle(self.screen, COLOR_GOLD, (x, y), PIECE_RADIUS - 8, 2)
            pygame.draw.circle(self.screen, COLOR_GOLD, (x, y), PIECE_RADIUS - 14, 1)
        else:
            # Traditional calligraphy
            char_color = COLOR_RED_PIECE if color_val == "red" else COLOR_BLACK_PIECE
            char = CHARACTERS.get(color_val, {}).get(piece_type, "?")
            
            # Gold highlights for Black pieces to stand out jade-like
            if color_val == "black":
                char_surf = self.font_calligraphy.render(char, True, COLOR_GOLD)
            else:
                char_surf = self.font_calligraphy.render(char, True, char_color)
                
            char_rect = char_surf.get_rect(center=(x, y))
            self.screen.blit(char_surf, char_rect)

    def draw_translucent_marker(self, x: int, y: int, color_rgb: Tuple[int, int, int], alpha: int, is_capture: bool):
        """Draws a premium translucent move highlight marker with custom alpha."""
        if not is_capture:
            # Empty square: clean glowing emerald dot (radius 7) and outer ring (radius 16)
            surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_rgb + (alpha,), (20, 20), 7)
            pygame.draw.circle(surf, color_rgb + (alpha - 50,), (20, 20), 16, 2)
            self.screen.blit(surf, (x - 20, y - 20))
        else:
            # Capture target: Crimson pulsing halo (radius PIECE_RADIUS + 3) wrapping around the piece
            surf = pygame.Surface((70, 70), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_rgb + (alpha - 90,), (35, 35), 28)
            pygame.draw.circle(surf, color_rgb + (alpha,), (35, 35), PIECE_RADIUS + 3, 3)
            self.screen.blit(surf, (x - 35, y - 35))

# ---------------------------------------------------------------------------
# Animation State Manager
# ---------------------------------------------------------------------------

class PieceAnimation:
    def __init__(self, piece_id: str, color: str, type_: str, from_px: Tuple[int, int], to_px: Tuple[int, int], is_face_down: bool, is_flip: bool = False):
        self.piece_id = piece_id
        self.color = color
        self.type = type_
        self.from_px = from_px
        self.to_px = to_px
        self.is_face_down = is_face_down
        self.is_flip = is_flip
        
        self.progress = 0.0  # ranges from 0.0 to 1.0
        self.duration_frames = 12.0  # smooth 200ms slide

    def update(self) -> bool:
        """Increments animation, returns True if complete."""
        self.progress += 1.0 / self.duration_frames
        return self.progress >= 1.0

    def get_current_pixel(self) -> Tuple[int, int]:
        """Calculates linear interpolation (Lerp) position."""
        t = min(1.0, max(0.0, self.progress))
        # Simple ease-out
        t = t * (2 - t)
        
        x = int(self.from_px[0] + (self.to_px[0] - self.from_px[0]) * t)
        y = int(self.from_px[1] + (self.to_px[1] - self.from_px[1]) * t)
        return x, y

# ---------------------------------------------------------------------------
# Main App Class
# ---------------------------------------------------------------------------

class PygameApp:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cờ Tướng & Cờ Úp Á Đông - Pygame Client")
        self.clock = pygame.time.Clock()
        self.graphics = GraphicsEngine(self.screen)
        
        # Core Game State
        self.local_board = Board()
        self.local_board.setup_classic()
        self.validator = MoveValidator()
        
        # Application parameters
        self.current_screen = "menu"      # "menu", "game", "rules"
        self.session_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.game_mode = "PvE"            # "PvE" (Local AI) or "PvP" (Online Server)
        self.sub_mode = "classic"         # "classic" or "co_up"
        self.ai_difficulty = "medium"     # "easy", "medium", "hard"
        self.ai_thread_active = False     # Guard for local AI calls
        
        # Selection / Interaction
        self.selected_pos: Optional[Position] = None
        self.current_turn = Color.RED
        self.player_color = Color.RED     # RED in local PvE, determined in server PvP
        self.game_state = "playing"       # "playing", "finished"
        self.winner = None
        
        # Server Connection
        self.net_thread: Optional[WebSocketClientThread] = None
        self.server_url = "ws://localhost:8000"
        self.room_id = ""
        self.chat_logs: List[Tuple[str, str]] = []
        
        # User interface inputs
        self.input_room_id = ""
        self.input_chat = ""
        self.active_input = "room"        # "room" or "chat"
        self.lang = "vi"                   # "vi" = Tiếng Việt, "en" = English
        self.status_message = LANG["vi"]["status_ready"]
        
        # Animations
        self.current_animation: Optional[PieceAnimation] = None
        self.move_history: List[dict] = []  # supports local undo
        self.shuffle_timer = 0

    def grid_to_pixel(self, col: int, row: int) -> Tuple[int, int]:
        """Converts board index to screen pixels."""
        x = BOARD_LEFT + col * GRID_CELL_SIZE
        y = BOARD_TOP + (9 - row) * GRID_CELL_SIZE  # In Xiangqi coordinates: row 0 is at bottom!
        return x, y

    def pixel_to_grid(self, x: int, y: int) -> Optional[Position]:
        """Snaps a screen click to the nearest grid intersection.
        Uses round() so clicking anywhere inside the piece circle (radius 26)
        correctly maps to the intersection center (fixes miss-click bugs).
        """
        col = round((x - BOARD_LEFT) / GRID_CELL_SIZE)
        row = 9 - round((y - BOARD_TOP) / GRID_CELL_SIZE)
        pos = Position(col, row)
        if pos.is_valid():
            return pos
        return None

    def trigger_local_ai_move(self):
        """Runs the strong Xiangqi AI in a background thread to prevent Pygame freeze."""
        if self.ai_thread_active or self.game_state != "playing":
            return
            
        self.ai_thread_active = True
        
        def ai_worker():
            from ai import get_best_move
            best_move = get_best_move(
                self.local_board,
                Color.BLACK,
                self.validator,
                difficulty=self.ai_difficulty
            )
            pygame.event.post(pygame.event.Event(pygame.USEREVENT + 1, {"move": best_move}))
            
        threading.Thread(target=ai_worker, daemon=True).start()


    def process_server_events(self):
        """Consumes events from thread-safe background WebSocket thread."""
        if not self.net_thread:
            return
            
        while not self.net_thread.receive_queue.empty():
            data = self.net_thread.receive_queue.get()
            event = data.get("event")
            
            if event == "connected":
                self.status_message = "Connected to Server Lobby."
                
            elif event == "room_state":
                room = data.get("room")
                self.room_id = room.get("room_id")
                self.sub_mode = room.get("mode")
                self.current_turn = Color.RED if room.get("turn") == "red" else Color.BLACK
                
                # Check player assignment
                players = room.get("players")
                if players.get("red") == self.session_id:
                    self.player_color = Color.RED
                    self.status_message = f"Room {self.room_id}: Red Turn (You)"
                elif players.get("black") == self.session_id:
                    self.player_color = Color.BLACK
                    self.status_message = f"Room {self.room_id}: Black Turn (You)"
                else:
                    self.status_message = f"Spectating Room {self.room_id}"
                    
                # Reconstruct Board
                self.local_board.grid.clear()
                self.local_board.is_co_up = (self.sub_mode == "co_up")
                for item in room.get("board"):
                    c, r = item["col"], item["row"]
                    pos = Position(c, r)
                    # Create Piece
                    p = Piece(
                        piece_id=item["id"],
                        color=Color.RED if item["color"] == "red" else Color.BLACK,
                        real_type=PieceType(item["type"]), # default
                        is_face_down=item["is_face_down"],
                        pseudo_type=PieceType(item["type"])
                    )
                    self.local_board.grid[pos] = p
                    
                # Check status transitions
                if room.get("state") == "playing":
                    self.game_state = "playing"
                elif room.get("state") == "finished":
                    self.game_state = "finished"
                    winner_val = room.get("winner")
                    self.winner = Color.RED if winner_val == "red" else Color.BLACK
                    self.status_message = f"Game Over. Winner: {winner_val.upper()}"
                    
            elif event == "move_made":
                # Start slide animation
                from_pos = Position(data["from"]["col"], data["from"]["row"])
                to_pos = Position(data["to"]["col"], data["to"]["row"])
                
                frm_px = self.grid_to_pixel(from_pos.col, from_pos.row)
                to_px = self.grid_to_pixel(to_pos.col, to_pos.row)
                
                p = self.local_board.get_piece_at(from_pos)
                if p:
                    self.current_animation = PieceAnimation(
                        piece_id=p.id,
                        color=p.color.value,
                        type_=p.get_current_type().value,
                        from_px=frm_px,
                        to_px=to_px,
                        is_face_down=p.is_face_down
                    )
                    
                # Play hollow wood click sound
                play_sound(180, 150, 0.7)
                
            elif event == "check":
                chk_color = data.get("color")
                self.status_message = f"WARNING: {chk_color.upper()} is Checked!"
                # Red beep warning chime
                play_sound(300, 120, 0.5)
                time.sleep(0.12)
                play_sound(300, 120, 0.5)
                
            elif event == "game_over":
                self.game_state = "finished"
                self.winner = Color.RED if data.get("winner") == "red" else Color.BLACK
                self.status_message = f"Game Over! Winner: {data.get('winner').upper()} ({data.get('result')})"
                play_sound(440, 400, 0.4)
                
            elif event == "chat":
                sender = data.get("sender")
                msg = data.get("message")
                self.chat_logs.append((sender, msg))
                if len(self.chat_logs) > 8:
                    self.chat_logs.pop(0)
                    
            elif event == "undo_requested":
                self.status_message = "Opponent requests UNDO. [A] Accept or [R] Reject?"
                
            elif event == "undo_done":
                # Server sent complete state reverted
                self.status_message = "Undo request accepted."
                
            elif event == "error":
                self.status_message = f"Server Error: {data.get('message')}"

    # ---------------------------------------------------------------------------
    # Main Event Loop and Update Methods
    # ---------------------------------------------------------------------------

    def handle_click(self, x: int, y: int):
        """Processes selection clicks on the board and menu buttons."""
        if self.current_screen == "menu":
            T = LANG[self.lang]
            # Language toggle buttons: VI (760,68,40,28)  EN (806,68,40,28)
            if 760 <= x <= 800 and 68 <= y <= 96:
                self.lang = "vi"
                play_sound(800, 40, 0.3)
                return
            elif 806 <= x <= 846 and 68 <= y <= 96:
                self.lang = "en"
                play_sound(800, 40, 0.3)
                return
            # 1. PvE: Rect(310, 268, 380, 54)
            if 310 <= x <= 690 and 268 <= y <= 322:
                self.current_screen = "game"
                self.game_mode = "PvE"
                self.sub_mode = "classic"
                self.local_board.setup_classic()
                self.current_turn = Color.RED
                self.game_state = "playing"
                self.move_history.clear()
                self.status_message = T["status_ready"]
                self.selected_pos = None
                play_sound(180, 150, 0.7)
            # 2. PvP: Rect(310, 355, 380, 54)
            elif 310 <= x <= 690 and 355 <= y <= 409:
                self.current_screen = "game"
                self.game_mode = "PvP"
                self.status_message = T["status_offline"]
                self.selected_pos = None
                play_sound(180, 150, 0.7)
            # 3. Rules: Rect(310, 442, 380, 54)
            elif 310 <= x <= 690 and 442 <= y <= 496:
                self.current_screen = "rules"
                play_sound(180, 150, 0.7)
            # 4. Exit: Rect(310, 529, 380, 54)
            elif 310 <= x <= 690 and 529 <= y <= 583:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                play_sound(180, 150, 0.7)
            return

        elif self.current_screen == "rules":
            # Back: (350, 620, 300, 45)
            if 350 <= x <= 650 and 620 <= y <= 665:
                self.current_screen = "menu"
                play_sound(180, 150, 0.7)
            return

        elif self.current_screen == "game":
            # Small top-right "MENU" button: (900, 10, 80, 28)
            if 900 <= x <= 980 and 10 <= y <= 38:
                self.current_screen = "menu"
                play_sound(180, 150, 0.7)
                if self.net_thread:
                    self.net_thread.running = False
                    self.net_thread = None
                return

            # Game-over overlay rematch button takes priority
            if self._handle_rematch_click(x, y):
                return

        # 1. Click on Board (9 columns x 10 rows in Xiangqi)
        if BOARD_LEFT <= x < BOARD_LEFT + 9 * GRID_CELL_SIZE and BOARD_TOP <= y < BOARD_TOP + 10 * GRID_CELL_SIZE:
            if self.game_state != "playing" or self.player_color != self.current_turn:
                return
            if getattr(self, 'shuffle_timer', 0) > 0:
                return # Block interactions while shuffling
                
            pos = self.pixel_to_grid(x, y)
            if not pos:
                return
                
            clicked_piece = self.local_board.get_piece_at(pos)
            
            if self.selected_pos is None:
                # First click: selection
                if clicked_piece and clicked_piece.color == self.current_turn:
                    self.selected_pos = pos
                    # Small tick selection sound
                    play_sound(800, 40, 0.3)
            else:
                # Second click: target movement destination
                target_pos = pos
                # Check if we clicked friendly piece again (re-select)
                if clicked_piece and clicked_piece.color == self.current_turn:
                    self.selected_pos = target_pos
                    play_sound(800, 40, 0.3)
                    return
                    
                # Execute move
                if self.game_mode == "PvE":
                    # Local PvE Move Execution
                    res = self.validator.make_move(self.local_board, self.selected_pos, target_pos, self.current_turn)
                    if res is not None:
                        captured, was_revealed = res
                        # Store in history for undo
                        self.move_history.append({
                            "from": {"col": self.selected_pos.col, "row": self.selected_pos.row},
                            "to": {"col": target_pos.col, "row": target_pos.row},
                            "captured": captured.clone() if captured else None,
                            "was_revealed": was_revealed,
                            "was_face_down": was_revealed
                        })
                        
                        # Trigger slide animation
                        frm_px = self.grid_to_pixel(self.selected_pos.col, self.selected_pos.row)
                        to_px = self.grid_to_pixel(target_pos.col, target_pos.row)
                        
                        piece_active = self.local_board.get_piece_at(target_pos)
                        if piece_active:
                            self.current_animation = PieceAnimation(
                                piece_id=piece_active.id,
                                color=piece_active.color.value,
                                type_=piece_active.get_current_type().value,
                                from_px=frm_px,
                                to_px=to_px,
                                is_face_down=piece_active.is_face_down
                            )
                            
                        play_sound(180, 150, 0.7)
                        
                        # Swap turn
                        self.current_turn = Color.BLACK if self.current_turn == Color.RED else Color.RED
                        self.selected_pos = None
                        self.status_message = "Thinking (Black AI)..."
                        
                        # Victory / check checks
                        opp_color = self.current_turn
                        if self.validator.is_checkmate(self.local_board, opp_color):
                            self.game_state = "finished"
                            self.winner = Color.RED
                            self.status_message = "Checkmate! Red Wins!"
                        elif self.validator.is_stalemate(self.local_board, opp_color):
                            self.game_state = "finished"
                            self.winner = Color.RED
                            self.status_message = "Stalemate! Red Wins!"
                        elif self.validator.is_in_check(self.local_board, opp_color):
                            self.status_message = "WARNING: BLACK is Checked!"
                            play_sound(300, 120, 0.5)
                            time.sleep(0.12)
                            play_sound(300, 120, 0.5)
                            
                        # Trigger Local AI computation
                        if self.game_state == "playing" and self.current_turn == Color.BLACK:
                            self.trigger_local_ai_move()
                    else:
                        self.selected_pos = None
                        self.status_message = "Illegal Move."
                        
                else:
                    # Online PvP WebSocket Move Broadcasting
                    if self.net_thread:
                        self.net_thread.send_queue.put({
                            "action": "make_move",
                            "from": {"col": self.selected_pos.col, "row": self.selected_pos.row},
                            "to": {"col": target_pos.col, "row": target_pos.row}
                        })
                    self.selected_pos = None

        # 2. Click on Side Control Panel
        else:
            PX = 655   # panel left edge (must match draw code)
            # --- Mode selection: PvE / PvP ---
            # PvE btn: (PX, 52, 152, 36)  PvP btn: (PX+160, 52, 152, 36)
            if PX <= x <= PX + 152 and 52 <= y <= 88:
                if self.ai_thread_active:
                    return
                self.game_mode = "PvE"
                self.local_board.setup_classic()
                self.current_turn = Color.RED
                self.game_state = "playing"
                self.status_message = "Local Game Ready (You: RED)"
                self.selected_pos = None
            elif PX + 160 <= x <= PX + 312 and 52 <= y <= 88:
                if self.ai_thread_active:
                    return
                self.game_mode = "PvP"
                self.status_message = "Offline Server. Connect to Start."
                self.selected_pos = None

            # --- Sub-mode selection: Classic / Cờ Úp ---
            # Classic btn: (PX+80, 108, 110, 28)  Cờ Úp btn: (PX+198, 108, 80, 28)
            if self.game_state == "playing" and len(self.move_history) == 0:
                if PX + 80 <= x <= PX + 190 and 108 <= y <= 136:
                    if self.ai_thread_active:
                        return
                    self.sub_mode = "classic"
                    self.local_board.setup_classic()
                    self.status_message = "Classic Mode initialized."
                elif PX + 198 <= x <= PX + 278 and 108 <= y <= 136:
                    if self.ai_thread_active:
                        return
                    self.sub_mode = "co_up"
                    self.local_board.setup_co_up()
                    self.status_message = "Cờ Úp Mode initialized."
                    self.shuffle_timer = 60

            # --- AI difficulty (PvE only) ---
            # EASY: (PX+80,150,68,28)  MEDIUM:(PX+154,150,82,28)  HARD:(PX+242,150,72,28)
            if self.game_mode == "PvE":
                if PX + 80 <= x <= PX + 148 and 150 <= y <= 178:
                    self.ai_difficulty = "easy"
                elif PX + 154 <= x <= PX + 236 and 150 <= y <= 178:
                    self.ai_difficulty = "medium"
                elif PX + 242 <= x <= PX + 314 and 150 <= y <= 178:
                    self.ai_difficulty = "hard"

            # --- Server lobby commands (PvP only) ---
            if self.game_mode == "PvP":
                # Connect Server button: (PX, 198, 312, 30)
                if PX <= x <= PX + 312 and 198 <= y <= 228:
                    self.net_thread = WebSocketClientThread(self.session_id, self.server_url)
                    self.net_thread.start()
                    self.status_message = "Connecting to WebSocket server..."
                # Room code input box: (PX, 245, 170, 30)
                if PX <= x <= PX + 170 and 245 <= y <= 275:
                    self.active_input = "room"
                # Create Room button: (PX+178, 245, 134, 30)
                if PX + 178 <= x <= PX + 312 and 245 <= y <= 275:
                    if self.net_thread:
                        self.net_thread.send_queue.put({"action": "create_room", "mode": self.sub_mode})
                        self.status_message = "Creating Room..."
                # Join Room button: (PX, 283, 312, 30)
                if PX <= x <= PX + 312 and 283 <= y <= 313:
                    if self.net_thread and self.input_room_id:
                        self.net_thread.send_queue.put({"action": "join_room", "room_id": self.input_room_id.upper()})
                        self.status_message = f"Joining Room {self.input_room_id.upper()}..."
                # Chat input: (PX, 650, 312, 30)
                if PX <= x <= PX + 312 and 650 <= y <= 680:
                    self.active_input = "chat"

            # --- Undo / Reset buttons ---
            # Undo: (PX, 706, 150, 32)  Reset: (PX+158, 706, 154, 32)
            if PX <= x <= PX + 150 and 706 <= y <= 738:
                if self.ai_thread_active:
                    return
                if self.game_mode == "PvE":
                    steps = 2 if len(self.move_history) >= 2 else 1
                    for _ in range(steps):
                        if self.move_history:
                            last = self.move_history.pop()
                            frm = Position(last["from"]["col"], last["from"]["row"])
                            to  = Position(last["to"]["col"],   last["to"]["row"])
                            moved = self.local_board.remove_piece(to)
                            if moved:
                                if last["was_face_down"]:
                                    moved.is_face_down = True
                                self.local_board.add_piece(frm, moved)
                            if last["captured"]:
                                self.local_board.add_piece(to, last["captured"])
                    self.current_turn = Color.RED
                    self.game_state = "playing"
                    self.status_message = "Undo complete."
                else:
                    if self.net_thread:
                        self.net_thread.send_queue.put({"action": "request_undo"})
                        self.status_message = "Undo requested..."
            elif PX + 158 <= x <= PX + 312 and 706 <= y <= 738:
                if self.ai_thread_active:
                    return
                if self.game_mode == "PvE":
                    if self.sub_mode == "co_up":
                        self.local_board.setup_co_up()
                        self.shuffle_timer = 60
                    else:
                        self.local_board.setup_classic()
                    self.current_turn = Color.RED
                    self.game_state = "playing"
                    self.move_history.clear()
                    self.status_message = "Game reset."
                else:
                    pass

    def draw_start_menu(self):
        """Draws a premium Eastern start menu with glowing hover interactions."""
        T = LANG[self.lang]  # shortcut to current language strings

        # 1. Base clean dark backdrop
        self.screen.fill(COLOR_BACKGROUND)
        
        # 2. Centered large wooden panel
        panel_rect = pygame.Rect(150, 60, 700, 630)
        self.graphics.draw_wood_background(panel_rect)
        pygame.draw.rect(self.screen, COLOR_GOLD, panel_rect, 2)
        
        # Draw elegant Chinese water-mark "棋" (Chess) in the background with low-contrast brown
        bg_char = self.graphics.font_calligraphy.render("棋", True, (110, 70, 30))
        bg_char_large = pygame.transform.scale(bg_char, (260, 260))
        bg_char_rect = bg_char_large.get_rect(center=(500, 375))
        self.screen.blit(bg_char_large, bg_char_rect)
        
        # 3. Title
        lbl_title = self.graphics.font_menu_title.render(T["title"], True, COLOR_GOLD)
        title_rect = lbl_title.get_rect(center=(500, 145))
        self.screen.blit(lbl_title, title_rect)

        pygame.draw.line(self.screen, COLOR_GOLD, (250, 232), (750, 232), 2)

        # 4. Menu buttons
        buttons = [
            (T["btn_pve"],   pygame.Rect(310, 268, 380, 54), "pve"),
            (T["btn_pvp"],   pygame.Rect(310, 355, 380, 54), "pvp"),
            (T["btn_rules"], pygame.Rect(310, 442, 380, 54), "rules"),
            (T["btn_exit"],  pygame.Rect(310, 529, 380, 54), "exit"),
        ]

        mx, my = pygame.mouse.get_pos()

        for text, rect, action in buttons:
            is_hover = rect.collidepoint(mx, my)
            bg_color = (72, 55, 42) if is_hover else (48, 40, 35)
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=10)
            border_col = COLOR_SEL_GLOW if is_hover else COLOR_GOLD
            border_w   = 2 if is_hover else 1
            pygame.draw.rect(self.screen, border_col, rect, border_w, border_radius=10)
            pygame.draw.rect(self.screen, border_col, pygame.Rect(rect.x + 6, rect.y + 8, 3, rect.height - 16), border_radius=2)
            txt_col = COLOR_SEL_GLOW if is_hover else COLOR_TEXT_LIGHT
            lbl = self.graphics.font_medium.render(text, True, txt_col)
            lbl_rect = lbl.get_rect(midleft=(rect.x + 20, rect.centery))
            self.screen.blit(lbl, lbl_rect)

        # 5. Language toggle buttons – top-right corner of the panel
        #    VI button: Rect(760, 68, 40, 28)   EN button: Rect(806, 68, 40, 28)
        lang_vi_rect = pygame.Rect(760, 68, 40, 28)
        lang_en_rect = pygame.Rect(806, 68, 40, 28)

        def draw_lang_btn(rect, code, label):
            is_active = (self.lang == code)
            is_hov    = rect.collidepoint(mx, my)
            bg  = (110, 78, 46) if is_active else ((62, 52, 44) if is_hov else (38, 32, 28))
            brd = COLOR_SEL_GLOW if is_hov else (COLOR_GOLD if is_active else (70, 60, 50))
            pygame.draw.rect(self.screen, bg,  rect, border_radius=6)
            pygame.draw.rect(self.screen, brd, rect, 2 if is_active or is_hov else 1, border_radius=6)
            txt_c = COLOR_SEL_GLOW if is_hov else (COLOR_GOLD if is_active else COLOR_TEXT_MUTED)
            lbl = self.graphics.font_ui.render(label, True, txt_c)
            self.screen.blit(lbl, lbl.get_rect(center=rect.center))

        draw_lang_btn(lang_vi_rect, "vi", "VI")
        draw_lang_btn(lang_en_rect, "en", "EN")

    def draw_rules_page(self):
        """Draws an elegant rules instruction scroll screen."""
        T = LANG[self.lang]
        self.screen.fill(COLOR_BACKGROUND)
        
        panel_rect = pygame.Rect(100, 50, 800, 650)
        self.graphics.draw_wood_background(panel_rect)
        pygame.draw.rect(self.screen, COLOR_GOLD, panel_rect, 2)
        
        lbl_title = self.graphics.font_title.render(T["rules_title"], True, COLOR_GOLD)
        title_rect = lbl_title.get_rect(center=(500, 95))
        self.screen.blit(lbl_title, title_rect)
        pygame.draw.line(self.screen, COLOR_GOLD, (250, 130), (750, 130), 2)
        
        for idx, line in enumerate(T["rules_lines"]):
            is_header = line.startswith("1.") or line.startswith("2.")
            color = COLOR_GOLD if is_header else COLOR_TEXT_LIGHT
            font = self.graphics.font_medium if is_header else self.graphics.font_ui
            lbl = font.render(line, True, color)
            self.screen.blit(lbl, (140, 160 + idx * 26))
            
        mx, my = pygame.mouse.get_pos()
        back_rect = pygame.Rect(350, 620, 300, 45)
        is_hover = back_rect.collidepoint(mx, my)
        
        pygame.draw.rect(self.screen, (60, 50, 45) if is_hover else (45, 38, 34), back_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_SEL_GLOW if is_hover else COLOR_GOLD, back_rect, 2 if is_hover else 1, border_radius=6)
        
        lbl_back = self.graphics.font_medium.render(T["rules_back"], True, COLOR_SEL_GLOW if is_hover else COLOR_TEXT_LIGHT)
        lbl_back_rect = lbl_back.get_rect(center=back_rect.center)
        self.screen.blit(lbl_back, lbl_back_rect)

    def run(self):
        """Primary Pygame application loop."""
        running = True
        while running:
            # 1. Process server thread updates
            self.process_server_events()
            
            # 2. Pygame Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    if self.net_thread:
                        self.net_thread.running = False
                        
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos[0], event.pos[1])
                        
                elif event.type == pygame.KEYDOWN:
                    # Text box input handling
                    if self.game_mode == "PvP":
                        if self.active_input == "room":
                            if event.key == pygame.K_BACKSPACE:
                                self.input_room_id = self.input_room_id[:-1]
                            elif event.key == pygame.K_RETURN:
                                if self.net_thread and self.input_room_id:
                                    self.net_thread.send_queue.put({
                                        "action": "join_room",
                                        "room_id": self.input_room_id.upper()
                                    })
                            else:
                                if len(self.input_room_id) < 6 and event.unicode.isalnum():
                                    self.input_room_id += event.unicode
                        elif self.active_input == "chat":
                            if event.key == pygame.K_BACKSPACE:
                                self.input_chat = self.input_chat[:-1]
                            elif event.key == pygame.K_RETURN:
                                if self.net_thread and self.input_chat:
                                    self.net_thread.send_queue.put({
                                        "action": "chat",
                                        "message": self.input_chat
                                    })
                                    self.input_chat = ""
                            else:
                                if len(self.input_chat) < 40:
                                    self.input_chat += event.unicode
                                    
                        # Handle consent hotkeys for PvP Undo
                        if event.key == pygame.K_a:  # Accept Undo
                            if self.net_thread:
                                self.net_thread.send_queue.put({"action": "respond_undo", "accept": True})
                        elif event.key == pygame.K_r:  # Reject Undo
                            if self.net_thread:
                                self.net_thread.send_queue.put({"action": "respond_undo", "accept": False})

                # Asynchronous completion of Local AI move calculation
                elif event.type == pygame.USEREVENT + 1:
                    best_move = event.dict.get("move")
                    self.ai_thread_active = False
                    
                    if best_move and self.game_state == "playing":
                        from_pos, to_pos = best_move
                        # Perform AI move
                        res = self.validator.make_move(self.local_board, from_pos, to_pos, Color.BLACK)
                        if res is not None:
                            captured, was_revealed = res
                            self.move_history.append({
                                "from": {"col": from_pos.col, "row": from_pos.row},
                                "to": {"col": to_pos.col, "row": to_pos.row},
                                "captured": captured.clone() if captured else None,
                                "was_revealed": was_revealed,
                                "was_face_down": was_revealed
                            })
                            
                            # Slide animation
                            frm_px = self.grid_to_pixel(from_pos.col, from_pos.row)
                            to_px = self.grid_to_pixel(to_pos.col, to_pos.row)
                            
                            piece_active = self.local_board.get_piece_at(to_pos)
                            if piece_active:
                                self.current_animation = PieceAnimation(
                                    piece_id=piece_active.id,
                                    color=piece_active.color.value,
                                    type_=piece_active.get_current_type().value,
                                    from_px=frm_px,
                                    to_px=to_px,
                                    is_face_down=piece_active.is_face_down
                                )
                                
                            play_sound(180, 150, 0.7)
                            
                            # Switch back to player
                            self.current_turn = Color.RED
                            self.status_message = "Your Turn."
                            
                            # End states checks
                            opp_color = self.current_turn
                            if self.validator.is_checkmate(self.local_board, opp_color):
                                self.game_state = "finished"
                                self.winner = Color.BLACK
                                self.status_message = "Checkmate! AI Wins!"
                            elif self.validator.is_stalemate(self.local_board, opp_color):
                                self.game_state = "finished"
                                self.winner = Color.BLACK
                                self.status_message = "Stalemate! AI Wins!"
                            elif self.validator.is_in_check(self.local_board, opp_color):
                                self.status_message = "WARNING: Red General Checked!"
                                play_sound(300, 120, 0.5)
                                time.sleep(0.12)
                                play_sound(300, 120, 0.5)
                        else:
                            self.current_turn = Color.RED
                            self.status_message = "AI calculated illegal move."
                    else:
                        self.current_turn = Color.RED
                        self.status_message = "AI resigned or cannot move."

            # 3. Drawing Phase
            if self.current_screen == "menu":
                self.draw_start_menu()
                pygame.display.flip()
                self.clock.tick(60)
                continue
            elif self.current_screen == "rules":
                self.draw_rules_page()
                pygame.display.flip()
                self.clock.tick(60)
                continue
                
            # Clean dark background
            self.screen.fill(COLOR_BACKGROUND)
            
            # Board area size: 612 x 676
            board_rect = pygame.Rect(BOARD_LEFT - 20, BOARD_TOP - 20, 8 * GRID_CELL_SIZE + 40, 9 * GRID_CELL_SIZE + 40)
            self.graphics.draw_board(board_rect)
            
            # Draw valid move suggestions for selected piece
            if self.selected_pos is not None:
                for col in range(9):
                    for row in range(10):
                        to_pos = Position(col, row)
                        if to_pos == self.selected_pos:
                            continue
                        if self.validator.is_valid_move(self.local_board, self.selected_pos, to_pos, self.current_turn):
                            px_x, px_y = self.grid_to_pixel(col, row)
                            dest_piece = self.local_board.get_piece_at(to_pos)
                            if dest_piece is None:
                                self.graphics.draw_translucent_marker(px_x, px_y, (46, 204, 113), alpha=150, is_capture=False)
                            else:
                                self.graphics.draw_translucent_marker(px_x, px_y, (231, 76, 60), alpha=180, is_capture=True)
                                
            # Draw standard pieces
            anim_piece_id = self.current_animation.piece_id if self.current_animation else None
            
            for pos, piece in self.local_board.grid.items():
                # Skip if this specific piece is currently in a sliding animation
                if piece.id == anim_piece_id:
                    continue
                    
                px_x, px_y = self.grid_to_pixel(pos.col, pos.row)
                is_selected = (self.selected_pos == pos)
                
                # Check General glow warning
                is_checked = False
                if piece.get_current_type() == PieceType.GENERAL:
                    is_checked = self.validator.is_in_check(self.local_board, piece.color)
                    
                # Apply shuffle animation offset if active and piece is face down
                if getattr(self, 'shuffle_timer', 0) > 0 and piece.is_face_down:
                    center_col = 4
                    center_row = 2.5 if piece.color == Color.RED else 7.5
                    cx = BOARD_LEFT + center_col * GRID_CELL_SIZE
                    cy = BOARD_TOP + int(center_row * GRID_CELL_SIZE)
                    
                    if self.shuffle_timer > 40: # slide to center
                        t = (60 - self.shuffle_timer) / 20.0
                        px_x = int(px_x + (cx - px_x) * t)
                        px_y = int(px_y + (cy - px_y) * t)
                    elif self.shuffle_timer > 20: # jiggle (mix)
                        px_x = int(cx + random.randint(-40, 40))
                        px_y = int(cy + random.randint(-40, 40))
                    else: # slide back to spot
                        t = (20 - self.shuffle_timer) / 20.0
                        px_x = int(cx + (px_x - cx) * t)
                        px_y = int(cy + (px_y - cy) * t)

                self.graphics.draw_3d_piece(
                    px_x, px_y, piece.color.value, piece.get_current_type().value, 
                    piece.is_face_down, is_selected, is_checked
                )
                
            # Draw active sliding animation
            if self.current_animation:
                anim_x, anim_y = self.current_animation.get_current_pixel()
                self.graphics.draw_3d_piece(
                    anim_x, anim_y, self.current_animation.color, self.current_animation.type,
                    self.current_animation.is_face_down, False, False
                )
                if self.current_animation.update():
                    self.current_animation = None  # animation ended
                    
            # ============================================================
            # 4. Right Sidebar – Redesigned layout (PX=655, panel width=320)
            # ============================================================
            PX  = 655   # panel left
            PW  = 320   # panel usable width
            mx, my = pygame.mouse.get_pos()

            # ── Header title + MENU button ──────────────────────────────
            T = LANG[self.lang]
            lbl_hdr = self.graphics.font_title.render(T["sidebar_title"], True, COLOR_GOLD)
            self.screen.blit(lbl_hdr, (PX, 12))

            btn_menu = pygame.Rect(900, 10, 72, 28)
            is_hov_m = btn_menu.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (90, 55, 50) if is_hov_m else (55, 45, 40), btn_menu, border_radius=5)
            pygame.draw.rect(self.screen, COLOR_SEL_GLOW if is_hov_m else COLOR_GOLD, btn_menu, 1, border_radius=5)
            lbl_m = self.graphics.font_ui.render(T["btn_menu"], True, COLOR_SEL_GLOW if is_hov_m else COLOR_TEXT_LIGHT)
            self.screen.blit(lbl_m, lbl_m.get_rect(center=btn_menu.center))

            pygame.draw.line(self.screen, (70, 60, 50), (PX, 46), (PX + PW, 46), 1)

            # ── Mode buttons (PvE / PvP) ────────────────────────────────
            # PvE: (PX, 52, 152, 36)   PvP: (PX+160, 52, 152, 36)
            def draw_btn(rect, label, active, hover_check):
                is_hov = rect.collidepoint(mx, my)
                bg  = (110, 78, 46) if active else ((62, 52, 44) if is_hov else (45, 38, 34))
                brd = COLOR_SEL_GLOW if is_hov else (COLOR_GOLD if active else (80, 70, 60))
                pygame.draw.rect(self.screen, bg,  rect, border_radius=7)
                pygame.draw.rect(self.screen, brd, rect, 2 if active or is_hov else 1, border_radius=7)
                txt_c = COLOR_SEL_GLOW if is_hov else COLOR_TEXT_LIGHT
                lbl = self.graphics.font_medium.render(label, True, txt_c)
                self.screen.blit(lbl, lbl.get_rect(center=rect.center))

            draw_btn(pygame.Rect(PX,       52, 152, 36), T["btn_vs_ai"],  self.game_mode == "PvE", True)
            draw_btn(pygame.Rect(PX + 160, 52, 152, 36), T["btn_online"], self.game_mode == "PvP", True)

            pygame.draw.line(self.screen, (70, 60, 50), (PX, 96), (PX + PW, 96), 1)

            # ── Sub-mode (Chế Độ) ───────────────────────────────────────
            # Label "Chế Độ:" + Classic (PX+80,108,110,28) + Cờ Úp (PX+198,108,80,28)
            lbl_sd = self.graphics.font_ui.render(T["label_mode"], True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl_sd, lbl_sd.get_rect(midleft=(PX, 122)))

            def draw_small_btn(rect, label, active):
                is_hov = rect.collidepoint(mx, my)
                bg  = (100, 70, 40) if active else ((55, 48, 40) if is_hov else (42, 36, 30))
                brd = COLOR_SEL_GLOW if is_hov else (COLOR_GOLD if active else (70, 60, 50))
                pygame.draw.rect(self.screen, bg,  rect, border_radius=5)
                pygame.draw.rect(self.screen, brd, rect, 2 if active or is_hov else 1, border_radius=5)
                txt_c = COLOR_SEL_GLOW if is_hov else COLOR_TEXT_LIGHT
                lbl = self.graphics.font_ui.render(label, True, txt_c)
                self.screen.blit(lbl, lbl.get_rect(center=rect.center))

            draw_small_btn(pygame.Rect(PX + 80,  108, 110, 28), T["btn_classic"], self.sub_mode == "classic")
            draw_small_btn(pygame.Rect(PX + 198, 108,  80, 28), T["btn_co_up"],   self.sub_mode == "co_up")

            # ── Difficulty (PvE only) ────────────────────────────────────
            if self.game_mode == "PvE":
                lbl_dh = self.graphics.font_ui.render(T["label_diff"], True, COLOR_TEXT_MUTED)
                self.screen.blit(lbl_dh, lbl_dh.get_rect(midleft=(PX, 164)))
                # EASY (68px)  MEDIUM (82px)  HARD (72px)  – with 6px gaps
                diff_rects = [
                    ("easy",   pygame.Rect(PX + 80,        150,  68, 28)),
                    ("medium", pygame.Rect(PX + 80 + 74,   150,  82, 28)),
                    ("hard",   pygame.Rect(PX + 80 + 162,  150,  72, 28)),
                ]
                for dname, drect in diff_rects:
                    draw_small_btn(drect, dname.upper(), self.ai_difficulty == dname)

                # Engine status badge
                try:
                    from pikafish_engine import is_pikafish_available
                    _pf_on = is_pikafish_available()
                except Exception:
                    _pf_on = False
                badge_col = (40, 160, 80) if _pf_on else (100, 80, 40)
                badge_txt = "PIKAFISH" if _pf_on else "Custom AI"
                badge_rect = pygame.Rect(PX, 184, PW, 20)
                pygame.draw.rect(self.screen, badge_col, badge_rect, border_radius=4)
                lbl_badge = self.graphics.font_ui.render(
                    f"Engine: {badge_txt}", True, (220, 255, 220) if _pf_on else (200, 180, 120)
                )
                self.screen.blit(lbl_badge, lbl_badge.get_rect(center=badge_rect.center))

            # ── PvP Server Controls ──────────────────────────────────────
            elif self.game_mode == "PvP":
                # Connect button (PX, 198, PW, 30)
                conn_rect = pygame.Rect(PX, 198, PW, 30)
                is_hc = conn_rect.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (50, 100, 70) if is_hc else (40, 85, 58), conn_rect, border_radius=5)
                pygame.draw.rect(self.screen, COLOR_SEL_GLOW if is_hc else (60, 140, 90), conn_rect, 1, border_radius=5)
                lbl_conn = self.graphics.font_ui.render(T["btn_connect"], True, COLOR_TEXT_LIGHT)
                self.screen.blit(lbl_conn, lbl_conn.get_rect(center=conn_rect.center))

                # Room code input (PX, 245, 170, 30)
                inp_col = (62, 56, 50) if self.active_input == "room" else (38, 33, 28)
                inp_rect = pygame.Rect(PX, 245, 170, 30)
                pygame.draw.rect(self.screen, inp_col, inp_rect, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_GOLD if self.active_input == "room" else COLOR_TEXT_MUTED, inp_rect, 1, border_radius=4)
                room_txt = self.input_room_id if self.input_room_id else T["placeholder_room"]
                lbl_ri = self.graphics.font_ui.render(room_txt, True, COLOR_TEXT_LIGHT if self.input_room_id else COLOR_TEXT_MUTED)
                self.screen.blit(lbl_ri, (PX + 8, 251))

                # Create Room button (PX+178, 245, 134, 30)
                cre_rect = pygame.Rect(PX + 178, 245, 134, 30)
                is_hcr = cre_rect.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (90, 65, 38) if is_hcr else (75, 54, 30), cre_rect, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_SEL_GLOW if is_hcr else COLOR_GOLD, cre_rect, 1, border_radius=4)
                lbl_cre = self.graphics.font_ui.render(T["btn_create_room"], True, COLOR_TEXT_LIGHT)
                self.screen.blit(lbl_cre, lbl_cre.get_rect(center=cre_rect.center))

                # Join Room button (PX, 283, PW, 30)
                join_rect = pygame.Rect(PX, 283, PW, 30)
                is_hjoin = join_rect.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (90, 65, 38) if is_hjoin else (75, 54, 30), join_rect, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_SEL_GLOW if is_hjoin else COLOR_GOLD, join_rect, 1, border_radius=4)
                lbl_join = self.graphics.font_ui.render(T["btn_join_room"], True, COLOR_TEXT_LIGHT)
                self.screen.blit(lbl_join, lbl_join.get_rect(center=join_rect.center))

                # Chat area
                lbl_ch = self.graphics.font_ui.render(T["label_chat"], True, COLOR_TEXT_MUTED)
                self.screen.blit(lbl_ch, (PX, 322))
                chat_area = pygame.Rect(PX, 344, PW, 290)
                pygame.draw.rect(self.screen, (22, 20, 18), chat_area, border_radius=6)
                pygame.draw.rect(self.screen, COLOR_BOARD_LINE, chat_area, 1, border_radius=6)
                for idx, (sender, msg) in enumerate(self.chat_logs):
                    txt_c2 = COLOR_TEXT_LIGHT if sender != "Spectator" else COLOR_TEXT_MUTED
                    lbl_msg = self.graphics.font_ui.render(f"{sender}: {msg}", True, txt_c2)
                    self.screen.blit(lbl_msg, (PX + 8, 352 + idx * 24))

                # Chat input
                ch_col = (60, 55, 50) if self.active_input == "chat" else (38, 33, 28)
                ch_rect = pygame.Rect(PX, 650, PW, 30)
                pygame.draw.rect(self.screen, ch_col, ch_rect, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_GOLD if self.active_input == "chat" else COLOR_TEXT_MUTED, ch_rect, 1, border_radius=4)
                ch_txt = self.input_chat if self.input_chat else T["placeholder_chat"]
                lbl_chi = self.graphics.font_ui.render(ch_txt, True, COLOR_TEXT_LIGHT if self.input_chat else COLOR_TEXT_MUTED)
                self.screen.blit(lbl_chi, (PX + 8, 656))

            # ── Undo / Reset buttons ─────────────────────────────────────
            pygame.draw.line(self.screen, (70, 60, 50), (PX, 700), (PX + PW, 700), 1)
            undo_rect  = pygame.Rect(PX,        706, 150, 32)
            reset_rect = pygame.Rect(PX + 158,  706, 154, 32)

            is_hu = undo_rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (90, 40, 40) if is_hu else (70, 35, 35), undo_rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_SEL_GLOW if is_hu else (140, 60, 60), undo_rect, 1, border_radius=6)
            lbl_u = self.graphics.font_ui.render(T["btn_undo"], True, COLOR_TEXT_LIGHT)
            self.screen.blit(lbl_u, lbl_u.get_rect(center=undo_rect.center))

            is_hr = reset_rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (95, 58, 30) if is_hr else (78, 48, 25), reset_rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_SEL_GLOW if is_hr else COLOR_GOLD, reset_rect, 1, border_radius=6)
            lbl_r = self.graphics.font_ui.render(T["btn_reset"], True, COLOR_TEXT_LIGHT)
            self.screen.blit(lbl_r, lbl_r.get_rect(center=reset_rect.center))

            # ── Status bar (bottom of board area) ───────────────────────
            sb_rect = pygame.Rect(BOARD_LEFT - 20, 700, 8 * GRID_CELL_SIZE + 40, 32)
            pygame.draw.rect(self.screen, (28, 26, 22), sb_rect, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_BOARD_LINE, sb_rect, 1, border_radius=4)
            lbl_status = self.graphics.font_ui.render(self.status_message, True, COLOR_GOLD)
            self.screen.blit(lbl_status, (BOARD_LEFT, 708))

            # ── Game Over Overlay ────────────────────────────────────────
            if self.game_state == "finished" and self.winner is not None:
                self._draw_game_over_overlay()

            # Render frame
            pygame.display.flip()
            
            if getattr(self, 'shuffle_timer', 0) > 0:
                self.shuffle_timer -= 1
                if self.shuffle_timer > 20 and self.shuffle_timer % 4 == 0:
                    play_sound(80 + random.randint(0, 40), 40, 0.4)
                    
            self.clock.tick(60)

    def _draw_game_over_overlay(self):
        """Draws a premium translucent Game Over overlay with win/lose result and a rematch button."""
        # Semi-transparent dark backdrop
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 6, 200))
        self.screen.blit(overlay, (0, 0))

        # Central panel
        panel_w, panel_h = 520, 340
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = (WINDOW_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        # Determine if local player won or lost
        player_wins = (self.winner == self.player_color)

        # Panel fill gradient effect (two rects)
        panel_bg = (28, 60, 35) if player_wins else (65, 20, 20)
        panel_edge = (60, 160, 80) if player_wins else (180, 50, 50)
        pygame.draw.rect(self.screen, panel_bg, panel_rect, border_radius=18)
        pygame.draw.rect(self.screen, panel_edge, panel_rect, 3, border_radius=18)

        # Inner glow line
        inner = panel_rect.inflate(-16, -16)
        pygame.draw.rect(self.screen, panel_edge, inner, 1, border_radius=12)

        cx = panel_rect.centerx

        # Big result icon characters
        T = LANG[self.lang]
        icon_char = T["win_title"] if player_wins else T["lose_title"]
        icon_color = (80, 230, 110) if player_wins else (230, 80, 80)
        lbl_icon = self.graphics.font_menu_title.render(icon_char, True, icon_color)
        self.screen.blit(lbl_icon, lbl_icon.get_rect(center=(cx, panel_y + 80)))

        # Subtitle
        if player_wins:
            winner_name = T["color_red"] if self.winner == Color.RED else T["color_black"]
            subtitle = T["win_sub"].format(color=winner_name)
        else:
            loser_name = T["color_red"] if self.winner != Color.RED else T["color_black"]
            subtitle = T["lose_sub"].format(color=loser_name)
        lbl_sub = self.graphics.font_title.render(subtitle, True, COLOR_TEXT_LIGHT)
        self.screen.blit(lbl_sub, lbl_sub.get_rect(center=(cx, panel_y + 155)))

        # Winner declaration line
        winner_label = T["win_label"] if player_wins else T["lose_label"]
        winner_color = (120, 255, 140) if player_wins else (255, 120, 120)
        lbl_win = self.graphics.font_title.render(winner_label, True, winner_color)
        self.screen.blit(lbl_win, lbl_win.get_rect(center=(cx, panel_y + 200)))

        # Rematch button
        mx, my = pygame.mouse.get_pos()
        btn_w, btn_h = 260, 52
        btn_rect = pygame.Rect(cx - btn_w // 2, panel_y + panel_h - 80, btn_w, btn_h)
        is_hov = btn_rect.collidepoint(mx, my)

        btn_bg  = (90, 130, 60) if (player_wins and is_hov) else \
                  (70, 105, 45) if player_wins else \
                  ((130, 60, 40) if is_hov else (105, 45, 30))
        btn_brd = COLOR_SEL_GLOW if is_hov else (COLOR_GOLD)
        pygame.draw.rect(self.screen, btn_bg,  btn_rect, border_radius=10)
        pygame.draw.rect(self.screen, btn_brd, btn_rect, 2 if is_hov else 1, border_radius=10)

        lbl_btn = self.graphics.font_title.render(T["rematch_btn"], True,
                                                   COLOR_SEL_GLOW if is_hov else COLOR_TEXT_LIGHT)
        self.screen.blit(lbl_btn, lbl_btn.get_rect(center=btn_rect.center))

        # Store rematch button rect for click detection
        self._rematch_btn_rect = btn_rect

    def _handle_rematch_click(self, x: int, y: int) -> bool:
        """Returns True if the rematch button was clicked during game-over state."""
        if self.game_state != "finished":
            return False
        btn = getattr(self, '_rematch_btn_rect', None)
        if btn and btn.collidepoint(x, y):
            # Reset game
            if self.sub_mode == "co_up":
                self.local_board.setup_co_up()
                self.shuffle_timer = 60
            else:
                self.local_board.setup_classic()
            self.current_turn = Color.RED
            self.game_state = "playing"
            self.winner = None
            self.move_history.clear()
            self.selected_pos = None
            self.ai_thread_active = False
            self.status_message = LANG[self.lang]["status_new_match"]
            play_sound(260, 200, 0.6)
            return True
        return False

if __name__ == "__main__":
    app = PygameApp()
    try:
        app.run()
    finally:
        try:
            from pikafish_engine import shutdown_pikafish
            shutdown_pikafish()
        except Exception:
            pass
