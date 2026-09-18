"""
Egress and Natural Light Access Constraints for VoxAssist.
Verifies that all bedrooms and habitable rooms possess direct exterior wall contact
for natural ventilation, daylight, and fire egress feasibility.
Detects and flags landlocked rooms.
"""

from typing import Dict, Any, Tuple, List
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString
from shapely.ops import unary_union
from .jurisdiction_profiles import get_profile

def get_room_external_walls(
    room_name: str,
    layout_rooms: Dict[str, Polygon]
) -> List[LineString]:
    """
    Computes the true exterior wall segments of a specific room polygon
    by subtracting all adjacent room boundaries.
    """
    poly = layout_rooms.get(room_name)
    if poly is None or poly.is_empty:
        return []
        
    other_polys = [p for k, p in layout_rooms.items() if k != room_name and p and not p.is_empty]
    if not other_polys:
        # Standalone room - all boundaries are external
        boundary = poly.boundary
        if isinstance(boundary, LineString):
            return [boundary]
        elif hasattr(boundary, 'geoms'):
            return list(boundary.geoms)
        return []
        
    other_union = unary_union(other_polys)
    # Epsilon buffer to prevent numerical precision artifacts along touching edges
    exterior_geom = poly.boundary.difference(other_union.buffer(1e-5))
    
    segments = []
    if exterior_geom.is_empty:
        return segments
    elif isinstance(exterior_geom, LineString):
        if exterior_geom.length > 0.05:
            segments.append(exterior_geom)
    elif hasattr(exterior_geom, 'geoms'):
        for g in exterior_geom.geoms:
            if isinstance(g, LineString) and g.length > 0.05:
                segments.append(g)
                
    return segments

def get_room_external_wall_length(
    room_name: str,
    layout_rooms: Dict[str, Polygon]
) -> float:
    """Returns the total exterior wall perimeter length in meters for a room."""
    segments = get_room_external_walls(room_name, layout_rooms)
    return round(sum(s.length for s in segments), 2)

def validate_bedroom_exterior_access(
    layout_rooms: Dict[str, Polygon],
    profile: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Validates that all bedrooms have adequate exterior wall exposure for daylight
    and emergency egress windows.
    
    Returns:
        Dict detailing compliance, exterior wall lengths, and list of violations.
    """
    if profile is None:
        profile = get_profile()
        
    egress_config = profile.get("egress", {})
    min_length = egress_config.get("min_exterior_wall_length", 1.5)
    required_types = egress_config.get("required_rooms", ["bedroom"])
    
    bedrooms = [k for k in layout_rooms.keys() if any(k.startswith(t) for t in required_types)]
    
    if not bedrooms:
        return {
            "valid": True,
            "bedrooms_checked": 0,
            "bedrooms_with_exterior_access": 0,
            "landlocked_bedrooms": [],
            "wall_lengths": {},
            "violations": []
        }
        
    landlocked = []
    wall_lengths = {}
    violations = []
    
    for b_name in bedrooms:
        ext_len = get_room_external_wall_length(b_name, layout_rooms)
        wall_lengths[b_name] = ext_len
        
        if ext_len < 0.1:
            landlocked.append(b_name)
            violations.append(
                f"{b_name} is completely landlocked inside the floorplan with 0m exterior wall contact."
            )
        elif ext_len < min_length:
            landlocked.append(b_name)
            violations.append(
                f"{b_name} has only {ext_len}m exterior wall (minimum {min_length}m required for daylight & egress)."
            )
            
    is_valid = len(violations) == 0
    
    return {
        "valid": is_valid,
        "bedrooms_checked": len(bedrooms),
        "bedrooms_with_exterior_access": len(bedrooms) - len(landlocked),
        "landlocked_bedrooms": landlocked,
        "wall_lengths": wall_lengths,
        "violations": violations
    }
