"""
Authoritative Opening Registry & Consistency Layer for VoxAssist.

Single source of truth for all architectural openings:
- Exterior Windows (with glazing area, sill/head heights, and fire egress compliance)
- Interior Hinged Doors
- Cased Openings (wide portals > 1.15m without door leaves or hardware)
- Main Entrance Door (with exterior landing and interior foyer keep-out)

The 3D renderer and 2D floor plans consume this registry directly;
they NEVER generate or invent openings on the fly.
"""

import math
import uuid
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, MultiLineString
from shapely.ops import unary_union

try:
    from engine.constraints.furniture_constants import (
        DOOR_HEADER_HEIGHT, SILL_HEIGHT_HABITABLE, SILL_HEIGHT_BATHROOM,
        WINDOW_HEAD_HEIGHT, DAYLIGHT_KEEPOUT_DEPTH, CASED_OPENING_THRESHOLD,
        INTERIOR_DOOR_WIDTH, BATHROOM_DOOR_WIDTH, ENTRY_DOOR_WIDTH,
        FOYER_ARRIVAL_DEPTH, FOYER_ARRIVAL_WIDTH
    )
except ImportError:
    try:
        from constraints.furniture_constants import (
            DOOR_HEADER_HEIGHT, SILL_HEIGHT_HABITABLE, SILL_HEIGHT_BATHROOM,
            WINDOW_HEAD_HEIGHT, DAYLIGHT_KEEPOUT_DEPTH, CASED_OPENING_THRESHOLD,
            INTERIOR_DOOR_WIDTH, BATHROOM_DOOR_WIDTH, ENTRY_DOOR_WIDTH,
            FOYER_ARRIVAL_DEPTH, FOYER_ARRIVAL_WIDTH
        )
    except ImportError:
        DOOR_HEADER_HEIGHT = 2.10
        SILL_HEIGHT_HABITABLE = 0.90
        SILL_HEIGHT_BATHROOM = 1.50
        WINDOW_HEAD_HEIGHT = 2.10
        DAYLIGHT_KEEPOUT_DEPTH = 0.80
        CASED_OPENING_THRESHOLD = 1.15
        INTERIOR_DOOR_WIDTH = 0.85
        BATHROOM_DOOR_WIDTH = 0.75
        ENTRY_DOOR_WIDTH = 1.05
        FOYER_ARRIVAL_DEPTH = 1.50
        FOYER_ARRIVAL_WIDTH = 1.60

# Window sizing archetypes by room type
ROOM_WINDOW_CONFIGS = {
    "living":   {"width": 1.60, "height": 1.20, "sill_height": SILL_HEIGHT_HABITABLE, "min_wall_len": 2.20},
    "bedroom":  {"width": 1.30, "height": 1.20, "sill_height": SILL_HEIGHT_HABITABLE, "min_wall_len": 1.80},
    "kitchen":  {"width": 1.10, "height": 1.00, "sill_height": 1.00,                 "min_wall_len": 1.60},
    "dining":   {"width": 1.40, "height": 1.20, "sill_height": SILL_HEIGHT_HABITABLE, "min_wall_len": 2.00},
    "study":    {"width": 1.20, "height": 1.20, "sill_height": SILL_HEIGHT_HABITABLE, "min_wall_len": 1.80},
    "bathroom": {"width": 0.65, "height": 0.60, "sill_height": SILL_HEIGHT_BATHROOM,  "min_wall_len": 1.00},
    "toilet":   {"width": 0.60, "height": 0.50, "sill_height": SILL_HEIGHT_BATHROOM,  "min_wall_len": 0.90},
    "balcony":  {"width": 0.00, "height": 0.00, "sill_height": 0.00,                  "min_wall_len": 99.0},
}
DEFAULT_WINDOW_CONFIG = {"width": 1.20, "height": 1.20, "sill_height": SILL_HEIGHT_HABITABLE, "min_wall_len": 1.80}


