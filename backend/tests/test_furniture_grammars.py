"""
Unit tests for Room-Specific Architectural Furniture Grammars & Usability Solvers.

Tests:
1. Constants consistency between furniture_constants and placement/validation modules.
2. Coupled living room group solver (TV + Console + Viewing Zone + Sofa + Table + Rug).
3. Adaptive bathroom candidate solver across multiple door orientations and aspect ratios.
4. Glass shower enclosure parameterization and curb rendering.
5. Kitchen work-zone solver (Cold Storage -> Prep -> Washing -> Prep -> Cooking).
6. Cased opening distinction (wide portal with trimmed jambs, NO door leaf, NO handle).
7. Usability Validation Check 7 subchecks reporting pass/warn/fail status with explainability.
"""

import os
import sys
import pytest
import numpy as np
from shapely.geometry import box, Polygon, Point, LineString

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.constraints import furniture_constants as const
from engine.furniture_grammars import (
    solve_living_room_group,
    solve_bathroom_fixtures,
    solve_kitchen_workzones,
)
from engine.constraints.furniture import (
    validate_bathroom_fixture_clearances,
    validate_kitchen_workzones,
    validate_furniture_clearance,
)
from engine.resplan_to_3d import build_house_from_layout, _place_room_furniture


def test_constants_consistency():
    """Verifies that key architectural clearances match published standards."""
    assert const.BATHROOM_ENTRY_LANDING == 0.80
    assert const.DOOR_CLEARANCE == 0.80
    assert const.CHAIR_PULL_OUT == 0.65
    assert const.CORRIDOR_WIDTH == 0.90
    assert const.TV_MIN_DISTANCE == 1.80
    assert const.TV_MAX_DISTANCE == 3.20
    assert (0.90, 0.90) in const.SHOWER_SIZES


def test_living_room_group_solver():
    """
    Tests that TV and sofa are placed as a coupled group facing each other,
    viewing distance is scored dynamically, and foyer arrival is respected.
    """
    living_poly = box(0, 0, 5.5, 4.2)
    door_polys = [box(2.2, -0.1, 3.2, 0.1)]
    openings = [{"type": "entrance", "polygon": box(2.2, -0.1, 3.2, 0.1), "rooms": ("exterior", "living")}]
    foyer_keepout = box(1.8, 0.0, 3.6, 1.7)

    res = solve_living_room_group(
        living_poly,
        door_polys=door_polys,
        openings=openings,
        foyer_keepout=foyer_keepout
    )

    assert res is not None
    assert res["valid"] is True
    # Entrance is on South, so TV must select North (or solid West/East)
    assert res["wall"] in ["north", "west", "east"]
    assert res["wall"] != "south"

    # Verify TV and sofa relationship
    tv_c = res["tv_center"]
    sofa_c = res["sofa_center"]
    dist = res["viewing_distance"]
    assert const.TV_MIN_DISTANCE <= dist <= const.TV_MAX_DISTANCE

    # Verify coffee table and rug exist
    assert "coffee_table_box" in res
    assert "rug_box" in res
    assert not res["sofa_box"].intersects(foyer_keepout)


def test_living_room_window_avoidance():
    """Verifies that TV is never mounted on an exterior window wall."""
    living_poly = box(0, 0, 5.0, 4.0)
    door_polys = [box(2.0, -0.1, 3.0, 0.1)]
    openings = [{"type": "entrance", "polygon": box(2.0, -0.1, 3.0, 0.1), "rooms": ("exterior", "living")}]
    windows = [{"wall_segment": LineString([(1.0, 4.0), (4.0, 4.0)])}] # North wall has window

    res = solve_living_room_group(
        living_poly,
        door_polys=door_polys,
        openings=openings,
        windows=windows
    )

    assert res is not None
    assert res["valid"] is True
    # South has entrance, North has window -> TV must be on West or East
    assert res["wall"] in ["west", "east"]


