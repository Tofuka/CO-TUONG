/* ==========================================================================
   Cờ Tướng & Cờ Úp Web Client - Logic & Network Sync (app.js)
   ========================================================================== */

// --------------------------------------------------------------------------
// Web Audio API Sound Synthesizer
// --------------------------------------------------------------------------
let audioCtx = null;

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playSynthSound(freq, duration, volume = 0.5) {
    try {
        initAudio();
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        
        // Skeuomorphic pluck decay
        gainNode.gain.setValueAtTime(volume, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch (e) {
        console.error("Audio synthesis failed:", e);
    }
}

// Custom programmatic sound indicators
const soundTick = () => playSynthSound(800, 0.04, 0.25);        // Selection tick
const soundPluck = () => playSynthSound(180, 0.18, 0.6);        // Piece wood block thud
const soundCheck = () => {                                      // Threat warning alert chime
    playSynthSound(300, 0.12, 0.5);
    setTimeout(() => playSynthSound(300, 0.12, 0.5), 120);
};
const soundGameOver = () => playSynthSound(440, 0.40, 0.4);     // Win/Lose chime

// --------------------------------------------------------------------------
// Calligraphic Characters Map
// --------------------------------------------------------------------------
const CHARACTERS = {
    red: {
        general: "帥", advisor: "仕", elephant: "相",
        horse: "傌", chariot: "俥", cannon: "炮", soldier: "兵"
    },
    black: {
        general: "將", advisor: "士", elephant: "象",
        horse: "馬", chariot: "車", cannon: "砲", soldier: "卒"
    }
};

// --------------------------------------------------------------------------
// Core Game State Variables
// --------------------------------------------------------------------------
let gameMode = "PvE";           // "PvE" (Local Bot) or "PvP" (Online Server)
let subMode = "classic";        // "classic" or "co_up"
let aiDifficulty = "medium";    // "easy", "medium", "hard"
let currentTurn = "red";
let playerColor = "red";        // red in local, server assigned in PvP
let gameState = "playing";      // "playing" or "finished"
let selectedPos = null;         // {col, row}
let checkedGeneralColor = null; // color of checked general

const grid = new Map();         // Map key: "col_row", val: Piece object
const moveHistory = [];         // Local undo history stack
let sessionId = Math.random().toString(36).substring(2, 10);
let socket = null;
let roomCode = "";

// Starting layout mappings (col_row) -> pseudoPieceType
const STARTING_POSITIONS = {
    "0_0": "chariot", "8_0": "chariot",
    "1_0": "horse", "7_0": "horse",
    "2_0": "elephant", "6_0": "elephant",
    "3_0": "advisor", "5_0": "advisor",
    "4_0": "general",
    "1_2": "cannon", "7_2": "cannon",
    "0_3": "soldier", "2_3": "soldier", "4_3": "soldier", "6_3": "soldier", "8_3": "soldier",
    
    "0_9": "chariot", "8_9": "chariot",
    "1_9": "horse", "7_9": "horse",
    "2_9": "elephant", "6_9": "elephant",
    "3_9": "advisor", "5_9": "advisor",
    "4_9": "general",
    "1_7": "cannon", "7_7": "cannon",
    "0_6": "soldier", "2_6": "soldier", "4_6": "soldier", "6_6": "soldier", "8_6": "soldier"
};

// --------------------------------------------------------------------------
// SVG Board Grid Initializer
// --------------------------------------------------------------------------
function drawSvgGrid() {
    const svg = document.getElementById("board-svg");
    if (!svg) return;
    
    // Draw horizontal rows (0 to 9)
    for (let r = 0; r < 10; r++) {
        const y = 50 + r * 100;
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", "50");
        line.setAttribute("y1", y);
        line.setAttribute("x2", "850");
        line.setAttribute("y2", y);
        line.setAttribute("stroke", "#32281E");
        line.setAttribute("stroke-width", (r === 0 || r === 9) ? "3" : "1");
        svg.appendChild(line);
    }
    
    // Draw vertical columns (0 to 8)
    for (let c = 0; c < 9; c++) {
        const x = 50 + c * 100;
        if (c === 0 || c === 8) {
            // Outermost run fully top to bottom
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("x1", x);
            line.setAttribute("y1", "50");
            line.setAttribute("x2", x);
            line.setAttribute("y2", "950");
            line.setAttribute("stroke", "#32281E");
            line.setAttribute("stroke-width", "3");
            svg.appendChild(line);
        } else {
            // Inner columns are split by River
            const lineRed = document.createElementNS("http://www.w3.org/2000/svg", "line");
            lineRed.setAttribute("x1", x);
            lineRed.setAttribute("y1", "50");
            lineRed.setAttribute("x2", x);
            lineRed.setAttribute("y2", "450");
            lineRed.setAttribute("stroke", "#32281E");
            lineRed.setAttribute("stroke-width", "1");
            svg.appendChild(lineRed);
            
            const lineBlack = document.createElementNS("http://www.w3.org/2000/svg", "line");
            lineBlack.setAttribute("x1", x);
            lineBlack.setAttribute("y1", "550");
            lineBlack.setAttribute("x2", x);
            lineBlack.setAttribute("y2", "950");
            lineBlack.setAttribute("stroke", "#32281E");
            lineBlack.setAttribute("stroke-width", "1");
            svg.appendChild(lineBlack);
        }
    }
    
    // Draw Palaces diagonals
    // Red Palace (rows 0-2, cols 3-5)
    drawDiag(350, 750, 550, 950, svg);
    drawDiag(550, 750, 350, 950, svg);
    
    // Black Palace (rows 7-9, cols 3-5)
    drawDiag(350, 50, 550, 250, svg);
    drawDiag(550, 50, 350, 250, svg);
    
    // River text calligraphy
    const riverY = 515;
    const textChu = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textChu.setAttribute("x", "250");
    textChu.setAttribute("y", riverY);
    textChu.setAttribute("font-size", "42");
    textChu.setAttribute("text-anchor", "middle");
    textChu.textContent = "楚  河";
    svg.appendChild(textChu);
    
    const textHan = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textHan.setAttribute("x", "650");
    textHan.setAttribute("y", riverY);
    textHan.setAttribute("font-size", "42");
    textHan.setAttribute("text-anchor", "middle");
    textHan.textContent = "漢  界";
    svg.appendChild(textHan);
}

function drawDiag(x1, y1, x2, y2, svg) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", x1);
    line.setAttribute("y1", y1);
    line.setAttribute("x2", x2);
    line.setAttribute("y2", y2);
    line.setAttribute("stroke", "#32281E");
    line.setAttribute("stroke-dasharray", "3,3");
    line.setAttribute("stroke-width", "1.5");
    svg.appendChild(line);
}

// --------------------------------------------------------------------------
// Board Init & Helper shuffles
// --------------------------------------------------------------------------
function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

function setupClassic() {
    grid.clear();
    moveHistory.length = 0;
    
    for (const [coord, pieceType] of Object.entries(STARTING_POSITIONS)) {
        const [col, row] = coord.split("_").map(Number);
        const color = row <= 4 ? "red" : "black";
        grid.set(coord, {
            id: `${color}_${pieceType}_${col}_${row}`,
            color: color,
            type: pieceType,
            is_face_down: false,
            real_type: pieceType
        });
    }
    
    currentTurn = "red";
    selectedPos = null;
    checkedGeneralColor = null;
    gameState = "playing";
    updateStatus("Trận đấu Sẵn sàng! Lượt đi của bạn (Đỏ).");
    renderBoard();
}

function setupCoUp() {
    grid.clear();
    moveHistory.length = 0;
    
    const basePool = [
        "chariot", "chariot", "horse", "horse", "elephant", "elephant",
        "advisor", "advisor", "cannon", "cannon",
        "soldier", "soldier", "soldier", "soldier", "soldier"
    ];
    
    const redPool = [...basePool];
    const blackPool = [...basePool];
    shuffle(redPool);
    shuffle(blackPool);
    
    let redIdx = 0;
    let blackIdx = 0;
    
    for (const [coord, pseudoType] of Object.entries(STARTING_POSITIONS)) {
        const [col, row] = coord.split("_").map(Number);
        const color = row <= 4 ? "red" : "black";
        
        if (pseudoType === "general") {
            grid.set(coord, {
                id: `${color}_general_${col}_${row}`,
                color: color,
                type: "general",
                is_face_down: false,
                real_type: "general"
            });
        } else {
            const realType = color === "red" ? redPool[redIdx++] : blackPool[blackIdx++];
            grid.set(coord, {
                id: `${color}_dark_${col}_${row}`,
                color: color,
                type: pseudoType, // behaves as starting pos type first
                is_face_down: true,
                real_type: realType
            });
        }
    }
    
    currentTurn = "red";
    selectedPos = null;
    checkedGeneralColor = null;
    gameState = "playing";
    updateStatus("Trận đấu Cờ Úp Sẵn sàng! Lượt đi của bạn (Đỏ).");
    renderBoard();
}

// --------------------------------------------------------------------------
// Clean DOM Rendering Elements
// --------------------------------------------------------------------------
function renderBoard() {
    const container = document.getElementById("pieces-container");
    if (!container) return;
    
    container.innerHTML = "";
    
    for (const [coord, piece] of grid.entries()) {
        const [col, row] = coord.split("_").map(Number);
        
        const div = document.createElement("div");
        div.className = `piece ${piece.color}`;
        div.id = piece.id;
        
        // Percentages matching SVG coordinate layout (responsive fluid grid)
        div.style.left = `${5.555 + col * 11.111}%`;
        div.style.top = `${5.0 + (9 - row) * 10.0}%`;
        
        // Selected highlight
        if (selectedPos && selectedPos.col === col && selectedPos.row === row) {
            div.classList.add("selected");
        }
        
        // General in check glow
        if (piece.type === "general" && piece.color === checkedGeneralColor) {
            div.classList.add("checked");
        }
        
        // Mystery face down
        if (piece.is_face_down) {
            div.classList.add("face-down");
        } else {
            const span = document.createElement("span");
            span.className = "piece-char";
            span.textContent = CHARACTERS[piece.color][piece.type];
            div.appendChild(span);
        }
        
        // Drag click handler
        div.addEventListener("click", (e) => {
            e.stopPropagation();
            handleCellClick(col, row);
        });
        
        container.appendChild(div);
    }
    
    // Reposition board highlights
    renderHighlights();
}

function renderHighlights() {
    const layer = document.getElementById("highlights-layer");
    if (!layer) return;
    layer.innerHTML = "";
    
    if (!selectedPos || gameState !== "playing") return;
    if (gameMode === "PvP" && playerColor !== currentTurn) return;
    
    // Scan full 9x10 grid intersections
    for (let c = 0; c < 9; c++) {
        for (let r = 0; r < 10; r++) {
            if (c === selectedPos.col && r === selectedPos.row) continue;
            
            if (isLocalMoveValid(selectedPos.col, selectedPos.row, c, r)) {
                const targetPiece = grid.get(`${c}_${r}`);
                const div = document.createElement("div");
                
                div.style.left = `${5.555 + c * 11.111}%`;
                div.style.top = `${5.0 + (9 - r) * 10.0}%`;
                
                if (!targetPiece) {
                    // Empty Suggestion
                    div.className = "suggest-marker";
                } else {
                    // Capture Threat suggest
                    div.className = "capture-marker";
                }
                
                layer.appendChild(div);
            }
        }
    }
}

// Click on empty spots on board grid
document.getElementById("wood-board").addEventListener("click", (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    // Round to nearest intersection using precise responsive margin offsets
    const col = Math.round(((clickX / rect.width) * 100 - 5.555) / 11.111);
    const row = 9 - Math.round(((clickY / rect.height) * 100 - 5.0) / 10.0);
    
    if (col >= 0 && col <= 8 && row >= 0 && row <= 9) {
        handleCellClick(col, row);
    }
});

// --------------------------------------------------------------------------
// Core Board Interactions
// --------------------------------------------------------------------------
function handleCellClick(col, row) {
    if (gameState !== "playing") return;
    
    // In PvP, block board interactions on opponent's turn
    if (gameMode === "PvP" && playerColor !== currentTurn) {
        updateStatus("Đang là lượt đi của đối thủ!");
        return;
    }
    
    const clickCoord = `${col}_${row}`;
    const piece = grid.get(clickCoord);
    
    if (selectedPos === null) {
        // Selection phase
        if (piece && piece.color === currentTurn) {
            selectedPos = { col, row };
            soundTick();
            renderBoard();
        }
    } else {
        // Move execution phase
        if (piece && piece.color === currentTurn) {
            // Re-select friendly piece
            selectedPos = { col, row };
            soundTick();
            renderBoard();
            return;
        }
        
        const fromCol = selectedPos.col;
        const fromRow = selectedPos.row;
        
        // Execute move locally or broadcast
        if (gameMode === "PvE") {
            // Local play validation
            if (isLocalMoveValid(fromCol, fromRow, col, row)) {
                executeLocalMove(fromCol, fromRow, col, row);
                
                // Trigger Simulated Bot move shortly
                if (gameState === "playing") {
                    updateStatus("Đối thủ (Máy) đang suy nghĩ...");
                    setTimeout(executeSimulatedBotMove, 800);
                }
            } else {
                selectedPos = null;
                updateStatus("Nước đi không hợp lệ!");
                renderBoard();
            }
        } else {
            // Online PvP WS Broadcasting
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    action: "make_move",
                    from: { col: fromCol, row: fromRow },
                    to: { col: col, row: row }
                }));
            }
            selectedPos = null;
            renderBoard();
        }
    }
}

