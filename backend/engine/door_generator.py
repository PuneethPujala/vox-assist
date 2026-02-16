from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

DOOR_DEPTH = 0.25
WALL_TOLERANCE = 0.5

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

def _opening_from_wall(wall, width):
    """Create a rectangular opening centered on the shared wall.

    We clamp the *effective* opening width so it never consumes the full
    shared wall segment. This guarantees there are small wall piers at
    both ends (e.g. between bedroom and bathroom), so 3D still has a
    visible wall except at the doorway.
    """

    L = wall.length
    if L <= 0:
        return None

    # Cap opening to at most 70% of available wall to leave side piers
    max_effective_width = 0.7 * L
    eff_width = min(width, max_effective_width)

    if eff_width <= 0:
        return None

    mid = wall.interpolate(0.5, normalized=True)
    (x1, y1), (x2, y2) = wall.coords[0], wall.coords[-1]
    dx, dy = x2 - x1, y2 - y1

    # Avoid division by zero
    if L == 0:
        return None

    nx, ny = dx / L, dy / L
    px, py = -ny, nx  # perpendicular unit vector

    w = eff_width / 2
    d = DOOR_DEPTH / 2

    return Polygon([
        (mid.x - nx*w - px*d, mid.y - ny*w - py*d),
        (mid.x + nx*w - px*d, mid.y + ny*w - py*d),
        (mid.x + nx*w + px*d, mid.y + ny*w + py*d),
        (mid.x - nx*w + px*d, mid.y - ny*w + py*d),
    ])

def generate_doors(rooms, opening_specs):
    """
    PURE GEOMETRY ENGINE.
    
    Input:
      - rooms: dict {room_id: shapely.Polygon}
      - opening_specs: list of (room_a, room_b, width)
    
    Rules:
      - One opening per spec.
      - No filtering, no validation, no rules.
      - Width is provided by layout synthesizer (architectural logic lives there).
      - External connections (e.g., front door, balcony) must be included as specs,
        e.g., ("living", "exterior", 1.2) — "exterior" must be a polygon in `rooms`.
    
    Output:
      - Unary union of all generated opening polygons.
      - Returns None if no valid openings produced.
    """
    openings = []

    for r1, r2, width in opening_specs:
        if r1 not in rooms or r2 not in rooms:
            continue

        wall = _shared_wall(rooms[r1], rooms[r2])
        if not wall:
            continue

        opening = _opening_from_wall(wall, width)
        if opening:
            openings.append(opening)

    if not openings:
        return None

    return unary_union(openings)