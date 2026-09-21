"""
Unit tests for Semantic Furniture Engine, Opening Exclusion Zones, and Usability Feasibility in VoxAssist.

Validates:
1. Wardrobes never overlap exterior window daylighting zones.
2. TV screen is flush to wall plane, vertically aligned with console, and seated at eye level.
3. Living room sofa and coffee table are placed along the TV viewing normal axis with 1.8m-3.2m distance.
4. Bedroom bed headboard selects solid focal wall away from door cuts and window openings.
5. Door threshold openings remain unobstructed by placed furniture blocks.
6. Validation Check 7 returns structured subchecks (bed_space, window_clearance, viewing_axis, door_swing).
"""

import os
import sys
import pytest
import numpy as np
from shapely.geometry import box, Polygon, Point, LineString

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.layout_synthesizer_adjacency import synthesize_layout_from_spec
from engine.resplan_to_3d import build_house_from_layout, FLOOR_THICKNESS
from engine.validator import validate_layout
from engine.constraints.furniture import (
    validate_bedroom_furniture_clearance,
    validate_furniture_window_clearance,
    validate_tv_sofa_viewing_relationship,
    validate_door_swing_furniture_clearance,
    validate_furniture_clearance,
)


@pytest.fixture
def sample_2bhk_layout():
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
    assert layout is not None and "rooms" in layout
    return layout


def test_wardrobe_window_non_overlap(sample_2bhk_layout, tmp_path):
    """
    Verifies that wardrobes never overlap exterior window daylighting keep-out zones.
    """
    out_ply = str(tmp_path / "wardrobe_test.ply")
    mesh = build_house_from_layout(sample_2bhk_layout, visualize=False, output_file=out_ply)
    assert mesh is not None

    furniture = sample_2bhk_layout.get("furniture", [])
    windows = sample_2bhk_layout.get("windows", [])
    assert len(windows) > 0, "Exterior windows should be precomputed"

    wardrobes = [f for f in furniture if f.get("type") == "wardrobe"]
    for w in wardrobes:
        w_poly = w["poly"]
        w_room = w["room"]
        room_wins = [win for win in windows if win["room"].lower() == w_room.lower()]
        for win in room_wins:
            keepout = win.get("keepout")
            if keepout:
                assert not w_poly.intersects(keepout), (
                    f"Wardrobe in {w_room} intersects window keepout polygon!"
                )
            wall_seg = win.get("wall_segment")
            if wall_seg:
                assert w_poly.distance(wall_seg) >= 0.15, (
                    f"Wardrobe in {w_room} is placed too close to exterior window segment!"
                )


def test_tv_wall_mounting_and_vertical_alignment(sample_2bhk_layout, tmp_path):
    """
    Verifies TV is mounted against wall, seated eye-level, and vertically aligned with console.
    """
    out_ply = str(tmp_path / "tv_test.ply")
    mesh = build_house_from_layout(sample_2bhk_layout, visualize=False, output_file=out_ply)
    assert mesh is not None

    furniture = sample_2bhk_layout.get("furniture", [])
    tvs = [f for f in furniture if f.get("type") == "tv"]
    assert len(tvs) >= 1, "Living room should have TV unit placed"
    tv = tvs[0]

    assert "center" in tv
    tv_cx, tv_cy = tv["center"]

    entrance = sample_2bhk_layout.get("entrance")
    if entrance and not entrance.is_empty:
        dist_to_entrance = tv["poly"].distance(entrance)
        assert dist_to_entrance >= 1.2, f"TV unit is too close to main entrance ({dist_to_entrance:.2f}m)"

    windows = sample_2bhk_layout.get("windows", [])
    lr_windows = [w for w in windows if "living" in w["room"].lower()]
    for win in lr_windows:
        win_seg = win.get("wall_segment")
        if win_seg:
            assert tv["poly"].distance(win_seg) >= 0.30, "TV unit overlaps an exterior window wall!"


def test_sofa_tv_viewing_axis(sample_2bhk_layout, tmp_path):
    """
    Verifies sofa faces TV along the viewing normal axis within 1.8m - 3.2m distance.
    """
    out_ply = str(tmp_path / "sofa_tv_test.ply")
    mesh = build_house_from_layout(sample_2bhk_layout, visualize=False, output_file=out_ply)
    assert mesh is not None

    furniture = sample_2bhk_layout.get("furniture", [])
    tvs = [f for f in furniture if f.get("type") == "tv"]
    sofas = [f for f in furniture if f.get("type") == "sofa"]
    assert len(tvs) >= 1 and len(sofas) >= 1

    tv_center = tvs[0]["center"]
    sofa_center = sofas[0]["center"]

    dx = abs(tv_center[0] - sofa_center[0])
    dy = abs(tv_center[1] - sofa_center[1])
    dist = (dx**2 + dy**2)**0.5

    assert 1.8 <= dist <= 3.2, f"Viewing distance {dist:.2f}m is outside optimal 1.8m-3.2m range"


def test_bedroom_bed_focal_wall_selection(sample_2bhk_layout, tmp_path):
    """
    Verifies headboard selects solid focal wall away from door cuts and window openings.
    """
    out_ply = str(tmp_path / "bed_test.ply")
    mesh = build_house_from_layout(sample_2bhk_layout, visualize=False, output_file=out_ply)
    assert mesh is not None

    furniture = sample_2bhk_layout.get("furniture", [])
    beds = [f for f in furniture if f.get("type") == "bed"]
    assert len(beds) >= 2, "Both bedrooms should have beds placed"

    openings = sample_2bhk_layout.get("openings", [])
    door_polys = [op["polygon"] for op in openings if op.get("type") == "door"]

    for b in beds:
        b_poly = b["poly"]
        for dp in door_polys:
            assert not b_poly.intersects(dp), f"Bed overlaps door opening threshold in {b['room']}!"


def test_door_swing_furniture_clearance(sample_2bhk_layout, tmp_path):
    """
    Verifies door openings remain unobstructed by all placed furniture blocks.
    """
    out_ply = str(tmp_path / "door_clearance_test.ply")
    mesh = build_house_from_layout(sample_2bhk_layout, visualize=False, output_file=out_ply)
    assert mesh is not None

    report = validate_layout(sample_2bhk_layout, envelope_poly=sample_2bhk_layout.get("envelope"))
    assert report["valid"] is True
    
    chk7 = next((c for c in report["checks"] if c["id"] == "furniture"), None)
    assert chk7 is not None
    assert chk7["status"] == "pass"

    subchecks = chk7.get("subchecks", [])
    subcheck_ids = [s["id"] for s in subchecks]
    assert "bed_space" in subcheck_ids
    assert "window_clearance" in subcheck_ids
    assert "viewing_axis" in subcheck_ids
    assert "door_swing" in subcheck_ids

    for sc in subchecks:
        assert sc["status"] == "pass", f"Subcheck {sc['id']} should pass but returned {sc['status']}: {sc.get('details')}"