function executeLocalMove(fromCol, fromRow, toCol, toRow) {
    const fromCoord = `${fromCol}_${fromRow}`;
    const toCoord = `${toCol}_${toRow}`;
    
    const piece = grid.get(fromCoord);
    const captured = grid.get(toCoord);
    
    // Save state in history
    moveHistory.push({
        from: { col: fromCol, row: fromRow },
        to: { col: toCol, row: toRow },
        captured: captured ? { ...captured } : null,
        was_revealed: piece.is_face_down,
        was_face_down: piece.is_face_down
    });
    
    // Execute move
    grid.delete(fromCoord);
    
    // Reveal Cờ Úp Piece
    let revealed = false;
    if (piece.is_face_down) {
        piece.is_face_down = false;
        piece.type = piece.real_type; // Reveal its true form!
        revealed = true;
        addChatLog("Hệ thống", `Quân cờ đã lật mở thành quân: ${CHARACTERS[piece.color][piece.type]}`);
    }
    
    grid.set(toCoord, piece);
    soundPluck();
    
    // Swap turn
    currentTurn = currentTurn === "red" ? "black" : "red";
    selectedPos = null;
    
    // Simple victory condition
    if (captured && captured.type === "general") {
        gameState = "finished";
        soundGameOver();
        updateStatus(`Chiếu Bí! ${piece.color === "red" ? "ĐỎ" : "ĐEN"} Thắng Cuộc!`);
    } else {
        updateStatus(`Lượt của ${currentTurn === "red" ? "Đỏ (Bạn)" : "Đen (Máy)"}`);
    }
    
    renderBoard();
}

