from shapely.geometry import box, Point, Polygon, LineString
from shapely.ops import unary_union
import numpy as np
import random
import logging

logger = logging.getLogger(__name__)

from adjacency_rules import ADJACENCY_RULES, validate_adjacency
from corridor_generator import generate_corridors
from door_generator import (
    generate_doors,
    generate_doors_with_metadata,
    INTERIOR_DOOR_WIDTH,
    BATH_DOOR_WIDTH,
    ENTRY_DOOR_WIDTH,
    CASED_OPENING_WIDTH,
)

try:
    from constraints.envelope import compute_building_envelope, is_within_envelope
    from constraints.room_dimensions import compute_bounded_room_dimensions
except ImportError:
    from engine.constraints.envelope import compute_building_envelope, is_within_envelope
    from engine.constraints.room_dimensions import compute_bounded_room_dimensions

# =========================
# CONSTANTS
# =========================
# Architectural opening widths in meters
DOOR_WIDTH = INTERIOR_DOOR_WIDTH
OPEN_SPACE_WIDTH = CASED_OPENING_WIDTH
WALL_TOLERANCE = 0.5
JITTER = 0.15  # Small positional noise

# =========================
# DEFAULT CONFIG
# =========================
DEFAULT_CONFIG = {
    "GAP": 0.0,
    "EXTERNAL_OFFSET": 5.0,
    "MAX_ROW_WIDTH": 40.0,
    "RANDOM_SEED": None,
    "adjacency_pairs": [],
}

ZONES = {
    "public": ["living", "dining"],
    "circulation": ["hallway"],
    "semi_public": ["kitchen"],
    "private": ["bedroom", "study"],
    "service": ["bathroom", "storage", "utility"],
}

def get_zone(room_type):
    for zone, types in ZONES.items():
        if room_type in types:
            return zone
    return "other"

def _random_aspect_ratio(base_ratio=1.5, variance=0.5):
    min_ratio = max(0.8, base_ratio - variance)
    max_ratio = min(2.0, base_ratio + variance)
    return random.uniform(min_ratio, max_ratio)

def _place_adjacent(base_poly, width, height, existing_polys, preferred_sides=None, envelope_poly=None, room_type=None):
    """
    Place room adjacent to base_poly with placement-time constraint pruning.
    Priority:
    1. STRICTLY within building envelope (hard constraint pruning).
    2. Matches preferred_sides (if provided).
    3. MAXIMIZES shared perimeter with ALL existing polys (Gap Filling / Corner Logic).
    4. Rewards exterior contact for bedrooms (egress feasibility).
    """
    # Safety check: prevent infinite sprawl
    MAX_DIMENSION = 100.0  # Maximum room dimension in meters
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        return None
    
    minx, miny, maxx, maxy = base_poly.bounds
    base_w = maxx - minx
    base_h = maxy - miny
    
    primary_candidates = []
    secondary_candidates = []
    
    # Try original orientation, and rotated orientation if distinct
    orientations = [(width, height)]
    if abs(width - height) > 0.3:
        orientations.append((height, width))
        
    for (w, h) in orientations:
        placements = {
            'right': [
                box(maxx, miny, maxx + w, miny + h),
                box(maxx, maxy - h, maxx + w, maxy),
                box(maxx, miny + (base_h - h)/2.0, maxx + w, miny + (base_h + h)/2.0)
            ],
            'left': [
                box(minx - w, miny, minx, miny + h),
                box(minx - w, maxy - h, minx, maxy),
                box(minx - w, miny + (base_h - h)/2.0, minx, miny + (base_h + h)/2.0)
            ],
            'top': [
                box(minx, maxy, minx + w, maxy + h),
                box(maxx - w, maxy, maxx, maxy + h),
                box(minx + (base_w - w)/2.0, maxy, minx + (base_w + w)/2.0, maxy + h)
            ],
            'bottom': [
                box(minx, miny - h, minx + w, miny),
                box(maxx - w, miny - h, maxx, miny),
                box(minx + (base_w - w)/2.0, miny - h, minx + (base_w + w)/2.0, miny)
            ]
        }
        for s, box_list in placements.items():
            for p in box_list:
                if preferred_sides and s in preferred_sides:
                    primary_candidates.append(p)
                else:
                    secondary_candidates.append(p)
            
    # Try per-candidate validation
    valid_candidates = []
    poly_list = list(existing_polys)
    
    # Helper to check validity and score at placement time
    def evaluate_candidate(cand, loops_list):
        # 1. Check Overlaps
        for existing in loops_list:
            if cand.intersects(existing):
                if cand.intersection(existing).area > 1e-5:
                    return None # Invalid (Overlap)

        # 2. Hard Constraint: Building Envelope Containment Pruning
        if envelope_poly is not None:
            if not is_within_envelope(cand, envelope_poly, tolerance_sqm=0.20):
                return None # REJECT candidate outside envelope
        
        # 3. Calculate Contact Score (Shared Perimeter)
        contact_length = 0
        cand_boundary = cand.boundary
        for existing in loops_list:
            if cand.touches(existing) or cand.intersects(existing):
                common = cand_boundary.intersection(existing.boundary)
                if not common.is_empty:
                    contact_length += common.length

        # 4. Bedroom Exterior Wall Bonus: favor outer boundary for natural light/egress
        if room_type == "bedroom" and envelope_poly is not None:
            ext_edge = cand_boundary.intersection(envelope_poly.boundary)
            if not ext_edge.is_empty and ext_edge.length >= 1.5:
                contact_length += 25.0 # Encourages bedroom exterior wall access
                
        return contact_length

    # Check Primary
    for cand in primary_candidates:
        score = evaluate_candidate(cand, poly_list)
        if score is not None:
            valid_candidates.append((cand, score + 100)) # Bonus for preferred
            
    # Check Secondary (Fallback)
    if not valid_candidates:
        for cand in secondary_candidates:
            score = evaluate_candidate(cand, poly_list)
            if score is not None:
                valid_candidates.append((cand, score))
    
    if not valid_candidates:
        return None
        
    # Sort by Contact Score (Descending) - favors corner filling and compact geometry
    valid_candidates.sort(key=lambda x: x[1], reverse=True)
    return valid_candidates[0][0]

