import pygame
import random
import math
import time

pygame.init()

# ---------------- SETTINGS ----------------
BLOCK_SIZE = 16
SCALE = 3
DISPLAY_SIZE = BLOCK_SIZE * SCALE
s = 0.045

VISIBLE_ROWS = 10
ROWS = 30
VISIBLE_COLS = 15
WINDOW_WIDTH = VISIBLE_COLS * DISPLAY_SIZE
WINDOW_HEIGHT = VISIBLE_ROWS * DISPLAY_SIZE
FPS = 60

PLAYER_SPEED = 4
GRAVITY = 0.5
JUMP_SPEED = -8
CAMERA_SPEED = 0.1

HOTBAR_SLOTS = 9
HOTBAR_SIZE = 40
HOTBAR_PADDING = 5
MAX_STACK = 64
HOTBAR_BLOCK_SCALE = 0.72

PICKUP_PADDING = 12

MAX_HP = 20
SAFE_FALL_BLOCKS = 3
DAMAGE_INVULN = 0.5
REGEN_INTERVAL = 4.0
REGEN_DELAY_AFTER_DAMAGE = 5.0
SUFFOCATION_INTERVAL = 1.0
HEART_SIZE = 18
HEART_PADDING = 3

INVENTORY_ROWS = 3
DESPAWN_TIME = 300

BREAK_TIMES = {
    "grass": 0.75,
    "dirt": 0.75,
    "wood": 1.5,
    "oak_planks": 1.5,
    "crafting_table": 1.5,
    "stone": 3.0,
    "leaves": 0.3,
}

# ---------------- SCREEN ----------------
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Mini Minecraft Smart Mining")

# ---------------- LOAD TEXTURES ----------------
grass_img = pygame.transform.scale(pygame.image.load("grass.png").convert_alpha(), (DISPLAY_SIZE, DISPLAY_SIZE))
dirt_img = pygame.transform.scale(pygame.image.load("dirt.png").convert_alpha(), (DISPLAY_SIZE, DISPLAY_SIZE))
stone_img = pygame.transform.scale(pygame.image.load("stone.png").convert_alpha(), (DISPLAY_SIZE, DISPLAY_SIZE))
wood_img = pygame.transform.scale(pygame.image.load("wood.png").convert_alpha(), (DISPLAY_SIZE, DISPLAY_SIZE))
leaves_img = pygame.transform.scale(pygame.image.load("leaves.png").convert_alpha(), (DISPLAY_SIZE, DISPLAY_SIZE))
oak_planks_img = pygame.transform.scale(pygame.image.load("oak_planks.png").convert_alpha(), (DISPLAY_SIZE, DISPLAY_SIZE))
crafting_table_img = pygame.transform.scale(pygame.image.load("crafting_table2.png").convert_alpha(), (DISPLAY_SIZE, DISPLAY_SIZE))

texture_map = {
    "grass": grass_img,
    "dirt": dirt_img,
    "stone": stone_img,
    "wood": wood_img,
    "leaves": leaves_img,
    "oak_planks": oak_planks_img,
    "crafting_table": crafting_table_img,
}

# ---------------- LOAD BREAKING ANIMATION ----------------
breaking_sheet = pygame.image.load("breaking_animation.png").convert_alpha()
sheet_w = breaking_sheet.get_width()
sheet_h = breaking_sheet.get_height()
frame_w = sheet_w // 2
frame_h = sheet_h // 3
breaking_frames = []

for row in range(3):
    for col in range(2):
        frame = breaking_sheet.subsurface(pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h))
        frame = pygame.transform.scale(frame, (DISPLAY_SIZE, DISPLAY_SIZE))

        # KEY CHANGE: Scan every pixel in this frame
        for x in range(frame.get_width()):
            for y in range(frame.get_height()):
                r, g, b, a = frame.get_at((x, y))
                # If Red, Green, and Blue are all above 200, it's white or light grey.
                # Adjust '200' lower (e.g., 180) if you still see grey bits remaining.
                if r > 200 and g > 200 and b > 200:
                    frame.set_at((x, y), (0, 0, 0, 0))  # Make it 100% transparent

        breaking_frames.append(frame)
# ---------------- BREAKING STATE ----------------
breaking_col = None
breaking_row = None
breaking_progress = 0.0  # 0.0 to 1.0
breaking_start_time = None

# ---------------- TREE HELPERS ----------------
pending_tree_leaves = []

LEAF_LAYOUT = [
    (0, 2),
    (-1, 2),
    (-2, 1),
    (-3, 0),
]

def place_trunk(col_blocks, surface_row, trunk_height):
    for i in range(1, trunk_height + 1):
        row = surface_row - i
        if 0 <= row < ROWS:
            col_blocks[row] = "wood"
    top_row = surface_row - trunk_height
    for dy, _ in LEAF_LAYOUT:
        leaf_row = top_row + dy
        if 0 <= leaf_row < ROWS and col_blocks[leaf_row] is None:
            col_blocks[leaf_row] = "leaves"

def apply_tree_leaves(abs_col, surface_row, trunk_height):
    top_row = surface_row - trunk_height
    for dy, radius in LEAF_LAYOUT:
        leaf_row = top_row + dy
        if not (0 <= leaf_row < ROWS):
            continue
        for dc in range(-radius, radius + 1):
            if dc == 0:
                continue
            target_abs = abs_col + dc
            target_rel = target_abs - leftmost_col
            if 0 <= target_rel < len(world_cols):
                if world_cols[target_rel][leaf_row] is None:
                    world_cols[target_rel][leaf_row] = "leaves"