// --------------------------------------------------------------------------
// Offline Basic Rules Engine (JS validation fallback)
// --------------------------------------------------------------------------
function isLocalMoveValid(fCol, fRow, tCol, tRow) {
    const fromCoord = `${fCol}_${fRow}`;
    const piece = grid.get(fromCoord);
    if (!piece) return false;
    
    const targetPiece = grid.get(`${tCol}_${tRow}`);
    if (targetPiece && targetPiece.color === piece.color) return false; // same color block
    
    const dCol = tCol - fCol;
    const dRow = tRow - fRow;
    
    const activeType = piece.type;
    
    // 1. General Rules
    if (activeType === "general") {
        if (Math.abs(dCol) + Math.abs(dRow) !== 1) return false;
        // palace restriction: columns 3-5, row 0-2 (red) or 7-9 (black)
        if (tCol < 3 || tCol > 5) return false;
        if (piece.color === "red" && (tRow < 0 || tRow > 2)) return false;
        if (piece.color === "black" && (tRow < 7 || tRow > 9)) return false;
        return true;
    }
    
    // 2. Advisor Rules
    if (activeType === "advisor") {
        if (Math.abs(dCol) !== 1 || Math.abs(dRow) !== 1) return false;
        
        // Classic mode restricts advisors to palace. Cờ Úp once revealed can cross river.
        if (subMode === "classic" || piece.is_face_down) {
            if (tCol < 3 || tCol > 5) return false;
            if (piece.color === "red" && (tRow < 0 || tRow > 2)) return false;
            if (piece.color === "black" && (tRow < 7 || tRow > 9)) return false;
        }
        return true;
    }
    
    // 3. Elephant Rules
    if (activeType === "elephant") {
        if (Math.abs(dCol) !== 2 || Math.abs(dRow) !== 2) return false;
        
        // Midpoint obstacle (cản mắt Tượng)
        const midCol = fCol + dCol / 2;
        const midRow = fRow + dRow / 2;
        if (grid.get(`${midCol}_${midRow}`)) return false;
        
        // River boundaries: red row <= 4, black row >= 5
        if (subMode === "classic" || piece.is_face_down) {
            if (piece.color === "red" && tRow > 4) return false;
            if (piece.color === "black" && tRow < 5) return false;
        }
        return true;
    }
    
    // 4. Horse Rules
    if (activeType === "horse") {
        if (Math.abs(dCol) === 1 && Math.abs(dRow) === 2) {
            // Vertical leg blocker
            const obsRow = fRow + dRow / 2;
            return !grid.get(`${fCol}_${obsRow}`);
        } else if (Math.abs(dCol) === 2 && Math.abs(dRow) === 1) {
            // Horizontal leg blocker
            const obsCol = fCol + dCol / 2;
            return !grid.get(`${obsCol}_${fRow}`);
        }
        return false;
    }
    
    // 5. Chariot Rules (Xe)
    if (activeType === "chariot") {
        if (dCol !== 0 && dRow !== 0) return false;
        return countObstacles(fCol, fRow, tCol, tRow) === 0;
    }
    
    // 6. Cannon Rules (Pháo)
    if (activeType === "cannon") {
        if (dCol !== 0 && dRow !== 0) return false;
        const obs = countObstacles(fCol, fRow, tCol, tRow);
        if (!targetPiece) {
            return obs === 0;
        } else {
            return obs === 1; // Needs screen (Ngòi)
        }
    }
    
    // 7. Soldier Rules (Tốt)
    if (activeType === "soldier") {
        if (Math.abs(dCol) + Math.abs(dRow) !== 1) return false;
        if (piece.color === "red") {
            if (dRow < 0) return false; // Never backward
            if (fRow <= 4 && dCol !== 0) return false; // No sideways before river
        } else {
            if (dRow > 0) return false; // Never backward
            if (fRow >= 5 && dCol !== 0) return false; // No sideways before river
        }
        return true;
    }
    
    return false;
}

