"""
Unit tests for Circulation Constraints & Protected Geometry Engine in VoxAssist.
Tests:
1. Door approach box generation in front of thresholds.
2. Protected circulation polygon calculation.
3. Dining clearance validation (pass vs door conflict).
4. Spatial reachability testing from main entrance to all rooms.
5. Deliberate entrance placement with front facade priority and corner setbacks.
6. 3D generation with collision-free dining and architectural front entrance styling.
"""

import pytest
import sys
import os
from shapely.geometry import box, Polygon, Point

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.constraints.circulation import (
    generate_door_approach_boxes,
    generate_primary_circulation_spine,
    compute_protected_circulation_polygon,
    validate_dining_circulation_clearance,
    evaluate_circulation_reachability,
    validate_circulation_continuity,
)
from engine.layout_synthesizer_adjacency import (
    _generate_entrance_door,
    synthesize_layout_from_spec,
)
from engine.resplan_to_3d import build_house_from_layout
from engine.validator import validate_layout


def test_door_approach_boxes_generation():
    """Verify door approach boxes extend into connected rooms from doorway thresholds."""
    rooms = {
        "living": box(0, 0, 6, 5),
        "bedroom_1": box(6, 0, 10, 5),
    }
    # Horizontal opening along X = 6
    door_poly = box(5.9, 2.0, 6.1, 2.85)
    openings = [
        {
            "rooms": ("living", "bedroom_1"),
            "width": 0.85,
            "type": "door",
            "polygon": door_poly,
        }
    ]

    boxes = generate_door_approach_boxes(openings, rooms, depth=1.1)
    assert len(boxes) >= 1, "Expected at least one approach clearance box"
    # Clearance boxes must lie inside either living or bedroom_1
    for b in boxes:
        assert rooms["living"].intersects(b) or rooms["bedroom_1"].intersects(b)
        assert b.area > 0.5


def test_dining_circulation_clearance():
    """Asserts that dining table clearance detects safe locations vs doorway blockage."""
    # Create protected circulation zone at (5, 2)
    protected_circ = box(4.8, 1.0, 6.2, 3.5)

    # Candidate 1: Safely away in dining corner (1.5, 3.5)
    res_safe = validate_dining_circulation_clearance(
        table_cx=1.5, table_cy=3.5, table_w=1.2, table_h=0.8,
        protected_circ_poly=protected_circ
    )
    assert res_safe["valid"] is True
    assert res_safe["status"] == "pass"

    # Candidate 2: Blocking doorway at (5.2, 2.2)
    res_blocking = validate_dining_circulation_clearance(
        table_cx=5.2, table_cy=2.2, table_w=1.2, table_h=0.8,
        protected_circ_poly=protected_circ
    )
    assert res_blocking["valid"] is False
    assert res_blocking["status"] == "fail"
    assert len(res_blocking["violations"]) >= 1


def test_circulation_reachability_test():
    """Asserts that reachability correctly identifies unobstructed navigation vs blocked paths."""
    rooms = {
        "living": box(0, 0, 6, 5),
        "bedroom_1": box(6, 0, 10, 5),
        "bathroom_1": box(0, 5, 3, 8),
    }
    openings = [
        {"rooms": ("living", "bedroom_1"), "polygon": box(5.9, 2.0, 6.1, 2.85)},
        {"rooms": ("living", "bathroom_1"), "polygon": box(1.0, 4.9, 1.8, 5.1)},
        {"rooms": ("living", "exterior"), "type": "entrance", "polygon": box(2.5, -0.1, 3.55, 0.1)},
    ]

    # Scenario A: Walkable floor with minimal furniture
    safe_furniture = [
        box(0.2, 0.2, 1.8, 0.6),  # TV unit on south wall
        box(7.0, 1.0, 9.0, 3.0),  # Bed in bedroom_1
    ]
    reach_ok = evaluate_circulation_reachability(rooms, openings, safe_furniture)
    assert reach_ok["reachable"] is True

    # Scenario B: Giant wardrobe placed directly over bedroom_1 doorway threshold
    blocking_furniture = [
        box(5.8, 1.8, 6.5, 3.2),  # Blocks bedroom_1 doorway
    ]
    reach_blocked = evaluate_circulation_reachability(rooms, openings, blocking_furniture)
    assert reach_blocked["reachable"] is False
    assert "bedroom_1" in reach_blocked["unreachable"]


def test_deliberate_entrance_placement():
    """Asserts that entrance is placed on front exterior wall with at least 0.80m corner setback."""
    living = box(0, 0, 8, 6)
    all_rooms = {
        "living": living,
        "kitchen": box(0, 6, 4, 10),
        "bedroom_1": box(4, 6, 8, 10),
    }

    entrance = _generate_entrance_door(living, all_rooms)
    assert entrance is not None
    assert isinstance(entrance, Polygon)
    assert entrance.area > 0.2

    # Verify entrance is on the south exterior wall (y near 0)
    ey = entrance.centroid.y
    assert abs(ey - 0.0) < 0.5, f"Expected entrance on front south facade, got y={ey}"

    # Verify entrance is setback from the corner (x=0 and x=8)
    ex = entrance.centroid.x
    assert ex >= 0.8, f"Entrance too close to left corner: {ex}"
    assert ex <= 7.2, f"Entrance too close to right corner: {ex}"


def test_3d_house_generation_with_circulation_and_front_door(tmp_path):
    """Verifies that 3D CAD mesh generation succeeds with protected circulation and front door styling."""
    spec = {
        "rooms": [
            {"type": "living", "area": 26.0},
            {"type": "kitchen", "area": 12.0},
            {"type": "bedroom", "area": 15.0},
            {"type": "bedroom", "area": 14.0},
            {"type": "bathroom", "area": 6.0},
        ]
    }
    layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 42})
    assert layout is not None

    output_ply = str(tmp_path / "circulation_test_house.ply")
    mesh = build_house_from_layout(layout, visualize=False, output_file=output_ply)

    assert mesh is not None
    assert len(mesh.vertices) > 200
    assert len(mesh.triangles) > 100
    assert os.path.exists(output_ply)

    # Validate architectural checks
    report = validate_layout(layout, envelope_poly=layout.get("envelope"))
    assert report["valid"] is True
    assert report["checks_passed"] >= 6
    assert report["feasibility_score"] >= 80