def _place_with_area_constraint(room_type, target_area, base_poly, existing_polys, preferred_sides=None, tolerance=0.15, max_retries=5):
    """
    Place room with area constraint and retry logic for tolerance compliance.
    Returns (polygon, actual_area) or (None, None) if failed.
    """
    for attempt in range(max_retries):
        # Vary aspect ratio slightly on each retry
        base_ratio = 1.5
        variance = 0.3 * (attempt + 1) / max_retries  # Increase variance with retries
        aspect_ratio = _random_aspect_ratio(base_ratio, variance)
        
        # Calculate dimensions from target area and aspect ratio
        width = np.sqrt(target_area * aspect_ratio)
        height = target_area / width
        
        # Try to place the room
        poly = _place_adjacent(base_poly, width, height, existing_polys, preferred_sides)
        
        if poly is not None:
            actual_area = poly.area
            error_pct = abs(actual_area - target_area) / target_area
            
            if error_pct <= tolerance:
                logger.info(f"{room_type}: area {actual_area:.1f} vs target {target_area:.1f} (error {error_pct*100:.1f}%)")
                return poly, actual_area
            else:
                logger.debug(f"{room_type}: area {actual_area:.1f} vs target {target_area:.1f} (error {error_pct*100:.1f}%) - retrying")
    
    logger.warning(f"{room_type}: Failed to meet area tolerance after {max_retries} attempts")
    # Return best effort placement
    poly = _place_adjacent(base_poly, width, height, existing_polys, preferred_sides)
    if poly is not None:
        return poly, poly.area
    return None, None

def _get_external_walls(poly, all_other_polys):
    boundary = poly.boundary
    if all_other_polys:
        other_boundaries = unary_union([p.boundary for p in all_other_polys if not p.is_empty])
    else:
        other_boundaries = Polygon()
    external = boundary.difference(other_boundaries.buffer(1e-6))
    
    segments = []
    if external.is_empty:
        return segments
    if isinstance(external, LineString):
        if external.length > WALL_TOLERANCE:
            segments.append(external)
    elif hasattr(external, 'geoms'):
        for geom in external.geoms:
            if isinstance(geom, LineString) and geom.length > WALL_TOLERANCE:
                segments.append(geom)
    return segments

def _generate_entrance_door(living_room_poly, all_rooms):
    other_rooms = [p for name, p in all_rooms.items() if name != next((k for k in all_rooms if k.startswith("living")), "")]
    external_walls = _get_external_walls(living_room_poly, other_rooms)
    
    if not external_walls:
        return None
    
    valid_walls = [w for w in external_walls if w.length >= ENTRY_DOOR_WIDTH]
    if not valid_walls:
        return None
    
    valid_walls.sort(key=lambda w: w.length, reverse=True)
    best_wall = random.choice(valid_walls[:3])
    t = random.uniform(0.2, 0.8)
    mid_point = best_wall.interpolate(t, normalized=True)
    
    coords = list(best_wall.coords)
    if len(coords) < 2:
        return None
    x1, y1 = coords[0]
    x2, y2 = coords[-1]
    dx, dy = x2 - x1, y2 - y1
    length = (dx**2 + dy**2)**0.5
    if length == 0:
        return None
    
    nx, ny = dx / length, dy / length
    px, py = -ny, nx
    
    door_depth = 0.3
    w = ENTRY_DOOR_WIDTH / 2
    d = door_depth / 2
    
    return Polygon([
        (mid_point.x - nx*w - px*d, mid_point.y - ny*w - py*d),
        (mid_point.x + nx*w - px*d, mid_point.y + ny*w - py*d),
        (mid_point.x + nx*w + px*d, mid_point.y + ny*w + py*d),
        (mid_point.x - nx*w + px*d, mid_point.y - ny*w + py*d),
    ])