function countObstacles(fCol, fRow, tCol, tRow) {
    let count = 0;
    const dCol = tCol - fCol;
    const dRow = tRow - fRow;
    
    if (dCol !== 0) {
        const step = dCol > 0 ? 1 : -1;
        for (let c = fCol + step; c !== tCol; c += step) {
            if (grid.get(`${c}_${fRow}`)) count++;
        }
    } else {
        const step = dRow > 0 ? 1 : -1;
        for (let r = fRow + step; r !== tRow; r += step) {
            if (grid.get(`${fCol}_${r}`)) count++;
        }
    }
    return count;
}

// --------------------------------------------------------------------------
// Local Simulated Engine AI
// --------------------------------------------------------------------------
function executeSimulatedBotMove() {
    if (gameState !== "playing" || currentTurn !== "black") return;
    
    // Gather all legal black moves
    const botMoves = [];
    for (const [coord, piece] of grid.entries()) {
        if (piece.color === "black") {
            const [c, r] = coord.split("_").map(Number);
            for (let tc = 0; tc < 9; tc++) {
                for (let tr = 0; tr < 10; tr++) {
                    if (isLocalMoveValid(c, r, tc, tr)) {
                        botMoves.push({ from: {col: c, row: r}, to: {col: tc, row: tr} });
                    }
                }
            }
        }
    }
    
    if (botMoves.length > 0) {
        // Simple random move executor (highly performant responsive sandbox fallback!)
        const move = botMoves[Math.floor(Math.random() * botMoves.length)];
        executeLocalMove(move.from.col, move.from.row, move.to.col, move.to.row);
    } else {
        gameState = "finished";
        soundGameOver();
        updateStatus("Hết nước đi! Máy chịu hàng. BẠN CHIẾN THẮNG!");
    }
}

