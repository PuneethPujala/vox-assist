"""
Building Envelope Constraint for VoxAssist.
Defines the boundary polygon within which all generated rooms must sit.
Prevents sprawling tetromino/pinwheel layouts by enforcing a cohesive external envelope.
"""

import math
from typing import Dict, Any, Tuple, List, Optional
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

def compute_building_envelope(
    total_room_area_sqm: float,
    aspect_ratio: float = 1.25,
    circulation_factor: float = 0.15,
    origin_x: float = 0.0,
    origin_y: float = 0.0
) -> Dict[str, Any]:
    """
    Computes a target rectangular building envelope for a given net room area.
    
    Args:
        total_room_area_sqm: Net sum of room areas in square meters.
        aspect_ratio: Width / Depth ratio (typically 1.1 to 1.4 for homes).
        circulation_factor: Extra allowance (15-20%) for walls and corridors.
        origin_x, origin_y: Lower-left coordinate.
        
    Returns:
        Dict containing polygon, width, height, target_area, and bounds.
    """
    if total_room_area_sqm <= 0:
        total_room_area_sqm = 100.0 # fallback default ~1076 sqft
        
    gross_footprint_sqm = total_room_area_sqm * (1.0 + max(0.0, circulation_factor))
    
    # Aspect ratio clamping (1.0 to 1.6)
    ar = max(1.0, min(1.6, aspect_ratio))
    width = math.sqrt(gross_footprint_sqm * ar)
    height = gross_footprint_sqm / width
    
    # Ceil to reasonable 50cm grid steps to ensure full gross allowance
    width = math.ceil(width * 2) / 2.0
    height = math.ceil(height * 2) / 2.0
    
    envelope_poly = box(origin_x, origin_y, origin_x + width, origin_y + height)
    
    return {
        "polygon": envelope_poly,
        "width": width,
        "height": height,
        "gross_area": envelope_poly.area,
        "bounds": envelope_poly.bounds,  # (minx, miny, maxx, maxy)
    }

def is_within_envelope(
    room_poly: Polygon,
    envelope_poly: Polygon,
    tolerance_sqm: float = 0.25
) -> bool:
    """
    Checks whether an individual room polygon is contained within the building envelope.
    Allows a small numerical tolerance for floating point edge intersections.
    """
    if room_poly is None or room_poly.is_empty:
        return True
    if envelope_poly is None or envelope_poly.is_empty:
        return True
        
    overflow = room_poly.difference(envelope_poly)
    return overflow.area <= tolerance_sqm

def validate_envelope_containment(
    layout_rooms: Dict[str, Polygon],
    envelope_poly: Polygon,
    tolerance_sqm: float = 0.50
) -> Tuple[bool, float, List[str]]:
    """
    Validates that all rooms in a synthesized layout sit cleanly within the envelope.
    
    Returns:
        (all_contained: bool, overflow_area_sqm: float, list_of_overflowing_rooms: List[str])
    """
    if not layout_rooms or envelope_poly is None:
        return True, 0.0, []
        
    overflowing_rooms = []
    total_overflow = 0.0
    
    # Practical tolerance: max of 0.5 sqm or 1.5% of envelope area
    effective_tolerance = max(tolerance_sqm, envelope_poly.area * 0.015)
    
    for name, poly in layout_rooms.items():
        if poly is None or poly.is_empty:
            continue
        overflow = poly.difference(envelope_poly)
        if overflow.area > effective_tolerance:
            overflowing_rooms.append(name)
            total_overflow += overflow.area
            
    is_valid = len(overflowing_rooms) == 0
    return is_valid, round(total_overflow, 2), overflowing_rooms
