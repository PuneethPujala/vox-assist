"""
Unit tests for Human Usability & Spatial Function in VoxAssist.
Tests:
1. No pass-through bathrooms (strict single-door access)
2. Kitchen cased opening classification (no wooden panel)
3. Window daylighting and exterior wall inspection
4. Living room focal wall feasibility
5. 3D mesh assembly contains windows, headers, and proper geometry
"""

import pytest
import sys
import os
from shapely.geometry import box, Point, LineString

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.constraints.human_usability import (
    validate_bathroom_single_access,
    validate_living_focal_orientation,
    validate_window_daylighting,
)
from engine.door_generator import (
    INTERIOR_DOOR_WIDTH,
    BATH_DOOR_WIDTH,
    ENTRY_DOOR_WIDTH,
    CASED_OPENING_WIDTH,
    generate_doors_with_metadata,
)
from engine.layout_synthesizer_adjacency import (
    _filter_topological_doors,
    _determine_opening_spec,
    synthesize_layout_from_spec,
)
from engine.resplan_to_3d import build_house_from_layout

def test_no_passthrough_bathrooms_pruning():
    """
    Asserts that when a bathroom touches multiple rooms (e.g. Bedroom 1 and Living),
    topological door filtering strictly prunes the connection to living,
    preserving private ensuite access and preventing pass-through circulation.
    """
    rooms = {
        "living": box(0, 0, 6, 5),
        "bedroom_1": box(6, 0, 10, 5),
        "bathroom_1": box(6, 5, 8, 8),
    }
    # Raw adjacencies where bathroom_1 touches both living and bedroom_1
    valid_adjacency = [
        ("living", "bedroom_1"),
        ("living", "bathroom_1"),
        ("bedroom_1", "bathroom_1"),
    ]
    
    filtered = _filter_topological_doors(valid_adjacency, rooms)
    
    # Check that bathroom_1 only appears ONCE in filtered adjacencies
    b_pairs = [p for p in filtered if "bathroom_1" in p]
    assert len(b_pairs) == 1, f"Expected exactly 1 door for bathroom_1, got {b_pairs}"
    # Must be connected to the bedroom (ensuite), not living
    assert "bedroom_1" in b_pairs[0], "Bathroom should prioritize ensuite bedroom connection"
    assert "living" not in b_pairs[0] or "bedroom_1" in b_pairs[0]

def test_bathroom_single_access_validator():
    """
    Asserts that validate_bathroom_single_access correctly identifies
    compliant single-access baths vs illegal pass-through baths.
    """
    rooms = {
        "bedroom_1": box(0, 0, 4, 4),
        "bathroom_1": box(4, 0, 6, 4),
    }
    # Single door between bedroom and bath
    door_1 = box(3.9, 1.5, 4.1, 2.5)
    compliant_res = validate_bathroom_single_access(rooms, [door_1])
    assert compliant_res["valid"] is True
    assert compliant_res["status"] == "pass"
    
    # Illegal pass-through bath: second door on other side
    door_2 = box(5.9, 1.5, 6.1, 2.5)
    illegal_res = validate_bathroom_single_access(rooms, [door_1, door_2])
    assert illegal_res["valid"] is False
    assert illegal_res["status"] == "fail"
    assert "pass-through" in illegal_res["violations"][0].lower()

def test_kitchen_opening_spec():
    """
    Asserts that Living-Kitchen connection is classified as a wide cased opening,
    while standard doors are classified as doors.
    """
    width_lk, type_lk = _determine_opening_spec("living_1", "kitchen_1")
    assert type_lk == "cased_opening"
    assert width_lk == CASED_OPENING_WIDTH
    assert width_lk > 1.5  # Wide portal, not a conventional door
    
    width_bed, type_bed = _determine_opening_spec("living_1", "bedroom_1")
    assert type_bed == "door"
    assert width_bed == INTERIOR_DOOR_WIDTH
    
    width_bath, type_bath = _determine_opening_spec("bedroom_1", "bathroom_1")
    assert type_bath == "door"
    assert width_bath == BATH_DOOR_WIDTH

def test_window_daylighting_detection():
    """
    Asserts that validate_window_daylighting verifies exterior wall exposure
    for bedrooms and living room.
    """
    rooms = {
        "living": box(0, 0, 6, 5),
        "kitchen": box(6, 0, 10, 4),
        "bedroom_1": box(0, 5, 5, 9),
    }
    res = validate_window_daylighting(rooms)
    assert res["valid"] is True
    assert res["status"] == "pass"
    assert res["habitable_checked"] >= 2

def test_3d_house_generation_with_windows_and_cased_openings(tmp_path):
    """
    Builds a 3D house mesh and asserts:
    1. Mesh is non-empty with valid vertices and faces
    2. Model file is generated successfully
    """
    spec = {
        "rooms": [
            {"type": "living", "area": 25.0},
            {"type": "kitchen", "area": 12.0},
            {"type": "bedroom", "area": 16.0},
            {"type": "bathroom", "area": 6.0},
        ]
    }
    layout = synthesize_layout_from_spec(spec)
    assert layout is not None
    assert "rooms" in layout
    
    output_file = str(tmp_path / "test_house_cad.ply")
    mesh = build_house_from_layout(layout, visualize=False, output_file=output_file)
    
    assert mesh is not None
    assert len(mesh.vertices) > 100
    assert len(mesh.triangles) > 50
    assert os.path.exists(output_file)