// --------------------------------------------------------------------------
// Online PvP WebSockets Integration
// --------------------------------------------------------------------------
function connectToServer() {
    const wsUrl = "ws://localhost:8000";
    updateStatus("Đang kết nối tới server game...");
    
    socket = new WebSocket(`${wsUrl}/ws/${sessionId}`);
    
    socket.onopen = () => {
        updateStatus("Đã Kết nối Server! Hãy tạo hoặc vào phòng.");
        document.getElementById("btn-connect").classList.add("hidden");
        document.getElementById("room-actions").classList.remove("hidden");
        addChatLog("Hệ thống", "Đã kết nối thành công tới máy chủ trực tuyến.");
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const evType = data.event;
        
        if (evType === "connected") {
            // session confirmation
        } else if (evType === "room_state") {
            const room = data.room;
            roomCode = room.room_id;
            subMode = room.mode;
            currentTurn = room.turn;
            
            // Sync toggle UI button states
            document.getElementById("btn-mode-classic").className = subMode === "classic" ? "btn-toggle active" : "btn-toggle";
            document.getElementById("btn-mode-co_up").className = subMode === "co_up" ? "btn-toggle active" : "btn-toggle";
            
            // Assign active colors
            const players = room.players;
            if (players.red === sessionId) {
                playerColor = "red";
                updateStatus(`Phòng ${roomCode}: Lượt của Đỏ ${currentTurn === "red" ? "(Bạn)" : "(Đối thủ)"}`);
            } else if (players.black === sessionId) {
                playerColor = "black";
                updateStatus(`Phòng ${roomCode}: Lượt của Đen ${currentTurn === "black" ? "(Bạn)" : "(Đối thủ)"}`);
            } else {
                playerColor = "spectator";
                updateStatus(`Đang Xem Phòng ${roomCode} (${currentTurn.toUpperCase()})`);
            }
            
            // Reconstruct web board completely from server JSON sync payload
            grid.clear();
            for (const item of room.board) {
                const c = item.col;
                const r = item.row;
                grid.set(`${c}_${r}`, {
                    id: item.id,
                    color: item.color,
                    type: item.type,
                    is_face_down: item.is_face_down,
                    real_type: item.type
                });
            }
            
            if (room.state === "playing") {
                gameState = "playing";
            } else if (room.state === "finished") {
                gameState = "finished";
                soundGameOver();
                updateStatus(`Ván đấu kết thúc! Người thắng: ${room.winner.toUpperCase()}`);
            }
            
            renderBoard();
            
        } else if (evType === "move_made") {
            soundPluck();
        } else if (evType === "check") {
            checkedGeneralColor = data.color;
            soundCheck();
            updateStatus(`CẢNH BÁO: TƯỚNG ${data.color.toUpperCase()} ĐANG BỊ CHIẾU!`);
            renderBoard();
        } else if (evType === "game_over") {
            gameState = "finished";
            soundGameOver();
            updateStatus(`Trận đấu kết thúc! Người thắng: ${data.winner.toUpperCase()} (${data.result})`);
            addChatLog("Trọng tài", `Trận đấu kết thúc. Người thắng: ${data.winner.toUpperCase()} (${data.result})`);
        } else if (evType === "chat") {
            addChatLog(data.sender, data.message);
        } else if (evType === "undo_requested") {
            addChatLog("Yêu cầu", "Đối thủ yêu cầu Quay lại nước đi (Undo). Đang chờ phản hồi.");
            updateStatus("Yêu cầu Undo. Hãy nhấn đồng ý hoặc từ chối.");
        } else if (evType === "undo_done") {
            addChatLog("Hệ thống", "Đã thu hồi nước đi thành công.");
        } else if (evType === "error") {
            addChatLog("Lỗi", data.message);
        }
    };
    
    socket.onclose = () => {
        updateStatus("Mất kết nối máy chủ.");
        document.getElementById("btn-connect").classList.remove("hidden");
        document.getElementById("room-actions").classList.add("hidden");
    };
}

