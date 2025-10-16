import pygame
import sys
import math
import random
import csv

import tkinter as tk
from tkinter import filedialog


# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Skill Tree Builder")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (30, 30, 30)
BLUE = (100, 100, 255) # Default BLUE color
RED = (255, 0, 0) # Color for temporary connection line

# Define a palette of distinct colors for paths
PATH_COLORS = [
    (30, 144, 255),  # Dodger Blue
    (50, 205, 50),   # Lime Green
    (255, 99, 71),   # Tomato
    (147, 112, 219), # Medium Purple
    (255, 140, 0),   # Dark Orange
    (0, 139, 139),   # Dark Cyan
    (218, 165, 32),  # Goldenrod
    (255, 20, 147),  # Deep Pink
    (72, 61, 139),   # Dark Slate Blue
    (0, 100, 0)      # Dark Green
]

MIN_RADIUS = 30

instructions = [
    "Create skill: Right-click.",
    "Rename skill: Select a skill, press Enter to start editing, press Enter again to finish.",
    "Link skills: Hold Shift and left-click Skill A, then Shift + left-click Skill B.",
    "Delete skill: Select it and press Delete.",
    "Detach skill from path: Select it and press D.",
    "Zoom: Mouse wheel.",
    "Pan (move canvas): Middle-click and drag."
]
instructions_open = False  # collapsed by default



class Path:
    next_id = 0
    def __init__(self, color=None):
        self.id = Path.next_id
        Path.next_id += 1
        self.color = color if color else random.choice(PATH_COLORS)
        self.skills = []

    def add_skill(self, skill):
        if skill not in self.skills:
            self.skills.append(skill)
            skill.path = self

    def remove_skill(self, skill):
        if skill in self.skills:
            self.skills.remove(skill)
            skill.path = None

    def merge_path(self, other_path):
        for skill in other_path.skills[:]: # Iterate over a copy to allow modification
            other_path.remove_skill(skill)
            self.add_skill(skill)