def process_pending_tree_leaves():
    still_pending = []
    for (abs_col, surface_row, trunk_height) in pending_tree_leaves:
        needed = [abs_col + dc for dc in range(-2, 3)]
        all_exist = all(0 <= (nc - leftmost_col) < len(world_cols) for nc in needed)
        if all_exist:
            apply_tree_leaves(abs_col, surface_row, trunk_height)
        else:
            still_pending.append((abs_col, surface_row, trunk_height))
    pending_tree_leaves[:] = still_pending

# ---------------- INITIAL TERRAIN ----------------
world_cols = []
heights = []
dirt_depths = []
leftmost_col = 0

current_height = random.randint(18, 22)

for col in range(VISIBLE_COLS + 20):
    change = random.choice([-1, 0, 1])
    current_height = max(10, min(24, current_height + change))
    heights.append(current_height)
    dirt_depths.append(random.randint(1, 3))

    col_blocks = []
    for row in range(ROWS):
        h = heights[col]
        d = dirt_depths[col]
        if row < h:
            col_blocks.append(None)
        elif row == h:
            col_blocks.append("grass")
        elif row <= h + d:
            col_blocks.append("dirt")
        else:
            col_blocks.append("stone")

    world_cols.append(col_blocks)

    if random.random() < s:
        trunk_height = random.randint(3, 5)
        place_trunk(col_blocks, heights[col], trunk_height)
        pending_tree_leaves.append((col, heights[col], trunk_height))

process_pending_tree_leaves()

# ---------------- PLAYER ----------------
player_img = pygame.image.load("steve.png").convert_alpha()
for x in range(player_img.get_width()):
    for y in range(player_img.get_height()):
        r, g, b, a = player_img.get_at((x, y))
        if r > 200 and g > 200 and b > 200:
            player_img.set_at((x, y), (0, 0, 0, 0))

ratio = min(DISPLAY_SIZE / player_img.get_width(), (DISPLAY_SIZE * 1.9) / player_img.get_height())
player_img = pygame.transform.scale(player_img, (int(player_img.get_width() * ratio), int(player_img.get_height() * ratio)))

player_rect = player_img.get_rect()
spawn_col = WINDOW_WIDTH // 2 // DISPLAY_SIZE
player_rect.bottom = heights[spawn_col] * DISPLAY_SIZE
player_rect.centerx = WINDOW_WIDTH // 2
spawn_x = player_rect.centerx
spawn_y = player_rect.bottom
vy = 0

hp = MAX_HP
last_damage_time = 0.0
last_regen_time = 0.0
last_suffocation_time = 0.0
peak_top_y = None

# ---------------- CAMERA ----------------
cam_x, cam_y = 0, 0

# ---------------- HOTBAR + INVENTORY ----------------
hotbar = [{"item": None, "count": 0} for _ in range(HOTBAR_SLOTS)]
inventory = [[{"item": None, "count": 0} for _ in range(HOTBAR_SLOTS)] for _ in range(INVENTORY_ROWS)]
selected_slot = 0
inventory_open = False

# ---------------- CRAFTING ----------------
crafting_grid = [[{"item": None, "count": 0} for _ in range(3)] for _ in range(3)]
crafting_output = {"item": None, "count": 0}
held_item = {"item": None, "count": 0}

# NEW: Track if the player is using a 3x3 block or their 2x2 personal slots
crafting_mode = "2x2" # Can be "2x2" or "3x3"


def get_crafting_result():
    max_size = 2 if crafting_mode == "2x2" else 3

    # In 2x2 mode, ignore any items accidentally lingering in row 3 or column 3
    if crafting_mode == "2x2":
        for i in range(3):
            if crafting_grid[2][i]["item"] is not None or crafting_grid[i][2]["item"] is not None:
                return None, 0

    active_rows = []
    active_cols = []
    for r in range(max_size):
        for c in range(max_size):
            if crafting_grid[r][c]["item"] is not None:
                active_rows.append(r)
                active_cols.append(c)

    if not active_rows:
        return None, 0

    min_r, max_r = min(active_rows), max(active_rows)
    min_c, max_c = min(active_cols), max(active_cols)
    h = max_r - min_r + 1
    w = max_c - min_c + 1

    sub_grid = [[crafting_grid[min_r + r][min_c + c]["item"] for c in range(w)] for r in range(h)]
    flat_items = [crafting_grid[r][c]["item"] for r in range(max_size) for c in range(max_size) if
                  crafting_grid[r][c]["item"] is not None]

    if h == 2 and w == 2:
        if (sub_grid[0][0] == "oak_planks" and sub_grid[0][1] == "oak_planks" and
                sub_grid[1][0] == "oak_planks" and sub_grid[1][1] == "oak_planks"):
            return "crafting_table", 1

    if len(flat_items) == 1 and flat_items[0] == "wood":
        return "oak_planks", 4

    return None, 0


def consume_crafting():
    max_size = 2 if crafting_mode == "2x2" else 3
    for r in range(max_size):
        for c in range(max_size):
            if crafting_grid[r][c]["item"] is not None:
                crafting_grid[r][c]["count"] -= 1
                if crafting_grid[r][c]["count"] <= 0:
                    crafting_grid[r][c]["item"] = None
                    crafting_grid[r][c]["count"] = 0

def update_crafting_output():
    item, count = get_crafting_result()
    crafting_output["item"] = item
    crafting_output["count"] = count