function createRoom() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            action: "create_room",
            mode: subMode
        }));
    }
}

function joinRoom() {
    const code = document.getElementById("room-code-input").value.trim().toUpperCase();
    if (!code) return;
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            action: "join_room",
            room_id: code
        }));
    }
}

// --------------------------------------------------------------------------
// UI State Controls (Undo, Reset, Chat, Toggles)
// --------------------------------------------------------------------------
function startGameMode(mode) {
    initAudio();
    gameMode = mode;
    
    document.getElementById("menu-screen").classList.remove("active");
    document.getElementById("game-screen").classList.add("active");
    
    // Switch visual panels
    if (gameMode === "PvE") {
        document.getElementById("pve-settings").classList.remove("hidden");
        document.getElementById("pvp-settings").classList.add("hidden");
        addChatLog("Hệ thống", "Chế độ Đấu với Máy (PvE). Nhấp một quân cờ để di chuyển.");
        
        // Initial setup
        triggerReset();
    } else {
        document.getElementById("pve-settings").classList.add("hidden");
        document.getElementById("pvp-settings").classList.remove("hidden");
        addChatLog("Hệ thống", "Chế độ Đấu Mạng (PvP). Hãy nhấp nút Kết nối Server Game.");
        
        // In PvP, wait for server
        grid.clear();
        renderBoard();
    }
}

