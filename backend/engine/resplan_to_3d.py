
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, box, Point
from shapely.ops import unary_union
from shapely.affinity import rotate
from collections import defaultdict
import open3d as o3d
import os

# =========================
# REALISTIC HOUSE CONFIG
# =========================
# Geometric units are meters. Use architectural proportions.
WALL_HEIGHT = 2.8        # Standard residential ceiling height (2.8m / ~9.2ft)
FLOOR_THICKNESS = 0.05   # Thin floor for CAD look
DOOR_HEIGHT = 2.1        # Standard door height (2.1m / ~7ft)
WALL_THICKNESS = 0.15    # Standard interior partition wall thickness (15cm)
EXTERIOR_WALL_THICKNESS = 0.20 # Exterior structural wall thickness (20cm)
DOOR_THICKNESS = 0.05    # Door panel thickness (5cm) - Thinner than walls

WINDOW_SILL_HEIGHT = 0.90      # Code-standard window sill height (0.9m)
WINDOW_HEAD_HEIGHT = 2.10      # Aligned with door header (2.1m)
BATH_WINDOW_SILL_HEIGHT = 1.50 # High-level privacy ventilator sill

# Wall/door/window colors - Modern Architectural Look
WALL_COLOR = "#F5F5F5"         # White Smoke walls
DOOR_FRAME_COLOR = "#5D4037"   # Dark Wood (Walnut)
DOOR_PANEL_COLOR = "#8D6E63"   # Rich Wood (Walnut)
WINDOW_FRAME_COLOR = "#334155" # Dark Slate Charcoal
WINDOW_GLASS_COLOR = "#93C5FD" # Translucent Sky Glass
GROUND_COLOR = "#E0E0E0"       # Light Grey Ground

# Refined room color palette (Modern Architectural Pastels)
ROOM_COLORS = [
    "#A8DADC",  # Powder Blue
    "#F1FAEE",  # Honeydew
    "#A8E6CF",  # Mint
    "#FFD3B6",  # Rose Gold
    "#FFAAA5",  # Salmon
    "#DCEDC1",  # Tea Green
    "#D4A5A5",  # Pale Pink
    "#9D8189",  # Muted Mauve
]

def _extrude_linestring_to_thin_wall(line, z_bottom, z_top, thickness=None):
    """Extrude a LineString into a thin *thickened* wall strip."""
    if line.is_empty or line.length < 0.01:
        return []

    coords = list(line.coords)
    if len(coords) < 2:
        return []

    faces = []
    actual_t = thickness if thickness is not None else WALL_THICKNESS
    half_t = actual_t / 2.0

    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]

        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-4:
            continue

        # Unit perpendicular vector
        nx = -dy / length
        ny = dx / length

        # Offset points to get inner/outer edges (Centered extrusion)
        x1_in, y1_in = x1 + nx * half_t, y1 + ny * half_t
        x2_in, y2_in = x2 + nx * half_t, y2 + ny * half_t
        x1_out, y1_out = x1 - nx * half_t, y1 - ny * half_t
        x2_out, y2_out = x2 - nx * half_t, y2 - ny * half_t

        # Outer face
        face_outer = [
            [x1_out, y1_out, z_bottom],
            [x2_out, y2_out, z_bottom],
            [x2_out, y2_out, z_top],
            [x1_out, y1_out, z_top],
        ]
        faces.append(face_outer)

        # Inner face
        face_inner = [
            [x2_in, y2_in, z_bottom],
            [x1_in, y1_in, z_bottom],
            [x1_in, y1_in, z_top],
            [x2_in, y2_in, z_top],
        ]
        faces.append(face_inner)

        # Start Cap (only if needed, but for closed loops usually not, however 
        # since we split by doors, we have open ends. Let's close them for solidity)
        face_start = [
             [x1_out, y1_out, z_bottom],
             [x1_in, y1_in, z_bottom],
             [x1_in, y1_in, z_top],
             [x1_out, y1_out, z_top]
        ]
        faces.append(face_start)
        
        face_end = [
             [x2_in, y2_in, z_bottom],
             [x2_out, y2_out, z_bottom],
             [x2_out, y2_out, z_top],
             [x2_in, y2_in, z_top]
        ]
        faces.append(face_end)
        
        # Top cap
        face_top = [
            [x1_out, y1_out, z_top],
            [x2_out, y2_out, z_top],
            [x2_in, y2_in, z_top],
            [x1_in, y1_in, z_top]
        ]
        faces.append(face_top)

    return faces


