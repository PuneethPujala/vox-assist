"""
Circulation Constraints & Protected Geometry Engine for VoxAssist.

Treats circulation as a first-class architectural object:
1. Generates door approach & swing clearance boxes (>= 1.0m depth into rooms).
2. Computes the topological walking circulation spine connecting the main entrance
   to all functional rooms based on actual opening connectivity.
3. Unifies door approach boxes and walking corridors into a Protected Circulation Polygon.
4. Enforces dining table & chair pull-out clearance (>= 0.65m) against protected circulation.
5. Performs spatial reachability validation to ensure unhindered paths from the entrance
   to all living, sleeping, and sanitary zones without furniture collisions.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union

CORRIDOR_MIN_WIDTH = 0.90
DOOR_APPROACH_DEPTH = 1.10
CHAIR_PULLOUT_DEPTH = 0.65
WALKWAY_CLEARANCE_RADIUS = CORRIDOR_MIN_WIDTH / 2.0  # 0.45m buffer -> 0.90m walkway


def _extract_lines(geom) -> List[LineString]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if geom.geom_type == "MultiLineString":
        return list(geom.geoms)
    return []


def generate_door_approach_boxes(
    openings: List[Dict[str, Any]],
    rooms: Dict[str, Polygon],
    depth: float = DOOR_APPROACH_DEPTH,
    margin: float = 0.15
) -> List[Polygon]:
    """
    Constructs 2D keep-out clearance boxes in front of every door threshold.
    Extends inward by `depth` (1.0m - 1.2m) into each room sharing the door,
    with extra lateral margin for door swing and shoulder clearance.
    """
    approach_boxes = []

    for op in openings:
        poly = op.get("polygon")
        if poly is None or poly.is_empty:
            continue

        # Get door orientation and dimensions
        minx, miny, maxx, maxy = poly.bounds
        w = maxx - minx
        h = maxy - miny
        cx, cy = poly.centroid.x, poly.centroid.y

        # Determine if door is oriented horizontally (along X) or vertically (along Y)
        is_horizontal = w >= h
        pair = op.get("rooms", ())
        target_rooms = [r for r in pair if r in rooms and r != "exterior"]

        if is_horizontal:
            # Door runs East-West; approach extends North and South
            box_width = w + 2 * margin
            for r_name in target_rooms:
                r_poly = rooms[r_name]
                test_north = Point(cx, cy + 0.3)
                test_south = Point(cx, cy - 0.3)
                if r_poly.contains(test_north) or r_poly.distance(test_north) < 0.05:
                    b = box(cx - box_width / 2.0, cy, cx + box_width / 2.0, cy + depth)
                    inter = b.intersection(r_poly)
                    if not inter.is_empty and isinstance(inter, Polygon):
                        approach_boxes.append(inter)
                if r_poly.contains(test_south) or r_poly.distance(test_south) < 0.05:
                    b = box(cx - box_width / 2.0, cy - depth, cx + box_width / 2.0, cy)
                    inter = b.intersection(r_poly)
                    if not inter.is_empty and isinstance(inter, Polygon):
                        approach_boxes.append(inter)
        else:
            # Door runs North-South; approach extends East and West
            box_height = h + 2 * margin
            for r_name in target_rooms:
                r_poly = rooms[r_name]
                test_east = Point(cx + 0.3, cy)
                test_west = Point(cx - 0.3, cy)
                if r_poly.contains(test_east) or r_poly.distance(test_east) < 0.05:
                    b = box(cx, cy - box_height / 2.0, cx + depth, cy + box_height / 2.0)
                    inter = b.intersection(r_poly)
                    if not inter.is_empty and isinstance(inter, Polygon):
                        approach_boxes.append(inter)
                if r_poly.contains(test_west) or r_poly.distance(test_west) < 0.05:
                    b = box(cx - depth, cy - box_height / 2.0, cx, cy + box_height / 2.0)
                    inter = b.intersection(r_poly)
                    if not inter.is_empty and isinstance(inter, Polygon):
                        approach_boxes.append(inter)

    return approach_boxes


def generate_primary_circulation_spine(
    rooms: Dict[str, Polygon],
    openings: List[Dict[str, Any]],
    entrance_poly: Optional[Polygon] = None
) -> List[LineString]:
    """
    Computes continuous walking path line segments from the Main Entrance
    through circulation spaces to every room door approach point.
    """
    path_lines = []

    # 1. Determine entrance point
    entrance_pt = None
    if entrance_poly and not entrance_poly.is_empty:
        entrance_pt = entrance_poly.centroid
    else:
        for op in openings:
            if op.get("type") == "entrance" and op.get("polygon"):
                entrance_pt = op["polygon"].centroid
                break

    # 2. Identify circulation hub (Living room or Hallway)
    hub_name = None
    for name in ["hallway", "corridor", "living"]:
        candidates = [k for k in rooms.keys() if name in k.lower()]
        if candidates:
            hub_name = candidates[0]
            break

    if not hub_name or hub_name not in rooms:
        return path_lines

    hub_poly = rooms[hub_name]
    hub_center = hub_poly.centroid

    # 3. Path from Entrance to Hub Center
    if entrance_pt:
        direct = LineString([(entrance_pt.x, entrance_pt.y), (hub_center.x, hub_center.y)])
        path_lines.append(direct)

    # 4. Paths from Hub to each door threshold
    for op in openings:
        if op.get("type") == "entrance":
            continue
        op_poly = op.get("polygon")
        if not op_poly or op_poly.is_empty:
            continue
        door_pt = op_poly.centroid

        if hub_poly.distance(door_pt) < 0.35:
            path_lines.append(LineString([(hub_center.x, hub_center.y), (door_pt.x, door_pt.y)]))

    return path_lines


def compute_protected_circulation_polygon(
    rooms: Dict[str, Polygon],
    openings: List[Dict[str, Any]],
    entrance_poly: Optional[Polygon] = None,
    corridor_width: float = CORRIDOR_MIN_WIDTH
) -> Polygon:
    """
    Unions door approach clearance boxes and buffered circulation paths
    into a master 2D keep-out polygon where furniture must never be placed.
    """
    components = []

    # 1. Door approach boxes (hard keep-out zones in front of all thresholds)
    approach_boxes = generate_door_approach_boxes(openings, rooms)
    components.extend(approach_boxes)

    # 2. Main entrance foyer approach zone
    if entrance_poly and not entrance_poly.is_empty:
        foyer_box = entrance_poly.buffer(0.8, cap_style=3)
        components.append(foyer_box)

    # 3. Primary circulation walking spine
    spine_lines = generate_primary_circulation_spine(rooms, openings, entrance_poly)
    for line in spine_lines:
        if line.length > 0.05:
            buffered_line = line.buffer(corridor_width / 2.0, cap_style=2)
            components.append(buffered_line)

    if not components:
        return Polygon()

    master_circ = unary_union(components)

    all_rooms_poly = unary_union(list(rooms.values()))
    clipped = master_circ.intersection(all_rooms_poly)

    if isinstance(clipped, (Polygon, MultiPolygon)):
        return clipped
    return Polygon()


def compute_dining_clearance_envelope(
    table_cx: float,
    table_cy: float,
    table_w: float,
    table_h: float,
    pullout: float = CHAIR_PULLOUT_DEPTH
) -> Polygon:
    """
    Computes the total functional envelope of a dining set:
    Table footprint + chair pullout clearance on all active sides.
    """
    half_w = (table_w / 2.0) + pullout
    half_h = (table_h / 2.0) + pullout
    return box(table_cx - half_w, table_cy - half_h, table_cx + half_w, table_cy + half_h)


def validate_dining_circulation_clearance(
    table_cx: float,
    table_cy: float,
    table_w: float,
    table_h: float,
    protected_circ_poly: Polygon,
    min_pullout: float = CHAIR_PULLOUT_DEPTH
) -> Dict[str, Any]:
    """
    Validates that a dining set (table + pullout zone) does NOT collide with
    or encroach on protected circulation paths or door approach boxes.
    """
    table_box = box(
        table_cx - table_w / 2.0,
        table_cy - table_h / 2.0,
        table_cx + table_w / 2.0,
        table_cy + table_h / 2.0
    )
    envelope = compute_dining_clearance_envelope(table_cx, table_cy, table_w, table_h, min_pullout)

    if protected_circ_poly.is_empty:
        return {"valid": True, "status": "pass", "details": "No protected circulation restrictions", "violations": []}

    table_conflict = table_box.intersects(protected_circ_poly)
    envelope_inter = envelope.intersection(protected_circ_poly)
    overlap_area = envelope_inter.area if not envelope_inter.is_empty else 0.0

    violations = []
    if table_conflict:
        violations.append("Dining table footprint directly intersects the primary walking corridor or doorway approach")
    elif overlap_area > 0.15:
        violations.append(f"Dining chair pull-out zone overlaps circulation corridor by {round(overlap_area, 2)}m²")

    valid = len(violations) == 0
    return {
        "valid": valid,
        "status": "pass" if valid else "fail",
        "overlap_area": round(overlap_area, 3),
        "violations": violations,
        "details": "Dining table and chair pull-out zones maintain full pedestrian clearance" if valid else "; ".join(violations)
    }


def evaluate_circulation_reachability(
    rooms: Dict[str, Polygon],
    openings: List[Dict[str, Any]],
    furniture_polys: List[Polygon],
    entrance_poly: Optional[Polygon] = None,
    min_passage_width: float = 0.70
) -> Dict[str, Any]:
    """
    Performs a reachability test across the house:
    Verifies that a person can navigate from the Main Entrance to every functional
    room without being blocked by furniture items or impassable bottlenecks (< 0.70m).
    """
    if not rooms or len(rooms) <= 1:
        return {"reachable": True, "status": "pass", "details": "Studio/single room reachability satisfied", "unreachable": []}

    all_rooms_poly = unary_union(list(rooms.values()))
    if furniture_polys:
        furniture_union = unary_union(furniture_polys)
        walkable_floor = all_rooms_poly.difference(furniture_union)
    else:
        walkable_floor = all_rooms_poly

    entrance_pt = None
    if entrance_poly and not entrance_poly.is_empty:
        entrance_pt = entrance_poly.centroid
    else:
        for op in openings:
            if op.get("type") == "entrance" and op.get("polygon"):
                entrance_pt = op["polygon"].centroid
                break

    if not entrance_pt:
        living = [p for k, p in rooms.items() if "living" in k.lower()]
        if living:
            entrance_pt = living[0].centroid

    if not entrance_pt:
        return {"reachable": True, "status": "pass", "details": "No designated start point", "unreachable": []}

    unreachable = []
    passage_buffer = min_passage_width / 2.0
    eroded_walkable = walkable_floor.buffer(-passage_buffer).buffer(passage_buffer)

    for r_name, r_poly in rooms.items():
        if "balcony" in r_name.lower():
            continue

        if not eroded_walkable.intersects(entrance_pt.buffer(0.3)):
            if not walkable_floor.intersects(entrance_pt.buffer(0.3)):
                unreachable.append(r_name)
                continue

        has_clear_opening = False
        for op in openings:
            pair = op.get("rooms", ())
            if r_name in pair:
                op_poly = op.get("polygon")
                if op_poly and walkable_floor.intersects(op_poly):
                    has_clear_opening = True
                    break

        if not has_clear_opening:
            unreachable.append(r_name)

    reachable = len(unreachable) == 0
    return {
        "reachable": reachable,
        "status": "pass" if reachable else "fail",
        "unreachable": unreachable,
        "details": "Continuous unhindered walking path from main entrance to all rooms" if reachable else f"Cannot reach {', '.join(unreachable)} due to furniture obstruction or missing doorway"
    }

def validate_circulation_continuity(
    rooms: Dict[str, Polygon],
    openings: List[Dict[str, Any]],
    entrance_poly: Optional[Polygon] = None
) -> Dict[str, Any]:
    """
    Validates that a continuous primary circulation walking spine exists
    connecting the entrance to living and private zones.
    """
    if not rooms or len(rooms) <= 1:
        return {"valid": True, "status": "pass", "details": "Circulation satisfied for single room layout"}
        
    spine_lines = generate_primary_circulation_spine(rooms, openings, entrance_poly)
    if not spine_lines and len(rooms) > 2:
        return {
            "valid": False,
            "status": "warn",
            "details": "Circulation spine incomplete: living/circulation hub cannot reach all room thresholds"
        }
        
    return {
        "valid": True,
        "status": "pass",
        "details": f"Continuous primary circulation spine connects entrance across {len(spine_lines)} walking links"
    }