def _determine_opening_spec(r1, r2):
    """
    Returns (width, opening_type) where opening_type is 'cased_opening' or 'door'.
    """
    t1 = r1.split("_")[0].lower()
    t2 = r2.split("_")[0].lower()
    pair = {t1, t2}
    if pair == {"living", "kitchen"} or pair == {"living", "dining"} or pair == {"dining", "kitchen"}:
        return CASED_OPENING_WIDTH, "cased_opening"
    if any(k in t1 or k in t2 for k in ["bath", "toilet", "wash", "powder"]):
        return BATH_DOOR_WIDTH, "door"
    return INTERIOR_DOOR_WIDTH, "door"

def _determine_opening_width(r1, r2):
    width, _ = _determine_opening_spec(r1, r2)
    return width

def _filter_topological_doors(valid_adjacency, rooms):
    """
    Enforces architectural privacy and connectivity:
    1. Every bathroom has AT MOST ONE entrance (eliminating pass-through bathrooms).
       - If adjacent to an ensuite bedroom, prioritize connecting to that bedroom.
       - Otherwise, connect to hallway or living room.
    2. Prune duplicate/unnecessary cross-room openings.
    """
    bathroom_rooms = [r for r in rooms.keys() if any(k in r.lower() for k in ["bath", "toilet", "wash", "powder"])]
    assigned_ensuites = set()

    baths_to_pairs = {b: [] for b in bathroom_rooms}
    non_bathroom_pairs = []

    for r1, r2 in valid_adjacency:
        b_in_pair = [b for b in bathroom_rooms if b in (r1, r2)]
        if b_in_pair:
            for b in b_in_pair:
                other = r2 if b == r1 else r1
                baths_to_pairs[b].append((b, other, (r1, r2)))
        else:
            non_bathroom_pairs.append((r1, r2))

    filtered_bathroom_pairs = []
    for b, candidates in baths_to_pairs.items():
        if not candidates:
            continue
        if len(candidates) == 1:
            filtered_bathroom_pairs.append(candidates[0][2])
            continue

        bedroom_cands = [c for c in candidates if "bedroom" in c[1].lower()]
        hall_cands = [c for c in candidates if "hall" in c[1].lower() or "corridor" in c[1].lower()]
        living_cands = [c for c in candidates if "living" in c[1].lower()]

        chosen_cand = None
        for bc in bedroom_cands:
            if bc[1] not in assigned_ensuites:
                chosen_cand = bc
                assigned_ensuites.add(bc[1])
                break

        if not chosen_cand:
            if hall_cands:
                chosen_cand = hall_cands[0]
            elif bedroom_cands:
                chosen_cand = bedroom_cands[0]
            elif living_cands:
                chosen_cand = living_cands[0]
            else:
                chosen_cand = candidates[0]

        filtered_bathroom_pairs.append(chosen_cand[2])
        logger.info(f"Bathroom Privacy: {b} restricted to single entrance via {chosen_cand[1]} (pruned {len(candidates)-1} pass-through candidate(s))")

    return non_bathroom_pairs + filtered_bathroom_pairs

def _get_compact_sides(existing_layouts):
    """
    Determine preferred placement sides to maintain a compact (square-ish) footprint.
    Returns list of sides ['top', 'bottom',...] sorted by preference.
    """
    if not existing_layouts:
        return ['right', 'left', 'top', 'bottom']
        
    # Calculate current bounding box
    minx, miny, maxx, maxy = float('inf'), float('inf'), float('-inf'), float('-inf')
    for poly in existing_layouts.values():
        x0, y0, x1, y1 = poly.bounds
        minx = min(minx, x0)
        miny = min(miny, y0)
        maxx = max(maxx, x1)
        maxy = max(maxy, y1)
        
    width = maxx - minx
    height = maxy - miny
    
    # Heuristic: If Wide, stack Top/Bottom. If Tall, stack Left/Right.
    # Aspect Ratio > 1.2 (Wide) -> Prefer Vertical
    # Aspect Ratio < 0.8 (Tall) -> Prefer Horizontal
    aspect = width / (height + 1e-6)
    
    sides = ['top', 'bottom', 'right', 'left']
    
    if aspect > 1.2:
        return ['top', 'bottom', 'right', 'left']
    elif aspect < 0.8:
        return ['right', 'left', 'top', 'bottom']
    else:
        random.shuffle(sides)
        return sides

