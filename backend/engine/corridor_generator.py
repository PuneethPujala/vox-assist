from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union

# =========================
# CONFIG
# =========================
CORRIDOR_WIDTH = 1.5
CLEARANCE = 0.2

# =========================
# HELPERS
# =========================
def _safe_centroid(poly):
    """Safely get centroid of a polygon"""
    if poly.is_empty:
        return Point(0, 0)
    return poly.centroid


def _wall_midpoint_towards(src, dst):
    """
    Pick midpoint of the wall of src polygon facing dst point
    """
    minx, miny, maxx, maxy = src.bounds
    cx, cy = src.centroid.coords[0]
    dx, dy = dst.x - cx, dst.y - cy

    if abs(dx) > abs(dy):
        # Left or right wall
        x = maxx if dx > 0 else minx
        y = (miny + maxy) / 2
    else:
        # Top or bottom wall
        y = maxy if dy > 0 else miny
        x = (minx + maxx) / 2

    return Point(x, y)


def _manhattan_path(p1, p2):
    """
    Create L-shaped corridor path between two points
    """
    lines = []
    # Horizontal segment
    if abs(p2.x - p1.x) > 1e-3:
        lines.append(LineString([(p1.x, p1.y), (p2.x, p1.y)]))
    # Vertical segment
    if abs(p2.y - p1.y) > 1e-3:
        lines.append(LineString([(p2.x, p1.y), (p2.x, p2.y)]))
    return lines


def _buffer_lines(lines):
    """
    Convert line segments to corridor polygons with proper width
    """
    polys = []
    for ln in lines:
        if ln.length < 1e-3:
            continue
        polys.append(ln.buffer(CORRIDOR_WIDTH / 2, cap_style=2))
    return polys


def _shared_wall_segment(poly_a, poly_b, tol=0.6):
    """
    Returns the shared wall segment between two adjacent rooms
    """
    inter = poly_a.boundary.intersection(poly_b.boundary)
    if inter.is_empty or inter.length < tol:
        return None
    return inter


# =========================
# MAIN GENERATOR
# =========================
def generate_corridors(rooms, adjacency):
    """
    Generate corridor polygons connecting non-adjacent rooms.
    For adjacent rooms (sharing a wall), no corridor is needed.
    
    rooms: dict {name: Polygon}
    adjacency: list of (roomA, roomB) tuples
    
    Returns: Shapely geometry (Polygon, MultiPolygon, or None)
    """
    corridors = []

    for r1, r2 in adjacency:
        if r1 not in rooms or r2 not in rooms:
            continue

        poly1 = rooms[r1]
        poly2 = rooms[r2]

        # Check if rooms share a wall (adjacent)
        shared = _shared_wall_segment(poly1, poly2)
        
        if not shared:
            # Rooms are not adjacent, create L-shaped corridor
            c1 = _safe_centroid(poly1)
            c2 = _safe_centroid(poly2)
            
            # Get wall points facing each other
            wall_p1 = _wall_midpoint_towards(poly1, c2)
            wall_p2 = _wall_midpoint_towards(poly2, c1)
            
            # Create manhattan path and buffer it
            path_lines = _manhattan_path(wall_p1, wall_p2)
            corridor_polys = _buffer_lines(path_lines)
            corridors.extend(corridor_polys)

    if not corridors:
        return None

    return unary_union(corridors)