def _extrude_polygon_vertical_shell(poly, z_bottom, z_top, thickness=0.05):
    """Extrude a polygon as a solid panel (door)."""
    if poly.is_empty: return []

    # For doors, we just want a box visualization
    # Buffer polygon by thickness/2 to get 2D footprint (if it's a line)
    # But usually doors are already Polygons in the layout. 
    # If it's a Polygon, just extrude it directly.
    
    if not isinstance(poly, Polygon):
        return []

    # Simplify: Just extrude the polygon vertically (prism)
    coords = list(poly.exterior.coords)
    if len(coords) < 3: return []
    
    faces = []
    
    # Side faces
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        face = [
            [x1, y1, z_bottom],
            [x2, y2, z_bottom],
            [x2, y2, z_top],
            [x1, y1, z_top]
        ]
        faces.append(face)
        
    # Top/Bottom
    top = [[x,y,z_top] for x,y in coords[:-1]]
    bottom = [[x,y,z_bottom] for x,y in reversed(coords[:-1])]
    
    faces.append(top)
    faces.append(bottom)
    
    return faces


def _extrude_polygon_to_3d(poly, z_bottom, z_top):
    """Extrude 2D polygon to 3D prism (Floors)."""
    if poly.is_empty or not hasattr(poly, 'exterior'): return []
    coords = list(poly.exterior.coords)
    if len(coords) < 3: return []
    if coords[0] != coords[-1]: coords.append(coords[0])
    
    faces = []
    # Vertical faces
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        face = [
            [x1, y1, z_bottom],
            [x2, y2, z_bottom],
            [x2, y2, z_top],
            [x1, y1, z_top]
        ]
        faces.append(face)
    
    # Top/Bottom
    faces.append([[x, y, z_top] for x, y in coords[:-1]])
    faces.append([[x, y, z_bottom] for x, y in reversed(coords[:-1])])
    
    return faces


def _normalize_orientation(rooms, doors):
    """Rotate rooms and doors to align with X-axis."""
    if not rooms: return rooms, doors
    
    all_coords = []
    for poly in rooms.values():
        if not poly.is_empty:
            all_coords.extend(list(poly.exterior.coords))
            
    if len(all_coords) < 2: return rooms, doors
    
    xs = np.array([c[0] for c in all_coords])
    ys = np.array([c[1] for c in all_coords])
    
    x_mean = xs.mean()
    y_mean = ys.mean()
    
    # PCI for rotation
    X = np.vstack((xs - x_mean, ys - y_mean))
    cov = np.cov(X)
    eigvals, eigvecs = np.linalg.eig(cov)
    idx = np.argmax(eigvals)
    vx, vy = eigvecs[:, idx]
    angle_deg = np.degrees(np.arctan2(vy, vx))
    
    origin = (x_mean, y_mean)
    
    rotated_rooms = {k: rotate(v, -angle_deg, origin=origin) for k, v in rooms.items()}
    
    rotated_doors = None
    if doors is not None:
        rotated_doors = rotate(doors, -angle_deg, origin=origin)
        
    return rotated_rooms, rotated_doors