function exitToMenu() {
    if (socket) {
        socket.close();
        socket = null;
    }
    document.getElementById("game-screen").classList.remove("active");
    document.getElementById("menu-screen").classList.add("active");
}

function setSubMode(mode) {
    if (gameMode === "PvE" && moveHistory.length === 0) {
        subMode = mode;
        document.getElementById("btn-mode-classic").className = subMode === "classic" ? "btn-toggle active" : "btn-toggle";
        document.getElementById("btn-mode-co_up").className = subMode === "co_up" ? "btn-toggle active" : "btn-toggle";
        triggerReset();
    }
}

function setDifficulty(diff) {
    aiDifficulty = diff;
    document.getElementById("btn-diff-easy").className = aiDifficulty === "easy" ? "btn-toggle active" : "btn-toggle";
    document.getElementById("btn-diff-medium").className = aiDifficulty === "medium" ? "btn-toggle active" : "btn-toggle";
    document.getElementById("btn-diff-hard").className = aiDifficulty === "hard" ? "btn-toggle active" : "btn-toggle";
}

function triggerUndo() {
    if (gameMode === "PvE") {
        // Offline sandbox rollback: 2 steps for players, 1 step for machine
        const steps = moveHistory.length >= 2 ? 2 : 1;
        for (let i = 0; i < steps; i++) {
            if (moveHistory.length > 0) {
                const last = moveHistory.pop();
                const fromCoord = `${last.from.col}_${last.from.row}`;
                const toCoord = `${last.to.col}_${last.to.row}`;
                
                const piece = grid.get(toCoord);
                grid.delete(toCoord);
                
                if (piece) {
                    if (last.was_face_down) {
                        piece.is_face_down = true;
                        piece.type = piece.pseudo_type || "soldier";
                    }
                    grid.set(fromCoord, piece);
                }
                
                if (last.captured) {
                    grid.set(toCoord, last.captured);
                }
            }
        }
        currentTurn = "red";
        gameState = "playing";
        checkedGeneralColor = null;
        updateStatus("Đã hoàn tác (Undo). Lượt của Đỏ.");
        renderBoard();
    } else {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: "request_undo" }));
        }
    }
}

function triggerReset() {
    if (gameMode === "PvE") {
        if (subMode === "co_up") {
            setupCoUp();
        } else {
            setupClassic();
        }
    } else {
        // PvP reset currently clears board locally and lets server restart
    }
}

function toggleModal(id, show) {
    const modal = document.getElementById(id);
    if (modal) {
        if (show) modal.classList.add("active");
        else modal.classList.remove("active");
    }
}

function addChatLog(sender, text) {
    const consoleDiv = document.getElementById("chat-console");
    if (!consoleDiv) return;
    
    const msg = document.createElement("div");
    msg.className = "chat-message chat";
    if (sender === "Hệ thống" || sender === "Yêu cầu") {
        msg.className = "chat-message system";
    }
    
    msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
    consoleDiv.appendChild(msg);
    
    // Auto scroll bottom
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}

function handleChatSubmit(e) {
    if (e.key === "Enter") {
        sendChatMessage();
    }
}

function sendChatMessage() {
    const input = document.getElementById("chat-input");
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    
    if (gameMode === "PvE") {
        addChatLog("Bạn", text);
        input.value = "";
    } else {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                action: "chat",
                message: text
            }));
            input.value = "";
        }
    }
}

function updateStatus(msg) {
    const statusText = document.getElementById("status-message");
    if (statusText) statusText.textContent = msg;
}

// --------------------------------------------------------------------------
// On Page Load Bootstraps
// --------------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
    drawSvgGrid();
    setupClassic(); // Default starting screen view
});
