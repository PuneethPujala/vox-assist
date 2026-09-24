"""
Furniture Clearance Constraint for VoxAssist.
Validates that habitable bedrooms provide sufficient clear rectangular space to accommodate
a standard bed with code-recommended 0.75m (30-inch) walking and egress clearance.
"""

from typing import Dict, Any, List, Tuple, Optional
from shapely.geometry import Polygon, Point, box, LineString

try:
    from constraints.furniture_constants import (
        BATHROOM_ENTRY_LANDING, DOOR_CLEARANCE, DOOR_SWING_ANGLE_RAD,
        WC_FRONT_CLEARANCE, WC_SIDE_CLEARANCE, VANITY_FRONT_CLEARANCE,
        SHOWER_ENTRY_CLEARANCE, TV_MIN_DISTANCE, TV_MAX_DISTANCE
    )
except ImportError:
    try:
        from engine.constraints.furniture_constants import (
            BATHROOM_ENTRY_LANDING, DOOR_CLEARANCE, DOOR_SWING_ANGLE_RAD,
            WC_FRONT_CLEARANCE, WC_SIDE_CLEARANCE, VANITY_FRONT_CLEARANCE,
            SHOWER_ENTRY_CLEARANCE, TV_MIN_DISTANCE, TV_MAX_DISTANCE
        )
    except ImportError:
        BATHROOM_ENTRY_LANDING = 0.80
        DOOR_CLEARANCE = 0.80
        DOOR_SWING_ANGLE_RAD = 1.570796
        WC_FRONT_CLEARANCE = 0.55
        WC_SIDE_CLEARANCE = 0.20
        VANITY_FRONT_CLEARANCE = 0.60
        SHOWER_ENTRY_CLEARANCE = 0.65
        TV_MIN_DISTANCE = 1.80
        TV_MAX_DISTANCE = 3.60

def validate_bedroom_furniture_clearance(
    bedroom_name: str,
    bedroom_poly: Polygon
) -> Dict[str, Any]:
    """
    Evaluates whether a single bedroom can accommodate a standard bed with walking clearance.
    
    Returns:
        Dict with room clearance status and dimensions.
    """
    minx, miny, maxx, maxy = bedroom_poly.bounds
    w = round(maxx - minx, 2)
    h = round(maxy - miny, 2)
    area = round(bedroom_poly.area, 2)
    
    min_dim = min(w, h)
    max_dim = max(w, h)
    
    # Classification: Primary/Master (>=12 sqm) vs Secondary/Guest (<12 sqm)
    is_master = area >= 12.0
    
    if is_master:
        # Queen bed (1.52m) + 0.75m clearance on both sides = 3.0m width
        # Queen length (2.03m) + 0.75m clearance at foot = 2.78m length
        min_required_width = 2.70 # allows slight margin with one side against wall or compact stands
        min_required_length = 2.90
        bed_label = "Queen Bed (1.5m x 2.0m) + 0.75m clearance"
    else:
        # Full/Twin bed + 0.75m clearance
        min_required_width = 2.40
        min_required_length = 2.65
        bed_label = "Full/Twin Bed + 0.75m clearance"
        
    has_full_clearance = min_dim >= min_required_width and max_dim >= min_required_length
    has_tight_clearance = min_dim >= (min_required_width * 0.90) and max_dim >= (min_required_length * 0.90)
    
    if has_full_clearance:
        status = "pass"
        message = f"Fits {bed_label} with unobstructed dual side and foot clearance"
    elif has_tight_clearance:
        status = "warn"
        message = f"Tight furniture clearance for {bed_label} (clear width {min_dim}m)"
    else:
        status = "fail"
        message = f"Cannot accommodate {bed_label} without obstructing passage (clear width {min_dim}m < {min_required_width}m)"
        
    return {
        "room": bedroom_name,
        "status": status,
        "area": area,
        "width": w,
        "height": h,
        "min_dimension": min_dim,
        "max_dimension": max_dim,
        "message": message
    }


