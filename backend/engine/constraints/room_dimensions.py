"""
Room Dimension and Aspect Ratio Constraints for VoxAssist.
Enforces habitable dimension thresholds and aspect ratio bounds.
Prevents unlivable geometries (e.g. 8ft x 25ft bowling alleys) from being synthesized or deemed valid.
"""

import math
from typing import Dict, Any, Tuple, List
from shapely.geometry import Polygon
from .jurisdiction_profiles import get_profile

def get_room_category(room_name: str) -> str:
    """Extract standard room category from instance name (e.g. 'bedroom_2' -> 'bedroom')."""
    return room_name.split("_")[0].strip().lower()

def validate_room_dimensions(
    room_name: str,
    poly: Polygon,
    profile: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Validates an individual room polygon against minimum area, minimum clear width,
    and aspect ratio thresholds.
    """
    if profile is None:
        profile = get_profile()
        
    dim_rules = profile.get("room_dimensions", {})
    room_type = get_room_category(room_name)
    rules = dim_rules.get(room_type, {
        "min_area": 3.0,
        "min_width": 1.5,
        "max_aspect_ratio": 2.5
    })
    
    if poly is None or poly.is_empty:
        return {
            "room": room_name,
            "type": room_type,
            "valid": False,
            "area": 0.0,
            "width": 0.0,
            "height": 0.0,
            "aspect_ratio": 0.0,
            "violations": ["Room polygon is empty or missing"]
        }
        
    minx, miny, maxx, maxy = poly.bounds
    w = round(maxx - minx, 2)
    h = round(maxy - miny, 2)
    
    min_dim = min(w, h)
    max_dim = max(w, h)
    aspect_ratio = round(max_dim / min_dim, 2) if min_dim > 0.01 else 999.0
    area = round(poly.area, 2)
    
    violations = []
    
    # 1. Area check
    req_min_area = rules.get("min_area", 0.0)
    if req_min_area and area < req_min_area * 0.90:  # Allow 10% relaxation threshold
        violations.append(
            f"Area {area}m² ({int(area*10.764)} sqft) below minimum {req_min_area}m²"
        )
        
    # 2. Width check (narrowest dimension)
    req_min_width = rules.get("min_width", 0.0)
    if req_min_width and min_dim < req_min_width * 0.92: # Allow 8% tolerance
        violations.append(
            f"Clear width {min_dim}m ({round(min_dim*3.28084, 1)}ft) below minimum {req_min_width}m"
        )
        
    # 3. Aspect Ratio check
    req_max_ar = rules.get("max_aspect_ratio", 2.5)
    if aspect_ratio > req_max_ar:
        violations.append(
            f"Aspect ratio {aspect_ratio}:1 exceeds maximum allowable {req_max_ar}:1"
        )
        
    is_valid = len(violations) == 0
    
    return {
        "room": room_name,
        "type": room_type,
        "valid": is_valid,
        "area": area,
        "width": w,
        "height": h,
        "min_dimension": min_dim,
        "aspect_ratio": aspect_ratio,
        "violations": violations
    }

def validate_all_room_dimensions(
    layout_rooms: Dict[str, Polygon],
    profile: Dict[str, Any] = None
) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
    """
    Evaluates all rooms in a layout for dimensional and aspect-ratio compliance.
    
    Returns:
        (all_valid: bool, per_room_results: List[Dict], aggregated_violations: List[str])
    """
    if not layout_rooms:
        return True, [], []
        
    per_room_results = []
    all_violations = []
    
    for name, poly in layout_rooms.items():
        res = validate_room_dimensions(name, poly, profile)
        per_room_results.append(res)
        for v in res["violations"]:
            all_violations.append(f"{name}: {v}")
            
    is_all_valid = len(all_violations) == 0
    return is_all_valid, per_room_results, all_violations

def compute_bounded_room_dimensions(
    room_type: str,
    target_area_sqm: float,
    profile: Dict[str, Any] = None
) -> Tuple[float, float]:
    """
    Generates (width, height) for room synthesis that strictly respects the
    minimum dimension and aspect ratio caps for this room type.
    """
    if profile is None:
        profile = get_profile()
        
    rules = profile.get("room_dimensions", {}).get(room_type, {
        "min_width": 1.5,
        "max_aspect_ratio": 1.8
    })
    
    max_ar = rules.get("max_aspect_ratio", 1.8)
    min_w = rules.get("min_width", 1.5)
    
    # Choose balanced aspect ratio between 1.05 and min(max_ar, 1.4)
    target_ar = min(max_ar, 1.35)
    
    # Calculate initial dimension
    w = math.sqrt(target_area_sqm * target_ar)
    h = target_area_sqm / w
    
    # Enforce minimum dimension
    if min(w, h) < min_w:
        if w < h:
            w = min_w
            h = target_area_sqm / w
        else:
            h = min_w
            w = target_area_sqm / h
            
    # Re-clamp aspect ratio
    current_ar = max(w, h) / min(w, h)
    if current_ar > max_ar:
        narrow = math.sqrt(target_area_sqm / max_ar)
        wide = target_area_sqm / narrow
        w, h = (wide, narrow) if w >= h else (narrow, wide)
        
    return round(w, 2), round(h, 2)
