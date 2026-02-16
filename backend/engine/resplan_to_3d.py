
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
WALL_THICKNESS = 0.15    # Standard wall thickness (15cm) - Structural
DOOR_THICKNESS = 0.05    # Door panel thickness (5cm) - Thinner than walls

# Wall/door colors - Modern Clean Look
WALL_COLOR = "#F5F5F5"         # White Smoke walls
DOOR_FRAME_COLOR = "#5D4037"   # Dark Wood (Walnut)
DOOR_PANEL_COLOR = "#D7CCC8"   # Light Wood / Beige
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

def _extrude_linestring_to_thin_wall(line, z_bottom, z_top):
    """Extrude a LineString into a thin *thickened* wall strip."""
    if line.is_empty or line.length < 0.01:
        return []

    coords = list(line.coords)
    if len(coords) < 2:
        return []

    faces = []
    half_t = WALL_THICKNESS / 2.0

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
             new_coords.append((round(x, 4), round(y, 4)))
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

    # 4. Generate Wall Geometry (Cutting for Doors)
    print(" Generating walls...")
    
    generated_door_panels = [] # New list for wall-aligned doors
    
    for (p1, p2), sharing_rooms in edge_to_rooms.items():
        base_line = LineString([p1, p2])
        if base_line.length < 0.1: continue
        
        # Determine Wall Type
        is_exterior = (len(sharing_rooms) == 1)
        
        # Determine Height
        z_bottom = FLOOR_THICKNESS
        z_top = FLOOR_THICKNESS + WALL_HEIGHT
        
        if is_exterior:
            room_name = sharing_rooms[0]
            if room_name in balcony_types:
                if balcony_types[room_name] == 'open':
                    z_top = FLOOR_THICKNESS + 0.1 # Curb
                elif balcony_types[room_name] == 'half':
                    z_top = FLOOR_THICKNESS + (WALL_HEIGHT * 0.4) # Parapet
        else:
            # Interior Wall
            pass 

        # Cut Doors physically from this segment
        # We subtract all door polygons from this line
        final_segments = [base_line]
        
        if door_polygons:
            for door in door_polygons:
                new_segments = []
                door_shape = door.buffer(0.01) # Slight buffer vs line for intersection
                
                for seg in final_segments:
                    if seg.intersects(door_shape):
                        # 1. Capture the Hole (Intersection)
                        intersection = seg.intersection(door_shape)
                        
                        # Generate Wall-Aligned Door Panel if valid intersection
                        if not intersection.is_empty and isinstance(intersection, LineString):
                             # Calculate Door Geometry aligned to Wall
                             i_coords = list(intersection.coords)
                             if len(i_coords) >= 2:
                                 ix1, iy1 = i_coords[0]
                                 ix2, iy2 = i_coords[-1]
                                 idx, idy = ix2 - ix1, iy2 - iy1
                                 ilen = (idx**2 + idy**2)**0.5
                                 
                                 if ilen > 0.5: # Min door width
                                     # Vector logic
                                     wall_dir = np.array([idx, idy]) / ilen
                                     perp_dir = np.array([-wall_dir[1], wall_dir[0]])
                                     
                                     center = np.array([(ix1+ix2)/2, (iy1+iy2)/2])
                                     
                                     # Dimensions
                                     d_thick = WALL_THICKNESS * 0.8 # Slightly thinner than wall
                                     d_half_width = ilen / 2
                                     d_half_thick = d_thick / 2
                                     
                                     # Construct corners (flush with wall center)
                                     c1 = center + wall_dir * d_half_width + perp_dir * d_half_thick
                                     c2 = center - wall_dir * d_half_width + perp_dir * d_half_thick
                                     c3 = center - wall_dir * d_half_width - perp_dir * d_half_thick
                                     c4 = center + wall_dir * d_half_width - perp_dir * d_half_thick
                                     
                                     door_poly = Polygon([tuple(c1), tuple(c2), tuple(c3), tuple(c4)])
                                     generated_door_panels.append(door_poly)

                        # 2. Subtract the Hole from Wall
                        diff = seg.difference(door_shape)
                        if not diff.is_empty:
                            if isinstance(diff, LineString):
                                new_segments.append(diff)
                            elif hasattr(diff, "geoms"):
                                new_segments.extend(diff.geoms)
                    else:
                        new_segments.append(seg)
                final_segments = new_segments
        
        # Extrude resulting segments
        for seg in final_segments:
            if seg.length < 0.05: continue
            w_faces = _extrude_linestring_to_thin_wall(seg, z_bottom, z_top)
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