def _preferred_partners(room_type: str, layouts: dict, adjacency_pairs: list) -> list:
    partners = []
    for pair in adjacency_pairs or []:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        a, b = pair
        partner_type = None
        if a == room_type:
            partner_type = b
        elif b == room_type:
            partner_type = a

        if partner_type:
            for name in layouts:
                if name.startswith(partner_type + "_") or name == partner_type:
                    partners.append(name)
    return partners

def _try_place_with_soft_constraints(
    room_type: str,
    width: float,
    height: float,
    layouts: dict,
    adjacency_pairs: list,
    envelope_poly=None,
):
    partners = _preferred_partners(room_type, layouts, adjacency_pairs)
    compact_sides = _get_compact_sides(layouts)

    for partner_name in partners:
        if partner_name not in layouts:
            continue
        partner_base_type = partner_name.split("_")[0]
        is_valid, _ = validate_adjacency(room_type, partner_base_type)
        if not is_valid:
            continue

        poly = _place_adjacent(
            layouts[partner_name], 
            width, 
            height, 
            layouts.values(), 
            compact_sides,
            envelope_poly=envelope_poly,
            room_type=room_type
        )
        if poly:
            return poly

    return None

def synthesize_single_floor(spec, config=None):
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    adjacency_pairs = cfg.get("adjacency_pairs", [])
    if cfg.get("RANDOM_SEED") is not None:
        random.seed(cfg["RANDOM_SEED"])
        np.random.seed(cfg["RANDOM_SEED"])
    
    if not spec.get("rooms"):
        raise ValueError("Spec must contain non-empty 'rooms' list")
    
    rooms_by_zone = {k: [] for k in ZONES.keys()}
    rooms_by_zone["other"] = []
    
    for i, room in enumerate(spec["rooms"]):
        r_type = room.get("type")
        area = room.get("area")
        if not r_type or not isinstance(r_type, str):
            raise ValueError(f"Room {i} missing or invalid 'type'")
        if not (isinstance(area, (int, float)) and area > 0):
            raise ValueError(f"Room {i} has invalid area: {area}")
        zone = get_zone(r_type)
        rooms_by_zone[zone].append(room)
    
    layouts = {}
    room_index = {}
    
    print("\n🏗️  Building house with architectural zones:")
    
    # ── ENVELOPE BOUNDS CALCULATION ──────────────────────────────────────
    total_area_sqm = sum(float(r.get("area", 10.0)) for r in spec.get("rooms", []))
    env_info = compute_building_envelope(total_area_sqm, aspect_ratio=1.20, circulation_factor=0.20)
    envelope_poly = env_info["polygon"]
    env_w = env_info["width"]
    env_h = env_info["height"]
    
    # PHASE 1: CORE (LIVING)
    living_rooms = rooms_by_zone["public"]
    core_room = None
    if living_rooms:
        # 1. Primary Living Room (The Hub)
        room = living_rooms[0]
        r_type = room["type"]
        area = float(room["area"])
        width, height = compute_bounded_room_dimensions(r_type, area)
        if random.random() < 0.5:
            width, height = height, width
            
        room_index[r_type] = 1
        room_name = f"{r_type}_1"
        # Place core living room against the front-left exterior wall (x=0, y=0)
        start_x = 0.0
        start_y = 0.0
        poly = box(start_x, start_y, start_x + width, start_y + height)
        layouts[room_name] = poly
        core_room = room_name
        print(f"  🏠 CORE: {room_name} (hub placed at [{start_x:.1f}, {start_y:.1f}])")
        
        core_poly = layouts[core_room]

        # 2. Additional Public Rooms (e.g. Dining)
        for room in living_rooms[1:]:
            r_type = room["type"]
            area = float(room["area"])
            width, height = compute_bounded_room_dimensions(r_type, area)
            if random.random() < 0.5:
                width, height = height, width
            room_index[r_type] = room_index.get(r_type, 0) + 1
            room_name = f"{r_type}_{room_index[r_type]}"
            
            poly = _try_place_with_soft_constraints(
                r_type, width, height, layouts, adjacency_pairs,
                envelope_poly=envelope_poly
            )
            if not poly:
                preferred_sides = _get_compact_sides(layouts)
                poly = _place_adjacent(
                    core_poly, width, height, layouts.values(), preferred_sides,
                    envelope_poly=envelope_poly, room_type=r_type
                )
            if not poly:
                poly = _place_adjacent(
                    core_poly, width, height, layouts.values(), None,
                    envelope_poly=envelope_poly.buffer(1.5), room_type=r_type
                )
            
            if poly:
                layouts[room_name] = poly
                print(f"  🍽️  DINING/PUBLIC: {room_name} (attached to core)")
    
    if not core_room:
        # No explicit living room — try to use any placed room as core anchor.
        if layouts:
            core_room = next(iter(layouts))
            core_poly = layouts[core_room]
            print(f"  ⚠️  No living room in spec — using '{core_room}' as layout anchor")
        else:
            raise ValueError(
                "Cannot synthesize layout: spec contains no placeable rooms. "
                "Add at least one public room (living, dining, or hallway)."
            )
    
    # ── PHASE 1.5: CIRCULATION (Hallway) ──────────────────────────────────
    for room in rooms_by_zone.get("circulation", []):
        r_type = room["type"]
        area   = float(room["area"])
        width, height = compute_bounded_room_dimensions(r_type, area)
        if random.random() < 0.5:
            width, height = height, width
        room_index[r_type] = room_index.get(r_type, 0) + 1
        room_name = f"{r_type}_{room_index[r_type]}"

        poly = _try_place_with_soft_constraints(
            r_type, width, height, layouts, adjacency_pairs,
            envelope_poly=envelope_poly
        )

        if not poly:
            compact_sides = _get_compact_sides(layouts)
            poly = _place_adjacent(
                core_poly, width, height, layouts.values(), compact_sides,
                envelope_poly=envelope_poly, room_type=r_type
            )

        if not poly:
            poly = _place_adjacent(
                core_poly, width, height, layouts.values(), None,
                envelope_poly=envelope_poly, room_type=r_type
            )

        if not poly:
            poly = _place_adjacent(
                core_poly, width, height, layouts.values(), None,
                envelope_poly=envelope_poly.buffer(1.5), room_type=r_type
            )

        if poly:
            layouts[room_name] = poly
            print(f"  🚪 CIRCULATION: {room_name} (spine adjacent to core)")
        else:
            print(f"  ⚠️  CIRCULATION: {room_name} could not be placed — will retry in Phase 6")
    # ────────────────────────────────────────────────────────────────────────
    
    # PHASE 2: KITCHEN
    kitchen_rooms = rooms_by_zone["semi_public"]
    for room in kitchen_rooms:
        r_type = room["type"]
        area = float(room["area"])
        width, height = compute_bounded_room_dimensions(r_type, area)
        if random.random() < 0.5:
            width, height = height, width
        room_index[r_type] = room_index.get(r_type, 0) + 1
        room_name = f"{r_type}_{room_index[r_type]}"
        
        # Priority: Attach to DINING if exists, else Core
        dining_rooms = [r for r in layouts.keys() if "dining" in r]
        
        poly = _try_place_with_soft_constraints(
            r_type, width, height, layouts, adjacency_pairs,
            envelope_poly=envelope_poly
        )
        if not poly and dining_rooms:
            for dining in dining_rooms:
                preferred_sides = _get_compact_sides(layouts)
                poly = _place_adjacent(
                    layouts[dining], width, height, layouts.values(), preferred_sides,
                    envelope_poly=envelope_poly, room_type=r_type
                )
                if poly:
                    print(f"  🍳 SEMI-PUBLIC: {room_name} (attached to {dining})")
                    break
        
        if not poly:
             preferred_sides = _get_compact_sides(layouts)
             poly = _place_adjacent(
                 core_poly, width, height, layouts.values(), preferred_sides[:2],
                 envelope_poly=envelope_poly, room_type=r_type
             )
             if poly:
                 print(f"  🍳 SEMI-PUBLIC: {room_name} (attached to core)")

        if not poly:
             poly = _place_adjacent(
                 core_poly, width, height, layouts.values(), None,
                 envelope_poly=envelope_poly.buffer(1.5), room_type=r_type
             )
        
        if poly:
            layouts[room_name] = poly

    # PHASE 3: BEDROOMS
    bedrooms = rooms_by_zone["private"]
    random.shuffle(bedrooms)
    bedroom_names = []
    circulation_rooms = [r for r in layouts.keys() if "hallway" in r]

    for idx, room in enumerate(bedrooms):
        r_type = room["type"]
        area = float(room["area"])
        width, height = compute_bounded_room_dimensions(r_type, area)
        if random.random() < 0.5:
            width, height = height, width
        room_index[r_type] = room_index.get(r_type, 0) + 1
        room_name = f"{r_type}_{room_index[r_type]}"
        
        preferred_sides = _get_compact_sides(layouts)
        
        poly = _try_place_with_soft_constraints(
            r_type, width, height, layouts, adjacency_pairs,
            envelope_poly=envelope_poly
        )
        
        # Prefer attaching to circulation hallway if available
        if not poly and circulation_rooms:
            for hall in circulation_rooms:
                poly = _place_adjacent(
                    layouts[hall], width, height, layouts.values(), preferred_sides,
                    envelope_poly=envelope_poly, room_type=r_type
                )
                if poly:
                    print(f"  🛏️  PRIVATE: {room_name} (attached to {hall})")
                    break

        if not poly:
            poly = _place_adjacent(
                core_poly, width, height, layouts.values(), preferred_sides[:3],
                envelope_poly=envelope_poly, room_type=r_type
            )
        
        if not poly:
             public_rooms = [r for r in layouts.keys() if "dining" in r or "living" in r]
             for pub in public_rooms:
                 poly = _place_adjacent(
                     layouts[pub], width, height, layouts.values(), preferred_sides,
                     envelope_poly=envelope_poly, room_type=r_type
                 )
                 if poly:
                     print(f"  🛏️  PRIVATE: {room_name} (attached to {pub})")
                     break

        if not poly:
             # Buffer relaxation
             for anchor in list(layouts.keys()):
                 poly = _place_adjacent(
                     layouts[anchor], width, height, layouts.values(), None,
                     envelope_poly=envelope_poly.buffer(2.0), room_type=r_type
                 )
                 if poly:
                     break

        if poly:
            layouts[room_name] = poly
            if r_type == "bedroom":
                bedroom_names.append(room_name)
            print(f"  🛏️  PRIVATE: {room_name} (branch from core/public)")
        else:
            print(f"  ❌ FAILED to place {room_name} (No valid public adjacency)")
    
    # PHASE 4: SERVICES (Bathrooms, Storage, Utility)
    services = rooms_by_zone["service"]
    study_names = [name for name in layouts.keys() if name.startswith("study")]
    bathroom_idx = 0
    
    for idx, room in enumerate(services):
        r_type = room["type"]
        area = float(room["area"])
        width, height = compute_bounded_room_dimensions(r_type, area)
        if random.random() < 0.5:
            width, height = height, width
        room_index[r_type] = room_index.get(r_type, 0) + 1
        room_name = f"{r_type}_{room_index[r_type]}"
        
        poly = _try_place_with_soft_constraints(
            r_type, width, height, layouts, adjacency_pairs,
            envelope_poly=envelope_poly
        )
        
        # Strategy 1: Ensuite Bathroom (attach to corresponding bedroom, or study if bedrooms are full)
        if not poly and r_type == "bathroom":
            target_room = None
            if bathroom_idx < len(bedroom_names):
                target_room = bedroom_names[bathroom_idx]
                bathroom_idx += 1
            elif study_names:
                target_room = study_names[0]
                study_names.pop(0)
                bathroom_idx += 1
                
            if target_room:
                 preferred_sides = _get_compact_sides(layouts)
                 poly = _place_adjacent(
                     layouts[target_room], width, height, layouts.values(), preferred_sides,
                     envelope_poly=envelope_poly, room_type=r_type
                 )
                 if poly:
                     print(f"  🚿 SERVICE: {room_name} (ensuite to {target_room})")

        # Strategy 2: Common Bath / Storage / Utility (plumbing & service clustering)
        if not poly:
            preferred_targets = []
            if r_type == "bathroom":
                # Wet wall clustering: bathroom near other bathrooms or kitchen
                preferred_targets.extend([n for n in layouts if "bathroom" in n])
                preferred_targets.extend([n for n in layouts if "kitchen" in n])
                preferred_targets.extend([n for n in layouts if "hallway" in n])
                preferred_targets.extend([n for n in layouts if "living" in n])
                preferred_targets.extend([n for n in layouts if "study" in n])
            elif r_type in ["storage", "utility", "pantry"]:
                preferred_targets.extend([n for n in layouts if "kitchen" in n])
                preferred_targets.extend([n for n in layouts if "hallway" in n])
                preferred_targets.extend([n for n in layouts if "living" in n])
            else:
                preferred_targets.extend([n for n in layouts if "living" in n])
            
            compact_sides = _get_compact_sides(layouts)
            for target in preferred_targets:
                if target in layouts:
                    poly = _place_adjacent(
                        layouts[target], width, height, layouts.values(), compact_sides,
                        envelope_poly=envelope_poly, room_type=r_type
                    )
                    if poly:
                        print(f"  🔧 SERVICE: {room_name} (attached to {target})")
                        break
        
        # Strategy 3: Envelope contained fallback
        if not poly:
             all_rooms = list(layouts.keys())
             random.shuffle(all_rooms)
             compact_sides = _get_compact_sides(layouts)
             for target in all_rooms:
                 poly = _place_adjacent(
                     layouts[target], width, height, layouts.values(), compact_sides,
                     envelope_poly=envelope_poly, room_type=r_type
                 )
                 if poly:
                     print(f"  🔧 SERVICE: {room_name} (fallback attached to {target})")
                     break

        # Strategy 4: Buffer relaxation fallback
        if not poly:
             all_rooms = list(layouts.keys())
             random.shuffle(all_rooms)
             for target in all_rooms:
                 poly = _place_adjacent(
                     layouts[target], width, height, layouts.values(), None,
                     envelope_poly=envelope_poly.buffer(2.0), room_type=r_type
                 )
                 if poly:
                     print(f"  🔧 SERVICE: {room_name} (buffer fallback attached to {target})")
                     break

        if poly:
            layouts[room_name] = poly
        else:
            print(f"  ❌ FAILED to place {room_name}")
    
    # PHASE 5: OTHER (balcony, etc.)
    for room in rooms_by_zone["other"]:
        r_type = room["type"]
        area = float(room["area"])
        width, height = compute_bounded_room_dimensions(r_type, area)
        if random.random() < 0.5:
            width, height = height, width
        room_index[r_type] = room_index.get(r_type, 0) + 1
        room_name = f"{r_type}_{room_index[r_type]}"
        
        poly = _try_place_with_soft_constraints(
            r_type, width, height, layouts, adjacency_pairs,
            envelope_poly=envelope_poly
        )

        # Balcony prefers living or bedroom
        if not poly and r_type == "balcony":
            targets = [name for name in layouts.keys() if name.startswith("living") or name.startswith("bedroom")]
            for target in targets:
                poly = _place_adjacent(
                    layouts[target], width, height, layouts.values(),
                    envelope_poly=envelope_poly.buffer(1.5), room_type=r_type
                )
                if poly:
                    break
        elif not poly:
            poly = _place_adjacent(
                core_poly, width, height, layouts.values(),
                envelope_poly=envelope_poly.buffer(1.5), room_type=r_type
            )
        
        if poly:
            layouts[room_name] = poly
            print(f"  📦 OTHER: {room_name}")
    
    # PHASE 6: FINAL RETRY (Desperation pass for any unplaced rooms)
    placed_names = set(layouts.keys())
    type_tracker = {}
    for room in spec.get("rooms", []):
        t = room["type"]
        type_tracker[t] = type_tracker.get(t, 0) + 1
        name = f"{t}_{type_tracker[t]}"
        alt_name = t if type_tracker[t] == 1 else "MISSING"
        
        if name not in placed_names and alt_name not in placed_names:
            area = float(room["area"])
            w, h = compute_bounded_room_dimensions(t, area)
            
            all_targets = list(layouts.keys())
            random.shuffle(all_targets)
            for target in all_targets:
                poly = _place_adjacent(
                    layouts[target], w, h, layouts.values(), None,
                    envelope_poly=envelope_poly.buffer(2.5), room_type=t
                )
                if poly:
                    layouts[name] = poly
                    print(f"  🩹 RECOVERED: {name} (Phase 6)")
                    break

    return layouts, envelope_poly

