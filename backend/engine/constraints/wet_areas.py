"""
Wet-Area & Plumbing Proximity Constraint for VoxAssist.
Evaluates plumbing efficiency and clustering among wet rooms (Kitchen, Bathrooms, Utility).
Clustering wet rooms minimizes plumbing pipe runs, reduces material costs, and improves hot water delivery.
"""

from typing import Dict, Any, List, Tuple
from shapely.geometry import Polygon

WET_ROOM_TYPES = {"bathroom", "kitchen", "utility", "laundry", "pantry"}

def is_wet_room(room_name: str) -> bool:
    room_type = room_name.split("_")[0].lower()
    return room_type in WET_ROOM_TYPES

def validate_wet_area_clustering(
    layout_rooms: Dict[str, Polygon],
    max_acceptable_run_m: float = 9.0,
    preferred_cluster_run_m: float = 6.0
) -> Dict[str, Any]:
    """
    Evaluates whether wet rooms are grouped efficiently or scattered across the floor plan.
    
    Args:
        layout_rooms: Dict mapping room names to Shapely Polygons.
        max_acceptable_run_m: Distance beyond which a plumbing fixture is considered isolated.
        preferred_cluster_run_m: Distance within which wet areas share an efficient plumbing zone.
        
    Returns:
        Dict detailing wet room count, shared walls, distances, and isolated outliers.
    """
    wet_rooms = {
        name: poly for name, poly in layout_rooms.items()
        if is_wet_room(name) and poly is not None and not poly.is_empty
    }
    
    wet_count = len(wet_rooms)
    if wet_count <= 1:
        return {
            "valid": True,
            "status": "pass",
            "wet_rooms_count": wet_count,
            "shared_wet_walls": 0,
            "avg_distance_m": 0.0,
            "max_distance_m": 0.0,
            "isolated_rooms": [],
            "warnings": [],
            "details": f"Single wet room ({list(wet_rooms.keys())[0] if wet_rooms else 'none'}) requires no clustering"
        }
        
    names = list(wet_rooms.keys())
    shared_walls_count = 0
    pairwise_distances: List[float] = []
    min_distances: Dict[str, float] = {n: float("inf") for n in names}
    
    for i, r1 in enumerate(names):
        poly1 = wet_rooms[r1]
        c1 = poly1.centroid
        for r2 in names[i+1:]:
            poly2 = wet_rooms[r2]
            c2 = poly2.centroid
            
            # Check shared boundary (back-to-back or adjacent wet walls)
            shared = poly1.boundary.intersection(poly2.boundary)
            if not shared.is_empty and shared.length >= 0.5:
                shared_walls_count += 1
                
            dist = c1.distance(c2)
            pairwise_distances.append(dist)
            min_distances[r1] = min(min_distances[r1], dist)
            min_distances[r2] = min(min_distances[r2], dist)
            
    avg_dist = round(sum(pairwise_distances) / max(1, len(pairwise_distances)), 1)
    max_dist = round(max(pairwise_distances), 1) if pairwise_distances else 0.0
    
    isolated = [name for name, d in min_distances.items() if d > max_acceptable_run_m]
    scattered = [name for name, d in min_distances.items() if d > preferred_cluster_run_m]
    
    warnings = []
    if isolated:
        warnings.append(
            f"Plumbing runs exceed {max_acceptable_run_m}m for isolated wet room(s): {', '.join(isolated)}"
        )
    elif scattered:
        warnings.append(
            f"Plumbing runs exceed preferred {preferred_cluster_run_m}m for: {', '.join(scattered)}"
        )
        
    # Status: 'pass' if well-clustered or sharing walls, 'warn' if extended runs, 'fail' if completely isolated (>12m)
    if isolated:
        status = "fail" if any(min_distances[n] > 12.0 for n in isolated) else "warn"
    elif scattered and shared_walls_count == 0:
        status = "warn"
    else:
        status = "pass"
        
    details = (
        f"{wet_count} wet rooms clustered (avg distance {avg_dist}m; "
        f"{shared_walls_count} shared wet-wall{'s' if shared_walls_count != 1 else ''})"
    )
    
    return {
        "valid": status != "fail",
        "status": status,
        "wet_rooms_count": wet_count,
        "shared_wet_walls": shared_walls_count,
        "avg_distance_m": avg_dist,
        "max_distance_m": max_dist,
        "isolated_rooms": isolated,
        "warnings": warnings,
        "details": details
    }