def return_crafting_to_inventory():
    for r in range(3):
        for c in range(3):
            slot = crafting_grid[r][c]
            if slot["item"]:
                for _ in range(slot["count"]):
                    collect_block(slot["item"])
                slot["item"] = None
                slot["count"] = 0
    crafting_output["item"] = None
    crafting_output["count"] = 0
# ---------------- DROPPED BLOCKS ----------------
dropped_blocks = []

# ---------------- FUNCTIONS ----------------
def on_ground(rect):
    rect_below = rect.move(0, 1)
    for col_index, col_blocks in enumerate(world_cols):
        col_x = (col_index + leftmost_col) * DISPLAY_SIZE
        for row_index, block in enumerate(col_blocks):
            if block:
                block_rect = pygame.Rect(col_x, row_index * DISPLAY_SIZE, DISPLAY_SIZE, DISPLAY_SIZE)
                if rect_below.colliderect(block_rect):
                    return True
    return False

def generate_column(prev_height):
    change = random.choice([-1, 0, 1])
    new_height = max(10, min(24, prev_height + change))
    dirt_depth = random.randint(1, 3)
    col_blocks = []
    for row in range(ROWS):
        if row < new_height:
            col_blocks.append(None)
        elif row == new_height:
            col_blocks.append("grass")
        elif row <= new_height + dirt_depth:
            col_blocks.append("dirt")
        else:
            col_blocks.append("stone")
    return col_blocks, new_height, dirt_depth

def mine_block(col_idx, row_idx):
    if 0 <= col_idx < len(world_cols) and 0 <= row_idx < ROWS:
        block_type = world_cols[col_idx][row_idx]
        world_cols[col_idx][row_idx] = None
        if block_type == "grass":
            return "dirt"
        if block_type == "stone":
            return None
        if block_type == "leaves":
            return None
        return block_type
    return None