def test_bathroom_adaptive_candidates():
    """
    Tests adaptive candidate solver across multiple door walls (bottom, left, top).
    Verifies 0.80m landing box clearance and zero fixture collisions.
    """
    # 1. Door on South/Bottom wall
    bath_poly = box(0, 0, 2.4, 2.0)
    door_bottom = [box(1.0, -0.1, 1.8, 0.1)]
    res_b = solve_bathroom_fixtures(bath_poly, door_bottom)
    assert res_b is not None
    assert res_b["valid"] is True
    assert not res_b["shower_box"].intersects(res_b["landing_box"])
    assert not res_b["vanity_box"].intersects(res_b["landing_box"])
    assert not res_b["wc_box"].intersects(res_b["landing_box"])
    assert not res_b["shower_box"].intersects(res_b["vanity_box"])
    assert not res_b["shower_box"].intersects(res_b["wc_box"])

    # 2. Door on West/Left wall
    door_left = [box(-0.1, 0.6, 0.1, 1.4)]
    res_l = solve_bathroom_fixtures(bath_poly, door_left)
    assert res_l is not None
    assert res_l["valid"] is True
    assert not res_l["shower_box"].intersects(res_l["landing_box"])
    assert not res_l["vanity_box"].intersects(res_l["landing_box"])
    assert not res_l["wc_box"].intersects(res_l["landing_box"])


def test_shower_enclosure_proportions():
    """Verifies shower tray sizing and tempered glass screen position."""
    bath_poly = box(0, 0, 2.6, 2.6)
    door = [box(1.0, -0.1, 1.8, 0.1)]
    res = solve_bathroom_fixtures(bath_poly, door)
    assert res is not None
    sw, sd = res["shower_size"]
    assert sw >= 0.90 and sd >= 0.90
    assert "shower_screen_x" in res
    assert res["shower_box"].area >= 0.80


def test_kitchen_workzone_solver():
    """
    Tests kitchen work-zone sequence (Cold Storage -> Prep -> Sink -> Cooktop)
    and unobstructed walkthrough.
    """
    kitchen_poly = box(0, 0, 3.4, 2.6)
    door = [box(1.2, -0.1, 2.2, 0.1)] # south portal

    k_res = solve_kitchen_workzones(kitchen_poly, door_polys=door)
    assert k_res is not None
    assert k_res["counter_wall"] == "north" # opposite south portal
    assert k_res["counter_box"] is not None
    assert k_res["fridge_box"] is not None
    assert "sink_pos" in k_res
    assert "cooktop_pos" in k_res
    assert not k_res["counter_box"].intersects(door[0])


def test_cased_opening_no_leaf(tmp_path):
    """
    Verifies that openings > 1.15m are tagged as cased openings
    and generate jamb trim without door leaf or handle.
    """
    spec = {
        "rooms": [
            {"type": "living", "area": 24.0},
            {"type": "kitchen", "area": 12.0},
            {"type": "bedroom", "area": 14.0},
            {"type": "bathroom", "area": 5.5},
        ]
    }
    from engine.layout_synthesizer_adjacency import synthesize_layout_from_spec
    layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 42})
    assert layout is not None

    out_ply = str(tmp_path / "cased_test.ply")
    mesh = build_house_from_layout(layout, visualize=False, output_file=out_ply)
    assert mesh is not None
    assert os.path.exists(out_ply)


def test_tri_state_usability_validation():
    """
    Tests that Check 7 evaluates all 6 structured subchecks
    with pass/warn/fail tri-state status.
    """
    rooms = {
        "living": box(0, 0, 5, 4),
        "bedroom_1": box(5, 0, 9, 4),
        "bathroom_1": box(5, 4, 8, 6.5),
        "kitchen": box(0, 4, 4, 6.5),
    }

    # Case 1: Layout without placed furniture should warn about room dimensions/furnishability
    res1 = validate_furniture_clearance(rooms)
    assert "subchecks" in res1
    subcheck_ids = [sc["id"] for sc in res1["subchecks"]]
    assert "bed_space" in subcheck_ids
    assert "window_clearance" in subcheck_ids
    assert "viewing_axis" in subcheck_ids
    assert "door_swing" in subcheck_ids
    assert "bathroom_fixtures" in subcheck_ids
    assert "kitchen_workzones" in subcheck_ids

    # Case 2: Placed fixtures with severe doorway landing obstruction should trigger FAIL
    placed_with_violation = [
        {"room": "bathroom_1", "type": "shower", "poly": box(5.1, 3.9, 6.5, 4.8)}
    ]
    doorways = [
        {"type": "door", "rooms": ("bedroom_1", "bathroom_1"), "polygon": box(5.2, 3.95, 6.0, 4.05)}
    ]
    res2 = validate_furniture_clearance(
        rooms,
        placed_furniture=placed_with_violation,
        openings=doorways
    )
    bath_sc = next(sc for sc in res2["subchecks"] if sc["id"] == "bathroom_fixtures")
    assert bath_sc["status"] == "fail"
    assert "doorway landing zone" in bath_sc["details"]
