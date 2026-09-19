from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

# =========================
# ARCHITECTURAL OPENING CONSTANTS
# =========================
DOOR_DEPTH = 0.25
WALL_TOLERANCE = 0.5
INTERIOR_DOOR_WIDTH = 0.85
BATH_DOOR_WIDTH = 0.80
ENTRY_DOOR_WIDTH = 1.05
CASED_OPENING_WIDTH = 2.20

def _extract_lines(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if geom.geom_type == "MultiLineString":
        return list(geom.geoms)
    return []

def _shared_wall(poly_a, poly_b):
    inter = poly_a.boundary.intersection(poly_b.boundary)
    lines = _extract_lines(inter)
    lines = [l for l in lines if l.length > WALL_TOLERANCE]
    if not lines:
        return None
    return max(lines, key=lambda l: l.length)

def _opening_from_wall(wall, width, position="center", existing_doors=None):
    """Create a rectangular opening on the shared wall.

    Enforces minimum 0.60m structural return from room corners and staggers
    doors away from nearby existing doors to prevent multi-door corner collisions.
    """
    L = wall.length
    if L <= 0:
        return None

    # Cap opening so there are at least structural piers at both ends
    max_effective_width = max(0.4, L - 0.50)
    eff_width = min(width, max_effective_width)

    if eff_width <= 0:
        return None

    min_return = 0.60
    candidates = []

    if position == "tucked" and L >= (eff_width + min_return * 2):
        # Candidate A: tucked near start (with >= 0.60m corner clearance)
        t_start = (min_return + eff_width / 2.0) / L
        candidates.append(wall.interpolate(t_start, normalized=True))
        # Candidate B: tucked near end (with >= 0.60m corner clearance)
        t_end = 1.0 - (min_return + eff_width / 2.0) / L
        candidates.append(wall.interpolate(t_end, normalized=True))
    elif position == "tucked" and L >= (eff_width + 0.5):
        t_start = (0.25 + eff_width / 2.0) / L
        candidates.append(wall.interpolate(t_start, normalized=True))
        t_end = 1.0 - (0.25 + eff_width / 2.0) / L
        candidates.append(wall.interpolate(t_end, normalized=True))
    else:
        # Centered opening
        candidates.append(wall.interpolate(0.5, normalized=True))

    # Pick candidate that maximizes clearance from any existing door
    if existing_doors and len(candidates) > 1:
        mid = max(
            candidates,
            key=lambda pt: min([pt.distance(d.centroid) for d in existing_doors], default=999.0)
        )
    else:
        mid = candidates[0]

    (x1, y1), (x2, y2) = wall.coords[0], wall.coords[-1]
    dx, dy = x2 - x1, y2 - y1

    if L == 0:
        return None

    nx, ny = dx / L, dy / L
    px, py = -ny, nx  # perpendicular unit vector

    w = eff_width / 2.0
    d = DOOR_DEPTH / 2.0

    return Polygon([
        (mid.x - nx*w - px*d, mid.y - ny*w - py*d),
        (mid.x + nx*w - px*d, mid.y + ny*w - py*d),
        (mid.x + nx*w + px*d, mid.y + ny*w + py*d),
        (mid.x - nx*w + px*d, mid.y - ny*w + py*d),
    ])

def generate_doors_with_metadata(rooms, opening_specs):
    """
    Generate door opening polygons and rich metadata.
    
    Input:
      - rooms: dict {room_id: shapely.Polygon}
      - opening_specs: list of (room_a, room_b, width) or (room_a, room_b, width, opening_type)
      
    Output:
      - (unary_union_geometry, list_of_opening_dicts)
    """
    openings = []
    metadata = []

    for spec in opening_specs:
        if len(spec) == 4:
            r1, r2, width, op_type = spec
        else:
            r1, r2, width = spec
            op_type = "cased_opening" if width > 1.1 else "door"

        if r1 not in rooms or r2 not in rooms:
            continue

        wall = _shared_wall(rooms[r1], rooms[r2])
        if not wall:
            continue

        # Position tucked for bedrooms to keep wall space for furniture & improve privacy
        t1 = r1.split("_")[0].lower()
        t2 = r2.split("_")[0].lower()
        pos = "tucked" if ("bedroom" in (t1, t2) and op_type == "door") else "center"

        opening = _opening_from_wall(wall, width, position=pos, existing_doors=openings)
        if opening:
            openings.append(opening)
            metadata.append({
                "rooms": (r1, r2),
                "width": width,
                "type": op_type,
                "polygon": opening,
                "wall_length": wall.length,
            })

    geom = unary_union(openings) if openings else None
    return geom, metadata

def generate_doors(rooms, opening_specs):
    """
    Backward-compatible geometry engine returning unary union of openings.
    """
    geom, _ = generate_doors_with_metadata(rooms, opening_specs)
    return geom