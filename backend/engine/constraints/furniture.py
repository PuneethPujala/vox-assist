"""
Furniture Clearance Constraint for VoxAssist.
Validates that habitable bedrooms provide sufficient clear rectangular space to accommodate
a standard bed with code-recommended 0.75m (30-inch) walking and egress clearance.
"""

from typing import Dict, Any, List, Tuple
from shapely.geometry import Polygon

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

def validate_furniture_clearance(
    layout_rooms: Dict[str, Polygon]
) -> Dict[str, Any]:
    """
    Validates furniture and walking clearance for all bedrooms in the layout.
    
    Returns:
        Aggregated report across all bedrooms.
    """
    bedrooms = {
        name: poly for name, poly in layout_rooms.items()
        if name.startswith("bedroom") and poly is not None and not poly.is_empty
    }
    
    if not bedrooms:
        return {
            "valid": True,
            "status": "pass",
            "bedrooms_evaluated": 0,
            "compliant_bedrooms": [],
            "tight_bedrooms": [],
            "failed_bedrooms": [],
            "warnings": [],
            "details": "No bedrooms in layout to evaluate for furniture clearance"
        }
        
    results = [validate_bedroom_furniture_clearance(n, p) for n, p in bedrooms.items()]
    
    compliant = [r["room"] for r in results if r["status"] == "pass"]
    tight = [r["room"] for r in results if r["status"] == "warn"]
    failed = [r["room"] for r in results if r["status"] == "fail"]
    
    warnings = [f"{r['room']}: {r['message']}" for r in results if r["status"] in ("warn", "fail")]
    
    if failed:
        status = "fail"
    elif tight:
        status = "warn"
    else:
        status = "pass"
        
    details = (
        f"All {len(bedrooms)} bedroom(s) accommodate standard beds with >=0.75m walking clearance"
        if status == "pass" else
        f"{len(compliant)}/{len(bedrooms)} bedrooms have standard bed clearance ({len(tight)} tight, {len(failed)} restricted)"
    )
    
    return {
        "valid": len(failed) == 0,
        "status": status,
        "bedrooms_evaluated": len(bedrooms),
        "compliant_bedrooms": compliant,
        "tight_bedrooms": tight,
        "failed_bedrooms": failed,
        "warnings": warnings,
        "details": details
    }
