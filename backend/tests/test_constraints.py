"""
Unit tests for architectural constraints:
- Envelope containment
- Room dimensions & aspect ratios (specifically checking the 8x25ft pathological case)
- Bedroom exterior-wall detection (specifically checking landlocked bedrooms)
"""

import pytest
import sys
import os
from shapely.geometry import box, Polygon

# Ensure backend and engine are importable
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.constraints.envelope import compute_building_envelope, is_within_envelope, validate_envelope_containment
from engine.constraints.room_dimensions import validate_room_dimensions, compute_bounded_room_dimensions
from engine.constraints.egress import validate_bedroom_exterior_access, get_room_external_wall_length

def test_envelope_computation_and_containment():
    # 100 sqm net area -> with 15% circulation = 115 gross sqm
    env = compute_building_envelope(100.0, aspect_ratio=1.25, circulation_factor=0.15)
    env_poly = env["polygon"]
    
    assert env["width"] > 0
    assert env["height"] > 0
    assert env_poly.area >= 110.0
    
    # A room completely inside the envelope
    inside_room = box(1.0, 1.0, 4.0, 4.0)
    assert is_within_envelope(inside_room, env_poly) is True
    
    # A room that spills outside the envelope boundary
    minx, miny, maxx, maxy = env_poly.bounds
    spilling_room = box(maxx - 1.0, 0, maxx + 5.0, 4.0)
    assert is_within_envelope(spilling_room, env_poly) is False
    
    # Layout validation
    layout = {
        "living": box(0, 0, 4, 4),
        "bedroom_1": spilling_room
    }
    is_valid, overflow, bad_rooms = validate_envelope_containment(layout, env_poly)
    assert is_valid is False
    assert "bedroom_1" in bad_rooms
    assert overflow > 0

def test_room_dimensions_normal_bedroom_passes():
    # Standard comfortable bedroom: 3.5m x 4.0m = 14.0 sqm (Aspect ratio 1.14)
    good_bedroom = box(0, 0, 3.5, 4.0)
    res = validate_room_dimensions("bedroom_1", good_bedroom)
    
    assert res["valid"] is True
    assert res["width"] == 3.5
    assert res["height"] == 4.0
    assert res["aspect_ratio"] == 1.14
    assert len(res["violations"]) == 0

def test_room_dimensions_pathological_8x25ft_fails():
    # 8ft x 25ft = ~2.44m x 7.62m = 18.6 sqm (200 sqft)
    # This was the exact pathological bowling-alley case called out in the prompt!
    narrow_bedroom = box(0, 0, 2.44, 7.62)
    res = validate_room_dimensions("bedroom_1", narrow_bedroom)
    
    assert res["valid"] is False
    # Violates minimum width (2.44m < 2.8m)
    # Violates aspect ratio (3.12:1 > 1.6:1)
    violations_str = " ".join(res["violations"])
    assert "Clear width" in violations_str
    assert "Aspect ratio" in violations_str

def test_compute_bounded_room_dimensions_clamps_aspect_ratio():
    # Target 18.6 sqm bedroom (200 sqft)
    w, h = compute_bounded_room_dimensions("bedroom", 18.6)
    
    min_dim = min(w, h)
    max_dim = max(w, h)
    ar = max_dim / min_dim
    
    # Must respect min_width of 2.8m and aspect ratio <= 1.6
    assert min_dim >= 2.8
    assert ar <= 1.6

def test_egress_exterior_bedroom_passes():
    # Layout where bedroom sits on the edge of the house
    layout = {
        "living": box(0, 0, 5, 5),
        "bedroom_1": box(5, 0, 9, 4), # Touches living on x=5, right/top/bottom are exterior
        "kitchen": box(0, 5, 4, 8)
    }
    
    ext_len = get_room_external_wall_length("bedroom_1", layout)
    assert ext_len >= 8.0 # Top (4m) + Right (4m) + Bottom (4m) = 12m exterior
    
    egress_res = validate_bedroom_exterior_access(layout)
    assert egress_res["valid"] is True
    assert egress_res["bedrooms_with_exterior_access"] == 1
    assert len(egress_res["landlocked_bedrooms"]) == 0

def test_egress_pathological_landlocked_bedroom_fails():
    # Construct a layout where bedroom_1 is surrounded on all 4 sides:
    # bedroom_1 is at (4, 4) to (8, 8)
    # west: (0, 3) to (4, 9)
    # east: (8, 3) to (12, 9)
    # south: (3, 0) to (9, 4)
    # north: (3, 8) to (9, 12)
    layout = {
        "bedroom_1": box(4, 4, 8, 8),
        "living": box(0, 3, 4, 9),    # Blocks west
        "dining": box(8, 3, 12, 9),   # Blocks east
        "kitchen": box(3, 0, 9, 4),   # Blocks south
        "storage": box(3, 8, 9, 12)   # Blocks north
    }
    
    ext_len = get_room_external_wall_length("bedroom_1", layout)
    assert ext_len == 0.0 # Completely landlocked!
    
    egress_res = validate_bedroom_exterior_access(layout)
    assert egress_res["valid"] is False
    assert "bedroom_1" in egress_res["landlocked_bedrooms"]
    assert "landlocked" in egress_res["violations"][0]

def test_wet_area_clustering_adjacent_passes():
    from engine.constraints.wet_areas import validate_wet_area_clustering
    # Kitchen and Bathroom share a common wall (x=4)
    layout = {
        "kitchen": box(0, 0, 4, 3),
        "bathroom_1": box(4, 0, 6, 3),
        "living": box(0, 3, 6, 7)
    }
    res = validate_wet_area_clustering(layout)
    assert res["valid"] is True
    assert res["status"] == "pass"
    assert res["shared_wet_walls"] == 1
    assert res["avg_distance_m"] <= 4.0

def test_furniture_clearance_generous_bedroom_passes():
    from engine.constraints.furniture import validate_bedroom_furniture_clearance, validate_furniture_clearance
    # 3.6m x 4.2m bedroom
    bed = box(0, 0, 3.6, 4.2)
    res = validate_bedroom_furniture_clearance("bedroom_1", bed)
    assert res["status"] == "pass"
    
    all_res = validate_furniture_clearance({"bedroom_1": bed})
    assert all_res["valid"] is True
    assert all_res["status"] == "pass"

def test_furniture_clearance_narrow_slit_fails():
    from engine.constraints.furniture import validate_bedroom_furniture_clearance
    # 2.0m x 7.0m narrow room (cannot fit standard bed with walking clearance)
    slit = box(0, 0, 2.0, 7.0)
    res = validate_bedroom_furniture_clearance("bedroom_1", slit)
    assert res["status"] == "fail"