class Skill:
    next_id = 0
    def __init__(self, x, y, name=""):
        self.id = Skill.next_id
        Skill.next_id += 1
        self.x = x
        self.y = y
        self.vx = 0 # Velocity X
        self.vy = 0 # Velocity Y
        self.name = name
        self.is_dragging = False
        self.is_editing = False
        self.path = None # Skill initially belongs to no path
        self.font = pygame.font.Font(None, 20)
        self.original_radius = MIN_RADIUS
        self.radius = self.original_radius
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius * 2, self.radius * 2)
        self._update_radius()

    def _update_radius(self):
        words = self.name.split(' ')
        lines = []
        current_line = ""
        max_text_width = 0

        for word in words:
            test_line = current_line + word + " "
            text_width, _ = self.font.size(test_line)
            if text_width < (self.original_radius * 1.8) or not current_line: # 1.8 to leave some padding, or if it's the first word
                current_line = test_line
            else:
                lines.append(current_line.strip())
                max_text_width = max(max_text_width, self.font.size(current_line.strip())[0])
                current_line = word + " "
        lines.append(current_line.strip())
        max_text_width = max(max_text_width, self.font.size(current_line.strip())[0])

        total_text_height = len(lines) * self.font.get_linesize()

        required_radius_by_width = (max_text_width / 2) + 10 # Add padding
        required_radius_by_height = (total_text_height / 2) + 10 # Add padding
        
        new_radius = max(MIN_RADIUS, int(required_radius_by_width), int(required_radius_by_height))
        self.original_radius = new_radius  # permitir crecer y encoger


        if new_radius > self.original_radius:
            self.original_radius = new_radius

    def draw(self, screen, pulsation_time, zoom, camera_offset, is_selected):
        # Use global pulsation time and path color if available
        current_color = self.path.color if self.path else BLUE # Default BLUE if no path

        screen_x = (self.x - camera_offset[0]) * zoom + WIDTH / 2
        screen_y = (self.y - camera_offset[1]) * zoom + HEIGHT / 2
        screen_radius = self.original_radius * zoom

        if is_selected:
            pulsating_radius = screen_radius + 5 * (1 + math.sin(pulsation_time * 0.008)) / 2 * zoom
        else:
            pulsating_radius = screen_radius
        
        self.radius = int(pulsating_radius)
        self.rect = pygame.Rect(screen_x - self.radius, screen_y - self.radius, self.radius * 2, self.radius * 2)

        # Draw editing glow if in editing mode
        if self.is_editing:
            glow_radius = self.radius + 5 * (1 + math.sin(pulsation_time * 0.01)) / 2 * zoom # Slightly faster pulsation
            pygame.draw.circle(screen, (255, 255, 0), (int(screen_x), int(screen_y)), int(glow_radius), 3) # Yellow glow, 3 pixels thick

        pygame.draw.circle(screen, current_color, (int(screen_x), int(screen_y)), self.radius)
        
        words = self.name.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if self.font.size(test_line)[0] < (self.original_radius * 1.8): # 1.8 to leave some padding
                current_line = test_line
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip())

        total_text_height = len(lines) * self.font.get_linesize()
        start_y = screen_y - total_text_height // 2

        for line in lines:
            text_surface = self.font.render(line, True, WHITE)
            text_rect = text_surface.get_rect(center=(screen_x, start_y + self.font.get_linesize() // 2))
            screen.blit(text_surface, text_rect)
            start_y += self.font.get_linesize()

    def apply_force(self, fx, fy):
        self.vx += fx
        self.vy += fy

    def update(self, dt):
        if not self.is_dragging:
            self.x += self.vx * dt
            self.y += self.vy * dt

        # Dampening
        self.vx *= 0.95
        self.vy *= 0.95

        # Cap de velocidad para evitar jitter
        MAX_SPEED = 600.0  # px/s
        sp2 = self.vx*self.vx + self.vy*self.vy
        if sp2 > MAX_SPEED*MAX_SPEED:
            scale = MAX_SPEED / (sp2 ** 0.5)
            self.vx *= scale
            self.vy *= scale



    def handle_event(self, event, zoom, camera_offset):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Actualiza rect con cámara/zoom
                sx = (self.x - camera_offset[0]) * zoom + WIDTH / 2
                sy = (self.y - camera_offset[1]) * zoom + HEIGHT / 2
                sr = self.original_radius * zoom
                self.rect = pygame.Rect(sx - sr, sy - sr, sr * 2, sr * 2)
                if self.rect.collidepoint(event.pos):
                    self.is_dragging = True
                    self.vx = 0
                    self.vy = 0
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                mouse_x, mouse_y = event.pos
                self.x = (mouse_x - WIDTH / 2) / zoom + camera_offset[0]
                self.y = (mouse_y - HEIGHT / 2) / zoom + camera_offset[1]
        elif event.type == pygame.KEYDOWN and self.is_editing:
            if event.key == pygame.K_RETURN:
                pass  # RETURN se maneja en el loop principal
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
                self._update_radius()
            else:
                self.name += event.unicode
                self._update_radius()


def draw_side_panel(screen, selected_path):
    if not selected_path:
        return

    panel_width = 200
    panel_rect = pygame.Rect(WIDTH - panel_width, 0, panel_width, HEIGHT)
    pygame.draw.rect(screen, DARK_GRAY, panel_rect)
    pygame.draw.rect(screen, WHITE, panel_rect, 2)

    font_title = pygame.font.Font(None, 24)
    title_surface = font_title.render(f"Path {selected_path.id}", True, WHITE)
    screen.blit(title_surface, (WIDTH - panel_width + 10, 10))

    font_skill = pygame.font.Font(None, 20)
    y_offset = 40
    for skill in selected_path.skills:
        skill_name = skill.name if skill.name else "empty"
        skill_surface = font_skill.render(skill_name, True, WHITE)
        screen.blit(skill_surface, (WIDTH - panel_width + 10, y_offset))
        y_offset += 25

def recalculate_paths_for_path(path_to_check, all_connections, all_paths):
    skills_in_path = list(path_to_check.skills)
    if not skills_in_path:
        if path_to_check in all_paths:
            all_paths.remove(path_to_check)
        return

    remaining_skills_set = set(skills_in_path)
    
    # First component stays in the original path
    q = [skills_in_path[0]]
    visited = {skills_in_path[0]}
    path_to_check.skills.clear()
    path_to_check.add_skill(skills_in_path[0])
    remaining_skills_set.remove(skills_in_path[0])

    head = 0
    while head < len(q):
        current_skill = q[head]
        head += 1
        
        for s1, s2 in all_connections:
            neighbor = None
            if s1 == current_skill and s2 in remaining_skills_set:
                neighbor = s2
            elif s2 == current_skill and s1 in remaining_skills_set:
                neighbor = s1
            
            if neighbor and neighbor not in visited:
                visited.add(neighbor)
                q.append(neighbor)
                path_to_check.add_skill(neighbor)
                remaining_skills_set.remove(neighbor)

    while remaining_skills_set:
        new_path = Path()
        all_paths.append(new_path)
        
        start_node = remaining_skills_set.pop()
        q_new = [start_node]
        visited_new = {start_node}
        new_path.add_skill(start_node)

        head_new = 0
        while head_new < len(q_new):
            current_skill = q_new[head_new]
            head_new += 1

            for s1, s2 in all_connections:
                neighbor = None
                if s1 == current_skill and s2 in remaining_skills_set:
                    neighbor = s2
                elif s2 == current_skill and s1 in remaining_skills_set:
                    neighbor = s1

                if neighbor and neighbor not in visited_new:
                    visited_new.add(neighbor)
                    q_new.append(neighbor)
                    new_path.add_skill(neighbor)
                    remaining_skills_set.remove(neighbor)

def export_to_csv(filename, skills, paths, connections):
    # Asegura que exportamos TODOS los paths realmente referenciados por skills
    paths_by_id = {p.id: p for p in paths}
    for s in skills:
        if s.path:
            paths_by_id[s.path.id] = s.path  # Incluye paths que no estén en la lista 'paths'

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['type','id','name','x','y','radius','path_id','path_color','edge_from','edge_to'])

        # Paths (únicos)
        for p in paths_by_id.values():
            color = ';'.join(map(str, p.color)) if isinstance(p.color, tuple) else str(p.color)
            w.writerow(['path', p.id, '', '', '', '', '', color, '', ''])

        # Skills (si no tienen path, crea uno para no dejar path_id vacío)
        for s in skills:
            if s.path is None:
                # Crea un path ad-hoc para que no queden skills huérfanas
                new_p = Path()
                new_p.add_skill(s)
                paths_by_id[new_p.id] = new_p
            pid = s.path.id
            w.writerow(['skill', s.id, s.name, f'{s.x:.3f}', f'{s.y:.3f}', s.original_radius, pid, '', '', ''])

        # Edges
        for a, b in connections:
            w.writerow(['edge', '', '', '', '', '', '', '', a.id, b.id])



def import_from_csv(filename):
    skills = []
    paths = []
    connections = []
    skill_by_id = {}
    path_by_id = {}
    # Reset contadores
    Skill.next_id = 0
    Path.next_id = 0

    with open(filename, 'r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        rows = list(r)
    print(rows)
    # Paths primero
    for row in rows:
        if row['type'] == 'path':
            p = Path()
            p.id = int(row['id'])
            Path.next_id = max(Path.next_id, p.id + 1)
            col = row.get('path_color','')
            if col and ';' in col:
                parts = col.split(';')
                if len(parts) == 3:
                    try:
                        p.color = tuple(int(x) for x in parts)
                        print(p.color)
                    except:
                        print("Im an error")
                        pass
                        
            paths.append(p)
            path_by_id[p.id] = p

    # Luego skills
    for row in rows:
        if row['type'] == 'skill':
            s = Skill(float(row['x']), float(row['y']), row['name'])
            s.id = int(row['id'])
            Skill.next_id = max(Skill.next_id, s.id + 1)
            s.original_radius = int(row['radius']) if row['radius'] else s.original_radius
            pid = row['path_id']
            if pid != '' and int(pid) in path_by_id:
                path_by_id[int(pid)].add_skill(s)
            skills.append(s)
            skill_by_id[s.id] = s

    # Finalmente edges
    for row in rows:
        if row['type'] == 'edge':
            a = skill_by_id.get(int(row['edge_from']))
            b = skill_by_id.get(int(row['edge_to']))
            if a and b:
                connections.append((a, b))

        # --- Reparación de pertenencia a paths tras la carga ---

    # 1) Propaga paths por las aristas (si alguno del componente tiene path)
    changed = True
    while changed:
        changed = False
        for a, b in connections:
            if a.path and not b.path:
                a.path.add_skill(b); changed = True
            elif b.path and not a.path:
                b.path.add_skill(a); changed = True

    # 2) Para componentes sin path asignado, asígnales uno reutilizando
    #    paths que llegaron del CSV (con sus colores) y que aún no tengan skills.
    unused_paths = [p for p in paths if not p.skills]

    # Detecta componentes restantes sin path
    unassigned = [s for s in skills if s.path is None]
    seen = set()
    for start in unassigned:
        if start in seen:
            continue

        # BFS para obtener todo el componente
        comp = []
        q = [start]
        seen.add(start)
        while q:
            u = q.pop()
            comp.append(u)
            for x, y in connections:
                if x == u and y not in seen:
                    seen.add(y); q.append(y)
                elif y == u and x not in seen:
                    seen.add(x); q.append(x)

        # Asigna un path (reusa uno con color si hay; si no, crea uno)
        if unused_paths:
            p = unused_paths.pop(0)
        else:
            p = Path()  # tendrá color aleatorio de PATH_COLORS
            paths.append(p)
        for s in comp:
            p.add_skill(s)


    return skills, paths, connections

def ensure_csv(name: str) -> str:
    return name if name.lower().endswith(".csv") else name + ".csv"

def ask_save_csv(default_name="skill_tree.csv"):
    root = tk.Tk(); root.withdraw()
    try:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=default_name,
            title="Save skill tree as..."
        )
        return ensure_csv(path) if path else None
    finally:
        root.destroy()

def ask_open_csv():
    root = tk.Tk(); root.withdraw()
    try:
        path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")],
            title="Open skill tree..."
        )
        return path if path else None
    finally:
        root.destroy()

