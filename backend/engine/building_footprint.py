"""
Building Footprint & Space Partitioning Engine for VoxAssist (V4 Architecture).

Transforms floor-plan generation from bottom-up greedy rectangle packing into
an outside-in architectural workflow:
PLOT & SETBACKS -> ENVELOPE -> ZONING -> CIRCULATION -> ARCHETYPE PARTITIONING.

Key Features:
1. PlotSpec with front, rear, and side setbacks.
2. Compact rectangular envelope calculation snapped to construction module grid (0.2m).
3. Multiple archetypes per program:
   - 2BHK: 2BHK_COMPACT (Front Living/Kitchen, Central Hall, Rear Master+Bed2)
           2BHK_SPLIT_WINGS (Master Wing West, Bed2 Wing East, Living/Spine Center)
   - 3BHK: 3BHK_COMPACT (Public Front, Hall+Common Bath Center, 3 Beds Rear)
           3BHK_MASTER_SUITE (Private Master Wing, Central Living, Secondary Bed Wing)
   - 1BHK: 1BHK_COMPACT (Front Living/Kitchen, Bath/Hall, Rear Bedroom)
4. Semantic Bathroom Typology:
   - Master Ensuite (bathroom_1): strictly attached to Master Bedroom (bedroom_1).
   - Common Bathroom (bathroom_2): opens to hallway / public circulation.
5. Topological Guarantee:
   - Space partitioning cleanly tiles the rectangular envelope with zero gaps,
     zero overlaps, and aligned interior walls.
   - All bedrooms receive exterior walls for natural daylighting and egress.
   - Living room receives South external wall for deliberate front entrance arrival.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import math
import random
import logging
from shapely.geometry import box, Polygon, Point, LineString
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

MODULE_GRID = 0.20  # 20cm construction module snap


@dataclass
class PlotSpec:
    """Represents a residential plot with boundaries and mandatory setbacks."""
    width: float   # meters (East-West width)
    depth: float   # meters (North-South depth)
    front_facing: str = "south"  # "south", "north", "east", "west"
    setbacks: Dict[str, float] = field(default_factory=lambda: {
        "front": 3.0,
        "rear": 2.0,
        "left": 1.5,
        "right": 1.5
    })

    def buildable_bounds(self) -> Tuple[float, float, float, float]:
        """Returns (minx, miny, maxx, maxy) for the buildable building envelope."""
        s_front = self.setbacks.get("front", 3.0)
        s_rear = self.setbacks.get("rear", 2.0)
        s_left = self.setbacks.get("left", 1.5)
        s_right = self.setbacks.get("right", 1.5)

        # Assuming front is South (Y=0)
        if self.front_facing == "south":
            miny = s_front
            maxy = self.depth - s_rear
            minx = s_left
            maxx = self.width - s_right
        elif self.front_facing == "north":
            miny = s_rear
            maxy = self.depth - s_front
            minx = s_left
            maxx = self.width - s_right
        elif self.front_facing == "east":
            minx = s_rear
            maxx = self.width - s_front
            miny = s_left
            maxy = self.depth - s_right
        else:  # west
            minx = s_front
            maxx = self.width - s_rear
            miny = s_left
            maxy = self.depth - s_right

        minx = round(max(0.0, minx), 2)
        miny = round(max(0.0, miny), 2)
        maxx = round(max(minx + 4.0, maxx), 2)
        maxy = round(max(miny + 4.0, maxy), 2)
        return minx, miny, maxx, maxy

    def buildable_polygon(self) -> Polygon:
        minx, miny, maxx, maxy = self.buildable_bounds()
        return box(minx, miny, maxx, maxy)


def snap_module(val: float, module: float = MODULE_GRID) -> float:
    """Snaps dimension to architectural construction module (default 0.2m)."""
    return round(round(val / module) * module, 2)


def compute_footprint_envelope(
    target_area_sqm: float,
    aspect_ratio: float = 1.18,
    plot: Optional[PlotSpec] = None,
    shape: str = "rectangular"
) -> Dict[str, Any]:
    """
    Computes a clean, compact building footprint envelope.
    If a plot is provided, respects plot setbacks. Otherwise generates a
    rectangular envelope with realistic architectural aspect ratio.
    """
    if plot:
        minx, miny, maxx, maxy = plot.buildable_bounds()
        w = snap_module(maxx - minx)
        h = snap_module(maxy - miny)
        poly = box(0.0, 0.0, w, h)
        return {
            "polygon": poly,
            "width": w,
            "height": h,
            "area": round(w * h, 2),
            "plot": plot,
            "shape": shape
        }

    # Derive rectangular envelope from target area
    # Aspect ratio W / D or D / W. For front street on South, W is typically width, D is depth.
    ar = max(1.05, min(1.60, aspect_ratio))
    # Area = W * D, W = ar * D => D = sqrt(Area / ar), W = ar * D
    depth = math.sqrt(target_area_sqm / ar)
    width = ar * depth

    width = snap_module(max(5.0, width))
    depth = snap_module(max(5.0, depth))
    actual_area = width * depth

    # If rounding deviated from target, adjust depth slightly
    if abs(actual_area - target_area_sqm) > 4.0 and depth > 4.0:
        depth = snap_module(target_area_sqm / width)

    poly = box(0.0, 0.0, width, depth)
    return {
        "polygon": poly,
        "width": width,
        "height": depth,
        "area": round(width * depth, 2),
        "plot": None,
        "shape": shape
    }


def can_partition_archetype(spec: Dict[str, Any]) -> Optional[str]:
    """
    Inspects room spec and returns archetype family:
    '1bhk', '2bhk', '3bhk', or None (if custom/exotic program).
    """
    rooms = spec.get("rooms", [])
    if not rooms:
        return None

    bed_count = sum(1 for r in rooms if "bedroom" in r.get("type", ""))
    bath_count = sum(1 for r in rooms if any(k in r.get("type", "") for k in ["bath", "toilet", "wash"]))
    has_living = any("living" in r.get("type", "") for r in rooms)
    has_hallway = any("hallway" in r.get("type", "").lower() for r in rooms)

    # Top-down archetypes require living, hallway, 1-3 bedrooms, and <= 2 bathrooms
    if not has_living or not has_hallway or bed_count < 1 or bed_count > 3 or bath_count > 2:
        return None

    # Check for non-standard rooms that require the open synthesizer
    exotic = {"gym", "meditation", "yoga", "parking", "garden"}
    for r in rooms:
        if r.get("type") in exotic:
            return None

    if bed_count == 1:
        return "1bhk"
    elif bed_count == 2:
        return "2bhk"
    elif bed_count == 3:
        return "3bhk"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ARCHETYPE PARTITIONERS (Zero-gap, aligned wall topological space partition)
# ─────────────────────────────────────────────────────────────────────────────

def partition_1bhk_compact(
    env_w: float,
    env_h: float,
    room_names: Dict[str, str]
) -> Dict[str, Polygon]:
    """
    1BHK Compact Partition:
    - Front Zone: Living (with South main entrance) and Kitchen
    - Circulation Spine: Central Hallway (if specified) connecting Living, Bed, and Bath
    - Rear Zone: Bedroom 1 and Bathroom 1 (accessible from circulation/hallway)
    """
    y_split = snap_module(env_h * 0.48)
    x_split_front = snap_module(env_w * 0.60)
    x_split_rear = snap_module(env_w * 0.60)

    rooms = {}
    living_name = room_names.get("living", "living")
    kitchen_name = room_names.get("kitchen", "kitchen")
    bed1_name = room_names.get("bedroom_1", "bedroom_1")
    bath1_name = room_names.get("bathroom_1", "bathroom_1")

    # If hallway in room_names, insert a continuous circulation corridor
    if "hallway" in room_names:
        hall_name = room_names["hallway"]
        y_hall_h = snap_module(max(1.2, env_h * 0.14))
        y_hall_start = snap_module(y_split - y_hall_h)
        rooms[living_name] = box(0.0, 0.0, x_split_front, y_hall_start)
        rooms[kitchen_name] = box(x_split_front, 0.0, env_w, y_hall_start)
        rooms[hall_name] = box(0.0, y_hall_start, env_w, y_split)
        rooms[bed1_name] = box(0.0, y_split, x_split_rear, env_h)
        rooms[bath1_name] = box(x_split_rear, y_split, env_w, env_h)
    else:
        # Overlap Living with Bathroom so Bathroom connects to Living (common bath access)
        x_front = snap_module(env_w * 0.65)
        x_rear = snap_module(env_w * 0.50)
        rooms[living_name] = box(0.0, 0.0, x_front, y_split)
        rooms[kitchen_name] = box(x_front, 0.0, env_w, y_split)
        rooms[bed1_name] = box(0.0, y_split, x_rear, env_h)
        rooms[bath1_name] = box(x_rear, y_split, env_w, env_h)

    return rooms


def partition_2bhk_compact(
    env_w: float,
    env_h: float,
    room_names: Dict[str, str],
    has_dining: bool = False,
    has_two_baths: bool = True
) -> Dict[str, Polygon]:
    """
    2BHK Compact Layout:
    -------------------------------------------------------
    Y = env_h
        ┌─────────────────────────┬───────────────────────┐
        │  MASTER BEDROOM         │  BEDROOM 2            │
        │  (bedroom_1)            │  (bedroom_2)          │
        │  ┌───────────────┐      │                       │
        │  │ MASTER ENSUITE│      │                       │
        │  │ (bathroom_1)  │      │                       │
    Y2  ├──┴───────────────┴──────┼───────────────────────┤
        │  CENTRAL HALLWAY        │  COMMON BATHROOM      │
        │  (hallway)              │  (bathroom_2)         │
    Y1  ├─────────────────────────┴───────────────────────┤
        │  LIVING ROOM            │  KITCHEN / DINING     │
        │  (South Front Entrance) │                       │
    Y=0 └─────────────────────────┴───────────────────────┘
        X=0                       X1                      X=env_w
    -------------------------------------------------------
    """
    # Balanced 3-tier zoning to guarantee all rooms satisfy residential aspect ratio rules (<= 1.6:1 for beds, <= 6.0:1 for hall)
    h_spine = snap_module(max(1.5, env_h * 0.18))
    h_rear = snap_module(max(3.2, env_h * 0.40))
    y1 = snap_module(env_h - h_rear - h_spine)
    y2 = snap_module(y1 + h_spine)

    # Front zone split: Living (52% width) vs Kitchen/Dining (48% width)
    x_front = snap_module(env_w * 0.52)
    # Rear zone split: Master Suite (50% width) vs Bedroom 2 (50% width)
    x_rear = snap_module(env_w * 0.50)

    rooms = {}

    # 1. Front Zone (Living & Kitchen)
    living_name = room_names.get("living", "living")
    kitchen_name = room_names.get("kitchen", "kitchen")
    dining_name = room_names.get("dining", None)

    if has_dining and dining_name:
        y_kd = snap_module(y1 * 0.50)
        rooms[living_name] = box(0.0, 0.0, x_front, y1)
        rooms[dining_name] = box(x_front, 0.0, env_w, y_kd)
        rooms[kitchen_name] = box(x_front, y_kd, env_w, y1)
    else:
        rooms[living_name] = box(0.0, 0.0, x_front, y1)
        rooms[kitchen_name] = box(x_front, 0.0, env_w, y1)

    # 2. Circulation Spine (Y1 -> Y2)
    hall_name = room_names.get("hallway", "hallway")
    bath2_name = room_names.get("bathroom_2", None)

    # Common bath width: keep aspect ratio <= 1.7:1 (max allowed 2.0:1)
    bath2_w = snap_module(min(2.4, h_spine * 1.50))
    x_spine = snap_module(env_w - bath2_w)

    if has_two_baths and bath2_name:
        rooms[hall_name] = box(0.0, y1, x_spine, y2)
        rooms[bath2_name] = box(x_spine, y1, env_w, y2)
    else:
        single_bath = room_names.get("bathroom_1", "bathroom_1")
        rooms[hall_name] = box(0.0, y1, x_spine, y2)
        rooms[single_bath] = box(x_spine, y1, env_w, y2)

    # 3. Rear Zone (Y2 -> env_h): Master Suite & Bedroom 2
    bed1_name = room_names.get("bedroom_1", "bedroom_1")
    bed2_name = room_names.get("bedroom_2", "bedroom_2")
    bath1_name = room_names.get("bathroom_1", "bathroom_1")

    rooms[bed2_name] = box(x_rear, y2, env_w, env_h)

    if has_two_baths and bath1_name and bath1_name not in rooms:
        # Place Master Ensuite at Northwest corner:
        # Touches North & West exterior walls for daylight/ventilation,
        # East and South borders are interior walls facing exclusively inside Master Bedroom!
        h_rear = env_h - y2
        ensuite_w = snap_module(min(2.2, x_rear * 0.44))
        ensuite_h = snap_module(min(2.0, h_rear * 0.48))
        rooms[bath1_name] = box(0.0, env_h - ensuite_h, ensuite_w, env_h)

        master_poly = Polygon([
            (ensuite_w, env_h),
            (x_rear, env_h),
            (x_rear, y2),
            (0.0, y2),
            (0.0, env_h - ensuite_h),
            (ensuite_w, env_h - ensuite_h)
        ])
        rooms[bed1_name] = master_poly
    else:
        rooms[bed1_name] = box(0.0, y2, x_rear, env_h)

    return rooms


def partition_2bhk_split_wings(
    env_w: float,
    env_h: float,
    room_names: Dict[str, str],
    has_dining: bool = False,
    has_two_baths: bool = True
) -> Dict[str, Polygon]:
    """
    2BHK Split-Wings Layout (Maximum acoustic privacy between bedrooms):
    -------------------------------------------------------
    Y = env_h
        ┌────────────────┬──────────────────────┬─────────────┐
        │ MASTER BEDROOM │ KITCHEN / DINING     │ BEDROOM 2   │
        │ (West Wing)    │                      │ (East Wing) │
        │                ├──────────────────────┤             │
        │                │ CENTRAL HALLWAY      │             │
    Y1  ├────────────────┼──────────────────────┼─────────────┤
        │ MASTER ENSUITE │ LIVING ROOM          │ COMMON BATH │
        │ (bathroom_1)   │ (South Main Entrance)│ (bathroom_2)│
    Y=0 └────────────────┴──────────────────────┴─────────────┘
        X=0              X1                     X2            X=env_w
    -------------------------------------------------------
    """
    x1 = snap_module(env_w * 0.32)  # West wing boundary (Master Suite)
    x2 = snap_module(env_w * 0.68)  # East wing boundary (Secondary Bed + Bath)
    y_front = snap_module(env_h * 0.40)

    rooms = {}
    living_name = room_names.get("living", "living")
    kitchen_name = room_names.get("kitchen", "kitchen")
    bed1_name = room_names.get("bedroom_1", "bedroom_1")
    bed2_name = room_names.get("bedroom_2", "bedroom_2")
    bath1_name = room_names.get("bathroom_1", "bathroom_1")
    bath2_name = room_names.get("bathroom_2", "bathroom_2")
    dining_name = room_names.get("dining", None)
    hall_name = room_names.get("hallway", None)

    # 1. Central Zone: Living (Front) + Hallway (Mid) + Kitchen / Dining (Rear)
    rooms[living_name] = box(x1, 0.0, x2, y_front)
    
    if hall_name:
        y_hall = snap_module(y_front + max(1.4, (env_h - y_front) * 0.30))
        rooms[hall_name] = box(x1, y_front, x2, y_hall)
        if has_dining and dining_name:
            y_mid = snap_module(y_hall + (env_h - y_hall) * 0.50)
            rooms[kitchen_name] = box(x1, y_hall, x2, y_mid)
            rooms[dining_name] = box(x1, y_mid, x2, env_h)
        else:
            rooms[kitchen_name] = box(x1, y_hall, x2, env_h)
    else:
        if has_dining and dining_name:
            y_mid = snap_module(y_front + (env_h - y_front) * 0.50)
            rooms[kitchen_name] = box(x1, y_front, x2, y_mid)
            rooms[dining_name] = box(x1, y_mid, x2, env_h)
        else:
            rooms[kitchen_name] = box(x1, y_front, x2, env_h)

    # 2. West Wing: Master Ensuite (Northwest or Southwest) & Master Bedroom
    if has_two_baths and bath1_name:
        bath1_h = snap_module(min(2.4, y_front))
        rooms[bath1_name] = box(0.0, 0.0, x1, bath1_h)
        rooms[bed1_name] = box(0.0, bath1_h, x1, env_h)
    else:
        rooms[bed1_name] = box(0.0, 0.0, x1, env_h)

    # 3. East Wing: Common Bathroom (Front) + Bedroom 2 (Rear)
    if has_two_baths and bath2_name:
        bath2_h = snap_module(min(2.4, y_front))
        rooms[bath2_name] = box(x2, 0.0, env_w, bath2_h)
        rooms[bed2_name] = box(x2, bath2_h, env_w, env_h)
    else:
        single_bath = bath1_name or "bathroom_1"
        if single_bath not in rooms:
            bath_h = snap_module(min(2.4, y_front))
            rooms[single_bath] = box(x2, 0.0, env_w, bath_h)
            rooms[bed2_name] = box(x2, bath_h, env_w, env_h)
        else:
            rooms[bed2_name] = box(x2, 0.0, env_w, env_h)

    return rooms


def partition_3bhk_compact(
    env_w: float,
    env_h: float,
    room_names: Dict[str, str],
    has_dining: bool = False
) -> Dict[str, Polygon]:
    """
    3BHK Compact Space Partition:
    - Front Zone (Y: 0 -> 0.38 D):
      - Living Room (West/Center, South Main Entrance)
      - Dining & Kitchen (East)
    - Central Spine (Y: 0.38 D -> 0.52 D):
      - Hallway (Spans across to serve all 3 bedrooms)
      - Common Bathroom (bathroom_2)
    - Rear Quarters (Y: 0.52 D -> D):
      - West: Master Bedroom with attached Ensuite (bathroom_1)
      - Center: Bedroom 2 (exterior window on North)
      - East: Bedroom 3 (exterior windows on North and East)
    """
    y1 = snap_module(env_h * 0.38)
    y2 = snap_module(env_h * 0.52)

    # Front zone split
    x_front = snap_module(env_w * 0.58)
    # Rear zone split into 3 bedrooms
    x_rear1 = snap_module(env_w * 0.38)
    x_rear2 = snap_module(env_w * 0.68)

    rooms = {}

    living_name = room_names.get("living", "living")
    kitchen_name = room_names.get("kitchen", "kitchen")
    dining_name = room_names.get("dining", None)
    hall_name = room_names.get("hallway", "hallway")
    bed1_name = room_names.get("bedroom_1", "bedroom_1")
    bed2_name = room_names.get("bedroom_2", "bedroom_2")
    bed3_name = room_names.get("bedroom_3", "bedroom_3")
    bath1_name = room_names.get("bathroom_1", "bathroom_1")
    bath2_name = room_names.get("bathroom_2", "bathroom_2")

    # Front Public
    rooms[living_name] = box(0.0, 0.0, x_front, y1)
    if has_dining and dining_name:
        y_kd = snap_module(y1 * 0.50)
        rooms[dining_name] = box(x_front, 0.0, env_w, y_kd)
        rooms[kitchen_name] = box(x_front, y_kd, env_w, y1)
    else:
        rooms[kitchen_name] = box(x_front, 0.0, env_w, y1)

    # Central Circulation Spine & Common Bath
    x_bath2 = snap_module(env_w * 0.72)
    rooms[hall_name] = box(0.0, y1, x_bath2, y2)
    if bath2_name:
        rooms[bath2_name] = box(x_bath2, y1, env_w, y2)

    # Rear Private Quarters
    if bath1_name:
        ensuite_w = snap_module(min(2.2, x_rear1 * 0.48))
        ensuite_h = snap_module(min(2.0, (env_h - y2) * 0.45))
        rooms[bath1_name] = box(x_rear1 - ensuite_w, y2, x_rear1, y2 + ensuite_h)
        master_poly = Polygon([
            (0.0, y2),
            (x_rear1 - ensuite_w, y2),
            (x_rear1 - ensuite_w, y2 + ensuite_h),
            (x_rear1, y2 + ensuite_h),
            (x_rear1, env_h),
            (0.0, env_h)
        ])
        rooms[bed1_name] = master_poly
    else:
        rooms[bed1_name] = box(0.0, y2, x_rear1, env_h)

    # Bedroom 2 (Center) & Bedroom 3 (East)
    rooms[bed2_name] = box(x_rear1, y2, x_rear2, env_h)
    rooms[bed3_name] = box(x_rear2, y2, env_w, env_h)

    return rooms


def partition_3bhk_master_suite(
    env_w: float,
    env_h: float,
    room_names: Dict[str, str],
    has_dining: bool = False
) -> Dict[str, Polygon]:
    """
    3BHK Master Wing Layout (Distinct Master Suite on West wing, secondary beds East):
    -------------------------------------------------------
    Y = env_h
        ┌────────────────┬──────────────────────┬─────────────┐
        │ MASTER BEDROOM │ BEDROOM 2            │ BEDROOM 3   │
        │ (West Wing)    │                      │ (East Wing) │
        │                ├──────────────────────┼─────────────┤
        │                │ CENTRAL HALLWAY      │ COMMON BATH │
    Y1  ├────────────────┼──────────────────────┴─────────────┤
        │ MASTER ENSUITE │ LIVING ROOM          │ KITCHEN     │
        │ (bathroom_1)   │ (South Main Entrance)│             │
    Y=0 └────────────────┴──────────────────────┴─────────────┘
        X=0              X1                     X2            X=env_w
    -------------------------------------------------------
    """
    x1 = snap_module(env_w * 0.32)  # Master Suite West Wing
    x2 = snap_module(env_w * 0.68)
    y1 = snap_module(env_h * 0.42)
    y2 = snap_module(env_h * 0.58)

    rooms = {}
    living_name = room_names.get("living", "living")
    kitchen_name = room_names.get("kitchen", "kitchen")
    bed1_name = room_names.get("bedroom_1", "bedroom_1")
    bed2_name = room_names.get("bedroom_2", "bedroom_2")
    bed3_name = room_names.get("bedroom_3", "bedroom_3")
    bath1_name = room_names.get("bathroom_1", "bathroom_1")
    bath2_name = room_names.get("bathroom_2", "bathroom_2")
    dining_name = room_names.get("dining", None)
    hall_name = room_names.get("hallway", "hallway")

    # 1. Master Suite Wing (West)
    if bath1_name:
        bath1_h = snap_module(min(2.4, y1 * 0.8))
        rooms[bath1_name] = box(0.0, 0.0, x1, bath1_h)
        rooms[bed1_name] = box(0.0, bath1_h, x1, env_h)
    else:
        rooms[bed1_name] = box(0.0, 0.0, x1, env_h)

    # 2. Front Center/East: Living & Kitchen
    rooms[living_name] = box(x1, 0.0, x2, y1)
    if has_dining and dining_name:
        y_kd = snap_module(y1 * 0.5)
        rooms[dining_name] = box(x2, 0.0, env_w, y_kd)
        rooms[kitchen_name] = box(x2, y_kd, env_w, y1)
    else:
        rooms[kitchen_name] = box(x2, 0.0, env_w, y1)

    # 3. Mid Spine: Hallway + Common Bath
    rooms[hall_name] = box(x1, y1, x2, y2)
    if bath2_name:
        rooms[bath2_name] = box(x2, y1, env_w, y2)

    # 4. Rear East: Bedroom 2 & Bedroom 3
    x_bed_split = snap_module(x1 + (env_w - x1) * 0.48)
    rooms[bed2_name] = box(x1, y2, x_bed_split, env_h)
    rooms[bed3_name] = box(x_bed_split, y2, env_w, env_h)

    return rooms


# ─────────────────────────────────────────────────────────────────────────────
# TOP-LEVEL DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def select_and_partition_archetype(
    spec: Dict[str, Any],
    envelope_box_dims: Optional[Tuple[float, float]] = None,
    plot: Optional[PlotSpec] = None,
    seed: Optional[int] = None
) -> Optional[Tuple[Dict[str, Polygon], Polygon]]:
    """
    Selects and executes an architectural space-partitioning archetype
    if the spec matches a standard residential program (1BHK, 2BHK, 3BHK).
    Returns (rooms_dict, envelope_polygon) or None if spec cannot be partitioned.
    """
    family = can_partition_archetype(spec)
    if not family:
        return None

    spec_rooms = spec.get("rooms", [])
    total_area_sqm = sum(float(r.get("area", 10.0)) for r in spec_rooms)

    # Build room name map with duplicate/collision guard
    room_names = {}
    bath_count = 0
    bed_count = 0
    has_dining = False
    used_names = set()

    for r in spec_rooms:
        rtype = r.get("type", "").strip().lower()
        raw_name = r.get("name", "").strip().lower()
        if "living" in rtype:
            rname = raw_name if (raw_name and raw_name not in used_names) else "living"
            room_names["living"] = rname
            used_names.add(rname)
        elif "kitchen" in rtype:
            rname = raw_name if (raw_name and raw_name not in used_names) else "kitchen"
            room_names["kitchen"] = rname
            used_names.add(rname)
        elif "dining" in rtype:
            rname = raw_name if (raw_name and raw_name not in used_names) else "dining"
            room_names["dining"] = rname
            used_names.add(rname)
            has_dining = True
        elif "hallway" in rtype:
            rname = raw_name if (raw_name and raw_name not in used_names) else "hallway"
            room_names["hallway"] = rname
            used_names.add(rname)
        elif "bedroom" in rtype:
            bed_count += 1
            default_name = f"bedroom_{bed_count}"
            rname = raw_name if (raw_name and raw_name not in used_names) else default_name
            room_names[f"bedroom_{bed_count}"] = rname
            used_names.add(rname)
        elif any(k in rtype for k in ["bath", "toilet", "wash"]):
            bath_count += 1
            default_name = f"bathroom_{bath_count}"
            rname = raw_name if (raw_name and raw_name not in used_names) else default_name
            room_names[f"bathroom_{bath_count}"] = rname
            used_names.add(rname)

    has_two_baths = (bath_count >= 2)

    # Determine building envelope
    if envelope_box_dims:
        env_w, env_h = envelope_box_dims
    else:
        env_info = compute_footprint_envelope(total_area_sqm, aspect_ratio=1.24, plot=plot)
        env_w, env_h = env_info["width"], env_info["height"]

    envelope_poly = box(0.0, 0.0, env_w, env_h)

    rng = random.Random(seed) if seed is not None else random

    if family == "1bhk":
        rooms = partition_1bhk_compact(env_w, env_h, room_names)
    elif family == "2bhk":
        is_wide = (env_w / env_h >= 1.25)
        use_split = is_wide or (rng.random() < 0.40)
        if use_split:
            logger.info(f"[Archetype] Selected 2BHK_SPLIT_WINGS (W={env_w}m, D={env_h}m)")
            rooms = partition_2bhk_split_wings(env_w, env_h, room_names, has_dining, has_two_baths)
        else:
            logger.info(f"[Archetype] Selected 2BHK_COMPACT (W={env_w}m, D={env_h}m)")
            rooms = partition_2bhk_compact(env_w, env_h, room_names, has_dining, has_two_baths)
    elif family == "3bhk":
        is_wide = (env_w / env_h >= 1.28)
        use_suite = is_wide or (rng.random() < 0.45)
        if use_suite:
            logger.info(f"[Archetype] Selected 3BHK_MASTER_SUITE (W={env_w}m, D={env_h}m)")
            rooms = partition_3bhk_master_suite(env_w, env_h, room_names, has_dining)
        else:
            logger.info(f"[Archetype] Selected 3BHK_COMPACT (W={env_w}m, D={env_h}m)")
            rooms = partition_3bhk_compact(env_w, env_h, room_names, has_dining)
    else:
        return None

    valid_rooms = {}
    for k, p in rooms.items():
        if p and not p.is_empty and p.area > 1.0:
            valid_rooms[k] = p

    return valid_rooms, envelope_poly