def _validate_room_counts(spec, placed_rooms):
    """
    Soft validation: log warnings when placed room counts differ from the spec,
    but NEVER raise. A layout with a missing hallway or an extra room is still
    a usable layout — the scoring engine will naturally penalise it. Raising
    here causes every candidate to be skipped when one room cannot be placed,
    which produces the 'Failed to generate any valid candidates' error.

    Returns True if everything matched, False if there are any mismatches.
    The caller should log the outcome but generation always continues.
    """
    spec_counts = {}
    for room in spec.get("rooms", []):
        room_type = room.get("type", "").lower()
        if room_type:
            spec_counts[room_type] = spec_counts.get(room_type, 0) + 1

    placed_counts = {}
    for room_name in placed_rooms.keys():
        room_type = room_name.split("_")[0].lower()
        placed_counts[room_type] = placed_counts.get(room_type, 0) + 1

    is_valid = True

    for room_type, spec_count in spec_counts.items():
        placed_count = placed_counts.get(room_type, 0)
        if placed_count != spec_count:
            logger.warning(
                f"Room count mismatch for '{room_type}': "
                f"spec wanted {spec_count}, placed {placed_count}. "
                f"Continuing with partial layout — scoring will reflect this."
            )
            is_valid = False

    for room_type, placed_count in placed_counts.items():
        if room_type not in spec_counts:
            logger.warning(
                f"Unexpected extra room placed: '{room_type}' (count={placed_count}). "
                f"May have been injected by a fallback placement phase."
            )
            is_valid = False

    if is_valid:
        logger.info("Room count validation passed — all rooms placed correctly.")

    return is_valid