def wrap_lines(lines, font, max_width):
    wrapped = []
    for line in lines:
        words = line.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size("• " + test)[0] <= max_width:
                cur = test
            else:
                if cur:
                    wrapped.append(cur)
                cur = w
        if cur:
            wrapped.append(cur)
    return wrapped


def draw_instructions_dropdown(screen, open_flag, pos=(10, 10), width=520):
    import pygame
    x, y = pos
    pad = 10
    gap_below_header = 8  # space between header and panel

    title_font = pygame.font.Font(None, 28)
    text_font  = pygame.font.Font(None, 22)

    # Header
    caret = "v" if open_flag else ">"
    header_text = f"{caret} Instructions  (press H)"
    header_surf = title_font.render(header_text, True, (255, 255, 255))
    header_rect = header_surf.get_rect(topleft=(x, y))

    # dark stripe behind header
    bg = pygame.Surface((width, header_rect.height + 8), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 140))
    screen.blit(bg, (x - 6, y - 4))
    screen.blit(header_surf, header_rect.topleft)

    if not open_flag:
        return  # collapsed

    # Use the same list for sizing and drawing
    items = instructions  # if you add word-wrapping later, replace this with your wrapped list

    # Use the same line height for sizing and stepping
    line_h = text_font.get_height() + 6

    # Panel geometry
    panel_h = pad + len(items) * line_h + pad
    panel_y = y + header_rect.height + gap_below_header

    panel = pygame.Surface((width, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    screen.blit(panel, (x, panel_y))

    # Draw lines
    ty = panel_y + pad
    for line in items:
        surf = text_font.render("• " + line, True, (230, 230, 230))
        screen.blit(surf, (x + pad, ty))
        ty += text_font.get_height() + 8



def main():
    skills = []
    paths = [] # List to store Path objects
    connections = [] # List to store connections (skill1, skill2)
    active_skill = None
    connecting_skill = None # Skill currently being connected from
    selected_path = None
    clock = pygame.time.Clock()
    global_pulsation_time = 0.0

    

    global instructions_open


    # Camera and zoom
    zoom = 1.0
    min_zoom = 0.2
    max_zoom = 3.0
    camera_offset = [WIDTH / 2, HEIGHT / 2]
    panning = False
    pan_start_pos = [0, 0]

    # Physics constants
    repulsion_strength = 10000
    attraction_strength = 0.05
    ideal_distance = 100
    repulsion_range_sq = 100**2 # Repel only nodes within 100 pixels

    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        global_pulsation_time += dt * 1000

        for s in skills:
            sx = (s.x - camera_offset[0]) * zoom + WIDTH / 2
            sy = (s.y - camera_offset[1]) * zoom + HEIGHT / 2
            sr = s.original_radius * zoom
            s.rect = pygame.Rect(sx - sr, sy - sr, sr * 2, sr * 2)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: # Zoom in
                    zoom = min(max_zoom, zoom * 1.1)
                elif event.button == 5: # Zoom out
                    zoom = max(min_zoom, zoom * 0.9)
                elif event.button == 2: # Middle mouse button for panning
                    panning = True
                    pan_start_pos = pygame.mouse.get_pos()

                if event.button == 1:  # Left-click
                    clicked_on_skill = False

                    for s in skills:
                        sx = (s.x - camera_offset[0]) * zoom + WIDTH / 2
                        sy = (s.y - camera_offset[1]) * zoom + HEIGHT / 2
                        sr = s.original_radius * zoom
                        s.rect = pygame.Rect(sx - sr, sy - sr, sr * 2, sr * 2)

                    for skill in skills:
                        if skill.rect.collidepoint(event.pos):
                            clicked_on_skill = True
                            selected_path = skill.path
                            keys = pygame.key.get_pressed()
                            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                                if connecting_skill is None:
                                    connecting_skill = skill
                                else:
                                    if connecting_skill != skill:
                                        if not any(c in [(connecting_skill, skill), (skill, connecting_skill)] for c in connections):
                                            connections.append((connecting_skill, skill))
                                        if connecting_skill.path and skill.path:
                                            if connecting_skill.path != skill.path:
                                                connecting_skill.path.merge_path(skill.path)
                                                if skill.path in paths:
                                                    paths.remove(skill.path)
                                        elif connecting_skill.path:
                                            connecting_skill.path.add_skill(skill)
                                        elif skill.path:
                                            skill.path.add_skill(connecting_skill)
                                        else:
                                            new_path = Path()
                                            new_path.add_skill(connecting_skill)
                                            new_path.add_skill(skill)
                                            paths.append(new_path)
                                        connecting_skill = None
                            else:
                                if active_skill:
                                    active_skill.is_editing = False
                                active_skill = skill
                            break
                    
                    if not clicked_on_skill:
                        if active_skill:
                            active_skill.is_editing = False
                            active_skill = None
                        selected_path = None
                        connecting_skill = None

                elif event.button == 3:
                    if active_skill:
                        active_skill.is_editing = False
                    mouse_x, mouse_y = event.pos
                    world_x = (mouse_x - WIDTH / 2) / zoom + camera_offset[0]
                    world_y = (mouse_y - HEIGHT / 2) / zoom + camera_offset[1]
                    new_skill = Skill(world_x, world_y)
                    skills.append(new_skill)
                    new_path = Path()
                    new_path.add_skill(new_skill)
                    paths.append(new_path)
                    active_skill = new_skill
                    active_skill.is_editing = True
                    connecting_skill = None

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    panning = False

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    pan_end_pos = pygame.mouse.get_pos()
                    dx = pan_end_pos[0] - pan_start_pos[0]
                    dy = pan_end_pos[1] - pan_start_pos[1]
                    camera_offset[0] -= dx / zoom
                    camera_offset[1] -= dy / zoom
                    pan_start_pos = pan_end_pos



            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()

                # Toggle instrucciones
                if event.key == pygame.K_h:
                    instructions_open = not instructions_open

                # Ctrl+S -> choose where to save
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_s:
                    fname = ask_save_csv("skill_tree_export.csv")
                    if fname:
                        export_to_csv(fname, skills, paths, connections)
                        print(f"[OK] Saved to {fname}")

                # Ctrl+O -> choose a CSV to open
                elif (mods & pygame.KMOD_CTRL) and event.key == pygame.K_o:
                    fname = ask_open_csv()
                    if fname:
                        skills, paths, connections = import_from_csv(fname)
                        # (optional) reset transient selections if your app needs it
                        active_skill = None
                        connecting_skill = None
                        selected_path = None
                        print(f"[OK] Loaded from {fname}")

                                    

                #Edition mode
                if event.key == pygame.K_RETURN and active_skill:
                    active_skill.is_editing = not active_skill.is_editing
                elif event.key == pygame.K_DELETE and active_skill:
                    skill_to_delete = active_skill
                    skills.remove(skill_to_delete)
                    connections = [c for c in connections if skill_to_delete not in c]
                    
                    if skill_to_delete.path:
                        original_path = skill_to_delete.path
                        original_path.remove_skill(skill_to_delete)
                        if original_path.skills:
                            recalculate_paths_for_path(original_path, connections, paths)
                        elif original_path in paths:
                            paths.remove(original_path)
                    
                    active_skill = None
                    
                elif event.key == pygame.K_d and active_skill and not active_skill.is_editing:
                    skill_to_disconnect = active_skill
                    had_conn = any(skill_to_disconnect in c for c in connections)
                    connections = [c for c in connections if skill_to_disconnect not in c]

                    if skill_to_disconnect.path:
                        original_path = skill_to_disconnect.path
                        original_path.remove_skill(skill_to_disconnect)

                        if had_conn:
                            new_path = Path()
                            new_path.add_skill(skill_to_disconnect)
                            paths.append(new_path)

                        if original_path.skills:
                            recalculate_paths_for_path(original_path, connections, paths)
                        elif original_path in paths:
                            paths.remove(original_path)

            if active_skill:
                active_skill.handle_event(event, zoom, camera_offset)
            
            for skill in skills:
                if skill != active_skill:
                    skill.handle_event(event, zoom, camera_offset)

        # Physics calculations
        for i, s1 in enumerate(skills):
            for s2 in skills[i+1:]:
                dx = s2.x - s1.x
                dy = s2.y - s1.y
                distance_sq = dx*dx + dy*dy
                if distance_sq == 0 or distance_sq > repulsion_range_sq:
                    continue

                # Repulsion
                distance = math.sqrt(distance_sq)
                force = repulsion_strength / distance_sq
                fx = force * dx / distance
                fy = force * dy / distance
                s1.apply_force(-fx, -fy)
                s2.apply_force(fx, fy)

        # Attraction for connected skills
        for s1, s2 in connections:
            dx = s2.x - s1.x
            dy = s2.y - s1.y
            distance = math.sqrt(dx*dx + dy*dy)
            if distance == 0: continue

            displacement = distance - ideal_distance
            force = attraction_strength * displacement
            fx = force * dx / distance
            fy = force * dy / distance
            s1.apply_force(fx, fy)
            s2.apply_force(-fx, -fy)

        for skill in skills:
            skill.update(dt)

        # Drawing
        screen.fill(DARK_GRAY)

        for s1, s2 in connections:
            line_color = BLACK
            if s1.path and s1.path == s2.path:
                line_color = s1.path.color
            
            s1_screen_x = (s1.x - camera_offset[0]) * zoom + WIDTH / 2
            s1_screen_y = (s1.y - camera_offset[1]) * zoom + HEIGHT / 2
            s2_screen_x = (s2.x - camera_offset[0]) * zoom + WIDTH / 2
            s2_screen_y = (s2.y - camera_offset[1]) * zoom + HEIGHT / 2
            pygame.draw.line(screen, line_color, (int(s1_screen_x), int(s1_screen_y)), (int(s2_screen_x), int(s2_screen_y)), 2)

        if connecting_skill:
            mouse_pos = pygame.mouse.get_pos()
            temp_line_color = connecting_skill.path.color if connecting_skill.path else RED
            skill_screen_x = (connecting_skill.x - camera_offset[0]) * zoom + WIDTH / 2
            skill_screen_y = (connecting_skill.y - camera_offset[1]) * zoom + HEIGHT / 2
            pygame.draw.line(screen, temp_line_color, (int(skill_screen_x), int(skill_screen_y)), mouse_pos, 2)

        for skill in skills:
            is_selected = skill == active_skill or (selected_path and skill in selected_path.skills)
            skill.draw(screen, global_pulsation_time, zoom, camera_offset, is_selected)

        if selected_path:
            draw_side_panel(screen, selected_path)

        info_font = pygame.font.Font(None, 20)
        info_panel_width = 250
        info_panel_padding = 10
        line_height = info_font.get_linesize()



        wrapped_instructions = []
        for instruction in instructions:
            words = instruction.split(' ')
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if info_font.size(test_line)[0] < (info_panel_width - 2 * info_panel_padding):
                    current_line = test_line
                else:
                    wrapped_instructions.append(current_line.strip())
                    current_line = word + " "
            wrapped_instructions.append(current_line.strip())

        total_info_height = len(wrapped_instructions) * line_height + 2 * info_panel_padding
        info_panel_rect = pygame.Rect(10, 10, info_panel_width, total_info_height)
        #pygame.draw.rect(screen, DARK_GRAY, info_panel_rect)
        #pygame.draw.rect(screen, WHITE, info_panel_rect, 2)

        
        

        draw_instructions_dropdown(screen, instructions_open, pos=(20, 20), width=720)
    

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()