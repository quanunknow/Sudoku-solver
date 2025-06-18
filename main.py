import pygame
import sys
import textwrap
from pygame.locals import *

# Constants
BASE_WIDTH = 600
WIDTH_SCALE = 1.15
LOG_PANEL_WIDTH = 200
WINDOW_WIDTH = int(BASE_WIDTH * WIDTH_SCALE) + LOG_PANEL_WIDTH
WINDOW_HEIGHT = 700
GRID_SIZE = 9
CELL_SIZE = 540 // GRID_SIZE
GRID_ORIGIN = ((WINDOW_WIDTH - LOG_PANEL_WIDTH - CELL_SIZE * GRID_SIZE) // 2, 30)
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 100
BUTTON_MARGIN = 10
BUTTON_Y = GRID_ORIGIN[1] + GRID_SIZE * CELL_SIZE + 20
FONT_SIZE = 30
NOTE_FONT_SIZE = 18
POPUP_PADDING = 20
HIGHLIGHT_COLOR = (200, 200, 255)
SAME_NUM_HIGHLIGHT = (200, 255, 200)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (130, 130, 130)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
LIGHT_BLUE = (173, 216, 230)
BUTTON_RED = (255, 100, 100)
BUTTON_GREEN = (100, 255, 100)
LOG_BG = (240, 240, 240)
LOG_TEXT_COLOR = BLACK

BUTTONS = ["Lock/Unlock", "Solve", "Next", "Note", "Clear All"]
MAX_LOG_ENTRIES = 6

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Sudoku Solver")
font = pygame.font.SysFont(None, FONT_SIZE)
note_font = pygame.font.SysFont(None, NOTE_FONT_SIZE)

# Board cell representation
def make_empty_board():
    board = []
    for r in range(GRID_SIZE):
        row = []
        for c in range(GRID_SIZE):
            row.append({
                'value': 0,
                'given': False,
                'notes': set(),
                'correct': None
            })
        board.append(row)
    return board

board = make_empty_board()
locked = False
note_mode = False
selected = (0, 0)
solution = None
start_ticks = None
elapsed_time = None
popup_text = ""
popup_buttons = []
popup_active = False
popup_clicks = []
notes_initialized = False
# Log entries fixed size
log_entries = []

# Button rectangles
def make_button_rects():
    rects = []
    widths = []
    for label in BUTTONS:
        if label == "Lock/Unlock": widths.append(140)
        else: widths.append(BUTTON_WIDTH)
    total_width = sum(widths) + (len(BUTTONS) - 1) * BUTTON_MARGIN
    start_x = GRID_ORIGIN[0] + (CELL_SIZE * GRID_SIZE - total_width) // 2
    x = start_x
    for i, label in enumerate(BUTTONS):
        w = widths[i]
        rect = pygame.Rect(x, BUTTON_Y, w, BUTTON_HEIGHT)
        rects.append((rect, label))
        x += w + BUTTON_MARGIN
    return rects

button_rects = make_button_rects()

# Solver utilities
def find_empty(bd):
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if bd[i][j] == 0: return i, j
    return None

def valid(bd, num, pos):
    r, c = pos
    for j in range(GRID_SIZE):
        if bd[r][j] == num and j != c: return False
    for i in range(GRID_SIZE):
        if bd[i][c] == num and i != r: return False
    box_x = (c // 3) * 3
    box_y = (r // 3) * 3
    for i in range(box_y, box_y + 3):
        for j in range(box_x, box_x + 3):
            if bd[i][j] == num and (i, j) != pos: return False
    return True

def solve_backtrack(bd):
    empty = find_empty(bd)
    if not empty: return True
    r, c = empty
    for num in range(1, 10):
        if valid(bd, num, (r, c)):
            bd[r][c] = num
            if solve_backtrack(bd): return True
            bd[r][c] = 0
    return False

def board_solvable(bd):
    given_count = sum(1 for i in range(GRID_SIZE) for j in range(GRID_SIZE) if bd[i][j] != 0)
    if given_count < 17: return False
    temp = [[bd[i][j] for j in range(GRID_SIZE)] for i in range(GRID_SIZE)]
    return solve_backtrack(temp)

def compute_solution(bd):
    temp = [[bd[i][j] for j in range(GRID_SIZE)] for i in range(GRID_SIZE)]
    if solve_backtrack(temp): return temp
    return None

def get_candidates(bd, r, c):
    if bd[r][c] != 0: return []
    candidates = set(range(1, 10))
    for j in range(GRID_SIZE):
        if bd[r][j] in candidates: candidates.remove(bd[r][j])
    for i in range(GRID_SIZE):
        if bd[i][c] in candidates: candidates.remove(bd[i][c])
    box_x = (c // 3) * 3
    box_y = (r // 3) * 3
    for i in range(box_y, box_y + 3):
        for j in range(box_x, box_x + 3):
            if bd[i][j] in candidates: candidates.discard(bd[i][j])
    return sorted(candidates)

# Techniques
def find_hidden_single(bd):
    for i in range(GRID_SIZE):
        empties = [j for j in range(GRID_SIZE) if bd[i][j] == 0]
        if not empties: continue
        cand_map = {j: get_candidates(bd, i, j) for j in empties}
        for val in range(1, 10):
            positions = [j for j in empties if val in cand_map[j]]
            if len(positions) == 1:
                j = positions[0]
                explanation = f"Row {i+1} only cell ({i+1},{j+1}) can be {val}."
                return i, j, val, explanation
    for j in range(GRID_SIZE):
        empties = [i for i in range(GRID_SIZE) if bd[i][j] == 0]
        if not empties: continue
        cand_map = {i: get_candidates(bd, i, j) for i in empties}
        for val in range(1, 10):
            positions = [i for i in empties if val in cand_map[i]]
            if len(positions) == 1:
                i = positions[0]
                explanation = f"Column {j+1} only cell ({i+1},{j+1}) can be {val}."
                return i, j, val, explanation
    for box_row in range(3):
        for box_col in range(3):
            cells = []
            for di in range(3):
                for dj in range(3):
                    i = box_row*3 + di; j = box_col*3 + dj
                    if bd[i][j] == 0: cells.append((i,j))
            if not cells: continue
            cand_map = {(i,j): get_candidates(bd, i, j) for (i,j) in cells}
            for val in range(1, 10):
                positions = [(i,j) for (i,j) in cells if val in cand_map[(i,j)]]
                if len(positions) == 1:
                    i,j = positions[0]
                    explanation = f"Box centered at ({box_row*3+2},{box_col*3+2}) only cell ({i+1},{j+1}) can be {val}."
                    return i, j, val, explanation
    return None

def find_naked_pair():
    for i in range(GRID_SIZE):
        empties = [(i,j) for j in range(GRID_SIZE) if board[i][j]['value']==0]
        pairs = {}
        for (r,c) in empties:
            notes = board[r][c]['notes']
            if len(notes)==2:
                key = frozenset(notes)
                pairs.setdefault(key, []).append((r,c))
        for key, cells in pairs.items():
            if len(cells)==2:
                affected = []
                for j in range(GRID_SIZE):
                    if (i,j) not in cells and board[i][j]['value']==0 and board[i][j]['notes'] & key:
                        affected.append((i,j))
                if affected:
                    explanation = f"Naked pair {set(key)} in row {i+1}, remove from other cells."
                    return ('row', i, key, affected, explanation)
    for j in range(GRID_SIZE):
        empties = [(i,j) for i in range(GRID_SIZE) if board[i][j]['value']==0]
        pairs = {}
        for (r,c) in empties:
            notes = board[r][c]['notes']
            if len(notes)==2:
                key = frozenset(notes)
                pairs.setdefault(key, []).append((r,c))
        for key, cells in pairs.items():
            if len(cells)==2:
                affected = []
                for i in range(GRID_SIZE):
                    if (i,j) not in cells and board[i][j]['value']==0 and board[i][j]['notes'] & key:
                        affected.append((i,j))
                if affected:
                    explanation = f"Naked pair {set(key)} in column {j+1}, remove from other cells."
                    return ('col', j, key, affected, explanation)
    for box_row in range(3):
        for box_col in range(3):
            cells = []
            for di in range(3):
                for dj in range(3):
                    i = box_row*3+di; j = box_col*3+dj
                    if board[i][j]['value']==0: cells.append((i,j))
            pairs = {}
            for (r,c) in cells:
                notes = board[r][c]['notes']
                if len(notes)==2:
                    key = frozenset(notes)
                    pairs.setdefault(key, []).append((r,c))
            for key, pcells in pairs.items():
                if len(pcells)==2:
                    affected = []
                    for (i,j) in cells:
                        if (i,j) not in pcells and board[i][j]['value']==0 and board[i][j]['notes'] & key:
                            affected.append((i,j))
                    if affected:
                        explanation = f"Naked pair {set(key)} in box centered at ({box_row*3+2},{box_col*3+2}), remove from other cells."
                        return ('box', (box_row,box_col), key, affected, explanation)
    return None

def find_naked_trio():
    from itertools import combinations
    for i in range(GRID_SIZE):
        empties = [(i,j) for j in range(GRID_SIZE) if board[i][j]['value']==0 and board[i][j]['notes']]
        for combo in combinations(empties, 3):
            union = set().union(*(board[r][c]['notes'] for r,c in combo))
            if len(union) == 3:
                affected = []
                for j in range(GRID_SIZE):
                    if (i,j) not in combo and board[i][j]['value']==0 and board[i][j]['notes'] & union:
                        affected.append((i,j))
                if affected:
                    explanation = f"Naked trio {union} in row {i+1}, remove from other cells."
                    return ('row', i, union, affected, explanation)
    for j in range(GRID_SIZE):
        empties = [(i,j) for i in range(GRID_SIZE) if board[i][j]['value']==0 and board[i][j]['notes']]
        for combo in combinations(empties, 3):
            union = set().union(*(board[r][c]['notes'] for r,c in combo))
            if len(union) == 3:
                affected = []
                for i in range(GRID_SIZE):
                    if (i,j) not in combo and board[i][j]['value']==0 and board[i][j]['notes'] & union:
                        affected.append((i,j))
                if affected:
                    explanation = f"Naked trio {union} in column {j+1}, remove from other cells."
                    return ('col', j, union, affected, explanation)
    for box_row in range(3):
        for box_col in range(3):
            cells = []
            for di in range(3):
                for dj in range(3):
                    i = box_row*3+di; j = box_col*3+dj
                    if board[i][j]['value']==0 and board[i][j]['notes']:
                        cells.append((i,j))
            for combo in combinations(cells, 3):
                union = set().union(*(board[r][c]['notes'] for r,c in combo))
                if len(union) == 3:
                    affected = []
                    for (i,j) in cells:
                        if (i,j) not in combo and board[i][j]['notes'] & union:
                            affected.append((i,j))
                    if affected:
                        explanation = f"Naked trio {union} in box centered at ({box_row*3+2},{box_col*3+2}), remove from other cells."
                        return ('box', (box_row,box_col), union, affected, explanation)
    return None

def find_single_note_correct():
    if not solution: return None
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if board[i][j]['value'] == 0 and len(board[i][j]['notes']) == 1:
                val = next(iter(board[i][j]['notes']))
                if solution[i][j] == val: return i, j, val
    return None

# Logging
def append_log(msg):
    global log_entries
    if len(log_entries) >= MAX_LOG_ENTRIES:
        log_entries.pop(0)
    log_entries.append(msg)

# Draw grid with borders on top of highlights
def draw_grid():
    pygame.draw.rect(screen, WHITE, (GRID_ORIGIN[0], GRID_ORIGIN[1], CELL_SIZE*GRID_SIZE, CELL_SIZE*GRID_SIZE))
    sel_r, sel_c = selected
    sel_cell_val = board[sel_r][sel_c]['value']
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            x = GRID_ORIGIN[0] + c * CELL_SIZE
            y = GRID_ORIGIN[1] + r * CELL_SIZE
            rect = pygame.Rect(x+1, y+1, CELL_SIZE-2, CELL_SIZE-2)
            if (r, c) == (sel_r, sel_c): pygame.draw.rect(screen, HIGHLIGHT_COLOR, rect)
            if sel_cell_val != 0 and (r, c) != (sel_r, sel_c):
                if r == sel_r or c == sel_c or (r//3 == sel_r//3 and c//3 == sel_c//3): pygame.draw.rect(screen, HIGHLIGHT_COLOR, rect)
                if sel_cell_val is not None and board[r][c]['value'] == sel_cell_val and (r,c) != (sel_r,sel_c): pygame.draw.rect(screen, SAME_NUM_HIGHLIGHT, rect)
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            cell = board[r][c]
            x = GRID_ORIGIN[0] + c * CELL_SIZE
            y = GRID_ORIGIN[1] + r * CELL_SIZE
            if cell['value'] != 0:
                text_color = BLACK if not locked or cell['given'] else BLUE
                text = font.render(str(cell['value']), True, text_color)
                text_rect = text.get_rect(center=(x + CELL_SIZE // 2, y + CELL_SIZE // 2))
                screen.blit(text, text_rect)
            else:
                notes = sorted(cell['notes'])
                for n in notes:
                    idx = n - 1; nr = idx // 3; nc = idx % 3
                    sx = x + nc * CELL_SIZE / 3 + 3; sy = y + nr * CELL_SIZE / 3 + 3
                    note_text = note_font.render(str(n), True, GREY)
                    screen.blit(note_text, (sx, sy))
    # Draw grid lines on top
    for r in range(GRID_SIZE+1):
        width = 4 if r % 3 == 0 else 1
        pygame.draw.line(screen, BLACK,
                         (GRID_ORIGIN[0], GRID_ORIGIN[1] + r * CELL_SIZE),
                         (GRID_ORIGIN[0] + GRID_SIZE * CELL_SIZE, GRID_ORIGIN[1] + r * CELL_SIZE), width)
    for c in range(GRID_SIZE+1):
        width = 4 if c % 3 == 0 else 1
        pygame.draw.line(screen, BLACK,
                         (GRID_ORIGIN[0] + c * CELL_SIZE, GRID_ORIGIN[1]),
                         (GRID_ORIGIN[0] + c * CELL_SIZE, GRID_ORIGIN[1] + GRID_SIZE * CELL_SIZE), width)
    pygame.draw.rect(screen, BLACK, (GRID_ORIGIN[0] - 2, GRID_ORIGIN[1] - 2, CELL_SIZE * GRID_SIZE + 4, CELL_SIZE * GRID_SIZE + 4), 3)

# Draw buttons
def draw_buttons():
    for rect, label in button_rects:
        if label == "Lock/Unlock": bg = BUTTON_GREEN if locked else BUTTON_RED
        elif label == "Note": bg = BUTTON_GREEN if note_mode else BUTTON_RED
        else: bg = LIGHT_BLUE
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, BLACK, rect, 2)
        text = font.render(label, True, BLACK)
        text_rect = text.get_rect(center=rect.center)
        screen.blit(text, text_rect)

# Draw timer
def draw_timer():
    if start_ticks is not None or elapsed_time is not None:
        if elapsed_time is None and locked: elapsed = (pygame.time.get_ticks() - start_ticks) // 1000
        else: elapsed = elapsed_time
        mins = elapsed // 60; secs = elapsed % 60
        timer_text = font.render(f"Time: {mins:02d}:{secs:02d}", True, BLACK)
        screen.blit(timer_text, (GRID_ORIGIN[0], GRID_ORIGIN[1] + GRID_SIZE * CELL_SIZE + BUTTON_HEIGHT + 40))

# Draw log panel without scrolling
def draw_log_panel():
    panel_x = GRID_ORIGIN[0] + GRID_SIZE*CELL_SIZE + 30
    panel_y = 10
    panel_w = LOG_PANEL_WIDTH - 20
    panel_h = WINDOW_HEIGHT - 20
    pygame.draw.rect(screen, LOG_BG, (panel_x, panel_y, panel_w, panel_h))
    title_surf = font.render("Log", True, BLACK)
    screen.blit(title_surf, (panel_x + 5, panel_y + 5))
    line_height = NOTE_FONT_SIZE + 4
    y = panel_y + 30
    for text in log_entries:
        wrapped = textwrap.wrap(text, width=20)
        for part in wrapped:
            entry_surf = note_font.render(part, True, LOG_TEXT_COLOR)
            screen.blit(entry_surf, (panel_x + 5, y))
            y += line_height
            if y > panel_y + panel_h - line_height: return

# Popup functions
def show_message(text):
    global popup_active, popup_text, popup_buttons
    popup_active = True
    popup_text = text
    popup_buttons = []

def confirm_action(text, yes_callback, no_callback):
    global popup_active, popup_text, popup_buttons
    popup_active = True
    popup_text = text
    popup_buttons = [(yes_callback, no_callback)]

def close_popup():
    global popup_active, popup_buttons
    popup_active = False
    popup_buttons = []

def draw_popup():
    max_w = WINDOW_WIDTH - 2 * POPUP_PADDING
    words = popup_text.split()
    lines = []
    line = ''
    for word in words:
        test = line + ' ' + word if line else word
        w, _ = font.size(test)
        if w <= max_w - 2*POPUP_PADDING: line = test
        else:
            lines.append(line); line = word
    if line: lines.append(line)
    text_h = len(lines) * (FONT_SIZE + 5)
    box_w = min(max(font.size(l)[0] for l in lines) + 2*POPUP_PADDING, max_w)
    btn_h = BUTTON_HEIGHT
    is_confirm = bool(popup_buttons and isinstance(popup_buttons[0], tuple))
    box_h = text_h + POPUP_PADDING*2 + btn_h + POPUP_PADDING
    box_x = GRID_ORIGIN[0] + CELL_SIZE*GRID_SIZE - box_w - POPUP_PADDING
    box_y = (WINDOW_HEIGHT - box_h) // 2
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0, 0))
    pygame.draw.rect(screen, WHITE, (box_x, box_y, box_w, box_h)); pygame.draw.rect(screen, BLACK, (box_x, box_y, box_w, box_h), 2)
    for i, l in enumerate(lines):
        text_surf = font.render(l, True, BLACK)
        screen.blit(text_surf, (box_x + POPUP_PADDING, box_y + POPUP_PADDING + i*(FONT_SIZE+5)))
    popup_clicks.clear()
    if is_confirm:
        yes_cb, no_cb = popup_buttons[0]
        btn_w = 80; total_w = btn_w*2 + BUTTON_MARGIN
        start_x = box_x + (box_w - total_w)//2; y = box_y + POPUP_PADDING + text_h + POPUP_PADDING
        yes_rect = pygame.Rect(start_x, y, btn_w, btn_h)
        no_rect = pygame.Rect(start_x+btn_w+BUTTON_MARGIN, y, btn_w, btn_h)
        for rect, label, cb in [(yes_rect, "Yes", yes_cb), (no_rect, "No", no_cb)]:
            pygame.draw.rect(screen, LIGHT_BLUE, rect); pygame.draw.rect(screen, BLACK, rect, 2)
            text_surf = font.render(label, True, BLACK); screen.blit(text_surf, text_surf.get_rect(center=rect.center))
            popup_clicks.append((rect, label, cb))
    else:
        btn_w = 80; x = box_x + (box_w - btn_w)//2; y = box_y + POPUP_PADDING + text_h + POPUP_PADDING
        ok_rect = pygame.Rect(x, y, btn_w, btn_h)
        pygame.draw.rect(screen, LIGHT_BLUE, ok_rect); pygame.draw.rect(screen, BLACK, ok_rect, 2)
        text_surf = font.render("OK", True, BLACK); screen.blit(text_surf, text_surf.get_rect(center=ok_rect.center))
        popup_clicks.append((ok_rect, "OK", close_popup))

# Handlers
def handle_lock_unlock():
    global locked, solution, start_ticks, elapsed_time, notes_initialized
    if not locked:
        bd = [[board[i][j]['value'] for j in range(GRID_SIZE)] for i in range(GRID_SIZE)]
        if not board_solvable(bd): show_message("Puzzle unsolvable! Check givens."); return
        sol = compute_solution(bd)
        if sol is None: show_message("Puzzle unsolvable! Check givens."); return
        solution = sol; locked = True
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if board[i][j]['value'] != 0: board[i][j]['given'] = True
                board[i][j]['correct'] = None; board[i][j]['notes'].clear()
        start_ticks = pygame.time.get_ticks(); elapsed_time = None; notes_initialized = False
        append_log("Puzzle locked and solution computed.")
    else:
        locked = False
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE): board[i][j]['given'] = False; board[i][j]['correct'] = None; board[i][j]['notes'].clear()
        solution = None; start_ticks = None; elapsed_time = None; notes_initialized = False
        append_log("Puzzle unlocked.")

def ask_solve():
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE): board[i][j]['value'] = solution[i][j]; board[i][j]['correct'] = True
    global start_ticks, elapsed_time
    if start_ticks is not None: elapsed_time = (pygame.time.get_ticks() - start_ticks) // 1000; start_ticks = None
    append_log("Puzzle solved via Solve.")

def handle_solve():
    if not locked: show_message("Lock the puzzle first to solve."); return
    confirm_action("Solve puzzle? No explanations will be given and it may ruin your experience.", ask_solve, lambda: close_popup())

def remove_notes_on_fill(r, c, val):
    for i in range(GRID_SIZE): board[i][c]['notes'].discard(val)
    for j in range(GRID_SIZE): board[r][j]['notes'].discard(val)
    br = (r//3)*3; bc = (c//3)*3
    for di in range(3):
        for dj in range(3): board[br+di][bc+dj]['notes'].discard(val)

def handle_next():
    global notes_initialized, elapsed_time, start_ticks, selected
    if not locked: show_message("Lock the puzzle first to get next step."); return
    bd = [[board[i][j]['value'] for j in range(GRID_SIZE)] for i in range(GRID_SIZE)]
    # Naked single
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if bd[i][j] == 0:
                candidates = get_candidates(bd, i, j)
                if len(candidates) == 1:
                    val = candidates[0]
                    board[i][j]['value'] = val; remove_notes_on_fill(i, j, val); selected = (i, j)
                    append_log(f"Naked Single: Cell ({i+1},{j+1}) = {val}.")
                    if start_ticks is not None and all(board[r][c]['value'] != 0 for r in range(GRID_SIZE) for c in range(GRID_SIZE)):
                        elapsed_time = (pygame.time.get_ticks() - start_ticks) // 1000; start_ticks = None
                    return
    # Hidden single
    hs = find_hidden_single(bd)
    if hs:
        i,j,val,explanation_text = hs
        board[i][j]['value'] = val; remove_notes_on_fill(i, j, val); selected = (i, j)
        append_log("Hidden Single: " + explanation_text)
        if start_ticks is not None and all(board[r][c]['value'] != 0 for r in range(GRID_SIZE) for c in range(GRID_SIZE)):
            elapsed_time = (pygame.time.get_ticks() - start_ticks) // 1000; start_ticks = None
        return
    # Initialize notes
    if not notes_initialized:
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if board[i][j]['value'] == 0: board[i][j]['notes'] = set(get_candidates(bd, i, j))
        notes_initialized = True
        append_log("Initialized notes with all candidates.")
        return
    # Single note fill
    sn = find_single_note_correct()
    if sn:
        i,j,val = sn
        board[i][j]['value'] = val; remove_notes_on_fill(i, j, val); selected = (i, j)
        append_log(f"Single Note Fill: Cell ({i+1},{j+1}) = {val}.")
        if start_ticks is not None and all(board[r][c]['value'] != 0 for r in range(GRID_SIZE) for c in range(GRID_SIZE)):
            elapsed_time = (pygame.time.get_ticks() - start_ticks) // 1000; start_ticks = None
        return
    # Naked pair
    np = find_naked_pair()
    if np:
        unit, idx, pair, affected, explanation_text = np
        for (r,c) in affected: board[r][c]['notes'] -= pair
        append_log("Naked Pair: " + explanation_text)
        return
    # Naked trio
    nt = find_naked_trio()
    if nt:
        unit, idx, trio, affected, explanation_text = nt
        for (r,c) in affected: board[r][c]['notes'] -= trio
        append_log("Naked Trio: " + explanation_text)
        return
    append_log("No advanced technique found.")

def handle_note():
    global note_mode
    note_mode = not note_mode
    if locked: append_log(f"Note mode {'ON' if note_mode else 'OFF'}")

def clear_board():
    global board
    board = make_empty_board()

def handle_clear_all():
    if locked: show_message("Cannot clear while locked. Unlock first."); return
    def yes(): clear_board(); close_popup(); append_log("Board cleared.")
    def no(): close_popup()
    confirm_action("Clear all entries? This CAN'T be undone.", yes, no)

# Main loop
clock = pygame.time.Clock()
while True:
    for event in pygame.event.get():
        if event.type == QUIT: pygame.quit(); sys.exit()
        if popup_active:
            if event.type == MOUSEBUTTONDOWN:
                pos = event.pos
                for rect, label, callback in popup_clicks:
                    if rect.collidepoint(pos): callback()
            continue
        if event.type == MOUSEBUTTONDOWN:
            pos = event.pos; gx, gy = GRID_ORIGIN
            if gx <= pos[0] < gx + CELL_SIZE * GRID_SIZE and gy <= pos[1] < gy + CELL_SIZE * GRID_SIZE:
                c = (pos[0] - gx) // CELL_SIZE; r = (pos[1] - gy) // CELL_SIZE; selected = (r, c)
            for rect, label in button_rects:
                if rect.collidepoint(pos):
                    if label == "Lock/Unlock": handle_lock_unlock()
                    elif label == "Solve": handle_solve()
                    elif label == "Next": handle_next()
                    elif label == "Note": handle_note()
                    elif label == "Clear All": handle_clear_all()
        if event.type == KEYDOWN:
            r, c = selected; cell = board[r][c]
            if event.key in [K_UP, K_w]: selected = (max(r-1, 0), c)
            elif event.key in [K_DOWN, K_s]: selected = (min(r+1, GRID_SIZE-1), c)
            elif event.key in [K_LEFT, K_a]: selected = (r, max(c-1, 0))
            elif event.key in [K_RIGHT, K_d]: selected = (r, min(c+1, GRID_SIZE-1))
            elif K_1 <= event.key <= K_9:
                num = event.key - K_0
                if not locked: board[r][c]['value'] = num
                else:
                    if cell['given']: continue
                    if solution:
                        if num == solution[r][c]:
                            cell['value'] = num; remove_notes_on_fill(r, c, num); append_log(f"Filled cell ({r+1},{c+1}) = {num}.")
                        else:
                            show_message(f"Incorrect entry for cell ({r+1},{c+1}).")
                    else:
                        board[r][c]['value'] = num
            elif event.key in [K_BACKSPACE, K_DELETE, K_0]:
                if not locked: board[r][c]['value'] = 0
                else:
                    if cell['given']: continue
                    cell['value'] = 0
    screen.fill(WHITE)
    draw_grid(); draw_buttons(); draw_timer(); draw_log_panel()
    if popup_active: draw_popup()
    pygame.display.flip(); clock.tick(30)
