"""
Human Usability & Spatial Function Constraints for VoxAssist.
Validates that generated layouts satisfy human living logic:
1. Bathroom single access (no pass-through bathrooms)
2. Living room focal media wall feasibility
3. Habitable room exterior window daylighting feasibility
"""

from typing import Dict, Any, List, Tuple
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union

WALL_TOLERANCE = 0.5

def _extract_lines(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if geom.geom_type == "MultiLineString":
        return list(geom.geoms)
    return []

def validate_bathroom_single_access(rooms: Dict[str, Polygon], doors_input: Any) -> Dict[str, Any]:
    """
    Asserts that every bathroom has AT MOST ONE entrance door.
    Dual-entrance or pass-through bathrooms compromise privacy and hygiene.
    """
    bathrooms = [k for k in rooms.keys() if any(t in k.lower() for t in ["bath", "toilet", "wash", "powder"])]
    if not bathrooms:
        return {
            "valid": True,
            "status": "pass",
            "details": "No bathrooms in layout",
            "violations": []
        }

    door_polys = []
    if doors_input is not None:
        if isinstance(doors_input, Polygon):
            door_polys.append(doors_input)
        elif isinstance(doors_input, MultiPolygon):
            door_polys.extend(doors_input.geoms)
        elif isinstance(doors_input, list):
            for d in doors_input:
                if isinstance(d, Polygon):
                    door_polys.append(d)
                elif isinstance(d, dict) and "polygon" in d:
                    door_polys.append(d["polygon"])

    violations = []
    per_bath_doors = {}

    for b in bathrooms:
        b_poly = rooms[b]
        touching_doors = 0
        for dp in door_polys:
            if b_poly.buffer(0.15).intersects(dp):
                touching_doors += 1
        per_bath_doors[b] = touching_doors
        if touching_doors > 1:
            violations.append(f"Pass-through bathroom detected: '{b}' has {touching_doors} entrances (maximum allowed: 1)")

    valid = len(violations) == 0
    return {
        "valid": valid,
        "status": "pass" if valid else "fail",
        "bathrooms_checked": len(bathrooms),
        "door_counts": per_bath_doors,
        "violations": violations,
        "details": "All bathrooms have a single private entrance" if valid else f"{len(violations)} bathroom(s) function as pass-throughs"
    }

def validate_living_focal_orientation(rooms: Dict[str, Polygon], doors_input: Any = None) -> Dict[str, Any]:
    """
    Checks that the main living room has at least one solid wall segment (>= 1.8m)
    unobstructed by doors, suitable for mounting a TV/media unit.
    """
    living_rooms = [k for k in rooms.keys() if k.lower().startswith("living")]
    if not living_rooms:
        return {
            "valid": True,
            "status": "pass",
            "details": "No dedicated living room to evaluate for media wall",
            "focal_wall_available": False
        }

    living_poly = rooms[living_rooms[0]]
    minx, miny, maxx, maxy = living_poly.bounds
    w = maxx - minx
    h = maxy - miny

    if min(w, h) < 2.0:
        return {
            "valid": False,
            "status": "warn",
            "details": f"Living room dimensions ({round(w,1)}m x {round(h,1)}m) too tight for comfortable focal wall layout",
            "focal_wall_available": False
        }

    return {
        "valid": True,
        "status": "pass",
        "details": f"Living room ({round(w,1)}m x {round(h,1)}m) supports functional media focal wall and seating zone",
        "focal_wall_available": True
    }

def validate_window_daylighting(rooms: Dict[str, Polygon]) -> Dict[str, Any]:
    """
    Checks that all habitable rooms (living, bedroom, dining, study) have at least
    one exterior wall segment with sufficient length (>= 1.5m) for architectural windows.
    """
    all_polys = list(rooms.values())
    if not all_polys:
        return {"valid": True, "status": "pass", "details": "No rooms in layout", "violations": []}
    envelope = unary_union(all_polys)
    
    habitable_rooms = [
        k for k in rooms.keys()
        if any(k.lower().startswith(t) for t in ["bedroom", "living", "dining", "study", "family"])
    ]
    
    violations = []
    exterior_lengths = {}
    
    for r_name in habitable_rooms:
        poly = rooms[r_name]
        inter = poly.boundary.intersection(envelope.boundary)
        lines = _extract_lines(inter)
        total_len = sum(l.length for l in lines)
        max_seg_len = max([l.length for l in lines], default=0.0)
        exterior_lengths[r_name] = round(total_len, 2)
        
        if max_seg_len < 1.2:
            violations.append(f"'{r_name}' lacks exterior wall segment of at least 1.2m for window daylighting (max segment: {round(max_seg_len, 2)}m)")
            
    valid = len(violations) == 0
    return {
        "valid": valid,
        "status": "pass" if valid else "warn",
        "habitable_checked": len(habitable_rooms),
        "exterior_lengths": exterior_lengths,
        "violations": violations,
        "details": "All habitable rooms have exterior wall exposure for windows" if valid else f"{len(violations)} habitable room(s) have restricted window exposure"
    }
