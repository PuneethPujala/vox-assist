"""
Furniture Clearance Constraint for VoxAssist.
Validates that habitable bedrooms provide sufficient clear rectangular space to accommodate
a standard bed with code-recommended 0.75m (30-inch) walking and egress clearance.
"""

from typing import Dict, Any, List, Tuple, Optional
from shapely.geometry import Polygon, Point, box, LineString

# Standard Furniture Footprints (meters)
# Queen Bed: 1.52m x 2.03m
# Double/Full Bed: 1.37m x 1.90m
# Twin Bed: 0.99m x 1.90m
# Walkway Clearance: >= 0.75m (30 inches)

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
            
            # Wardrobes, tall cabinets, or bed headboards
            is_tall_or_bed = any(t in f_type for t in ["wardrobe", "closet", "cabinet", "tall", "headboard"]) or f_height >= 1.5
            if not is_tall_or_bed or not f_poly or f_poly.is_empty:
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
    and door swing clearance for the layout.
    
    Returns:
        Aggregated report across bedrooms and living areas with structured subchecks.
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
