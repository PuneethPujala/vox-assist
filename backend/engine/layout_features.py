import numpy as np
from shapely.geometry import Polygon

def extract_layout_features(layout):
    """
    Extract geometric features from a layout dictionary.
    
    Args:
        layout (dict): Dictionary containing "rooms" (dict of Polygons) and optional "doors".
        
    Returns:
        dict: Geometric features (total_area, exterior_exposure, avg_distance, room_count).
    """
    rooms = layout.get("rooms", {})
    if not rooms:
        return {
            "total_area": 0,
            "exterior_exposure": 0,
            "avg_distance": 0,
            "room_count": 0
        }

    total_area = sum(poly.area for poly in rooms.values())
    
    exterior_exposure = 0
    room_centers = {}
    
    # Calculate simple exterior exposure (perimeter summation)
    # A improved version would check which walls are actually external (using unary_union),
    # but for now we follow the requested logic which approximates it via perimeter.
    # Note: Using properly unioned boundary is better for "exterior", but sum of perimeters 
    # proxies "surface area" which correlates with cost/daylight potential.
    
    # Calculate footprint and convex hull for Efficiency
    bbox_area = 0
    convex_hull_area = 0
    
    from shapely.ops import unary_union
    try:
        all_polys = [p for p in rooms.values() if not p.is_empty]
        if all_polys:
            union_poly = unary_union(all_polys)
            total_area = union_poly.area # Use actual union area (dedup overlaps)
            
            convex_hull = union_poly.convex_hull
            convex_hull_area = convex_hull.area
            
            exterior_exposure = union_poly.boundary.length
    except:
        # Fallback if union fails
        convex_hull_area = total_area * 1.2 # Approx
        exterior_exposure = sum(poly.length for poly in rooms.values())

    # Connectivity Metric (Average Graph Distance)
    for name, poly in rooms.items():
        if not poly.is_empty:
            center = poly.centroid
            room_centers[name] = np.array([center.x, center.y])

    names = list(room_centers.keys())
    dist_sum = 0
    count = 0
    
    if len(names) > 1:
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                d = np.linalg.norm(room_centers[names[i]] - room_centers[names[j]])
                dist_sum += d
                count += 1
        avg_distance = dist_sum / max(count, 1)
    else:
        avg_distance = 0

    features = {
        "total_area": round(total_area, 2),
        "convex_hull_area": round(convex_hull_area, 2),
        "exterior_exposure": round(exterior_exposure, 2),
        "avg_distance": round(avg_distance, 2),
        "room_count": len(rooms)
    }

    return features