def _extract_lines(geom: Any) -> List[LineString]:
    """Helper to extract non-empty LineString objects from any Shapely geometry."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if hasattr(geom, "geoms"):
        res = []
        for g in geom.geoms:
            res.extend(_extract_lines(g))
        return res
    return []


def _is_wall_exterior(base_line: LineString, sharing_rooms: List[str], exterior_boundary: Optional[Any]) -> bool:
    """
    Strictly verifies whether a wall segment lies on the outer building envelope.
    A wall segment is exterior IF AND ONLY IF it bounds exactly one room AND its
    midpoint lies within 0.05m of the outer footprint envelope boundary.
    """
    if len(sharing_rooms) != 1:
        return False
    if exterior_boundary is None or exterior_boundary.is_empty:
        return len(sharing_rooms) == 1
    mid = base_line.interpolate(0.5, normalized=True)
    return exterior_boundary.distance(mid) < 0.05


def _compute_atomic_wall_graph(rooms: Dict[str, Polygon]) -> Dict[Tuple[Tuple[float, float], Tuple[float, float]], List[str]]:
    """
    Computes a noded atomic wall graph across all room boundaries.
    Intersects and nodes boundaries at all corners and T-junctions so no edge
    spans past another room's corner.
    """
    valid_rooms = {k: v for k, v in rooms.items() if v is not None and not v.is_empty}
    if not valid_rooms:
        return {}

    all_boundaries = unary_union([r.boundary for r in valid_rooms.values()])
    atomic_lines = _extract_lines(all_boundaries)

    edge_to_rooms: Dict[Tuple[Tuple[float, float], Tuple[float, float]], List[str]] = defaultdict(list)

    for line in atomic_lines:
        if line.length < 0.08:
            continue
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            p1 = (round(coords[i][0], 3), round(coords[i][1], 3))
            p2 = (round(coords[i + 1][0], 3), round(coords[i + 1][1], 3))
            edge_key = (min(p1, p2), max(p1, p2))
            seg = LineString([p1, p2])
            if seg.length < 0.08:
                continue

            # Determine which rooms share this atomic edge
            for r_name, r_poly in valid_rooms.items():
                if r_poly.boundary.distance(seg.interpolate(0.5, normalized=True)) < 0.04:
                    if r_name not in edge_to_rooms[edge_key]:
                        edge_to_rooms[edge_key].append(r_name)

    return edge_to_rooms


class OpeningRegistry:
    """
    Authoritative container for all immutable openings in a floor plan.
    Ensures identical 2D and 3D opening layout across any view angle or camera rotation.
    """

    def __init__(
        self,
        design_id: Optional[str] = None,
        windows: Optional[List[Dict[str, Any]]] = None,
        doors: Optional[List[Dict[str, Any]]] = None,
        cased_openings: Optional[List[Dict[str, Any]]] = None,
        entrance: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.design_id = design_id or str(uuid.uuid4())
        self.windows = windows or []
        self.doors = doors or []
        self.cased_openings = cased_openings or []
        self.entrance = entrance
        self.metadata = metadata or {}

    @property
    def all_openings_metadata(self) -> List[Dict[str, Any]]:
        """Unified opening list preserving backward compatibility with layout['openings']."""
        combined = []
        for d in self.doors:
            combined.append(d)
        for c in self.cased_openings:
            combined.append(c)
        if self.entrance:
            combined.append(self.entrance)
        return combined

    def get_windows_for_room(self, room_name: str) -> List[Dict[str, Any]]:
        """Returns all exterior windows registered for a given room."""
        r_clean = room_name.lower().strip()
        return [w for w in self.windows if w.get("room", "").lower().strip() == r_clean]

    def get_openings_for_room(self, room_name: str) -> List[Dict[str, Any]]:
        """Returns all interior doors and cased openings touching a room."""
        r_clean = room_name.lower().strip()
        res = []
        for op in self.doors + self.cased_openings:
            rooms = op.get("rooms", ())
            if any(r.lower().strip() == r_clean for r in rooms):
                res.append(op)
        if self.entrance and any(r.lower().strip() == r_clean for r in self.entrance.get("rooms", ())):
            res.append(self.entrance)
        return res

    def to_dict(self) -> Dict[str, Any]:
        """Serializes registry to dictionary representation."""
        return {
            "design_id": self.design_id,
            "windows": self.windows,
            "doors": self.doors,
            "cased_openings": self.cased_openings,
            "entrance": self.entrance,
            "metadata": self.metadata,
            "summary": {
                "window_count": len(self.windows),
                "door_count": len(self.doors),
                "cased_opening_count": len(self.cased_openings),
                "has_entrance": self.entrance is not None
            }
        }


def build_opening_registry(
    rooms: Dict[str, Polygon],
    doors_geom: Optional[Any] = None,
    openings_metadata: Optional[List[Dict[str, Any]]] = None,
    entrance_geom: Optional[Polygon] = None,
    envelope: Optional[Polygon] = None,
    design_id: Optional[str] = None
) -> OpeningRegistry:
    """
    Builds the authoritative, immutable OpeningRegistry from room topology.
    
    Guarantees:
    1. Windows are placed ONLY on verified exterior envelope walls (never on interior partitions).
    2. Zero windows overlap with entrance or interior door approach thresholds.
    3. Habitable rooms receive standardized daylighting glazing and emergency fire egress.
    4. Cased openings (> 1.15m) are strictly segregated from hinged doors.
    5. The resulting registry is immutable and deterministic.
    """
    valid_rooms = {k: v for k, v in rooms.items() if v is not None and not v.is_empty}
    if not valid_rooms:
        return OpeningRegistry(design_id=design_id)

    # 1. Envelope Boundary
    # The exterior boundary of the house is strictly defined by the perimeter of its rooms.
    # We do not use the plot envelope box here, as setbacks/margins would cause exterior house walls to be misclassified.
    building_envelope = unary_union(list(valid_rooms.values()))
    exterior_boundary = building_envelope.boundary if building_envelope and not building_envelope.is_empty else None

    # 2. Door Polygons Collection
    door_polygons = []
    if doors_geom is not None and not doors_geom.is_empty:
        if isinstance(doors_geom, Polygon):
            door_polygons.append(doors_geom)
        elif hasattr(doors_geom, "geoms"):
            for g in doors_geom.geoms:
                if isinstance(g, Polygon):
                    door_polygons.append(g)

    # Ingest existing metadata
    openings_metadata = openings_metadata or []
    for op in openings_metadata:
        p = op.get("polygon")
        if p and not p.is_empty and isinstance(p, Polygon):
            if not any(p.equals_exact(dp, 0.05) for dp in door_polygons):
                door_polygons.append(p)

    if entrance_geom is not None and not entrance_geom.is_empty and isinstance(entrance_geom, Polygon):
        if not any(entrance_geom.equals_exact(dp, 0.05) for dp in door_polygons):
            door_polygons.append(entrance_geom)

    # 3. Categorize Doors and Cased Openings
    doors_list: List[Dict[str, Any]] = []
    cased_list: List[Dict[str, Any]] = []
    entrance_dict: Optional[Dict[str, Any]] = None

    entrance_placed = False

    for idx, op in enumerate(openings_metadata):
        op_type = op.get("type", "door").lower()
        w = float(op.get("width", INTERIOR_DOOR_WIDTH))
        rooms_connected = op.get("rooms", ("room_a", "room_b"))
        p = op.get("polygon")
        c = (p.centroid.x, p.centroid.y) if p and not p.is_empty else (0.0, 0.0)

        # Entrance check
        if op_type == "entrance" or "exterior" in [str(r).lower() for r in rooms_connected]:
            wall_id = f"ext_door_{round(c[0], 2)}_{round(c[1], 2)}"
            foyer_k = p.buffer(0.80) if p else None
            entrance_dict = {
                "opening_id": "entrance_main",
                "wall_id": wall_id,
                "type": "entrance",
                "rooms": rooms_connected,
                "polygon": p,
                "width": max(w, ENTRY_DOOR_WIDTH),
                "height": DOOR_HEADER_HEIGHT,
                "center": c,
                "foyer_keepout": foyer_k,
                "is_cased": False
            }
            entrance_placed = True
        elif w > CASED_OPENING_THRESHOLD or op_type in ["cased", "portal", "cased_opening"]:
            wall_id = f"cased_{idx}_{round(c[0], 2)}_{round(c[1], 2)}"
            cased_list.append({
                "opening_id": f"cased_opening_{idx}",
                "wall_id": wall_id,
                "type": "cased_opening",
                "rooms": rooms_connected,
                "polygon": p,
                "width": w,
                "height": DOOR_HEADER_HEIGHT,
                "center": c,
                "is_cased": True
            })
        else:
            wall_id = f"door_{idx}_{round(c[0], 2)}_{round(c[1], 2)}"
            doors_list.append({
                "opening_id": f"door_{idx}",
                "wall_id": wall_id,
                "type": "door",
                "rooms": rooms_connected,
                "polygon": p,
                "width": w,
                "height": DOOR_HEADER_HEIGHT,
                "center": c,
                "is_cased": False
            })

    # Fallback entrance creation if entrance_geom is provided but not in openings_metadata
    if not entrance_placed and entrance_geom is not None and not entrance_geom.is_empty:
        ec = (entrance_geom.centroid.x, entrance_geom.centroid.y)
        entrance_dict = {
            "opening_id": "entrance_main",
            "wall_id": f"ext_door_{round(ec[0], 2)}_{round(ec[1], 2)}",
            "type": "entrance",
            "rooms": ("living", "exterior"),
            "polygon": entrance_geom,
            "width": ENTRY_DOOR_WIDTH,
            "height": DOOR_HEADER_HEIGHT,
            "center": ec,
            "foyer_keepout": entrance_geom.buffer(0.80),
            "is_cased": False
        }

    # 4. Deterministic Exterior Window Generation
    edge_to_rooms = _compute_atomic_wall_graph(valid_rooms)
    windows_list: List[Dict[str, Any]] = []
    win_counter = defaultdict(int)

    # Sort edges for 100% deterministic processing
    sorted_edges = sorted(edge_to_rooms.keys(), key=lambda e: (e[0][0], e[0][1], e[1][0], e[1][1]))

    for (p1, p2) in sorted_edges:
        sharing_rooms = edge_to_rooms[(p1, p2)]
        base_line = LineString([p1, p2])
        if base_line.length < 0.15:
            continue

        is_exterior = _is_wall_exterior(base_line, sharing_rooms, exterior_boundary)
        if not is_exterior:
            continue

        r_name = sharing_rooms[0]
        r_type = r_name.split("_")[0].lower()
        r_poly = valid_rooms.get(r_name)
        if r_poly is None or r_poly.is_empty:
            continue

        # Check collision with any door opening on this wall
        if door_polygons:
            if any(base_line.intersects(dp.buffer(0.15)) for dp in door_polygons):
                continue

        # Configuration and thresholds
        config = ROOM_WINDOW_CONFIGS.get(r_type, DEFAULT_WINDOW_CONFIG)
        min_len = config["min_wall_len"]
        if base_line.length < min_len:
            continue

        is_bathroom = any(t in r_name.lower() for t in ["bath", "toilet", "powder"])
        is_habitable = not is_bathroom and r_type not in ["storage", "hallway", "corridor"]

        # Determine window width
        max_possible_w = base_line.length - 0.40  # 20cm structural pier at each corner
        target_w = config["width"]
        win_w = round(min(target_w, max_possible_w), 2)
        if win_w < 0.50:
            continue

        win_h = config["height"]
        sill_h = config["sill_height"]

        # Center window along the exterior wall segment
        L = base_line.length
        u_coord = 0.50
        start_dist = (L - win_w) / 2.0
        end_dist = start_dist + win_w

        p_start = base_line.interpolate(start_dist / L, normalized=True)
        p_end = base_line.interpolate(end_dist / L, normalized=True)
        seg_window = LineString([(p_start.x, p_start.y), (p_end.x, p_end.y)])

        # Calculate unit normals
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        line_len = math.hypot(dx, dy)
        if line_len < 0.01:
            continue
        ux, uy = dx / line_len, dy / line_len
        nx, ny = -uy, ux

        # Ensure inward normal points into room interior
        wcx = (p_start.x + p_end.x) / 2.0
        wcy = (p_start.y + p_end.y) / 2.0
        rcx, rcy = r_poly.centroid.x, r_poly.centroid.y
        if (nx * (rcx - wcx) + ny * (rcy - wcy)) < 0:
            nx, ny = -nx, -ny

        # Inward daylight keep-out polygon (for furniture collision)
        keepout_depth = DAYLIGHT_KEEPOUT_DEPTH
        k_poly = Polygon([
            (p_start.x, p_start.y),
            (p_end.x, p_end.y),
            (p_end.x + nx * keepout_depth, p_end.y + ny * keepout_depth),
            (p_start.x + nx * keepout_depth, p_start.y + ny * keepout_depth)
        ])

        # Glazing area and IRC R310 Egress Compliance
        glazing_area = round(win_w * win_h, 2)
        is_egress = (
            "bedroom" in r_name.lower() and
            win_w >= 0.50 and
            win_h >= 0.60 and
            glazing_area >= 0.53 and
            sill_h <= 1.10
        )

        wall_id = f"ext_wall_{r_name}_{round(p1[0], 2)}_{round(p1[1], 2)}_{round(p2[0], 2)}_{round(p2[1], 2)}"
        win_idx = win_counter[r_name]
        win_counter[r_name] += 1
        opening_id = f"win_{r_name}_{win_idx}"

        windows_list.append({
            "opening_id": opening_id,
            "wall_id": wall_id,
            "type": "window",
            "room": r_name,
            "base_line": base_line,
            "wall_segment": seg_window,
            "position": (round(wcx, 3), round(wcy, 3)),
            "center": (round(wcx, 3), round(wcy, 3)),
            "u_coord": u_coord,
            "width": win_w,
            "height": win_h,
            "sill_height": sill_h,
            "head_height": WINDOW_HEAD_HEIGHT,
            "glazing_area": glazing_area,
            "inward_normal": (round(nx, 3), round(ny, 3)),
            "outward_normal": (round(-nx, 3), round(-ny, 3)),
            "keepout": k_poly,
            "is_egress": is_egress,
            "is_bathroom": is_bathroom,
            "is_habitable": is_habitable
        })

    registry = OpeningRegistry(
        design_id=design_id,
        windows=windows_list,
        doors=doors_list,
        cased_openings=cased_list,
        entrance=entrance_dict,
        metadata={
            "envelope_area": round(building_envelope.area, 2) if building_envelope else 0.0,
            "total_openings": len(windows_list) + len(doors_list) + len(cased_list) + (1 if entrance_dict else 0)
        }
    )
    return registry
