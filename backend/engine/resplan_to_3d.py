
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, box, Point
from shapely.ops import unary_union
from shapely.affinity import rotate
from collections import defaultdict
import open3d as o3d
import os

try:
    from constraints.circulation import compute_protected_circulation_polygon
except ImportError:
    try:
        from engine.constraints.circulation import compute_protected_circulation_polygon
    except ImportError:
        compute_protected_circulation_polygon = None

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


def _place_room_furniture(all_faces, name, poly, door_polys=None, all_rooms=None, protected_circ_poly=None, openings=None, entrance_geom=None, room_windows=None, window_exclusion_polys=None, wall_graph=None, placed_furniture_out=None):
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
    room_windows = room_windows or []
    window_exclusion_polys = window_exclusion_polys or []
    
    if entrance_geom is None and openings:
        for op in openings:
            if op.get("type") == "entrance" or "exterior" in op.get("rooms", ()):
                entrance_geom = op.get("polygon")
                break
    
    if "living" in name or "lounge" in name or "family" in name:
        walls = {
            "south": LineString([(minx, miny), (maxx, miny)]),
            "north": LineString([(minx, maxy), (maxx, maxy)]),
            "west":  LineString([(minx, miny), (minx, maxy)]),
            "east":  LineString([(maxx, miny), (maxx, maxy)]),
        }

        # 1. Identify Entrance Wall and Directional Inward Foyer Arrival Polygon
        entrance_wall = None
        foyer_keepout = None
        if entrance_geom and not entrance_geom.is_empty:
            for w_side, w_line in walls.items():
                if entrance_geom.distance(w_line) < 0.45:
                    entrance_wall = w_side
                    break

            eb = entrance_geom.bounds
            ecx = (eb[0] + eb[2]) / 2.0
            ecy = (eb[1] + eb[3]) / 2.0
            ew = eb[2] - eb[0]
            eh = eb[3] - eb[1]
            foyer_depth = 1.70  # 1.7m inward arrival clearance
            foyer_width = max(1.80, max(ew, eh) + 0.80)

            if entrance_wall == "south":
                foyer_keepout = box(ecx - foyer_width / 2.0, miny, ecx + foyer_width / 2.0, miny + foyer_depth)
            elif entrance_wall == "north":
                foyer_keepout = box(ecx - foyer_width / 2.0, maxy - foyer_depth, ecx + foyer_width / 2.0, maxy)
            elif entrance_wall == "west":
                foyer_keepout = box(minx, ecy - foyer_width / 2.0, minx + foyer_depth, ecy + foyer_width / 2.0)
            elif entrance_wall == "east":
                foyer_keepout = box(maxx - foyer_depth, ecy - foyer_width / 2.0, maxx, ecy + foyer_width / 2.0)
            else:
                foyer_keepout = entrance_geom.buffer(1.6)

        wall_scores = {}
        for w_side, w_line in walls.items():
            doors_on_wall = sum(1 for dp in door_polys if dp.intersects(w_line.buffer(0.25)))
            has_win_on_wall = any(
                w_line.distance(win["wall_segment"]) < 0.25 or w_line.distance(win["base_line"]) < 0.25
                for win in room_windows
            )
            
            is_interior = False
            if wall_graph:
                for (p1, p2), sharing in wall_graph.items():
                    if LineString([p1, p2]).distance(w_line) < 0.15 and len(sharing) > 1:
                        is_interior = True
                        break
                        
            score = -doors_on_wall * 15.0 + (w_line.length * 2.0)
            if is_interior:
                score += 25.0  # Strongly favor solid interior drywall

            # The Main Entrance wall must NEVER host TV / media console
            if w_side == entrance_wall:
                score = -9999.0

            # Exterior window wall must NEVER host TV / media console!
            if has_win_on_wall:
                score = -9999.0

            # If placing TV on opposite wall would force sofa into the foyer arrival path, penalize it
            if entrance_wall == "south" and w_side == "north" and h < (foyer_depth + 2.2):
                score -= 20.0
            elif entrance_wall == "north" and w_side == "south" and h < (foyer_depth + 2.2):
                score -= 20.0
            elif entrance_wall == "west" and w_side == "east" and w < (foyer_depth + 2.2):
                score -= 20.0
            elif entrance_wall == "east" and w_side == "west" and w < (foyer_depth + 2.2):
                score -= 20.0

            wall_scores[w_side] = score

        best_wall = max(wall_scores.items(), key=lambda x: x[1])[0]
        if wall_scores[best_wall] < -5000.0:
            # Fallback: pick any wall without entrance and least doors
            cand_walls = [ws for ws in walls.keys() if ws != entrance_wall]
            if cand_walls:
                best_wall = min(cand_walls, key=lambda ws: sum(1 for dp in door_polys if dp.intersects(walls[ws].buffer(0.25))))
            else:
                best_wall = "north"
        
        if best_wall in ["south", "north"]:
            is_south = (best_wall == "south")
            tw = min(0.9 * scale, w * 0.28)
            tv_y = miny + 0.05 if is_south else maxy - 0.45 * scale
            tv_center_y = miny + 0.25 * scale if is_south else maxy - 0.25 * scale
            dist = min(2.4, max(1.8, (h - 0.8) * 0.55))
            sofa_y = miny + dist if is_south else maxy - dist - 0.7 * scale

            # Protect Foyer Arrival Zone: ensure sofa never blocks entrance
            if foyer_keepout and not is_south:
                foyer_top = foyer_keepout.bounds[3]
                if sofa_y < foyer_top + 0.20:
                    sofa_y = min(maxy - 1.2 * scale, foyer_top + 0.20)
            elif foyer_keepout and is_south:
                foyer_bottom = foyer_keepout.bounds[1]
                if sofa_y + 0.7 * scale > foyer_bottom - 0.20:
                    sofa_y = max(miny + 0.5 * scale, foyer_bottom - 0.20 - 0.7 * scale)

            coffee_y = (tv_center_y + sofa_y) / 2.0
            
            # 1. Floor-grounded TV Media Console (width ~1.8m, depth 0.4m, height 0.42m)
            add_box_to_faces(all_faces, cx - tw, cx + tw, tv_y, tv_y + 0.40 * scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#334155")
            
            # 2. Wall Accent Backplate (anchors TV to wall plane, eliminating air gap)
            pan_y1 = miny + 0.02 if is_south else maxy - 0.06
            pan_y2 = miny + 0.06 if is_south else maxy - 0.02
            add_box_to_faces(all_faces, cx - tw * 0.95, cx + tw * 0.95, pan_y1, pan_y2, FLOOR_THICKNESS + 0.40 * scale, FLOOR_THICKNESS + 1.50 * scale, "#1E293B")
            
            # 3. Wall-mounted TV Screen (flush to wall plane, center height ~1.15m seated eye level)
            sw = tw * 0.85
            screen_y1 = miny + 0.04 if is_south else maxy - 0.08
            screen_y2 = miny + 0.07 if is_south else maxy - 0.05
            add_box_to_faces(all_faces, cx - sw, cx + sw, screen_y1, screen_y2, FLOOR_THICKNESS + 0.82 * scale, FLOOR_THICKNESS + 1.45 * scale, "#0F172A")
            
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
            
            if placed_furniture_out is not None:
                placed_furniture_out.append({
                    "room": name, "type": "tv", "poly": box(cx - tw, min(tv_y, screen_y1), cx + tw, max(tv_y + 0.4*scale, screen_y2)),
                    "center": (cx, tv_center_y), "height": 1.45
                })
                placed_furniture_out.append({
                    "room": name, "type": "sofa", "poly": box(cx - cw - 0.1*scale, sofa_y, cx + cw + 0.1*scale, sofa_y + cd),
                    "center": (cx, sofa_y + cd/2.0), "height": 0.78
                })
        else:
            # West or East TV Wall
            is_west = (best_wall == "west")
            th = min(0.9 * scale, h * 0.28)
            tv_x = minx + 0.05 if is_west else maxx - 0.45 * scale
            tv_center_x = minx + 0.25 * scale if is_west else maxx - 0.25 * scale
            dist = min(2.4, max(1.8, (w - 0.8) * 0.55))
            sofa_x = minx + dist if is_west else maxx - dist - 0.7 * scale

            # If entrance is on South wall, adjust conversation center north of foyer keep-out
            cy_furniture = cy
            if foyer_keepout and entrance_wall == "south":
                foyer_top = foyer_keepout.bounds[3]
                if cy - 1.2 * scale < foyer_top:
                    cy_furniture = min(maxy - 1.3 * scale, foyer_top + 1.2 * scale)

            coffee_x = (cx + sofa_x) / 2.0
            
            # 1. Floor-grounded TV Media Console
            add_box_to_faces(all_faces, tv_x, tv_x + 0.40 * scale, cy_furniture - th, cy_furniture + th, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#334155")
            
            # 2. Wall Accent Backplate
            pan_x1 = minx + 0.02 if is_west else maxx - 0.06
            pan_x2 = minx + 0.06 if is_west else maxx - 0.02
            add_box_to_faces(all_faces, pan_x1, pan_x2, cy_furniture - th * 0.95, cy_furniture + th * 0.95, FLOOR_THICKNESS + 0.40 * scale, FLOOR_THICKNESS + 1.50 * scale, "#1E293B")
            
            # 3. Mounted TV Screen (seated eye level)
            sh = th * 0.85
            screen_x1 = minx + 0.04 if is_west else maxx - 0.08
            screen_x2 = minx + 0.07 if is_west else maxx - 0.05
            add_box_to_faces(all_faces, screen_x1, screen_x2, cy_furniture - sh, cy_furniture + sh, FLOOR_THICKNESS + 0.82 * scale, FLOOR_THICKNESS + 1.45 * scale, "#0F172A")
            
            # Area Rug & Coffee Table
            add_box_to_faces(all_faces, coffee_x - 0.8 * scale, coffee_x + 0.8 * scale, cy_furniture - 1.2 * scale, cy_furniture + 1.2 * scale, FLOOR_THICKNESS + 0.005, FLOOR_THICKNESS + 0.01, "#E2E8F0")
            add_box_to_faces(all_faces, coffee_x - 0.3 * scale, coffee_x + 0.3 * scale, cy_furniture - 0.5 * scale, cy_furniture + 0.5 * scale, FLOOR_THICKNESS + 0.32 * scale, FLOOR_THICKNESS + 0.36 * scale, "#D7CCC8")
            
            # Sofa Facing West/East
            cd = 0.4 * scale
            back_x1 = sofa_x + 0.3 * scale if is_west else sofa_x
            back_x2 = sofa_x + 0.4 * scale if is_west else sofa_x + 0.1 * scale
            add_box_to_faces(all_faces, sofa_x, sofa_x + cd, cy_furniture - 1.0 * scale, cy_furniture + 1.0 * scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#475569")
            add_box_to_faces(all_faces, back_x1, back_x2, cy_furniture - 1.0 * scale, cy_furniture + 1.0 * scale, FLOOR_THICKNESS + 0.42 * scale, FLOOR_THICKNESS + 0.78 * scale, "#334155")
            
            if placed_furniture_out is not None:
                placed_furniture_out.append({
                    "room": name, "type": "tv", "poly": box(min(tv_x, screen_x1), cy_furniture - th, max(tv_x + 0.4*scale, screen_x2), cy_furniture + th),
                    "center": (tv_center_x, cy_furniture), "height": 1.45
                })
                placed_furniture_out.append({
                    "room": name, "type": "sofa", "poly": box(sofa_x, cy_furniture - 1.0*scale, sofa_x + cd, cy_furniture + 1.0*scale),
                    "center": (sofa_x + cd/2.0, cy_furniture), "height": 0.78
                })

        # Integrated Dining Zone if spacious and no separate dining room
        has_dining_room = any("dining" in r.lower() for r in all_rooms.keys())
        if not has_dining_room and (w * h >= 16.0 or max(w, h) >= 4.6):
            dtw, dth = 0.6 * scale, 0.4 * scale
            pullout = 0.60
            
            # Find kitchen connection if any
            kitchen_pos = None
            if openings:
                for op in openings:
                    pair = op.get("rooms", ())
                    if any("kitchen" in str(r).lower() for r in pair) and any("living" in str(r).lower() for r in pair):
                        op_p = op.get("polygon")
                        if op_p:
                            kitchen_pos = op_p.centroid
                            break

            # Generate candidate dining positions across available quadrants of the living room
            candidate_positions = []
            x_steps = [minx + dtw + 0.6, cx - dtw - 0.2, cx + dtw + 0.2, maxx - dtw - 0.6]
            y_steps = [miny + dth + 0.6, cy - dth - 0.2, cy + dth + 0.2, maxy - dth - 0.6]
            
            for cx_cand in x_steps:
                for cy_cand in y_steps:
                    if (minx + dtw + 0.2) <= cx_cand <= (maxx - dtw - 0.2) and (miny + dth + 0.2) <= cy_cand <= (maxy - dth - 0.2):
                        candidate_positions.append((cx_cand, cy_cand))

            # Filter & score candidates against protected circulation and window keep-outs
            valid_candidates = []
            for cx_cand, cy_cand in candidate_positions:
                t_box = box(cx_cand - dtw, cy_cand - dth, cx_cand + dtw, cy_cand + dth)
                env = box(cx_cand - dtw - pullout, cy_cand - dth - pullout, cx_cand + dtw + pullout, cy_cand + dth + pullout)
                
                # Must stay inside room
                if not poly.contains(t_box):
                    continue
                    
                # Conflict with TV / Sofa area
                if best_wall in ["south", "north"]:
                    if abs(cy_cand - sofa_y) < 1.0 or abs(cy_cand - tv_y) < 1.0:
                        continue
                else:
                    if abs(cx_cand - sofa_x) < 1.0 or abs(cx_cand - tv_x) < 1.0:
                        continue
                
                # Check intersection with protected circulation
                inter_area = 0.0
                hard_conflict = False
                if protected_circ_poly and not protected_circ_poly.is_empty:
                    if t_box.intersects(protected_circ_poly):
                        hard_conflict = True
                    inter = env.intersection(protected_circ_poly)
                    inter_area = inter.area if not inter.is_empty else 0.0

                if hard_conflict:
                    continue

                if foyer_keepout and env.intersects(foyer_keepout):
                    continue

                min_door_dist = 999.0
                if door_polys:
                    min_door_dist = min(t_box.distance(dp) for dp in door_polys)
                
                kitchen_score = 0.0
                if kitchen_pos:
                    dist_k = ((cx_cand - kitchen_pos.x)**2 + (cy_cand - kitchen_pos.y)**2)**0.5
                    kitchen_score = -dist_k * 2.0
                
                score = (-inter_area * 100.0) + (min_door_dist * 5.0) + kitchen_score
                valid_candidates.append((score, cx_cand, cy_cand, inter_area, min_door_dist))

            if valid_candidates:
                valid_candidates.sort(key=lambda x: x[0], reverse=True)
                best_cand = valid_candidates[0]
                dx, dy = best_cand[1], best_cand[2]

                # Render Dining Table
                add_box_to_faces(all_faces, dx - dtw, dx + dtw, dy - dth, dy + dth, FLOOR_THICKNESS + 0.72 * scale, FLOOR_THICKNESS + 0.76 * scale, "#8D6E63")
                # Table Legs
                for lx in [-dtw + 0.05*scale, dtw - 0.05*scale]:
                    for ly in [-dth + 0.05*scale, dth - 0.05*scale]:
                        add_box_to_faces(all_faces, dx + lx - 0.02*scale, dx + lx + 0.02*scale, dy + ly - 0.02*scale, dy + ly + 0.02*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.72*scale, "#5D4037")
                # Dining Chairs
                for ox in [-dtw * 0.6, dtw * 0.6]:
                    for oy in [-dth - 0.25 * scale, dth + 0.25 * scale]:
                        add_box_to_faces(all_faces, dx + ox - 0.12*scale, dx + ox + 0.12*scale, dy + oy - 0.12*scale, dy + oy + 0.12*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42*scale, "#475569")
                
                if placed_furniture_out is not None:
                    placed_furniture_out.append({
                        "room": name, "type": "dining_table", "poly": box(dx - dtw, dy - dth, dx + dtw, dy + dth), "height": 0.76
                    })
                
    elif "bedroom" in name or "bed" in name:
        walls = {
            "south": LineString([(minx, miny), (maxx, miny)]),
            "north": LineString([(minx, maxy), (maxx, maxy)]),
            "west":  LineString([(minx, miny), (minx, maxy)]),
            "east":  LineString([(maxx, miny), (maxx, maxy)]),
        }
        
        # Check doors, windows, and interior drywall for each wall
        wall_has_door = {}
        wall_has_window = {}
        wall_is_interior = {}
        
        for w_side, w_line in walls.items():
            wall_has_door[w_side] = any(dp.intersects(w_line.buffer(0.30)) for dp in door_polys)
            wall_has_window[w_side] = any(
                w_line.distance(win["wall_segment"]) < 0.25 or w_line.distance(win["base_line"]) < 0.25
                for win in room_windows
            )
            is_int = False
            if wall_graph:
                for (p1, p2), sharing in wall_graph.items():
                    if LineString([p1, p2]).distance(w_line) < 0.15 and len(sharing) > 1:
                        is_int = True
                        break
            wall_is_interior[w_side] = is_int

        # 1. Select Headboard Focal Wall (Solid Wall, no doors, no windows)
        head_scores = {}
        for w_side, w_line in walls.items():
            score = 0.0
            if wall_has_door[w_side]: score -= 150.0
            if wall_has_window[w_side]: score -= 60.0
            if wall_is_interior[w_side]: score += 50.0
            score += w_line.length * 1.5
            head_scores[w_side] = score
            
        best_head_wall = max(head_scores.items(), key=lambda x: x[1])[0]
        
        bw, bh = 0.8 * scale, 0.95 * scale
        
        # Orient bed according to headboard wall
        if best_head_wall == "north":
            bed_cx = cx
            head_y1 = maxy - 0.18 * scale
            head_y2 = maxy - 0.06
            mat_y1 = maxy - 0.18 * scale - 1.7 * scale
            mat_y2 = maxy - 0.18 * scale
            pil_y1 = maxy - 0.52 * scale
            pil_y2 = maxy - 0.22 * scale
            night_y1 = maxy - 0.48 * scale
            night_y2 = maxy - 0.10
            add_box_to_faces(all_faces, bed_cx - bw - 0.05*scale, bed_cx + bw + 0.05*scale, head_y1, head_y2, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.0 * scale, "#D7CCC8")
            add_box_to_faces(all_faces, bed_cx - bw, bed_cx + bw, mat_y1, mat_y2, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.48 * scale, "#FFFFFF")
            add_box_to_faces(all_faces, bed_cx - 0.65*scale, bed_cx - 0.1*scale, pil_y1, pil_y2, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            add_box_to_faces(all_faces, bed_cx + 0.1*scale, bed_cx + 0.65*scale, pil_y1, pil_y2, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            for side_x in [bed_cx - bw - 0.35*scale, bed_cx + bw + 0.05*scale]:
                if minx + 0.05 <= side_x and side_x + 0.3*scale <= maxx - 0.05:
                    add_box_to_faces(all_faces, side_x, side_x + 0.3*scale, night_y1, night_y2, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#5D4037")
                    add_box_to_faces(all_faces, side_x + 0.1*scale, side_x + 0.2*scale, (night_y1 + night_y2)/2 - 0.05*scale, (night_y1 + night_y2)/2 + 0.05*scale, FLOOR_THICKNESS + 0.42*scale, FLOOR_THICKNESS + 0.65*scale, "#FDE047")
            bed_box = box(bed_cx - bw, mat_y1, bed_cx + bw, head_y2)
        elif best_head_wall == "south":
            bed_cx = cx
            head_y1 = miny + 0.06
            head_y2 = miny + 0.18 * scale
            mat_y1 = miny + 0.18 * scale
            mat_y2 = miny + 0.18 * scale + 1.7 * scale
            pil_y1 = miny + 0.22 * scale
            pil_y2 = miny + 0.52 * scale
            night_y1 = miny + 0.10
            night_y2 = miny + 0.48 * scale
            add_box_to_faces(all_faces, bed_cx - bw - 0.05*scale, bed_cx + bw + 0.05*scale, head_y1, head_y2, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.0 * scale, "#D7CCC8")
            add_box_to_faces(all_faces, bed_cx - bw, bed_cx + bw, mat_y1, mat_y2, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.48 * scale, "#FFFFFF")
            add_box_to_faces(all_faces, bed_cx - 0.65*scale, bed_cx - 0.1*scale, pil_y1, pil_y2, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            add_box_to_faces(all_faces, bed_cx + 0.1*scale, bed_cx + 0.65*scale, pil_y1, pil_y2, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            for side_x in [bed_cx - bw - 0.35*scale, bed_cx + bw + 0.05*scale]:
                if minx + 0.05 <= side_x and side_x + 0.3*scale <= maxx - 0.05:
                    add_box_to_faces(all_faces, side_x, side_x + 0.3*scale, night_y1, night_y2, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#5D4037")
                    add_box_to_faces(all_faces, side_x + 0.1*scale, side_x + 0.2*scale, (night_y1 + night_y2)/2 - 0.05*scale, (night_y1 + night_y2)/2 + 0.05*scale, FLOOR_THICKNESS + 0.42*scale, FLOOR_THICKNESS + 0.65*scale, "#FDE047")
            bed_box = box(bed_cx - bw, head_y1, bed_cx + bw, mat_y2)
        elif best_head_wall == "west":
            bed_cy = cy
            head_x1 = minx + 0.06
            head_x2 = minx + 0.18 * scale
            mat_x1 = minx + 0.18 * scale
            mat_x2 = minx + 0.18 * scale + 1.7 * scale
            pil_x1 = minx + 0.22 * scale
            pil_x2 = minx + 0.52 * scale
            night_x1 = minx + 0.10
            night_x2 = minx + 0.48 * scale
            add_box_to_faces(all_faces, head_x1, head_x2, bed_cy - bw - 0.05*scale, bed_cy + bw + 0.05*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.0 * scale, "#D7CCC8")
            add_box_to_faces(all_faces, mat_x1, mat_x2, bed_cy - bw, bed_cy + bw, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.48 * scale, "#FFFFFF")
            add_box_to_faces(all_faces, pil_x1, pil_x2, bed_cy - 0.65*scale, bed_cy - 0.1*scale, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            add_box_to_faces(all_faces, pil_x1, pil_x2, bed_cy + 0.1*scale, bed_cy + 0.65*scale, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            for side_y in [bed_cy - bw - 0.35*scale, bed_cy + bw + 0.05*scale]:
                if miny + 0.05 <= side_y and side_y + 0.3*scale <= maxy - 0.05:
                    add_box_to_faces(all_faces, night_x1, night_x2, side_y, side_y + 0.3*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#5D4037")
                    add_box_to_faces(all_faces, (night_x1 + night_x2)/2 - 0.05*scale, (night_x1 + night_x2)/2 + 0.05*scale, side_y + 0.1*scale, side_y + 0.2*scale, FLOOR_THICKNESS + 0.42*scale, FLOOR_THICKNESS + 0.65*scale, "#FDE047")
            bed_box = box(head_x1, bed_cy - bw, mat_x2, bed_cy + bw)
        else: # east
            bed_cy = cy
            head_x1 = maxx - 0.18 * scale
            head_x2 = maxx - 0.06
            mat_x1 = maxx - 0.18 * scale - 1.7 * scale
            mat_x2 = maxx - 0.18 * scale
            pil_x1 = maxx - 0.52 * scale
            pil_x2 = maxx - 0.22 * scale
            night_x1 = maxx - 0.48 * scale
            night_x2 = maxx - 0.10
            add_box_to_faces(all_faces, head_x1, head_x2, bed_cy - bw - 0.05*scale, bed_cy + bw + 0.05*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.0 * scale, "#D7CCC8")
            add_box_to_faces(all_faces, mat_x1, mat_x2, bed_cy - bw, bed_cy + bw, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.48 * scale, "#FFFFFF")
            add_box_to_faces(all_faces, pil_x1, pil_x2, bed_cy - 0.65*scale, bed_cy - 0.1*scale, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            add_box_to_faces(all_faces, pil_x1, pil_x2, bed_cy + 0.1*scale, bed_cy + 0.65*scale, FLOOR_THICKNESS + 0.48*scale, FLOOR_THICKNESS + 0.55*scale, "#E2E8F0")
            for side_y in [bed_cy - bw - 0.35*scale, bed_cy + bw + 0.05*scale]:
                if miny + 0.05 <= side_y and side_y + 0.3*scale <= maxy - 0.05:
                    add_box_to_faces(all_faces, night_x1, night_x2, side_y, side_y + 0.3*scale, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.42 * scale, "#5D4037")
                    add_box_to_faces(all_faces, (night_x1 + night_x2)/2 - 0.05*scale, (night_x1 + night_x2)/2 + 0.05*scale, side_y + 0.1*scale, side_y + 0.2*scale, FLOOR_THICKNESS + 0.42*scale, FLOOR_THICKNESS + 0.65*scale, "#FDE047")
            bed_box = box(mat_x1, bed_cy - bw, head_x2, bed_cy + bw)

        if placed_furniture_out is not None:
            placed_furniture_out.append({"room": name, "type": "bed", "poly": bed_box, "height": 1.0})

        # 2. Select Wardrobe Wall (Solid Interior Wall, NEVER an Exterior Window Wall!)
        wardrobe_scores = {}
        for w_side in [w_key for w_key in walls.keys() if w_key != best_head_wall]:
            w_line = walls[w_side]
            has_w = wall_has_window[w_side]
            has_d = wall_has_door[w_side]
            is_int = wall_is_interior[w_side]
            
            if has_w:
                score = -9999.0 # STRICTLY DISQUALIFIED
            elif has_d:
                score = -100.0
            else:
                score = 50.0
                if is_int: score += 50.0
            wardrobe_scores[w_side] = score
            
        best_wardrobe_wall = max(wardrobe_scores.items(), key=lambda x: x[1])[0]
        if wardrobe_scores[best_wardrobe_wall] > -5000.0:
            # Build wardrobe on best_wardrobe_wall
            w_depth = 0.58
            w_len = min(1.6 * scale, max(1.1, 0.42 * (w if best_wardrobe_wall in ["north", "south"] else h)))
            
            if best_wardrobe_wall == "west":
                wx1, wx2 = minx + 0.05, minx + 0.05 + w_depth
                wy1, wy2 = cy - w_len/2.0, cy + w_len/2.0
            elif best_wardrobe_wall == "east":
                wx1, wx2 = maxx - 0.05 - w_depth, maxx - 0.05
                wy1, wy2 = cy - w_len/2.0, cy + w_len/2.0
            elif best_wardrobe_wall == "north":
                wx1, wx2 = cx - w_len/2.0, cx + w_len/2.0
                wy1, wy2 = maxy - 0.05 - w_depth, maxy - 0.05
            else: # south
                wx1, wx2 = cx - w_len/2.0, cx + w_len/2.0
                wy1, wy2 = miny + 0.05, miny + 0.05 + w_depth

            w_box = box(wx1, wy1, wx2, wy2)
            # Verify no collision with window keepout, door swing, or bed
            overlaps_win = any(w_box.intersects(kp) for kp in window_exclusion_polys)
            overlaps_door = any(w_box.intersects(dp.buffer(0.25)) for dp in door_polys)
            overlaps_bed = w_box.intersects(bed_box.buffer(0.20))
            
            if not overlaps_win and not overlaps_door and not overlaps_bed:
                add_box_to_faces(all_faces, wx1, wx2, wy1, wy2, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 2.15 * scale, "#5D4037")
                hx = (wx1 + wx2) / 2.0
                hy = (wy1 + wy2) / 2.0
                add_box_to_faces(all_faces, hx - 0.02, hx + 0.02, hy - 0.02, hy + 0.02, FLOOR_THICKNESS + 0.95*scale, FLOOR_THICKNESS + 1.20*scale, "#CBD5E1")
                if placed_furniture_out is not None:
                    placed_furniture_out.append({"room": name, "type": "wardrobe", "poly": w_box, "height": 2.15})
        
    elif "bathroom" in name or "bath" in name or "toilet" in name:
        # Modern Bathroom Suite: Vanity, Toilet, and Shower/Tub
        door_closest = "bottom"
        if door_polys:
            for door in door_polys:
                if door.intersects(poly.buffer(0.15)):
                    dx, dy = door.centroid.x, door.centroid.y
                    dists = {"top": abs(dy - maxy), "bottom": abs(dy - miny), "left": abs(dx - minx), "right": abs(dx - maxx)}
                    door_closest = min(dists, key=dists.get)

        door_near_top = (door_closest == "top")
        door_near_right = (door_closest == "right")
        
        fix_y = miny + 0.15 if door_near_top else maxy - 0.55
        
        # 1. Floating Vanity Unit with Basin & Mirror (placed along back/fixture wall)
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
        if door_near_right:
            sx1, sx2 = minx + 0.1, minx + 1.0 * scale
            screen_x = sx2
        else:
            sx1, sx2 = maxx - 1.0 * scale, maxx - 0.1
            screen_x = sx1

        add_box_to_faces(all_faces, sx1, sx2, miny + 0.1, maxy - 0.1, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 0.04*scale, "#E2E8F0")
        add_box_to_faces(all_faces, screen_x - 0.02, screen_x + 0.02, miny + 0.1, maxy - 0.4, FLOOR_THICKNESS + 0.01, FLOOR_THICKNESS + 1.95*scale, "#93C5FD", alpha=0.4)
        
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

    # 2. Build Wall Topology & Precompute Windows & Keepouts
    print(" Building wall topology and precomputing openings...")
    edge_to_rooms = _compute_wall_graph(rooms)

    # Precompute exterior windows & opening exclusion polygons
    room_windows = defaultdict(list)
    window_exclusion_polys = []
    exterior_windows_meta = []

    for (p1, p2), sharing_rooms in edge_to_rooms.items():
        base_line = LineString([p1, p2])
        if base_line.length < 0.1: continue
        is_exterior = (len(sharing_rooms) == 1)
        if not is_exterior: continue

        r_name = sharing_rooms[0].lower()
        has_door = False
        if door_polygons:
            has_door = any(base_line.intersects(d.buffer(0.02)) for d in door_polygons)
        if has_door:
            continue

        is_habitable = any(t in r_name for t in ["living", "bedroom", "dining", "kitchen", "study", "family"])
        is_bathroom = any(t in r_name for t in ["bath", "toilet", "powder"])

        if is_habitable and base_line.length >= 1.6:
            win_width = min(1.8, max(1.0, base_line.length * 0.55))
        elif is_bathroom and base_line.length >= 1.0:
            win_width = min(0.8, base_line.length * 0.45)
        else:
            continue

        L = base_line.length
        start_dist = (L - win_width) / 2.0
        end_dist = start_dist + win_width

        p_start = base_line.interpolate(start_dist / L, normalized=True)
        p_end = base_line.interpolate(end_dist / L, normalized=True)
        seg_window = LineString([(p_start.x, p_start.y), (p_end.x, p_end.y)])

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        line_len = (dx**2 + dy**2)**0.5
        if line_len < 0.01: continue
        ux, uy = dx / line_len, dy / line_len
        nx, ny = -uy, ux

        r_poly = rooms.get(sharing_rooms[0])
        if r_poly and not r_poly.is_empty:
            rcx, rcy = r_poly.centroid.x, r_poly.centroid.y
            wcx = (p_start.x + p_end.x) / 2.0
            wcy = (p_start.y + p_end.y) / 2.0
            if (nx * (rcx - wcx) + ny * (rcy - wcy)) < 0:
                nx, ny = -nx, -ny

            keepout_depth = 0.80
            k_poly = Polygon([
                (p_start.x, p_start.y),
                (p_end.x, p_end.y),
                (p_end.x + nx * keepout_depth, p_end.y + ny * keepout_depth),
                (p_start.x + nx * keepout_depth, p_start.y + ny * keepout_depth)
            ])
            win_item = {
                "room": sharing_rooms[0],
                "base_line": base_line,
                "wall_segment": seg_window,
                "p_start": (p_start.x, p_start.y),
                "p_end": (p_end.x, p_end.y),
                "width": win_width,
                "keepout": k_poly,
                "center": (wcx, wcy),
                "inward_normal": (nx, ny),
                "is_bathroom": is_bathroom
            }
            room_windows[sharing_rooms[0].lower()].append(win_item)
            window_exclusion_polys.append(k_poly)
            exterior_windows_meta.append(win_item)

    layout["windows"] = exterior_windows_meta

    # 3. Build Floor Geometry & Place Furniture
    all_faces = []
    placed_furniture = []
    
    # Compute Protected Circulation Polygon
    openings = layout.get("openings", [])
    entrance_geom = layout.get("entrance", None)
    protected_circ = None
    if compute_protected_circulation_polygon:
        try:
            protected_circ = compute_protected_circulation_polygon(rooms, openings, entrance_geom)
        except Exception as e:
            print(f"⚠️ Circulation polygon calculation: {e}")

    # Create Room Floors
    print(" Building floors and placing semantic furniture...")
    room_items = list(rooms.items())
    for i, (name, poly) in enumerate(room_items):
        color = ROOM_COLORS[i % len(ROOM_COLORS)]
        faces = _extrude_polygon_to_3d(poly, 0, FLOOR_THICKNESS)
        for f in faces:
            all_faces.append({"vertices": f, "color": color, "alpha": 0.9})
            
        # Add 3D Furniture blocks (constrained by windows, protected circulation, and entrance keep-out)
        _place_room_furniture(
            all_faces, name.lower(), poly, door_polygons,
            all_rooms=rooms, protected_circ_poly=protected_circ,
            openings=openings, entrance_geom=entrance_geom,
            room_windows=room_windows.get(name.lower(), []),
            window_exclusion_polys=window_exclusion_polys,
            wall_graph=edge_to_rooms,
            placed_furniture_out=placed_furniture
        )

    layout["furniture"] = placed_furniture

    # Add Foyer Mat / Welcome Tile Inlay directly inside Entrance Door
    if entrance_geom and not entrance_geom.is_empty:
        try:
            ecx, ecy = entrance_geom.centroid.x, entrance_geom.centroid.y
            for r_name, r_poly in rooms.items():
                if ("living" in r_name.lower() or "hall" in r_name.lower() or "foyer" in r_name.lower()) and r_poly.buffer(0.35).contains(Point(ecx, ecy)):
                    rcx, rcy = r_poly.centroid.x, r_poly.centroid.y
                    vx, vy = rcx - ecx, rcy - ecy
                    vlen = (vx**2 + vy**2)**0.5
                    if vlen > 0:
                        ux, uy = vx / vlen, vy / vlen
                        mcx, mcy = ecx + ux * 0.60, ecy + uy * 0.60
                        mw, mh = 1.10, 0.80
                        mat_box = box(mcx - mw/2.0, mcy - mh/2.0, mcx + mw/2.0, mcy + mh/2.0).intersection(r_poly)
                        if not mat_box.is_empty and isinstance(mat_box, Polygon):
                            add_box_to_faces(
                                all_faces,
                                mat_box.bounds[0], mat_box.bounds[2],
                                mat_box.bounds[1], mat_box.bounds[3],
                                FLOOR_THICKNESS + 0.003, FLOOR_THICKNESS + 0.015,
                                "#334155"
                            )
        except Exception as e:
            print(f"⚠️ Foyer mat generation: {e}")

    # 4. Generate Wall Geometry (Cutting for Doors & Windows)
    # Parse Adjacency for Balcony Logic
    adj_list = layout.get("adjacency", [])
    balcony_types = {} 
    for r_name in rooms:
        if "balcony" in r_name.lower() or "garden" in r_name.lower():
            b_type = 'half'
            neighbors = []
            for a, b in adj_list:
                if a == r_name: neighbors.append(b)
                elif b == r_name: neighbors.append(a)
            for n in neighbors:
                if "living" in n.lower() or "hall" in n.lower():
                    b_type = 'open'
            balcony_types[r_name] = b_type

    print(" Generating walls and windows...")
    generated_door_panels = []
    
    for (p1, p2), sharing_rooms in edge_to_rooms.items():
        base_line = LineString([p1, p2])
        if base_line.length < 0.1: continue
        
        is_exterior = (len(sharing_rooms) == 1)
        wall_thick = EXTERIOR_WALL_THICKNESS if is_exterior else WALL_THICKNESS
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

            # Check if this exterior segment has a window in precomputed list
            matched_win = None
            for win in room_windows.get(room_name, []):
                if win["base_line"].equals(base_line) or win["base_line"].distance(base_line) < 0.05:
                    matched_win = win
                    break

            if matched_win:
                p_start = matched_win["p_start"]
                p_end = matched_win["p_end"]
                seg_window = matched_win["wall_segment"]
                is_bathroom = matched_win.get("is_bathroom", False)

                seg_before = LineString([p1, p_start])
                seg_after = LineString([p_end, p2])

                if seg_before.length > 0.05:
                    for f in _extrude_linestring_to_thin_wall(seg_before, z_bottom, z_top, thickness=wall_thick):
                        all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                if seg_after.length > 0.05:
                    for f in _extrude_linestring_to_thin_wall(seg_after, z_bottom, z_top, thickness=wall_thick):
                        all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})

                z_sill = FLOOR_THICKNESS + (BATH_WINDOW_SILL_HEIGHT if is_bathroom else WINDOW_SILL_HEIGHT)
                z_head = FLOOR_THICKNESS + WINDOW_HEAD_HEIGHT

                for f in _extrude_linestring_to_thin_wall(seg_window, z_bottom, z_sill, thickness=wall_thick):
                    all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                for f in _extrude_linestring_to_thin_wall(seg_window, z_head, z_top, thickness=wall_thick):
                    all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})
                # Glass pane
                glass_color = "#E2E8F0" if is_bathroom else WINDOW_GLASS_COLOR
                glass_alpha = 0.70 if is_bathroom else 0.55
                for f in _extrude_linestring_to_thin_wall(seg_window, z_sill + 0.02, z_head - 0.02, thickness=0.03):
                    all_faces.append({"vertices": f, "color": glass_color, "alpha": glass_alpha})
                # Frame trim
                for f in _extrude_linestring_to_thin_wall(seg_window, z_sill, z_sill + 0.03, thickness=wall_thick * 1.05):
                    all_faces.append({"vertices": f, "color": WINDOW_FRAME_COLOR, "alpha": 1.0})
                for f in _extrude_linestring_to_thin_wall(seg_window, z_head - 0.03, z_head, thickness=wall_thick * 1.05):
                    all_faces.append({"vertices": f, "color": WINDOW_FRAME_COLOR, "alpha": 1.0})
                continue

        # Interior Wall (or exterior wall with entrance door)
        final_segments = [base_line]
        
        if door_polygons:
            for door in door_polygons:
                new_segments = []
                door_shape = door.buffer(0.01)
                
                for seg in final_segments:
                    if seg.intersects(door_shape):
                        intersection = seg.intersection(door_shape)
                        
                        if not intersection.is_empty and isinstance(intersection, LineString):
                            # Extrude WALL LINTEL/HEADER above door
                            z_header_bottom = FLOOR_THICKNESS + DOOR_HEIGHT
                            header_faces = _extrude_linestring_to_thin_wall(
                                intersection, z_header_bottom, z_top, thickness=wall_thick
                            )
                            for f in header_faces:
                                all_faces.append({"vertices": f, "color": WALL_COLOR, "alpha": 1.0})

                            i_coords = list(intersection.coords)
                            if len(i_coords) >= 2:
                                ix1, iy1 = i_coords[0]
                                ix2, iy2 = i_coords[-1]
                                idx, idy = ix2 - ix1, iy2 - iy1
                                ilen = (idx**2 + idy**2)**0.5
                                
                                if 0.55 <= ilen <= 1.15:
                                    wall_dir = np.array([idx, idy]) / ilen
                                    perp_dir = np.array([-wall_dir[1], wall_dir[0]])
                                    center = np.array([(ix1+ix2)/2, (iy1+iy2)/2])
                                    
                                    d_thick = wall_thick * 0.8
                                    d_half_width = ilen / 2.0
                                    d_half_thick = d_thick / 2.0
                                    
                                    c1 = center + wall_dir * d_half_width + perp_dir * d_half_thick
                                    c2 = center - wall_dir * d_half_width + perp_dir * d_half_thick
                                    c3 = center - wall_dir * d_half_width - perp_dir * d_half_thick
                                    c4 = center + wall_dir * d_half_width - perp_dir * d_half_thick
                                    
                                    door_poly = Polygon([tuple(c1), tuple(c2), tuple(c3), tuple(c4)])
                                    generated_door_panels.append({
                                        "poly": door_poly,
                                        "is_exterior": is_exterior,
                                        "center": center,
                                        "wall_dir": wall_dir,
                                        "perp_dir": perp_dir,
                                        "width": ilen,
                                        "d_thick": d_thick
                                    })

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

    # 5. Generate Doors (Use Wall-Aligned Panels with Jambs & Open Swing)
    print(" Generating doors with architectural frames and swing leaves...")
    for d_item in generated_door_panels:
        if not isinstance(d_item, dict):
            continue
        is_front = d_item.get("is_exterior", False)
        ilen = d_item["width"]
        wall_dir = d_item["wall_dir"]
        perp_dir = d_item["perp_dir"]
        center = d_item["center"]
        d_thick = d_item["d_thick"]
        
        # Frame Jambs (both left and right jambs)
        jamb_w = 0.045
        p_jamb_left = center - wall_dir * (ilen / 2.0 - jamb_w / 2.0)
        p_jamb_right = center + wall_dir * (ilen / 2.0 - jamb_w / 2.0)
        for p_jamb in [p_jamb_left, p_jamb_right]:
            jb_poly = Polygon([
                p_jamb - wall_dir * (jamb_w/2) - perp_dir * (d_thick/2),
                p_jamb + wall_dir * (jamb_w/2) - perp_dir * (d_thick/2),
                p_jamb + wall_dir * (jamb_w/2) + perp_dir * (d_thick/2),
                p_jamb - wall_dir * (jamb_w/2) + perp_dir * (d_thick/2),
            ])
            for f in _extrude_polygon_vertical_shell(jb_poly, FLOOR_THICKNESS, FLOOR_THICKNESS + DOOR_HEIGHT):
                all_faces.append({"vertices": f, "color": "#334155", "alpha": 1.0})

        if is_front:
            # Front Entrance Door: Rich architectural solid slab with vision slit and pull bar
            door = d_item["poly"]
            d_faces = _extrude_polygon_vertical_shell(door, FLOOR_THICKNESS, FLOOR_THICKNESS + DOOR_HEIGHT)
            for f in d_faces:
                all_faces.append({"vertices": f, "color": "#1E293B", "alpha": 1.0})
                
            # Vertical Frosted Glass Vision Slit
            slit_w = 0.10
            slit_thick = d_thick * 1.05
            p_slit = center - wall_dir * (ilen * 0.18)
            slit_poly = Polygon([
                p_slit - wall_dir * (slit_w/2) - perp_dir * (slit_thick/2),
                p_slit + wall_dir * (slit_w/2) - perp_dir * (slit_thick/2),
                p_slit + wall_dir * (slit_w/2) + perp_dir * (slit_thick/2),
                p_slit - wall_dir * (slit_w/2) + perp_dir * (slit_thick/2),
            ])
            for f in _extrude_polygon_vertical_shell(slit_poly, FLOOR_THICKNESS + 0.60, FLOOR_THICKNESS + 1.85):
                all_faces.append({"vertices": f, "color": "#7DD3FC", "alpha": 0.70})

            # Architectural Vertical Pull Handle (Brushed Metal)
            h_pt = center + wall_dir * (ilen * 0.28) + perp_dir * (d_thick/2 + 0.03)
            add_box_to_faces(
                all_faces,
                h_pt[0] - 0.02, h_pt[0] + 0.02,
                h_pt[1] - 0.02, h_pt[1] + 0.02,
                FLOOR_THICKNESS + 0.85, FLOOR_THICKNESS + 1.35,
                "#E2E8F0"
            )
        else:
            # Interior Door: Swung open 25 degrees into room to show clear doorway passage!
            p_hinge = center - wall_dir * (ilen / 2.0 - 0.03)
            # 25 degrees swing: cos(25°) ≈ 0.906, sin(25°) ≈ 0.423
            swung_dir = wall_dir * 0.906 + perp_dir * 0.423
            swung_perp = np.array([-swung_dir[1], swung_dir[0]])
            leaf_len = ilen * 0.94
            leaf_thick = 0.04
            
            p_leaf_end = p_hinge + swung_dir * leaf_len
            leaf_poly = Polygon([
                p_hinge - swung_perp * (leaf_thick / 2.0),
                p_leaf_end - swung_perp * (leaf_thick / 2.0),
                p_leaf_end + swung_perp * (leaf_thick / 2.0),
                p_hinge + swung_perp * (leaf_thick / 2.0),
            ])
            for f in _extrude_polygon_vertical_shell(leaf_poly, FLOOR_THICKNESS, FLOOR_THICKNESS + DOOR_HEIGHT):
                all_faces.append({"vertices": f, "color": DOOR_PANEL_COLOR, "alpha": 1.0})
                
            # Metallic lever handle near outer edge of swung door
            p_handle = p_hinge + swung_dir * (leaf_len * 0.88) + swung_perp * (leaf_thick / 2.0 + 0.02)
            add_box_to_faces(
                all_faces,
                p_handle[0] - 0.02, p_handle[0] + 0.02,
                p_handle[1] - 0.02, p_handle[1] + 0.02,
                FLOOR_THICKNESS + 0.95, FLOOR_THICKNESS + 1.05,
                "#CBD5E1"
            )

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