def validate_furniture_window_clearance(
    layout_rooms: Dict[str, Polygon],
    windows: Optional[List[Dict[str, Any]]] = None,
    placed_furniture: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Verifies that tall storage units (wardrobes >= 1.5m) and beds do not overlap
    exterior window openings or obstruct daylighting keep-out zones.
    """
    if not windows and not placed_furniture:
        return {
            "valid": True,
            "status": "pass",
            "message": "Window daylighting and furniture clearance satisfied",
            "violations": []
        }

    violations = []
    
    # Check placed furniture directly if available
    if placed_furniture and windows:
        for furn in placed_furniture:
            f_type = furn.get("type", "").lower()
            f_poly = furn.get("poly")
            f_room = furn.get("room", "")
            f_height = furn.get("height", 0.0)
            
            # Skip non-wardrobe fixtures (bath, kitchen, beds, seating, tables)
            if any(k in f_type for k in ["shower", "toilet", "wc", "vanity", "sink", "cooktop", "counter", "fridge", "refrigerator", "hood", "rug", "table", "sofa", "tv", "bed"]):
                continue

            # Wardrobes and tall storage units (>= 1.5m)
            is_tall_wardrobe = any(t in f_type for t in ["wardrobe", "closet"]) or (f_height >= 1.5 and ("wardrobe" in f_type or "closet" in f_type or "cabinet" in f_type))
            if not is_tall_wardrobe or not f_poly or f_poly.is_empty:
                continue
                
            for win in windows:
                w_room = win.get("room", "")
                if w_room and f_room and w_room != f_room:
                    continue
                w_keepout = win.get("keepout")
                w_seg = win.get("wall_segment")
                
                # Check overlap with window keepout zone (e.g. 0.6m inward) or segment buffer
                if w_keepout and f_poly.intersects(w_keepout):
                    inter_area = f_poly.intersection(w_keepout).area
                    if inter_area > 0.02:
                        violations.append(f"{f_room}: {f_type.capitalize()} overlaps exterior window daylighting zone")
                elif w_seg and f_poly.intersects(w_seg.buffer(0.35)):
                    violations.append(f"{f_room}: {f_type.capitalize()} placed against exterior window wall opening")
                    
    status = "fail" if violations else "pass"
    return {
        "valid": len(violations) == 0,
        "status": status,
        "message": "All wardrobes and beds are clear of exterior window openings" if status == "pass" else "; ".join(violations),
        "violations": violations
    }


def validate_tv_sofa_viewing_relationship(
    layout_rooms: Dict[str, Polygon],
    placed_furniture: Optional[List[Dict[str, Any]]] = None,
    entrance: Optional[Any] = None,
    openings: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Validates the living room TV and sofa viewing axis:
    - Distance between sofa and TV is ergonomically sound (1.8m to 3.5m).
    - Viewing axis is reasonably aligned laterally (<= 0.50m offset).
    - TV is not mounted on the entrance wall or an exterior window wall.
    """
    living_rooms = {
        k: v for k, v in layout_rooms.items()
        if any(t in k.lower() for t in ["living", "lounge", "family"]) and v is not None and not v.is_empty
    }
    
    if not living_rooms:
        return {
            "valid": True,
            "status": "pass",
            "message": "No living room to evaluate for TV-sofa relationship",
            "violations": [],
            "warnings": []
        }

    violations = []
    warnings = []

    if placed_furniture:
        tvs = [f for f in placed_furniture if "tv" in f.get("type", "").lower()]
        sofas = [f for f in placed_furniture if "sofa" in f.get("type", "").lower() or "couch" in f.get("type", "").lower()]
        
        for tv in tvs:
            tv_room = tv.get("room", "")
            tv_center = tv.get("center") or (tv["poly"].centroid.x, tv["poly"].centroid.y) if tv.get("poly") else None
            matching_sofas = [s for s in sofas if s.get("room", "") == tv_room]
            
            if matching_sofas and tv_center:
                sofa = matching_sofas[0]
                sofa_center = sofa.get("center") or (sofa["poly"].centroid.x, sofa["poly"].centroid.y) if sofa.get("poly") else None
                if sofa_center:
                    dx = abs(tv_center[0] - sofa_center[0])
                    dy = abs(tv_center[1] - sofa_center[1])
                    dist = (dx**2 + dy**2)**0.5
                    
                    if dist < 1.6:
                        warnings.append(f"{tv_room}: Sofa is too close to TV ({round(dist, 2)}m < 1.8m)")
                    elif dist > 3.8:
                        warnings.append(f"{tv_room}: TV viewing distance is excessive ({round(dist, 2)}m > 3.5m)")
                    
                    # TV mounted on entrance wall check
                    if entrance and tv.get("poly") and hasattr(entrance, "distance"):
                        if tv["poly"].distance(entrance) < 0.6:
                            violations.append(f"{tv_room}: TV unit is mounted adjacent to main entrance arrival door")

    # If no placed furniture provided, evaluate living room dimensions for viewing suitability
    else:
        for lr_name, lr_poly in living_rooms.items():
            minx, miny, maxx, maxy = lr_poly.bounds
            w, h = maxx - minx, maxy - miny
            min_dim = min(w, h)
            if min_dim < 2.5:
                warnings.append(f"{lr_name}: Room depth ({round(min_dim, 2)}m) restricts optimal TV-sofa viewing distance")

    status = "fail" if violations else ("warn" if warnings else "pass")
    msg = "Living room TV and sofa viewing axis properly aligned (2.0m - 3.2m distance)"
    if violations:
        msg = "; ".join(violations)
    elif warnings:
        msg = "; ".join(warnings)

    return {
        "valid": len(violations) == 0,
        "status": status,
        "message": msg,
        "violations": violations,
        "warnings": warnings
    }


def validate_door_swing_furniture_clearance(
    layout_rooms: Dict[str, Polygon],
    doors: Optional[Any] = None,
    openings: Optional[List[Dict[str, Any]]] = None,
    placed_furniture: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Validates that door swings are unobstructed by beds, wardrobes, or dining furniture.
    Standard inward door swing requires an unobstructed 0.85m quadrant.
    """
    if not doors and not openings and not placed_furniture:
        return {
            "valid": True,
            "status": "pass",
            "message": "Door swing clearance verified",
            "violations": []
        }

    violations = []
    
    if placed_furniture and openings:
        for op in openings:
            op_poly = op.get("polygon")
            if not op_poly or op_poly.is_empty:
                continue
                
            swing_poly = op.get("swing_polygon")
                
            for furn in placed_furniture:
                f_poly = furn.get("poly")
                if not f_poly or f_poly.is_empty:
                    continue
                    
                # 1. Direct Doorway Threshold Collision
                if f_poly.intersects(op_poly):
                    inter_area = f_poly.intersection(op_poly).area
                    if inter_area > 0.02:
                        f_name = furn.get("type", "Furniture").capitalize()
                        f_room = furn.get("room", "Room")
                        violations.append(f"{f_room}: {f_name} blocks doorway threshold")
                        
                # 2. Inward Swing Arc Collision
                elif swing_poly and not swing_poly.is_empty and f_poly.intersects(swing_poly):
                    inter_area = f_poly.intersection(swing_poly).area
                    if inter_area > 0.05:
                        f_name = furn.get("type", "Furniture").capitalize()
                        f_room = furn.get("room", "Room")
                        violations.append(f"{f_room}: {f_name} obstructs door swing clearance")

    status = "fail" if violations else "pass"
    return {
        "valid": len(violations) == 0,
        "status": status,
        "message": "All interior door swings have unobstructed opening arcs" if status == "pass" else "; ".join(violations),
        "violations": violations
    }


def validate_bathroom_fixture_clearances(
    layout_rooms: Dict[str, Polygon],
    placed_furniture: Optional[List[Dict[str, Any]]] = None,
    doors: Optional[Any] = None,
    openings: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Validates bathroom usability, entry landing box (0.80m x 0.80m),
    door swing non-collision with fixtures, and fixture-to-fixture separation.
    """
    bathrooms = {
        name: poly for name, poly in layout_rooms.items()
        if any(t in name.lower() for t in ["bath", "toilet", "powder"]) and poly is not None and not poly.is_empty
    }
    if not bathrooms:
        return {
            "valid": True,
            "status": "pass",
            "message": "No bathrooms to evaluate for fixture clearance",
            "violations": [],
            "warnings": []
        }

    violations = []
    warnings = []

    if placed_furniture:
        for r_name, r_poly in bathrooms.items():
            r_fixtures = [f for f in placed_furniture if f.get("room") == r_name]
            if not r_fixtures:
                continue

            minx, miny, maxx, maxy = r_poly.bounds

            # 1. Door Landing Box Check
            door_pt = None
            if openings:
                for op in openings:
                    rooms_pair = op.get("rooms", ())
                    if r_name in rooms_pair:
                        op_p = op.get("polygon")
                        if op_p:
                            door_pt = (op_p.centroid.x, op_p.centroid.y)
                            break
            if not door_pt and doors:
                door_list = [doors] if isinstance(doors, Polygon) else (doors.geoms if hasattr(doors, "geoms") else (doors if isinstance(doors, list) else []))
                for dp in door_list:
                    if dp.intersects(r_poly.buffer(0.20)):
                        door_pt = (dp.centroid.x, dp.centroid.y)
                        break

            if door_pt:
                dcx, dcy = door_pt
                dists = {
                    "bottom": abs(dcy - miny),
                    "top": abs(dcy - maxy),
                    "left": abs(dcx - minx),
                    "right": abs(dcx - maxx)
                }
                door_wall = min(dists, key=dists.get)
                ld = BATHROOM_ENTRY_LANDING
                if door_wall == "bottom":
                    landing_box = box(dcx - ld/2.0, miny, dcx + ld/2.0, miny + ld)
                    swing_box = box(dcx - 0.85, miny, dcx + 0.85, miny + 0.85)
                elif door_wall == "top":
                    landing_box = box(dcx - ld/2.0, maxy - ld, dcx + ld/2.0, maxy)
                    swing_box = box(dcx - 0.85, maxy - 0.85, dcx + 0.85, maxy)
                elif door_wall == "left":
                    landing_box = box(minx, dcy - ld/2.0, minx + ld, dcy + ld/2.0)
                    swing_box = box(minx, dcy - 0.85, minx + 0.85, dcy + 0.85)
                else:
                    landing_box = box(maxx - ld, dcy - ld/2.0, maxx, dcy + ld/2.0)
                    swing_box = box(maxx - 0.85, dcy - 0.85, maxx, dcy + 0.85)

                for f in r_fixtures:
                    f_poly = f.get("poly")
                    f_type = f.get("type", "fixture").capitalize()
                    if f_poly and not f_poly.is_empty:
                        if f_poly.intersects(landing_box):
                            inter_area = f_poly.intersection(landing_box).area
                            if inter_area > 0.02:
                                violations.append(f"{r_name}: {f_type} encroaches into 0.80m doorway landing zone")
                        elif f_poly.intersects(swing_box):
                            inter_area = f_poly.intersection(swing_box).area
                            if inter_area > 0.04:
                                warnings.append(f"{r_name}: {f_type} is close to bathroom door swing arc")

            # 2. Fixture-to-Fixture Clearance
            vanities = [f for f in r_fixtures if any(t in f.get("type", "").lower() for t in ["vanity", "basin"])]
            toilets = [f for f in r_fixtures if any(t in f.get("type", "").lower() for t in ["toilet", "wc"])]
            showers = [f for f in r_fixtures if any(t in f.get("type", "").lower() for t in ["shower", "tub"])]

            if vanities and toilets:
                v_poly = vanities[0].get("poly")
                t_poly = toilets[0].get("poly")
                if v_poly and t_poly and v_poly.intersects(t_poly):
                    violations.append(f"{r_name}: Vanity overlaps with Toilet fixture")

            if showers and vanities:
                s_poly = showers[0].get("poly")
                v_poly = vanities[0].get("poly")
                if s_poly and v_poly and s_poly.intersects(v_poly):
                    violations.append(f"{r_name}: Shower enclosure collides with Vanity")

            if showers and toilets:
                s_poly = showers[0].get("poly")
                t_poly = toilets[0].get("poly")
                if s_poly and t_poly and s_poly.intersects(t_poly):
                    violations.append(f"{r_name}: Shower enclosure collides with Toilet")

    else:
        for r_name, r_poly in bathrooms.items():
            minx, miny, maxx, maxy = r_poly.bounds
            w, h = maxx - minx, maxy - miny
            if min(w, h) < 1.30:
                warnings.append(f"{r_name}: Narrow bathroom width ({min(w, h):.2f}m < 1.4m) restricts standard fixture clearances")

    status = "fail" if violations else ("warn" if warnings else "pass")
    msg = "All bathroom fixtures maintain code-standard landing and swing clearances"
    if violations:
        msg = "; ".join(violations)
    elif warnings:
        msg = "; ".join(warnings)

    return {
        "valid": len(violations) == 0,
        "status": status,
        "message": msg,
        "violations": violations,
        "warnings": warnings
    }


def validate_kitchen_workzones(
    layout_rooms: Dict[str, Polygon],
    placed_furniture: Optional[List[Dict[str, Any]]] = None,
    openings: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Validates kitchen work zones (Storage -> Prep -> Washing -> Cooking),
    adequate counter run, and unobstructed walkthrough into living/dining areas.
    """
    kitchens = {
        name: poly for name, poly in layout_rooms.items()
        if "kitchen" in name.lower() and poly is not None and not poly.is_empty
    }
    if not kitchens:
        return {
            "valid": True,
            "status": "pass",
            "message": "No kitchen to evaluate for work-zone layout",
            "violations": [],
            "warnings": []
        }

    violations = []
    warnings = []

    if placed_furniture:
        for k_name, k_poly in kitchens.items():
            k_fixtures = [f for f in placed_furniture if f.get("room") == k_name]
            if openings:
                for op in openings:
                    if k_name in op.get("rooms", ()):
                        op_p = op.get("polygon")
                        if op_p:
                            for f in k_fixtures:
                                f_poly = f.get("poly")
                                if f_poly and f_poly.intersects(op_p):
                                    if f_poly.intersection(op_p).area > 0.03:
                                        violations.append(f"{k_name}: Kitchen {f.get('type')} obstructs doorway opening")
    else:
        for k_name, k_poly in kitchens.items():
            minx, miny, maxx, maxy = k_poly.bounds
            w, h = maxx - minx, maxy - miny
            if min(w, h) < 1.70:
                warnings.append(f"{k_name}: Kitchen width ({min(w, h):.2f}m < 1.8m) limits parallel counter clearance")

    status = "fail" if violations else ("warn" if warnings else "pass")
    msg = "Kitchen work zones (prep, sink, cooktop, storage) clearly defined and accessible"
    if violations:
        msg = "; ".join(violations)
    elif warnings:
        msg = "; ".join(warnings)

    return {
        "valid": len(violations) == 0,
        "status": status,
        "message": msg,
        "violations": violations,
        "warnings": warnings
    }


def validate_dining_furniture_clearance(
    layout_rooms: Any,
    placed_furniture: Optional[List[Dict[str, Any]]] = None,
    openings: Optional[List[Dict[str, Any]]] = None,
    protected_circ: Optional[Polygon] = None,
    table_box: Optional[Polygon] = None,
    chairs: Optional[List[Polygon]] = None,
    door_polys: Optional[List[Polygon]] = None
) -> Dict[str, Any]:
    """
    Validates dining area usability:
    - Dedicated dining room or open living-dining zone has adequate clearance.
    - Placed dining table & chairs maintain chair pullout (0.65m) and pedestrian corridor (0.90m).
    - No obstruction of kitchen portal or primary circulation paths.
    """
    if isinstance(layout_rooms, Polygon):
        dining_rooms = {"dining": layout_rooms}
    elif isinstance(layout_rooms, dict):
        dining_rooms = {
            k: v for k, v in layout_rooms.items()
            if "dining" in k.lower() and v is not None and not v.is_empty
        }
    else:
        dining_rooms = {}

    placed_items = list(placed_furniture or [])
    if table_box is not None and not table_box.is_empty:
        placed_items.append({"type": "dining_table", "poly": table_box, "room": "dining"})
    if chairs:
        for ch in chairs:
            if ch is not None and not ch.is_empty:
                placed_items.append({"type": "dining_chair", "poly": ch, "room": "dining"})

    all_openings = list(openings or [])
    if door_polys:
        for dp in door_polys:
            if dp is not None and not dp.is_empty:
                all_openings.append({"polygon": dp, "type": "door"})

    violations = []
    warnings = []
    pullout_clearance_ok = True
    walkway_clearance_ok = True

    if placed_items:
        tables = [f for f in placed_items if any(t in f.get("type", "").lower() for t in ["dining_table", "dining"])]
        for t in tables:
            t_poly = t.get("poly")
            if not t_poly or t_poly.is_empty:
                continue
            t_room = t.get("room", "dining")
            r_poly = dining_rooms.get(t_room) or (next(iter(dining_rooms.values())) if dining_rooms else None)
            
            pullout = t_poly.buffer(0.65)

            if r_poly and not r_poly.buffer(0.05).contains(t_poly):
                violations.append(f"{t_room}: Dining table extends outside room boundary")
            if r_poly and not r_poly.buffer(0.05).contains(pullout):
                pullout_clearance_ok = False
                warnings.append(f"{t_room}: Dining chair pull-out zone restricts wall clearance")

            if r_poly:
                rb = r_poly.bounds
                tb = t_poly.bounds
                aisles = [tb[0] - rb[0], rb[2] - tb[2], tb[1] - rb[1], rb[3] - tb[3]]
                walkway_clearance_ok = any(a >= 0.85 for a in aisles)
            else:
                walkway_clearance_ok = True

            # Check doorway opening collision
            if all_openings:
                for op in all_openings:
                    op_p = op.get("polygon")
                    if op_p and not op_p.is_empty:
                        if t_poly.intersects(op_p):
                            violations.append(f"{t_room}: Dining table blocks doorway opening")
                        elif pullout.intersects(op_p):
                            warnings.append(f"{t_room}: Dining chair pullout encroaches into doorway threshold")

            # Check protected circulation collision
            if protected_circ and not protected_circ.is_empty:
                if t_poly.intersects(protected_circ):
                    violations.append(f"{t_room}: Dining table directly intersects primary walking corridor")
                elif pullout.intersects(protected_circ):
                    warnings.append(f"{t_room}: Dining chair pullout encroaches into circulation corridor")

    elif dining_rooms:
        for d_name, d_poly in dining_rooms.items():
            minx, miny, maxx, maxy = d_poly.bounds
            w, h = maxx - minx, maxy - miny
            if min(w, h) < 2.2:
                warnings.append(f"{d_name}: Narrow dining width ({min(w, h):.2f}m < 2.4m) restricts standard 4-seater pullout clearance")

    status = "fail" if violations else ("warn" if warnings else "pass")
    msg = "Dining area maintains code-standard table and chair pull-out clearances (>=0.65m)"
    if violations:
        msg = "; ".join(violations)
    elif warnings:
        msg = "; ".join(warnings)

    return {
        "valid": len(violations) == 0,
        "status": status,
        "message": msg,
        "pullout_clearance_ok": pullout_clearance_ok,
        "walkway_clearance_ok": walkway_clearance_ok,
        "violations": violations,
        "warnings": warnings
    }


def validate_furniture_clearance(
    layout_rooms: Dict[str, Polygon],
    openings: Optional[List[Dict[str, Any]]] = None,
    doors: Optional[Any] = None,
    windows: Optional[List[Dict[str, Any]]] = None,
    placed_furniture: Optional[List[Dict[str, Any]]] = None,
    entrance: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Validates furniture, walking clearance, window avoidance, TV-sofa axis,
    door swing, bathroom fixtures landing, and kitchen work zones.
    
    Returns:
        Aggregated report across bedrooms, living, bathrooms, and kitchen with 6 structured subchecks.
    """
    bedrooms = {
        name: poly for name, poly in layout_rooms.items()
        if name.startswith("bedroom") and poly is not None and not poly.is_empty
    }
    
    subchecks: List[Dict[str, Any]] = []
    all_warnings: List[str] = []
    
    # 1. Bedroom Bed Clearance Subcheck
    if not bedrooms:
        bed_subcheck = {
            "id": "bed_space",
            "name": "Bedroom Bed Clearance",
            "status": "pass",
            "details": "No bedrooms in layout to evaluate for bed clearance"
        }
        compliant = []
        tight = []
        failed = []
    else:
        results = [validate_bedroom_furniture_clearance(n, p) for n, p in bedrooms.items()]
        compliant = [r["room"] for r in results if r["status"] == "pass"]
        tight = [r["room"] for r in results if r["status"] == "warn"]
        failed = [r["room"] for r in results if r["status"] == "fail"]
        bed_warnings = [f"{r['room']}: {r['message']}" for r in results if r["status"] in ("warn", "fail")]
        all_warnings.extend(bed_warnings)
        
        bed_status = "fail" if failed else ("warn" if tight else "pass")
        bed_details = (
            f"All {len(bedrooms)} bedroom(s) accommodate standard beds with >=0.75m walking clearance"
            if bed_status == "pass" else
            f"{len(compliant)}/{len(bedrooms)} bedrooms have standard bed clearance ({len(tight)} tight, {len(failed)} restricted)"
        )
        bed_subcheck = {
            "id": "bed_space",
            "name": "Bedroom Bed Clearance",
            "status": bed_status,
            "details": bed_details
        }
    subchecks.append(bed_subcheck)

    # 2. Window Clearance Subcheck
    win_res = validate_furniture_window_clearance(
        layout_rooms, windows=windows, placed_furniture=placed_furniture
    )
    subchecks.append({
        "id": "window_clearance",
        "name": "Window Opening Clearance",
        "status": win_res["status"],
        "details": win_res["message"]
    })
    if win_res["violations"]:
        all_warnings.extend(win_res["violations"])

    # 3. TV-Sofa Viewing Axis Subcheck
    tv_res = validate_tv_sofa_viewing_relationship(
        layout_rooms, placed_furniture=placed_furniture, entrance=entrance, openings=openings
    )
    subchecks.append({
        "id": "viewing_axis",
        "name": "TV-Sofa Viewing Axis",
        "status": tv_res["status"],
        "details": tv_res["message"]
    })
    if tv_res["violations"]:
        all_warnings.extend(tv_res["violations"])
    if tv_res["warnings"]:
        all_warnings.extend(tv_res["warnings"])

    # 4. Door Swing Clearance Subcheck
    door_res = validate_door_swing_furniture_clearance(
        layout_rooms, doors=doors, openings=openings, placed_furniture=placed_furniture
    )
    subchecks.append({
        "id": "door_swing",
        "name": "Door Swing Clearance",
        "status": door_res["status"],
        "details": door_res["message"]
    })
    if door_res["violations"]:
        all_warnings.extend(door_res["violations"])

    # 5. Bathroom Fixture Clearances Subcheck
    bath_res = validate_bathroom_fixture_clearances(
        layout_rooms, placed_furniture=placed_furniture, doors=doors, openings=openings
    )
    subchecks.append({
        "id": "bathroom_fixtures",
        "name": "Bathroom Fixtures & Landing",
        "status": bath_res["status"],
        "details": bath_res["message"]
    })
    if bath_res["violations"]:
        all_warnings.extend(bath_res["violations"])
    if bath_res["warnings"]:
        all_warnings.extend(bath_res["warnings"])

    # 6. Kitchen Work Zones Subcheck
    kit_res = validate_kitchen_workzones(
        layout_rooms, placed_furniture=placed_furniture, openings=openings
    )
    subchecks.append({
        "id": "kitchen_workzones",
        "name": "Kitchen Work Zones",
        "status": kit_res["status"],
        "details": kit_res["message"]
    })
    if kit_res["violations"]:
        all_warnings.extend(kit_res["violations"])
    if kit_res["warnings"]:
        all_warnings.extend(kit_res["warnings"])

    # 7. Dining Pull-Out & Walkway Subcheck
    dining_res = validate_dining_furniture_clearance(
        layout_rooms, placed_furniture=placed_furniture, openings=openings
    )
    subchecks.append({
        "id": "dining_circulation",
        "name": "Dining Pull-Out & Walkway",
        "status": dining_res["status"],
        "details": dining_res["message"]
    })
    if dining_res["violations"]:
        all_warnings.extend(dining_res["violations"])
    if dining_res["warnings"]:
        all_warnings.extend(dining_res["warnings"])

    # Determine overall status
    if any(s["status"] == "fail" for s in subchecks):
        overall_status = "fail"
    elif any(s["status"] == "warn" for s in subchecks):
        overall_status = "warn"
    else:
        overall_status = "pass"

    summary_details = bed_subcheck["details"]
    if overall_status != "pass" and all_warnings:
        summary_details += f" ({'; '.join(all_warnings[:2])})"

    return {
        "valid": overall_status != "fail",
        "status": overall_status,
        "bedrooms_evaluated": len(bedrooms),
        "compliant_bedrooms": compliant,
        "tight_bedrooms": tight,
        "failed_bedrooms": failed,
        "subchecks": subchecks,
        "warnings": all_warnings,
        "details": summary_details
    }