def _hex_to_rgb01(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def add_box_to_faces(all_faces, x1, x2, y1, y2, z1, z2, color, alpha=1.0):
    # Corners
    c000 = [x1, y1, z1]
    c100 = [x2, y1, z1]
    c110 = [x2, y2, z1]
    c010 = [x1, y2, z1]
    c001 = [x1, y1, z2]
    c101 = [x2, y1, z2]
    c111 = [x2, y2, z2]
    c011 = [x1, y2, z2]
    
    # 6 Faces
    # Bottom
    all_faces.append({"vertices": [c000, c010, c110, c100], "color": color, "alpha": alpha})
    # Top
    all_faces.append({"vertices": [c001, c101, c111, c011], "color": color, "alpha": alpha})
    # Front
    all_faces.append({"vertices": [c000, c100, c101, c001], "color": color, "alpha": alpha})
    # Back
    all_faces.append({"vertices": [c110, c010, c011, c111], "color": color, "alpha": alpha})
    # Left
    all_faces.append({"vertices": [c010, c000, c001, c011], "color": color, "alpha": alpha})
    # Right
    all_faces.append({"vertices": [c100, c110, c111, c101], "color": color, "alpha": alpha})


def _place_room_furniture(all_faces, name, poly, door_polys=None, all_rooms=None):
    if poly.is_empty: return
    
    # Bounding box and dimensions
    minx, miny, maxx, maxy = poly.bounds
    cx, cy = poly.centroid.x, poly.centroid.y
    w = maxx - minx
    h = maxy - miny
    
    if w < 2.0 or h < 2.0:
        return
        
    scale = min(1.0, min(w / 4.0, h / 4.0))
    door_polys = door_polys or []
    all_rooms = all_rooms or {}
    
    if "living" in name or "lounge" in name or "family" in name:
        # 1. Determine best solid wall for TV (score North, South, East, West walls)
        walls = {
            "south": LineString([(minx, miny), (maxx, miny)]),
            "north": LineString([(minx, maxy), (maxx, maxy)]),
            "west":  LineString([(minx, miny), (minx, maxy)]),
            "east":  LineString([(maxx, miny), (maxx, maxy)]),
        }
        
        wall_scores = {}
        for w_side, w_line in walls.items():
            doors_on_wall = sum(1 for dp in door_polys if dp.intersects(w_line.buffer(0.25)))
            length_pref = w_line.length if w_side in ["south", "north"] else w_line.length * 0.95
            wall_scores[w_side] = -doors_on_wall * 10.0 + length_pref

        best_wall = max(wall_scores.items(), key=lambda x: x[1])[0]
        
        if best_wall in ["south", "north"]:
            is_south = (best_wall == "south")
            tv_y = miny + 0.15 if is_south else maxy - 0.55 * scale
            tv_center_y = miny + 0.35 if is_south else maxy - 0.35 * scale
            dist = min(2.4, max(1.8, (h - 0.8) * 0.55))
            sofa_y = miny + dist if is_south else maxy - dist - 0.7 * scale
            coffee_y = (tv_center_y + sofa_y) / 2.0
            
            # TV Media Unit (width 1.8m, depth 0.4m, height 0.45m)
            tw = min(0.9 * scale, w * 0.28)
            add_box_to_faces(all_faces, cx - tw, cx + tw, tv_y, tv_y + 0.4 * scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.45 * scale, "#334155")
            # Wall-mounted TV Screen (width 1.4m, height 0.75m)
            sw = tw * 0.8
            screen_y1 = miny + 0.04 if is_south else maxy - 0.08
            screen_y2 = miny + 0.08 if is_south else maxy - 0.04
            add_box_to_faces(all_faces, cx - sw, cx + sw, screen_y1, screen_y2, FLOOR_THICKNESS + 0.9 * scale, FLOOR_THICKNESS + 1.65 * scale, "#0F172A")
            
            # Area Rug
            rw, rh = 1.3 * scale, 1.0 * scale
            add_box_to_faces(all_faces, cx - rw, cx + rw, coffee_y - rh, coffee_y + rh, FLOOR_THICKNESS + 0.005, FLOOR_THICKNESS + 0.01, "#E2E8F0")
            
            # Coffee Table
            cw_tab, ch_tab = 0.5 * scale, 0.3 * scale
            add_box_to_faces(all_faces, cx - cw_tab, cx + cw_tab, coffee_y - ch_tab, coffee_y + ch_tab, FLOOR_THICKNESS + 0.32 * scale, FLOOR_THICKNESS + 0.36 * scale, "#D7CCC8")
            for lx in [-cw_tab + 0.05*scale, cw_tab - 0.05*scale]:
                for ly in [-ch_tab + 0.05*scale, ch_tab - 0.05*scale]:
                    add_box_to_faces(all_faces, cx + lx - 0.02*scale, cx + lx + 0.02*scale, coffee_y + ly - 0.02*scale, coffee_y + ly + 0.02*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.32*scale, "#5D4037")
                    
            # Sofa Facing TV (opposite the TV wall)
            cw, cd = 1.1 * scale, 0.4 * scale
            back_y1 = sofa_y + 0.3 * scale if is_south else sofa_y
            back_y2 = sofa_y + 0.4 * scale if is_south else sofa_y + 0.1 * scale
            add_box_to_faces(all_faces, cx - cw, cx + cw, sofa_y, sofa_y + cd, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#475569")
            add_box_to_faces(all_faces, cx - cw, cx + cw, back_y1, back_y2, FLOOR_THICKNESS + 0.42 * scale, FLOOR_THICKNESS + 0.78 * scale, "#334155")
            add_box_to_faces(all_faces, cx - cw - 0.1 * scale, cx - cw, sofa_y, sofa_y + cd, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.55 * scale, "#334155")
            add_box_to_faces(all_faces, cx + cw, cx + cw + 0.1 * scale, sofa_y, sofa_y + cd, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.55 * scale, "#334155")
        else:
            # West or East TV Wall
            is_west = (best_wall == "west")
            tv_x = minx + 0.15 if is_west else maxx - 0.55 * scale
            dist = min(2.4, max(1.8, (w - 0.8) * 0.55))
            sofa_x = minx + dist if is_west else maxx - dist - 0.7 * scale
            coffee_x = (cx + sofa_x) / 2.0
            
            # TV Media Unit
            th = min(0.9 * scale, h * 0.28)
            add_box_to_faces(all_faces, tv_x, tv_x + 0.4 * scale, cy - th, cy + th, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.45 * scale, "#334155")
            # Mounted TV Screen
            sh = th * 0.8
            screen_x1 = minx + 0.04 if is_west else maxx - 0.08
            screen_x2 = minx + 0.08 if is_west else maxx - 0.04
            add_box_to_faces(all_faces, screen_x1, screen_x2, cy - sh, cy + sh, FLOOR_THICKNESS + 0.9 * scale, FLOOR_THICKNESS + 1.65 * scale, "#0F172A")
            
            # Area Rug & Coffee Table
            add_box_to_faces(all_faces, coffee_x - 0.8 * scale, coffee_x + 0.8 * scale, cy - 1.2 * scale, cy + 1.2 * scale, FLOOR_THICKNESS + 0.005, FLOOR_THICKNESS + 0.01, "#E2E8F0")
            add_box_to_faces(all_faces, coffee_x - 0.3 * scale, coffee_x + 0.3 * scale, cy - 0.5 * scale, cy + 0.5 * scale, FLOOR_THICKNESS + 0.32 * scale, FLOOR_THICKNESS + 0.36 * scale, "#D7CCC8")
            
            # Sofa Facing West/East
            cd = 0.4 * scale
            back_x1 = sofa_x + 0.3 * scale if is_west else sofa_x
            back_x2 = sofa_x + 0.4 * scale if is_west else sofa_x + 0.1 * scale
            add_box_to_faces(all_faces, sofa_x, sofa_x + cd, cy - 1.0 * scale, cy + 1.0 * scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#475569")
            add_box_to_faces(all_faces, back_x1, back_x2, cy - 1.0 * scale, cy + 1.0 * scale, FLOOR_THICKNESS + 0.42 * scale, FLOOR_THICKNESS + 0.78 * scale, "#334155")

        # Integrated Dining Zone if spacious and no separate dining room
        has_dining_room = any("dining" in r.lower() for r in all_rooms.keys())
        if not has_dining_room and (w * h >= 16.0 or max(w, h) >= 4.8):
            dx = minx + 1.2 * scale if best_wall == "east" else maxx - 1.2 * scale
            dy = miny + 1.2 * scale if best_wall == "north" else maxy - 1.2 * scale
            dtw, dth = 0.6 * scale, 0.4 * scale
            add_box_to_faces(all_faces, dx - dtw, dx + dtw, dy - dth, dy + dth, FLOOR_THICKNESS + 0.72 * scale, FLOOR_THICKNESS + 0.76 * scale, "#8D6E63")
            for lx in [-dtw + 0.05*scale, dtw - 0.05*scale]:
                for ly in [-dth + 0.05*scale, dth - 0.05*scale]:
                    add_box_to_faces(all_faces, dx + lx - 0.02*scale, dx + lx + 0.02*scale, dy + ly - 0.02*scale, dy + ly + 0.02*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.72*scale, "#5D4037")
            for ox in [-dtw * 0.6, dtw * 0.6]:
                for oy in [-dth - 0.25 * scale, dth + 0.25 * scale]:
                    add_box_to_faces(all_faces, dx + ox - 0.12*scale, dx + ox + 0.12*scale, dy + oy - 0.12*scale, dy + oy + 0.12*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42*scale, "#475569")
                
    elif "bedroom" in name or "bed" in name:
        # Double Bed with Padded Headboard against solid wall
        bw, bh = 0.8 * scale, 0.95 * scale
        bed_cx = cx
        bed_cy = miny + bh + 0.25 * scale
        
        # Padded Headboard against wall
        add_box_to_faces(all_faces, bed_cx - bw - 0.05*scale, bed_cx + bw + 0.05*scale, miny + 0.08, miny + 0.18*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.0 * scale, "#D7CCC8")
        # Mattress
        add_box_to_faces(all_faces, bed_cx - bw, bed_cx + bw, miny + 0.18*scale, miny + 0.18*scale + 1.7*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.48 * scale, "#FFFFFF")
        # Pillows
        add_box_to_faces(all_faces, bed_cx - 0.65*scale, bed_cx - 0.1*scale, miny + 0.22*scale, miny + 0.52*scale, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
        add_box_to_faces(all_faces, bed_cx + 0.1*scale, bed_cx + 0.65*scale, miny + 0.22*scale, miny + 0.52*scale, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
        
        # Bedside Nightstands flanking bed with lamps
        for side_x in [bed_cx - bw - 0.35*scale, bed_cx + bw + 0.05*scale]:
            add_box_to_faces(all_faces, side_x, side_x + 0.3*scale, miny + 0.12, miny + 0.48*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#5D4037")
            add_box_to_faces(all_faces, side_x + 0.1*scale, side_x + 0.2*scale, miny + 0.22*scale, miny + 0.32*scale, FLOOR_THICKNESS + 0.42*scale, FLOOR_THICKNESS + 0.65*scale, "#FDE047")
            
        # Wardrobe Closet along side wall (depth 0.6m, height 2.2m)
        if w >= 2.8:
            add_box_to_faces(all_faces, maxx - 0.62, maxx - 0.05, cy - 0.7*scale, cy + 0.7*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 2.2 * scale, "#5D4037")
        
    elif "bathroom" in name or "bath" in name or "toilet" in name:
        # Modern Bathroom Suite: Vanity, Toilet, and Shower/Tub
        door_near_top = False
        if door_polys:
            for door in door_polys:
                if door.intersects(poly.buffer(0.15)):
                    dy = door.centroid.y
                    if abs(dy - maxy) < abs(dy - miny):
                        door_near_top = True

        fix_y = miny + 0.15 if door_near_top else maxy - 0.55
        
        # 1. Floating Vanity Unit with Basin & Mirror
        vx = minx + 0.15
        add_box_to_faces(all_faces, vx, vx + 0.7 * scale, fix_y, fix_y + 0.45 * scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.82 * scale, "#8D6E63")
        add_box_to_faces(all_faces, vx + 0.1*scale, vx + 0.6*scale, fix_y + 0.05*scale, fix_y + 0.4*scale, FLOOR_THICKNESS + 0.82*scale, FLOOR_THICKNESS + 0.87*scale, "#FFFFFF")
        mirror_y1 = miny + 0.04 if door_near_top else maxy - 0.08
        mirror_y2 = miny + 0.08 if door_near_top else maxy - 0.04
        add_box_to_faces(all_faces, vx + 0.1*scale, vx + 0.6*scale, mirror_y1, mirror_y2, FLOOR_THICKNESS + 1.1*scale, FLOOR_THICKNESS + 1.7*scale, "#CBD5E1")
        
        # 2. Porcelain Toilet Bowl & Cistern
        tx = cx
        add_box_to_faces(all_faces, tx - 0.18*scale, tx + 0.18*scale, fix_y, fix_y + 0.4*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.4*scale, "#FFFFFF")
        cistern_y1 = miny + 0.04 if door_near_top else maxy - 0.2*scale
        cistern_y2 = miny + 0.2*scale if door_near_top else maxy - 0.04
        add_box_to_faces(all_faces, tx - 0.2*scale, tx + 0.2*scale, cistern_y1, cistern_y2, FLOOR_THICKNESS + 0.4*scale, FLOOR_THICKNESS + 0.75*scale, "#FFFFFF")
        
        # 3. Walk-in Shower with Tempered Glass Screen
        sx1, sx2 = maxx - 1.0 * scale, maxx - 0.1
        add_box_to_faces(all_faces, sx1, sx2, miny + 0.1, maxy - 0.1, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.04*scale, "#E2E8F0")
        add_box_to_faces(all_faces, sx1 - 0.02, sx1 + 0.02, miny + 0.1, maxy - 0.4, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.95*scale, "#93C5FD", alpha=0.4)
        
    elif "kitchen" in name:
        # Kitchen Work Triangle: Refrigerator -> Countertop -> Sink -> Cooktop
        door_near_bottom = False
        if door_polys:
            for door in door_polys:
                if door.intersects(poly.buffer(0.15)):
                    dy = door.centroid.y
                    if abs(dy - miny) < abs(dy - maxy):
                        door_near_bottom = True

        counter_y_min, counter_y_max = (maxy - 0.65, maxy - 0.05) if door_near_bottom else (miny + 0.05, miny + 0.65)
        
        # Counter cabinetry and quartz countertop
        add_box_to_faces(all_faces, minx + 0.8, maxx - 0.1, counter_y_min, counter_y_max, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.85 * scale, "#334155")
        add_box_to_faces(all_faces, minx + 0.8, maxx - 0.1, counter_y_min - 0.02, counter_y_max + 0.02, FLOOR_THICKNESS + 0.83 * scale, FLOOR_THICKNESS + 0.87 * scale, "#F8FAFC")
        
        # Refrigerator Tower (width 0.75m, height 1.85m)
        add_box_to_faces(all_faces, minx + 0.05, minx + 0.75, counter_y_min, counter_y_max + 0.05, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.85 * scale, "#94A3B8")
        
        # Inset Sink
        sink_cx = minx + 1.5 * scale
        add_box_to_faces(all_faces, sink_cx - 0.3*scale, sink_cx + 0.3*scale, (counter_y_min + counter_y_max)/2 - 0.2*scale, (counter_y_min + counter_y_max)/2 + 0.2*scale, FLOOR_THICKNESS + 0.84*scale, FLOOR_THICKNESS + 0.88*scale, "#CBD5E1")
        
        # Inset 4-Burner Cooktop
        stove_cx = maxx - 0.8 * scale
        add_box_to_faces(all_faces, stove_cx - 0.35*scale, stove_cx + 0.35*scale, (counter_y_min + counter_y_max)/2 - 0.25*scale, (counter_y_min + counter_y_max)/2 + 0.25*scale, FLOOR_THICKNESS + 0.85*scale, FLOOR_THICKNESS + 0.89*scale, "#0F172A")
        # Overhead Range Hood
        add_box_to_faces(all_faces, stove_cx - 0.35*scale, stove_cx + 0.35*scale, counter_y_min, counter_y_max, FLOOR_THICKNESS + 1.65*scale, FLOOR_THICKNESS + 1.95*scale, "#64748B")
        
        # Island / Breakfast Bar if spacious
        if h >= 3.2:
            island_y = cy
            add_box_to_faces(all_faces, cx - 0.8*scale, cx + 0.8*scale, island_y - 0.35*scale, island_y + 0.35*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.88*scale, "#CBD5E1")
            
    elif "dining" in name:
        # 6-Seater Dining Table and Chairs
        tw, th = 0.85 * scale, 0.5 * scale
        add_box_to_faces(all_faces, cx - tw, cx + tw, cy - th, cy + th, FLOOR_THICKNESS + 0.72*scale, FLOOR_THICKNESS + 0.76*scale, "#8D6E63")
        for lx in [-tw + 0.05*scale, tw - 0.05*scale]:
            for ly in [-th + 0.05*scale, th - 0.05*scale]:
                add_box_to_faces(all_faces, cx + lx - 0.02*scale, cx + lx + 0.02*scale, cy + ly - 0.02*scale, cy + ly + 0.02*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.72*scale, "#5D4037")
        
        # Chairs (6)
        for cx_offset in [-0.5 * scale, 0.0, 0.5 * scale]:
            for cy_offset in [-0.75 * scale, 0.75 * scale]:
                add_box_to_faces(all_faces, cx + cx_offset - 0.15*scale, cx + cx_offset + 0.15*scale, cy + cy_offset - 0.15*scale, cy + cy_offset + 0.15*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42*scale, "#475569")
                ry_min = cy + cy_offset - 0.15*scale if cy_offset < 0 else cy + cy_offset + 0.12*scale
                ry_max = cy + cy_offset - 0.12*scale if cy_offset < 0 else cy + cy_offset + 0.15*scale
                add_box_to_faces(all_faces, cx + cx_offset - 0.15*scale, cx + cx_offset + 0.15*scale, ry_min, ry_max, FLOOR_THICKNESS + 0.42*scale, FLOOR_THICKNESS + 0.78*scale, "#5D4037")


def _compute_wall_graph(rooms):
    """
    Build a topological graph of walls.
    Returns:
        edges: dict mapping (p1, p2) -> list of room_names sharing this edge
    """
    edge_to_rooms = defaultdict(list)
    
    for room_name, poly in rooms.items():
        if poly.is_empty: continue
        coords = list(poly.exterior.coords)
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            
            # Canonicalize edge key (sort points)
            if p1 > p2:
                key = (p2, p1)
            else:
                key = (p1, p2)
                
            edge_to_rooms[key].append(room_name)
            
    return edge_to_rooms


def build_house_from_layout(layout, visualize=True, output_file="house_3d_cad.ply"):
    """
    3D House Renderer - Wall-Centric CAD Logic
    """
    print("\n" + "=" * 60)
    print(" 3D House - Wall-Centric CAD Engine")
    print("=" * 60)

    if not layout or "rooms" not in layout:
        print("Invalid layout")
        return None

    # Filter Valid Rooms
    raw_rooms = {k: v for k, v in layout["rooms"].items() if v and not v.is_empty and isinstance(v, (Polygon, MultiPolygon))}
    if not raw_rooms:
        return None

    # Prepare Doors
    doors_input = layout.get("doors", None)
    
    # 1. Normalize Orientation (DISABLED to ensure 1:1 match with frontend highlight)
    # rooms, doors_geom = _normalize_orientation(raw_rooms, doors_input)
    rooms = raw_rooms
    doors_geom = doors_input
    
    # Snap angles to fix floating point drift
    def _snap_coords(poly):
         if not poly or poly.is_empty: return poly
         new_coords = []
         for x, y in poly.exterior.coords:
             # Strongly snap to 0.1m grid (10cm) to enforce squareness
             new_coords.append((round(x * 10) / 10.0, round(y * 10) / 10.0))
         return Polygon(new_coords)

    rooms = {k: _snap_coords(v) for k, v in rooms.items()}

    # Collect Door Polygons (for cutting reference only)
    door_polygons = []
    if doors_geom:
        if isinstance(doors_geom, Polygon): door_polygons.append(doors_geom)
        elif isinstance(doors_geom, MultiPolygon): door_polygons.extend(doors_geom.geoms)
        elif isinstance(doors_geom, list):
             for d in doors_geom:
                 if isinstance(d, Polygon): door_polygons.append(d)

    # 2. Build Floor Geometry
    all_faces = []
    
    # Create Ground Plane (Context) - REMOVED per user request
    # ground_poly = box(-10, -10, 30, 30) 
    # ground_faces = _extrude_polygon_to_3d(ground_poly, -0.1, -0.01)
    # for face in ground_faces:
    #     all_faces.append({"vertices": face, "color": GROUND_COLOR, "alpha": 1.0})

    # Create Room Floors
    print(" Building floors...")
    room_items = list(rooms.items())
    for i, (name, poly) in enumerate(room_items):
        color = ROOM_COLORS[i % len(ROOM_COLORS)]
        # Floor 0 to THICKNESS
        faces = _extrude_polygon_to_3d(poly, 0, FLOOR_THICKNESS)
        for f in faces:
            all_faces.append({"vertices": f, "color": color, "alpha": 0.9})
            
        # Add 3D Furniture blocks
        _place_room_furniture(all_faces, name.lower(), poly, door_polygons, all_rooms=rooms)

    # 3. Build Wall Topology
    print(" Building wall topology...")
    edge_to_rooms = _compute_wall_graph(rooms)
    
    # Parse Adjacency for Balcony Logic
    adj_list = layout.get("adjacency", [])
    balcony_types = {} 
    for r_name in rooms:
        if "balcony" in r_name.lower() or "garden" in r_name.lower():
            # Determine type
            b_type = 'half' # Default
            # Find neighbors
            neighbors = []
            for a, b in adj_list:
                if a == r_name: neighbors.append(b)
                elif b == r_name: neighbors.append(a)
            for n in neighbors:
                if "living" in n.lower() or "hall" in n.lower():
                    b_type = 'open'
            balcony_types[r_name] = b_type

    # 4. Generate Wall Geometry (Cutting for Doors & Windows)
    print(" Generating walls and windows...")
    
    generated_door_panels = [] # New list for wall-aligned doors
    
    for (p1, p2), sharing_rooms in edge_to_rooms.items():
        base_line = LineString([p1, p2])
        if base_line.length < 0.1: continue
        
        # Determine Wall Type & Thickness
        is_exterior = (len(sharing_rooms) == 1)
        wall_thick = EXTERIOR_WALL_THICKNESS if is_exterior else WALL_THICKNESS
        
        # Determine Height
        z_bottom = FLOOR_THICKNESS
        z_top = FLOOR_THICKNESS + WALL_HEIGHT
        
        if is_exterior:
            room_name = sharing_rooms[0].lower()
            if room_name in balcony_types:
                if balcony_types[room_name] == 'open':
                    z_top = FLOOR_THICKNESS + 0.1 # Curb
                elif balcony_types[room_name] == 'half':
                    z_top = FLOOR_THICKNESS + (WALL_HEIGHT * 0.4) # Parapet
                for f in _extrude_linestring_to_thin_wall(base_line, z_bottom, z_top, thickness=wall_thick):
                    all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                continue

            # Check if this exterior segment has an entrance door
            has_door = False
            if door_polygons:
                has_door = any(base_line.intersects(d.buffer(0.02)) for d in door_polygons)

            # If no door on this exterior wall, insert architectural window!
            if not has_door:
                is_habitable = any(t in room_name for t in ["living", "bedroom", "dining", "kitchen", "study", "family"])
                is_bathroom = any(t in room_name for t in ["bath", "toilet", "powder"])

                if is_habitable and base_line.length >= 1.6:
                    win_width = min(1.8, max(1.0, base_line.length * 0.55))
                    L = base_line.length
                    start_dist = (L - win_width) / 2.0
                    end_dist = start_dist + win_width

                    p_start = base_line.interpolate(start_dist / L, normalized=True)
                    p_end = base_line.interpolate(end_dist / L, normalized=True)

                    seg_before = LineString([p1, (p_start.x, p_start.y)])
                    seg_window = LineString([(p_start.x, p_start.y), (p_end.x, p_end.y)])
                    seg_after = LineString([(p_end.x, p_end.y), p2])

                    if seg_before.length > 0.05:
                        for f in _extrude_linestring_to_thin_wall(seg_before, z_bottom, z_top, thickness=wall_thick):
                            all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                    if seg_after.length > 0.05:
                        for f in _extrude_linestring_to_thin_wall(seg_after, z_bottom, z_top, thickness=wall_thick):
                            all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})

                    z_sill = FLOOR_THICKNESS + WINDOW_SILL_HEIGHT
                    z_head = FLOOR_THICKNESS + WINDOW_HEAD_HEIGHT

                    # Wall below sill & header above window
                    for f in _extrude_linestring_to_thin_wall(seg_window, z_bottom, z_sill, thickness=wall_thick):
                        all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                    for f in _extrude_linestring_to_thin_wall(seg_window, z_head, z_top, thickness=wall_thick):
                        all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                    # Glass pane (translucent sky blue)
                    for f in _extrude_linestring_to_thin_wall(seg_window, z_sill + 0.02, z_head - 0.02, thickness=0.03):
                        all_faces.append({"vertices": f, "color": WINDOW_GLASS_COLOR, "alpha": 0.55})
                    # Window frame trim
                    for f in _extrude_linestring_to_thin_wall(seg_window, z_sill, z_sill + 0.03, thickness=wall_thick * 1.05):
                        all_faces.append({"vertices": f, "color": WINDOW_FRAME_COLOR, "alpha": 1.0})
                    for f in _extrude_linestring_to_thin_wall(seg_window, z_head - 0.03, z_head, thickness=wall_thick * 1.05):
                        all_faces.append({"vertices": f, "color": WINDOW_FRAME_COLOR, "alpha": 1.0})
                    continue

                elif is_bathroom and base_line.length >= 1.0:
                    win_width = min(0.8, base_line.length * 0.45)
                    L = base_line.length
                    start_dist = (L - win_width) / 2.0
                    end_dist = start_dist + win_width

                    p_start = base_line.interpolate(start_dist / L, normalized=True)
                    p_end = base_line.interpolate(end_dist / L, normalized=True)

                    seg_before = LineString([p1, (p_start.x, p_start.y)])
                    seg_window = LineString([(p_start.x, p_start.y), (p_end.x, p_end.y)])
                    seg_after = LineString([(p_end.x, p_end.y), p2])

                    if seg_before.length > 0.05:
                        for f in _extrude_linestring_to_thin_wall(seg_before, z_bottom, z_top, thickness=wall_thick):
                            all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                    if seg_after.length > 0.05:
                        for f in _extrude_linestring_to_thin_wall(seg_after, z_bottom, z_top, thickness=wall_thick):
                            all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})

                    z_sill = FLOOR_THICKNESS + BATH_WINDOW_SILL_HEIGHT
                    z_head = FLOOR_THICKNESS + WINDOW_HEAD_HEIGHT

                    for f in _extrude_linestring_to_thin_wall(seg_window, z_bottom, z_sill, thickness=wall_thick):
                        all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                    for f in _extrude_linestring_to_thin_wall(seg_window, z_head, z_top, thickness=wall_thick):
                        all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                    for f in _extrude_linestring_to_thin_wall(seg_window, z_sill + 0.02, z_head - 0.02, thickness=0.03):
                        all_faces.append({"vertices": f, "color": "#E2E8F0", "alpha": 0.70})
                    continue

        # Interior Wall (or exterior wall with entrance door)
        final_segments = [base_line]
        
        if door_polygons:
            for door in door_polygons:
                new_segments = []
                door_shape = door.buffer(0.01) # Slight buffer vs line for intersection
                
                for seg in final_segments:
                    if seg.intersects(door_shape):
                        intersection = seg.intersection(door_shape)
                        
                        if not intersection.is_empty and isinstance(intersection, LineString):
                            # Extrude WALL LINTEL/HEADER above door or cased opening!
                            z_header_bottom = FLOOR_THICKNESS + DOOR_HEIGHT
                            header_faces = _extrude_linestring_to_thin_wall(
                                intersection, z_header_bottom, z_top, thickness=wall_thick
                            )
                            for f in header_faces:
                                all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})

                            # Only extrude wooden door panel for actual hinged doors (width <= 1.10m)!
                            # Cased openings (> 1.10m, such as open kitchen portal) do NOT get a door panel.
                            i_coords = list(intersection.coords)
                            if len(i_coords) >= 2:
                                ix1, iy1 = i_coords[0]
                                ix2, iy2 = i_coords[-1]
                                idx, idy = ix2 - ix1, iy2 - iy1
                                ilen = (idx**2 + idy**2)**0.5
                                
                                if 0.55 <= ilen <= 1.10: # Min/max hinged door width
                                    wall_dir = np.array([idx, idy]) / ilen
                                    perp_dir = np.array([-wall_dir[1], wall_dir[0]])
                                    center = np.array([(ix1+ix2)/2, (iy1+iy2)/2])
                                    
                                    d_thick = wall_thick * 0.8 # Slightly thinner than wall
                                    d_half_width = ilen / 2
                                    d_half_thick = d_thick / 2
                                    
                                    c1 = center + wall_dir * d_half_width + perp_dir * d_half_thick
                                    c2 = center - wall_dir * d_half_width + perp_dir * d_half_thick
                                    c3 = center - wall_dir * d_half_width - perp_dir * d_half_thick
                                    c4 = center + wall_dir * d_half_width - perp_dir * d_half_thick
                                    
                                    door_poly = Polygon([tuple(c1), tuple(c2), tuple(c3), tuple(c4)])
                                    generated_door_panels.append(door_poly)

                        diff = seg.difference(door_shape)
                        if not diff.is_empty:
                            if isinstance(diff, LineString):
                                new_segments.append(diff)
                            elif hasattr(diff, "geoms"):
                                new_segments.extend(diff.geoms)
                    else:
                        new_segments.append(seg)
                final_segments = new_segments
        
        # Extrude solid remaining segments
        for seg in final_segments:
            if seg.length < 0.05: continue
            w_faces = _extrude_linestring_to_thin_wall(seg, z_bottom, z_top, thickness=wall_thick)
            for f in w_faces:
                all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})

    # 5. Generate Doors (Use Wall-Aligned Panels)
    print(" Generating doors...")
    for door in generated_door_panels:
        if door.is_empty: continue
        # Thinner panel
        d_faces = _extrude_polygon_vertical_shell(door, FLOOR_THICKNESS, FLOOR_THICKNESS + DOOR_HEIGHT)
        for f in d_faces:
            all_faces.append({"vertices": f, "color": DOOR_PANEL_COLOR, "alpha": 1.0})

    # 6. Render Mesh
    print(" Rendering Mesh...")
    vertices = []
    triangles = []
    colors = []
    
    for item in all_faces:
        face = item["vertices"]
        if len(face) < 3: continue
        base = len(vertices)
        c = _hex_to_rgb01(item["color"])
        for v in face:
            vertices.append(v)
            colors.append(c)
        # Triangulation (fan)
        for i in range(1, len(face) - 1):
            triangles.append([base, base+i, base+i+1])
            
    if not vertices:
        return None
        
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(np.array(vertices, dtype=float))
    mesh.triangles = o3d.utility.Vector3iVector(np.array(triangles, dtype=np.int32))
    mesh.vertex_colors = o3d.utility.Vector3dVector(np.array(colors, dtype=float))
    mesh.compute_vertex_normals()
    
    if output_file:
        o3d.io.write_triangle_mesh(output_file, mesh)
        
    return mesh