def synthesize_layout_from_spec(spec, config=None):
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    rooms, envelope_poly = synthesize_single_floor(spec, config)
    
    # Soft validation: log whether all rooms were placed, but never abort.
    # A partial layout (e.g. hallway couldn't be placed) still gets scored
    # and potentially selected. Raising here caused "Failed to generate any
    # valid candidates" because every candidate was silently discarded.
    is_valid = _validate_room_counts(spec, rooms)
    if not is_valid:
        logger.warning("Proceeding with partial layout — one or more rooms could not be placed.")
    
    adjacency_set = set()
    room_names = list(rooms.keys())
    
    print("\n🔍 Detecting geometric adjacencies:")
    for i, r1 in enumerate(room_names):
        for r2 in room_names[i+1:]:
            poly1 = rooms[r1]
            poly2 = rooms[r2]
            intersection = poly1.boundary.intersection(poly2.boundary)
            if not intersection.is_empty and intersection.length > WALL_TOLERANCE:
                pair = tuple(sorted([r1, r2]))
                adjacency_set.add(pair)
                print(f"  ✅ Geometric: {r1} ↔ {r2}")
    
    valid_adjacency = []
    print("\n🛡️  Applying architectural rules:")
    for r1, r2 in adjacency_set:
        t1 = r1.split("_")[0]
        t2 = r2.split("_")[0]
        is_valid, reason = validate_adjacency(t1, t2)
        if is_valid:
            valid_adjacency.append((r1, r2))
            print(f"  ✅ Allowed: {r1} ↔ {r2} ({reason})")
        else:
            print(f"  ❌ Rejected: {r1} ↔ {r2} ({reason})")
    
    corridors = None
    if valid_adjacency:
        try:
            corridors = generate_corridors(rooms, valid_adjacency)
        except Exception as e:
            print(f"⚠️  Corridor: {e}")
    
    doors = None
    openings_metadata = []
    opening_specs = []
    filtered_adjacency = valid_adjacency

    if valid_adjacency:
        try:
            # 1. Topological filtering: strictly max 1 door per bathroom to prevent pass-through bathrooms
            filtered_adjacency = _filter_topological_doors(valid_adjacency, rooms)
            
            # 2. Assign architectural dimensions and types (cased opening vs door)
            for r1, r2 in filtered_adjacency:
                width, op_type = _determine_opening_spec(r1, r2)
                opening_specs.append((r1, r2, width, op_type))
                
            doors, openings_metadata = generate_doors_with_metadata(rooms, opening_specs)
            if doors:
                print(f"\n🚪 Generated {len(opening_specs)} openings")
                for (a, b, w, o_type) in opening_specs:
                    print(f"   • {a} ↔ {b} ({o_type}, {w}m)")
        except Exception as e:
            print(f"⚠️  Doors: {e}")
            import traceback
            traceback.print_exc()
    
    living_rooms = [name for name in rooms.keys() if name.startswith("living")]
    entrance = None
    if living_rooms:
        print("\n🚪 Placing entrance on true external wall:")
        entrance = _generate_entrance_door(rooms[living_rooms[0]], rooms)
        if entrance:
            doors = unary_union([doors, entrance]) if doors else entrance
            openings_metadata.append({
                "rooms": (living_rooms[0], "exterior"),
                "width": ENTRY_DOOR_WIDTH,
                "type": "entrance",
                "polygon": entrance,
                "wall_length": 0.0,
            })
            print("  ✅ Entrance door placed")
        else:
            print("  ⚠️  Failed to place entrance door")
    
    # Calculate Score
    # Base score 100
    # Penalty for rejected adjacencies
    # Penalty for missing entrance
    
    score = 100
    total_adj = len(adjacency_set)
    valid_adj = len(valid_adjacency)
    
    if total_adj > 0:
        rejected = total_adj - valid_adj
        score -= (rejected * 10) # -10 per bad connection
    
    if not entrance:
        score -= 20
        
    score = max(0, min(100, score))

    # Adjacency satisfaction (soft constraints)
    satisfied = 0
    for pair in cfg.get("adjacency_pairs", []):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        t_a, t_b = pair[0], pair[1]
        for r1, r2 in adjacency_set:
            base1, base2 = r1.split("_")[0], r2.split("_")[0]
            if {base1, base2} == {t_a, t_b}:
                satisfied += 1
                break

    requested_pairs = cfg.get("adjacency_pairs", [])
    adjacency_satisfaction = (satisfied / len(requested_pairs)) if requested_pairs else 1.0
    
    return {
        "rooms": rooms,
        "corridors": corridors,
        "doors": doors,
        "openings": openings_metadata,
        "opening_specs": opening_specs,
        "adjacency": filtered_adjacency,
        "entrance": entrance,
        "score": score,
        "adjacency_satisfaction": adjacency_satisfaction,
        "envelope": envelope_poly,
    }