def get_mineable_block(head_x, head_y, mouse_col, mouse_row, max_distance):
    target_world_x = (mouse_col + leftmost_col) * DISPLAY_SIZE + DISPLAY_SIZE // 2
    target_world_y = mouse_row * DISPLAY_SIZE + DISPLAY_SIZE // 2
    dx = target_world_x - head_x
    dy = target_world_y - head_y
    distance = math.hypot(dx, dy)
    if distance == 0:
        return None
    dx /= distance
    dy /= distance
    step_size = 4
    distance_traveled = 0
    while distance_traveled < min(max_distance, distance):
        check_x = head_x + dx * distance_traveled
        check_y = head_y + dy * distance_traveled
        col = int(check_x // DISPLAY_SIZE) - leftmost_col
        row = int(check_y // DISPLAY_SIZE)
        if 0 <= col < len(world_cols) and 0 <= row < ROWS:
            if world_cols[col][row] is not None:
                if col == mouse_col and row == mouse_row:
                    return col, row
                else:
                    return None
        distance_traveled += step_size
    return None

def has_line_of_sight_to_cell(head_x, head_y, target_col, target_row):
    target_world_x = (target_col + leftmost_col) * DISPLAY_SIZE + DISPLAY_SIZE // 2
    target_world_y = target_row * DISPLAY_SIZE + DISPLAY_SIZE // 2
    dx = target_world_x - head_x
    dy = target_world_y - head_y
    distance = math.hypot(dx, dy)
    if distance == 0:
        return True
    dx /= distance
    dy /= distance
    step_size = 4
    distance_traveled = 0
    while distance_traveled < distance:
        check_x = head_x + dx * distance_traveled
        check_y = head_y + dy * distance_traveled
        col = int(check_x // DISPLAY_SIZE) - leftmost_col
        row = int(check_y // DISPLAY_SIZE)
        if col == target_col and row == target_row:
            return True
        if 0 <= col < len(world_cols) and 0 <= row < ROWS:
            if world_cols[col][row] is not None:
                return False
        distance_traveled += step_size
    return True

def has_adjacent_block(col, row):
    for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nc, nr = col + dc, row + dr
        if 0 <= nc < len(world_cols) and 0 <= nr < ROWS:
            if world_cols[nc][nr] is not None:
                return True
    return False

def collect_block(block_type):
    for slot in hotbar:
        if slot["item"] == block_type and slot["count"] < MAX_STACK:
            slot["count"] += 1
            return True
    for row in inventory:
        for slot in row:
            if slot["item"] == block_type and slot["count"] < MAX_STACK:
                slot["count"] += 1
                return True
    for slot in hotbar:
        if slot["item"] is None:
            slot["item"] = block_type
            slot["count"] = 1
            return True
    for row in inventory:
        for slot in row:
            if slot["item"] is None:
                slot["item"] = block_type
                slot["count"] = 1
                return True
    return False

def draw_heart(surf, x, y, size, fraction):
    empty_color = (60, 60, 60)
    full_color = (220, 30, 30)
    def shape(color):
        r = size // 4
        cy = y + size // 3
        pygame.draw.circle(surf, color, (x + size // 4, cy), r)
        pygame.draw.circle(surf, color, (x + 3 * size // 4, cy), r)
        pygame.draw.polygon(surf, color, [(x + 1, cy), (x + size - 1, cy), (x + size // 2, y + size - 1)])
    shape(empty_color)
    if fraction >= 1.0:
        shape(full_color)
    elif fraction >= 0.5:
        old_clip = surf.get_clip()
        surf.set_clip(pygame.Rect(x, y, size // 2, size))
        shape(full_color)
        surf.set_clip(old_clip)

def draw_slot(surf, rect, slot, highlight=False):
    pygame.draw.rect(surf, (100, 100, 100), rect)
    pygame.draw.rect(surf, (255, 255, 0) if highlight else (0, 0, 0), rect, 2)
    if slot and slot["item"]:
        block_size_px = int(rect.width * HOTBAR_BLOCK_SCALE)
        offset = (rect.width - block_size_px) // 2
        surf.blit(
            pygame.transform.scale(texture_map[slot["item"]], (block_size_px, block_size_px)),
            (rect.x + offset, rect.y + offset)
        )
        if slot["count"] > 1:
            font = pygame.font.SysFont(None, 20)
            count_text = font.render(str(slot["count"]), True, (255, 255, 255))
            surf.blit(count_text, (rect.right - count_text.get_width() - 2, rect.bottom - count_text.get_height() - 2))

def click_slot(slot, held):
    if held["item"] is None:
        held["item"] = slot["item"]
        held["count"] = slot["count"]
        slot["item"] = None
        slot["count"] = 0
    elif slot["item"] is None:
        slot["item"] = held["item"]
        slot["count"] = held["count"]
        held["item"] = None
        held["count"] = 0
    elif slot["item"] == held["item"] and slot["count"] < MAX_STACK:
        space = MAX_STACK - slot["count"]
        add = min(space, held["count"])
        slot["count"] += add
        held["count"] -= add
        if held["count"] <= 0:
            held["item"] = None
            held["count"] = 0
    else:
        slot["item"], held["item"] = held["item"], slot["item"]
        slot["count"], held["count"] = held["count"], slot["count"]

def right_click_slot(slot, held):
    if held["item"] is None:
        return
    if slot["item"] is None:
        slot["item"] = held["item"]
        slot["count"] = 1
        held["count"] -= 1
        if held["count"] <= 0:
            held["item"] = None
            held["count"] = 0
    elif slot["item"] == held["item"] and slot["count"] < MAX_STACK:
        slot["count"] += 1
        held["count"] -= 1
        if held["count"] <= 0:
            held["item"] = None
            held["count"] = 0

# ---------------- GAME LOOP ----------------
clock = pygame.time.Clock()
running = True
mouse_held = False

while running:
    dt = clock.tick(FPS)
    current_time = time.time()

    # -------- INVENTORY LAYOUT --------
    hotbar_total_width = HOTBAR_SLOTS * HOTBAR_SIZE + (HOTBAR_SLOTS - 1) * HOTBAR_PADDING
    hotbar_start_x = (WINDOW_WIDTH - hotbar_total_width) // 2
    hotbar_y = WINDOW_HEIGHT - HOTBAR_SIZE - 10

    inv_start_x = hotbar_start_x
    inv_start_y = hotbar_y - (INVENTORY_ROWS * (HOTBAR_SIZE + HOTBAR_PADDING)) - 10

    craft_cell = HOTBAR_SIZE + HOTBAR_PADDING
    craft_start_x = inv_start_x
    craft_start_y = inv_start_y - (3 * craft_cell) - 20 if crafting_mode == "3x3" else inv_start_y - (2 * craft_cell) - 20

    grid_width = 2 if crafting_mode == "2x2" else 3
    arrow_x = craft_start_x + grid_width * craft_cell + 6
    output_x = arrow_x + 24
    output_y = craft_start_y + craft_cell if crafting_mode == "3x3" else craft_start_y + (craft_cell // 2)


    # -------- EVENTS --------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                inventory_open = not inventory_open
                if not inventory_open:
                    return_crafting_to_inventory()
                    if held_item["item"]:
                        for _ in range(held_item["count"]):
                            collect_block(held_item["item"])
                        held_item["item"] = None
                        held_item["count"] = 0
            elif pygame.K_1 <= event.key <= pygame.K_9:
                selected_slot = event.key - pygame.K_1

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()

            if inventory_open:
                if event.button == 1:
                    clicked = False
                    for i, slot in enumerate(hotbar):
                        rect = pygame.Rect(hotbar_start_x + i * (HOTBAR_SIZE + HOTBAR_PADDING), hotbar_y, HOTBAR_SIZE, HOTBAR_SIZE)
                        if rect.collidepoint(mx, my):
                            click_slot(slot, held_item)
                            clicked = True
                            break
                    if not clicked:
                        for row_i, row in enumerate(inventory):
                            for col_i, slot in enumerate(row):
                                rect = pygame.Rect(
                                    inv_start_x + col_i * (HOTBAR_SIZE + HOTBAR_PADDING),
                                    inv_start_y + row_i * (HOTBAR_SIZE + HOTBAR_PADDING),
                                    HOTBAR_SIZE, HOTBAR_SIZE
                                )
                                if rect.collidepoint(mx, my):
                                    click_slot(slot, held_item)
                                    clicked = True
                                    break
                            if clicked:
                                break
                    if not clicked:
                        for r in range(2):
                            for c in range(2):
                                rect = pygame.Rect(craft_start_x + c * craft_cell, craft_start_y + r * craft_cell, HOTBAR_SIZE, HOTBAR_SIZE)
                                if rect.collidepoint(mx, my):
                                    click_slot(crafting_grid[r][c], held_item)
                                    update_crafting_output()
                                    clicked = True
                                    break
                            if clicked:
                                break
                    if not clicked:
                        out_rect = pygame.Rect(output_x, output_y, HOTBAR_SIZE, HOTBAR_SIZE)
                        if out_rect.collidepoint(mx, my) and crafting_output["item"]:
                            if held_item["item"] is None:
                                held_item["item"] = crafting_output["item"]
                                held_item["count"] = crafting_output["count"]
                                consume_crafting()
                                update_crafting_output()
                            elif held_item["item"] == crafting_output["item"] and held_item["count"] + crafting_output["count"] <= MAX_STACK:
                                held_item["count"] += crafting_output["count"]
                                consume_crafting()
                                update_crafting_output()

                elif event.button == 3:
                    clicked = False
                    for r in range(2):
                        for c in range(2):
                            rect = pygame.Rect(craft_start_x + c * craft_cell, craft_start_y + r * craft_cell, HOTBAR_SIZE, HOTBAR_SIZE)
                            if rect.collidepoint(mx, my):
                                right_click_slot(crafting_grid[r][c], held_item)
                                update_crafting_output()
                                clicked = True
                                break
                        if clicked:
                            break
                    if not clicked:
                        for row_i, row in enumerate(inventory):
                            for col_i, slot in enumerate(row):
                                rect = pygame.Rect(
                                    inv_start_x + col_i * (HOTBAR_SIZE + HOTBAR_PADDING),
                                    inv_start_y + row_i * (HOTBAR_SIZE + HOTBAR_PADDING),
                                    HOTBAR_SIZE, HOTBAR_SIZE
                                )
                                if rect.collidepoint(mx, my):
                                    right_click_slot(slot, held_item)
                                    clicked = True
                                    break
                            if clicked:
                                break
                    if not clicked:
                        for i, slot in enumerate(hotbar):
                            rect = pygame.Rect(hotbar_start_x + i * (HOTBAR_SIZE + HOTBAR_PADDING), hotbar_y, HOTBAR_SIZE, HOTBAR_SIZE)
                            if rect.collidepoint(mx, my):
                                right_click_slot(slot, held_item)
                                clicked = True
                                break

            else:
                if event.button == 1:
                    mouse_held = True
                    # Reset breaking if clicking a new block
                    world_x = mx + cam_x
                    world_y = my + cam_y
                    mc = int(world_x // DISPLAY_SIZE) - leftmost_col
                    mr = int(world_y // DISPLAY_SIZE)
                    head_x = player_rect.centerx
                    head_y = player_rect.top + player_rect.height // 4
                    target = get_mineable_block(head_x, head_y, mc, mr, DISPLAY_SIZE * 2) if (0 <= mc < len(world_cols) and 0 <= mr < ROWS and world_cols[mc][mr] is not None) else None
                    if target != (breaking_col, breaking_row):
                        breaking_col = target[0] if target else None
                        breaking_row = target[1] if target else None
                        breaking_progress = 0.0
                        breaking_start_time = current_time if target else None

                elif event.button == 3:
                    selected = hotbar[selected_slot]
                    if selected["item"] and selected["count"] > 0:
                        world_x = mx + cam_x
                        world_y = my + cam_y
                        mouse_col = int(world_x // DISPLAY_SIZE) - leftmost_col
                        mouse_row = int(world_y // DISPLAY_SIZE)
                        if 0 <= mouse_col < len(world_cols) and 0 <= mouse_row < ROWS:
                            if world_cols[mouse_col][mouse_row] is None:
                                player_col = int(player_rect.centerx // DISPLAY_SIZE) - leftmost_col
                                player_top_row = player_rect.top // DISPLAY_SIZE
                                player_bottom_row = (player_rect.bottom - 1) // DISPLAY_SIZE
                                if not (mouse_col == player_col and player_top_row <= mouse_row <= player_bottom_row):
                                    if has_adjacent_block(mouse_col, mouse_row):
                                        block_world_x = (mouse_col + leftmost_col) * DISPLAY_SIZE
                                        block_world_y = mouse_row * DISPLAY_SIZE
                                        head_x = player_rect.centerx
                                        head_y = player_rect.top + player_rect.height // 4
                                        target_x = block_world_x + DISPLAY_SIZE // 2
                                        target_y = block_world_y + DISPLAY_SIZE // 2
                                        if math.hypot(target_x - head_x, target_y - head_y) <= DISPLAY_SIZE * 4:
                                            if has_line_of_sight_to_cell(head_x, head_y, mouse_col, mouse_row):
                                                placed_rect = pygame.Rect(block_world_x, block_world_y, DISPLAY_SIZE, DISPLAY_SIZE)
                                                too_much_overlap = False
                                                if player_rect.colliderect(placed_rect):
                                                    overlap = player_rect.clip(placed_rect)
                                                    too_much_overlap = overlap.width * overlap.height > (DISPLAY_SIZE * DISPLAY_SIZE) * 0.25
                                                if not too_much_overlap:
                                                    world_cols[mouse_col][mouse_row] = selected["item"]
                                                    selected["count"] -= 1
                                                    if selected["count"] <= 0:
                                                        selected["item"] = None
                                                        selected["count"] = 0
                                                    if player_rect.colliderect(placed_rect):
                                                        overlap = player_rect.clip(placed_rect)
                                                        if overlap.width < overlap.height:
                                                            if player_rect.centerx < placed_rect.centerx:
                                                                player_rect.right = placed_rect.left
                                                            else:
                                                                player_rect.left = placed_rect.right
                                                        else:
                                                            if player_rect.centery < placed_rect.centery:
                                                                player_rect.bottom = placed_rect.top
                                                            else:
                                                                player_rect.top = placed_rect.bottom

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_held = False
                breaking_col = None
                breaking_row = None
                breaking_progress = 0.0
                breaking_start_time = None

    # -------- BREAKING LOGIC --------
    if mouse_held and not inventory_open:
        mx, my = pygame.mouse.get_pos()
        world_x = mx + cam_x
        world_y = my + cam_y
        mc = int(world_x // DISPLAY_SIZE) - leftmost_col
        mr = int(world_y // DISPLAY_SIZE)
        head_x = player_rect.centerx
        head_y = player_rect.top + player_rect.height // 4

        target = None
        if 0 <= mc < len(world_cols) and 0 <= mr < ROWS and world_cols[mc][mr] is not None:
            target = get_mineable_block(head_x, head_y, mc, mr, DISPLAY_SIZE * 2)

        if target is None:
            # No valid target, reset
            breaking_col = None
            breaking_row = None
            breaking_progress = 0.0
            breaking_start_time = None
        else:
            tc, tr = target
            if (tc, tr) != (breaking_col, breaking_row):
                # Switched to a different block
                breaking_col = tc
                breaking_row = tr
                breaking_progress = 0.0
                breaking_start_time = current_time
            else:
                block_type = world_cols[breaking_col][breaking_row]
                break_time = BREAK_TIMES.get(block_type, 1.0)
                frame_duration = break_time / 10
                elapsed = current_time - breaking_start_time
                breaking_progress = (int(elapsed / frame_duration) / 10)
                if breaking_progress >= 1.0:
                    # Break the block
                    block_type = mine_block(breaking_col, breaking_row)
                    if block_type:
                        mini_size = 0.5
                        dropped_blocks.append({
                            "type": block_type,
                            "x": (breaking_col + leftmost_col) * DISPLAY_SIZE + (DISPLAY_SIZE - DISPLAY_SIZE * mini_size) / 2,
                            "y": breaking_row * DISPLAY_SIZE,
                            "vy": 0,
                            "size": mini_size,
                            "spawn_time": current_time
                        })
                    breaking_col = None
                    breaking_row = None
                    breaking_progress = 0.0
                    breaking_start_time = None

    # -------- MOVEMENT --------
    keys = pygame.key.get_pressed()
    dx = 0 if inventory_open else (keys[pygame.K_d] - keys[pygame.K_a]) * PLAYER_SPEED

    new_rect = player_rect.move(dx, 0)
    for col_index, col_blocks in enumerate(world_cols):
        col_x = (col_index + leftmost_col) * DISPLAY_SIZE
        for row_index, block in enumerate(col_blocks):
            if block and new_rect.colliderect(pygame.Rect(col_x, row_index * DISPLAY_SIZE, DISPLAY_SIZE, DISPLAY_SIZE)):
                new_rect = player_rect
                break
    player_rect = new_rect

    vy += GRAVITY
    new_rect = player_rect.move(0, vy)
    for col_index, col_blocks in enumerate(world_cols):
        col_x = (col_index + leftmost_col) * DISPLAY_SIZE
        for row_index, block in enumerate(col_blocks):
            if block:
                block_rect = pygame.Rect(col_x, row_index * DISPLAY_SIZE, DISPLAY_SIZE, DISPLAY_SIZE)
                if new_rect.colliderect(block_rect):
                    if vy > 0:
                        new_rect.bottom = block_rect.top
                    else:
                        new_rect.top = block_rect.bottom
                    vy = 0
    player_rect = new_rect

    # -------- FALL DAMAGE --------
    if on_ground(player_rect):
        if peak_top_y is not None:
            fall_blocks = (player_rect.top - peak_top_y) / DISPLAY_SIZE
            if fall_blocks > SAFE_FALL_BLOCKS:
                damage = round(fall_blocks - SAFE_FALL_BLOCKS)
                if damage > 0 and current_time - last_damage_time >= DAMAGE_INVULN:
                    hp = max(0, hp - damage)
                    last_damage_time = current_time
            peak_top_y = None
    else:
        if peak_top_y is None or player_rect.top < peak_top_y:
            peak_top_y = player_rect.top

    # -------- VOID DAMAGE --------
    if player_rect.top > ROWS * DISPLAY_SIZE:
        if current_time - last_damage_time >= SUFFOCATION_INTERVAL:
            hp = max(0, hp - 7)
            last_damage_time = current_time

    # -------- SUFFOCATION --------
    if current_time - last_suffocation_time >= SUFFOCATION_INTERVAL:
        player_col_check = int(player_rect.centerx // DISPLAY_SIZE) - leftmost_col
        suffocating = False
        for col_index in range(max(0, player_col_check - 1), min(len(world_cols), player_col_check + 2)):
            col_x = (col_index + leftmost_col) * DISPLAY_SIZE
            for row_index, block in enumerate(world_cols[col_index]):
                if block:
                    block_rect = pygame.Rect(col_x, row_index * DISPLAY_SIZE, DISPLAY_SIZE, DISPLAY_SIZE)
                    if player_rect.colliderect(block_rect):
                        suffocating = True
                        break
            if suffocating:
                break
        if suffocating and current_time - last_damage_time >= DAMAGE_INVULN:
            hp = max(0, hp - 1)
            last_damage_time = current_time
        last_suffocation_time = current_time

    # -------- REGEN --------
    if hp < MAX_HP and current_time - last_damage_time >= REGEN_DELAY_AFTER_DAMAGE and current_time - last_regen_time >= REGEN_INTERVAL:
        hp = min(MAX_HP, hp + 1)
        last_regen_time = current_time

    # -------- RESPAWN --------
    if hp <= 0:
        player_rect.centerx = spawn_x
        found = False
        for search_range in range(0, len(world_cols)):
            for direction in [0, -1, 1]:
                check_x = spawn_x + direction * search_range * DISPLAY_SIZE
                for col_index, col_blocks in enumerate(world_cols):
                    col_x = (col_index + leftmost_col) * DISPLAY_SIZE
                    if col_x <= check_x < col_x + DISPLAY_SIZE:
                        for row_idx, block in enumerate(col_blocks):
                            if block:
                                player_rect.centerx = col_x + DISPLAY_SIZE // 2
                                player_rect.bottom = row_idx * DISPLAY_SIZE
                                found = True
                                break
                        break
                if found:
                    break
            if found:
                break
        if not found:
            player_rect.bottom = spawn_y
        hp = MAX_HP
        vy = 0
        peak_top_y = None
        last_damage_time = current_time

    if not inventory_open and keys[pygame.K_SPACE] and on_ground(player_rect):
        vy = JUMP_SPEED

    # -------- TERRAIN GENERATION --------
    player_col = player_rect.centerx // DISPLAY_SIZE

    while player_col + 10 >= len(world_cols) + leftmost_col:
        col_blocks, new_h, new_d = generate_column(heights[-1])
        abs_col = len(world_cols) + leftmost_col
        if random.random() < s:
            trunk_height = random.randint(3, 5)
            place_trunk(col_blocks, new_h, trunk_height)
            pending_tree_leaves.append((abs_col, new_h, trunk_height))
        world_cols.append(col_blocks)
        heights.append(new_h)
        dirt_depths.append(new_d)

    while player_col - 10 < leftmost_col:
        col_blocks, new_h, new_d = generate_column(heights[0])
        leftmost_col -= 1
        abs_col = leftmost_col
        if random.random() < s:
            trunk_height = random.randint(3, 5)
            place_trunk(col_blocks, new_h, trunk_height)
            pending_tree_leaves.append((abs_col, new_h, trunk_height))
        world_cols.insert(0, col_blocks)
        heights.insert(0, new_h)
        dirt_depths.insert(0, new_d)

    process_pending_tree_leaves()

    # -------- CAMERA --------
    cam_x += (player_rect.centerx - WINDOW_WIDTH // 2 - cam_x) * CAMERA_SPEED
    cam_y += (player_rect.centery - WINDOW_HEIGHT // 2 - cam_y) * CAMERA_SPEED

    # -------- DRAW WORLD --------
    screen.fill((135, 206, 235))
    for col_index, col_blocks in enumerate(world_cols):
        col_x = (col_index + leftmost_col) * DISPLAY_SIZE - cam_x
        for row_index, block in enumerate(col_blocks):
            if block:
                screen.blit(texture_map[block], (col_x, row_index * DISPLAY_SIZE - cam_y))

    # -------- DRAW BREAKING ANIMATION --------
    if breaking_col is not None and breaking_progress > 0:
        frame_index = 5 - min(int(breaking_progress * 6), 5)
        bx = (breaking_col + leftmost_col) * DISPLAY_SIZE - cam_x
        by = breaking_row * DISPLAY_SIZE - cam_y
        screen.blit(breaking_frames[frame_index], (bx, by))

    # -------- UPDATE & DRAW DROPPED BLOCKS --------
    blocks_to_remove = []
    for block in dropped_blocks:
        if current_time - block["spawn_time"] > DESPAWN_TIME:
            blocks_to_remove.append(block)
            continue
        block["vy"] += GRAVITY
        block["y"] += block["vy"]
        center_x = block["x"] + (DISPLAY_SIZE * block["size"]) / 2
        col_index = int(center_x // DISPLAY_SIZE) - leftmost_col
        floor_row = int((block["y"] + DISPLAY_SIZE * block["size"]) // DISPLAY_SIZE)
        if 0 <= col_index < len(world_cols) and 0 <= floor_row < ROWS:
            if world_cols[col_index][floor_row] is not None:
                block["y"] = floor_row * DISPLAY_SIZE - DISPLAY_SIZE * block["size"]
                block["vy"] = 0
        block_rect = pygame.Rect(block["x"], block["y"], DISPLAY_SIZE * block["size"], DISPLAY_SIZE * block["size"])
        block_center_x = block["x"] + DISPLAY_SIZE * block["size"] / 2
        block_center_y = block["y"] + DISPLAY_SIZE * block["size"] / 2
        closest_x = max(player_rect.left, min(block_center_x, player_rect.right))
        closest_y = max(player_rect.top, min(block_center_y, player_rect.bottom))
        gap_x = max(0, block_rect.left - closest_x, closest_x - block_rect.right)
        gap_y = max(0, block_rect.top - closest_y, closest_y - block_rect.bottom)
        if math.hypot(gap_x, gap_y) <= PICKUP_PADDING:
            if collect_block(block["type"]):
                blocks_to_remove.append(block)
            continue
        size_px = int(DISPLAY_SIZE * block["size"])
        img_scaled = pygame.transform.scale(texture_map[block["type"]], (size_px, size_px))
        screen.blit(img_scaled, (block["x"] - cam_x, block["y"] - cam_y))
    for block in blocks_to_remove:
        if block in dropped_blocks:
            dropped_blocks.remove(block)

    # -------- DRAW OUTLINE --------
    mouse_x, mouse_y = pygame.mouse.get_pos()
    world_x = mouse_x + cam_x
    world_y = mouse_y + cam_y
    mouse_col = int(world_x // DISPLAY_SIZE) - leftmost_col
    mouse_row = int(world_y // DISPLAY_SIZE)
    if not inventory_open and 0 <= mouse_col < len(world_cols) and 0 <= mouse_row < ROWS:
        if world_cols[mouse_col][mouse_row] is not None:
            head_x = player_rect.centerx
            head_y = player_rect.top + player_rect.height // 4
            target = get_mineable_block(head_x, head_y, mouse_col, mouse_row, DISPLAY_SIZE * 2)
            if target:
                col, row = target
                pygame.draw.rect(screen, (255, 255, 255), ((col + leftmost_col) * DISPLAY_SIZE - cam_x, row * DISPLAY_SIZE - cam_y, DISPLAY_SIZE, DISPLAY_SIZE), 2)
        else:
            selected = hotbar[selected_slot]
            if selected["item"] and selected["count"] > 0:
                block_world_x = (mouse_col + leftmost_col) * DISPLAY_SIZE
                block_world_y = mouse_row * DISPLAY_SIZE
                head_x = player_rect.centerx
                head_y = player_rect.top + player_rect.height // 4
                target_x = block_world_x + DISPLAY_SIZE // 2
                target_y = block_world_y + DISPLAY_SIZE // 2
                in_range = math.hypot(target_x - head_x, target_y - head_y) <= DISPLAY_SIZE * 4
                adjacent = has_adjacent_block(mouse_col, mouse_row)
                has_los = has_line_of_sight_to_cell(head_x, head_y, mouse_col, mouse_row)
                placed_rect = pygame.Rect(block_world_x, block_world_y, DISPLAY_SIZE, DISPLAY_SIZE)
                overlap_area = 0
                if player_rect.colliderect(placed_rect):
                    overlap = player_rect.clip(placed_rect)
                    overlap_area = overlap.width * overlap.height
                too_much_overlap = overlap_area > (DISPLAY_SIZE * DISPLAY_SIZE) * 0.25
                if in_range and adjacent and has_los and not too_much_overlap:
                    pygame.draw.rect(screen, (255, 255, 255), (block_world_x - cam_x, block_world_y - cam_y, DISPLAY_SIZE, DISPLAY_SIZE), 2)

    # -------- DRAW PLAYER --------
    screen.blit(player_img, (player_rect.x - cam_x, player_rect.y - cam_y))

    # -------- DRAW HOTBAR --------
    font = pygame.font.SysFont(None, 20)
    for i, slot in enumerate(hotbar):
        rect = pygame.Rect(hotbar_start_x + i * (HOTBAR_SIZE + HOTBAR_PADDING), hotbar_y, HOTBAR_SIZE, HOTBAR_SIZE)
        draw_slot(screen, rect, slot, highlight=(i == selected_slot))

    # -------- DRAW INVENTORY + CRAFTING --------
    if inventory_open:
        for row_i, row in enumerate(inventory):
            for col_i, slot in enumerate(row):
                rect = pygame.Rect(
                    inv_start_x + col_i * (HOTBAR_SIZE + HOTBAR_PADDING),
                    inv_start_y + row_i * (HOTBAR_SIZE + HOTBAR_PADDING),
                    HOTBAR_SIZE, HOTBAR_SIZE
                )
                draw_slot(screen, rect, slot)

        font_label = pygame.font.SysFont(None, 18)
        label = font_label.render("Crafting", True, (255, 255, 255))
        screen.blit(label, (craft_start_x, craft_start_y - 18))

        for r in range(2):
            for c in range(2):
                rect = pygame.Rect(craft_start_x + c * craft_cell, craft_start_y + r * craft_cell, HOTBAR_SIZE, HOTBAR_SIZE)
                draw_slot(screen, rect, crafting_grid[r][c])

        ax = craft_start_x + 2 * craft_cell + 6
        ay = craft_start_y + craft_cell
        pygame.draw.polygon(screen, (255, 255, 255), [
            (ax, ay - 7),
            (ax + 14, ay),
            (ax, ay + 7),
        ])

        out_rect = pygame.Rect(output_x, output_y, HOTBAR_SIZE, HOTBAR_SIZE)
        draw_slot(screen, out_rect, crafting_output)

        if held_item["item"]:
            mx, my = pygame.mouse.get_pos()
            size_px = int(HOTBAR_SIZE * HOTBAR_BLOCK_SCALE)
            img = pygame.transform.scale(texture_map[held_item["item"]], (size_px, size_px))
            screen.blit(img, (mx - size_px // 2, my - size_px // 2))
            if held_item["count"] > 1:
                count_text = font.render(str(held_item["count"]), True, (255, 255, 255))
                screen.blit(count_text, (mx + size_px // 2 - count_text.get_width(), my + size_px // 2 - count_text.get_height()))

    # -------- DRAW HEARTS --------
    num_hearts = MAX_HP // 2
    for i in range(num_hearts):
        hx = 10 + i * (HEART_SIZE + HEART_PADDING)
        hp_for_this = hp - i * 2
        fraction = 1.0 if hp_for_this >= 2 else (0.5 if hp_for_this == 1 else 0.0)
        draw_heart(screen, hx, 10, HEART_SIZE, fraction)

    pygame.display.flip()

pygame.quit()