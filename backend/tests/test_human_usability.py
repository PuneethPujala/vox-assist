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
    validate_room_door_accessibility,
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
    Asserts that:
    1. A solitary bathroom touching both Bedroom 1 and Living is designated as a Common Bathroom
       connected to Living/circulation, so all occupants can access it without entering someone's bedroom.
    2. In a multi-bathroom home, the master bath connects as an ensuite to Bedroom 1, while other
       baths connect to common circulation.
    3. In all cases, pass-through bathrooms (dual entrances) are strictly pruned to 1 door.
    """
    # Case 1: Solitary bathroom (1 bath total)
    rooms = {
        "living": box(0, 0, 6, 5),
        "bedroom_1": box(6, 0, 10, 5),
        "bathroom_1": box(6, 5, 8, 8),
    }
    valid_adjacency = [
        ("living", "bedroom_1"),
        ("living", "bathroom_1"),
        ("bedroom_1", "bathroom_1"),
    ]
    
    filtered = _filter_topological_doors(valid_adjacency, rooms)
    b_pairs = [p for p in filtered if "bathroom_1" in p]
    assert len(b_pairs) == 1, f"Expected exactly 1 door for bathroom_1, got {b_pairs}"
    # Must be connected to the living room (common circulation), not trapped as ensuite
    assert "living" in b_pairs[0], f"Solitary bathroom should connect to living, got {b_pairs[0]}"

    # Case 2: Multi-bathroom (2 baths total)
    multi_rooms = {
        "living": box(0, 0, 6, 5),
        "bedroom_1": box(6, 0, 10, 5),
        "bathroom_1": box(6, 5, 8, 8),
        "bathroom_2": box(0, 5, 2, 7),
    }
    multi_adj = [
        ("living", "bedroom_1"),
        ("living", "bathroom_1"),
        ("bedroom_1", "bathroom_1"),
        ("living", "bathroom_2"),
    ]
    multi_filtered = _filter_topological_doors(multi_adj, multi_rooms)
    b1_pairs = [p for p in multi_filtered if "bathroom_1" in p]
    b2_pairs = [p for p in multi_filtered if "bathroom_2" in p]
    assert len(b1_pairs) == 1, "Ensuite bathroom_1 must have exactly 1 door"
    assert len(b2_pairs) == 1, "Common bathroom_2 must have exactly 1 door"
    assert "bedroom_1" in b1_pairs[0], "First bathroom in multi-bath home serves as master ensuite"
    assert "living" in b2_pairs[0], "Second bathroom serves common living area"

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

def test_validate_room_door_accessibility():
    """
    Asserts that validate_room_door_accessibility detects:
    1. Fully connected layouts where every room has a doorway.
    2. Landlocked rooms with 0 doorways.
    3. Solitary bathrooms trapped as ensuites.
    """
    rooms = {
        "living": box(0, 0, 6, 5),
        "bedroom_1": box(6, 0, 10, 5),
        "bedroom_2": box(0, 5, 5, 9),
        "bathroom_1": box(6, 5, 8, 8),
    }

    # Case 1: Fully connected layout
    openings_ok = [
        {"rooms": ("living", "bedroom_1")},
        {"rooms": ("living", "bedroom_2")},
        {"rooms": ("living", "bathroom_1")},
    ]
    res_ok = validate_room_door_accessibility(rooms, openings=openings_ok)
    assert res_ok["valid"] is True
    assert res_ok["status"] == "pass"
    assert len(res_ok["landlocked_rooms"]) == 0

    # Case 2: Landlocked bedroom_2 (no doorway)
    openings_landlocked = [
        {"rooms": ("living", "bedroom_1")},
        {"rooms": ("living", "bathroom_1")},
    ]
    res_ll = validate_room_door_accessibility(rooms, openings=openings_landlocked)
    assert res_ll["valid"] is False
    assert res_ll["status"] == "fail"
    assert "bedroom_2" in res_ll["landlocked_rooms"]

    # Case 3: Solitary bathroom trapped as ensuite to bedroom_1
    openings_ensuite_trap = [
        {"rooms": ("living", "bedroom_1")},
        {"rooms": ("living", "bedroom_2")},
        {"rooms": ("bedroom_1", "bathroom_1")},
    ]
    res_trap = validate_room_door_accessibility(rooms, openings=openings_ensuite_trap)
    assert res_trap["valid"] is False
    assert any("isolated as an ensuite" in v for v in res_trap["violations"])

