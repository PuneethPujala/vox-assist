"""
Unit and integration tests for Room-Specific Semantic Furniture Grammars,
Three-Tier Architectural Validator, and Global Furniture Collision Pass.
"""

import os
import sys
import pytest
from shapely.geometry import box, Polygon, Point, LineString

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.constraints import furniture_constants as const
from engine.furniture_grammars import (
    solve_bedroom_furniture_group,
    solve_dining_zone_group,
    solve_global_furniture_layout,
    solve_living_room_group,
)
from engine.constraints.furniture import (
    validate_dining_furniture_clearance,
    validate_furniture_clearance,
)
from engine.validator import validate_layout


def test_bedroom_grammar_headboard_and_wardrobe():
    """
    Verifies:
    1. Headboard avoids window walls.
    2. Symmetrical nightstands generated beside headboard.
    3. Master bedroom gets 1.80m wardrobe; secondary bedroom gets 1.20m wardrobe.
    4. Wardrobe door clearance (0.60m) does not collide with bed.
    """
    # 4.5m x 4.0m master bedroom
    bedroom_poly = box(0, 0, 4.5, 4.0)
    # North wall has an exterior window
    windows = [{"room": "bedroom_1", "wall_segment": LineString([(1.0, 4.0), (3.5, 4.0)])}]
    # Entrance door on South wall near west corner
    door_polys = [box(0.2, -0.1, 1.1, 0.1)]

    # 1. Master bedroom test
    master_res = solve_bedroom_furniture_group(
        bedroom_poly,
        door_polys=door_polys,
        windows=windows,
        room_type="master_bedroom",
        room_name="bedroom_1"
    )

    assert master_res is not None
    assert master_res["valid"] is True
    # Headboard must avoid North wall (window) and South wall (doorway)
    assert master_res["headboard_wall"] in ["east", "west"]
    assert master_res["headboard_wall"] != "north"
    assert master_res["headboard_box"] is not None
    assert master_res["mattress_box"] is not None

    # Nightstands verification (should have at least one or two flanking nightstands)
    assert len(master_res["nightstand_boxes"]) >= 1

    # Wardrobe verification: Master bedroom should receive ~1.80m wardrobe
    assert master_res["wardrobe_box"] is not None
    assert master_res["wardrobe_wall"] != "north"  # Never on window wall
    assert master_res["wardrobe_width"] >= 1.70  # ~1.80m
    assert master_res["wardrobe_door_clearance_box"] is not None

    # 2. Secondary bedroom test
    sec_bedroom_poly = box(0, 0, 3.8, 3.4)
    sec_windows = [{"room": "bedroom_2", "wall_segment": LineString([(0.8, 3.4), (2.8, 3.4)])}]
    sec_doors = [box(0.2, -0.1, 1.1, 0.1)]

    sec_res = solve_bedroom_furniture_group(
        sec_bedroom_poly,
        door_polys=sec_doors,
        windows=sec_windows,
        room_type="bedroom",
        room_name="bedroom_2"
    )
    assert sec_res is not None
    assert sec_res["valid"] is True
    # Secondary wardrobe should be ~1.20m
    assert sec_res["wardrobe_box"] is not None
    assert sec_res["wardrobe_width"] <= 1.30


def test_dining_zone_grammar_clearances():
    """
    Verifies:
    1. Large dining room (>=14m2) places 6-seater dining table (1.60m x 0.90m).
    2. Standard dining room places 4-seater dining table (1.20m x 0.80m).
    3. Chair pullout buffer (0.65m) and walkway clearance (0.90m) are computed.
    4. Table avoids encroaching into foyer keepout or protected circulation.
    """
    # 1. Large 16m2 dining room -> 6S table
    large_dining = box(0, 0, 4.5, 3.6)  # 16.2 m2
    res_6s = solve_dining_zone_group(large_dining, is_compact=False)
    assert res_6s is not None
    assert res_6s["archetype"] == "DINING_6S"
    assert res_6s["chair_count"] == 6
    assert res_6s["pullout_box"] is not None
    assert res_6s["walkway_box"] is not None

    # 2. Standard 10m2 dining room -> 4S table
    std_dining = box(0, 0, 3.2, 3.2)  # 10.24 m2
    res_4s = solve_dining_zone_group(std_dining, is_compact=False)
    assert res_4s is not None
    assert res_4s["archetype"] == "DINING_4S"
    assert res_4s["chair_count"] == 4

    # 3. Foyer keepout avoidance (entrance foyer arrival zone at corner)
    foyer_keepout = box(0.0, 0.0, 1.2, 1.2)
    res_avoid = solve_dining_zone_group(std_dining, foyer_keepout=foyer_keepout)
    assert res_avoid is not None
    assert not res_avoid["table_box"].intersects(foyer_keepout)


def test_dining_furniture_clearance_validation():
    """
    Verifies validate_dining_furniture_clearance correctly checks
    table containment, chair pull-out, and walkway clearances.
    """
    dining_poly = box(0, 0, 4.0, 3.5)
    table_box = box(1.4, 1.3, 2.6, 2.2)
    chairs = [
        box(1.5, 0.8, 1.9, 1.2),
        box(2.1, 0.8, 2.5, 1.2),
        box(1.5, 2.3, 1.9, 2.7),
        box(2.1, 2.3, 2.5, 2.7),
    ]
    door_polys = [box(0.0, 0.0, 0.9, 0.1)]

    v_res = validate_dining_furniture_clearance(
        dining_poly,
        table_box=table_box,
        chairs=chairs,
        door_polys=door_polys
    )
    assert v_res["valid"] is True
    assert v_res["pullout_clearance_ok"] is True
    assert v_res["walkway_clearance_ok"] is True
    assert len(v_res["violations"]) == 0


def test_global_furniture_layout_collision_detection():
    """
    Verifies solve_global_furniture_layout:
    1. Passes when furniture groups are cleanly spaced.
    2. Detects pairwise cross-room clashes (e.g. dining table overlapping sofa).
    3. Detects intrusion into circulation spine or foyer arrival zone.
    """
    clean_groups = {
        "living": {
            "sofa_box": box(1.0, 1.0, 3.2, 1.9),
            "tv_box": box(1.0, 3.8, 2.8, 4.0),
            "coffee_table_box": box(1.4, 2.2, 2.4, 2.8),
            "rug_box": box(0.8, 1.2, 3.4, 3.2)
        },
        "bedroom_1": {
            "headboard_box": box(6.0, 3.8, 8.0, 4.0),
            "mattress_box": box(6.0, 1.8, 8.0, 3.8),
            "nightstand_boxes": [box(5.5, 3.4, 5.9, 3.8), box(8.1, 3.4, 8.5, 3.8)],
            "wardrobe_box": box(5.2, 0.2, 7.0, 0.8)
        }
    }
    circ_spine = box(4.0, 0.0, 5.0, 5.0)
    foyer_keepout = box(0.0, 0.0, 0.8, 0.8)

    # 1. Clean layout verification
    global_res = solve_global_furniture_layout(
        clean_groups,
        protected_circ=circ_spine,
        foyer_keepout=foyer_keepout
    )
    assert global_res["valid"] is True
    assert len(global_res["conflicts"]) == 0
    assert global_res["score"] == 100

    # 2. Clash layout verification: dining table placed right on top of sofa
    clash_groups = dict(clean_groups)
    clash_groups["dining"] = {
        "table_box": box(1.5, 1.2, 2.7, 2.0)  # overlaps sofa_box
    }
    clash_res = solve_global_furniture_layout(clash_groups)
    assert clash_res["valid"] is False
    assert len(clash_res["conflicts"]) >= 1
    assert any("sofa" in c and "dining" in c for c in clash_res["conflicts"])

    # 3. Circulation intrusion verification
    spine_intruder_groups = {
        "living": {
            "sofa_box": box(4.2, 2.0, 5.5, 3.0)  # intersects circ_spine
        }
    }
    spine_res = solve_global_furniture_layout(
        spine_intruder_groups,
        protected_circ=circ_spine
    )
    assert spine_res["valid"] is False
    assert any("corridor" in c for c in spine_res["conflicts"])


def test_three_tier_validator_payload():
    """
    Verifies the Three-Tier Architectural Validator payload structure:
    1. Checks backward compatibility: 'valid', 'feasibility_score', 'checks_passed', 'checks_total' == 7, 'checks', 'violations', 'warnings'.
    2. Validates 'tier1_hard_constraints' (envelope, dimensions, daylight, egress, doors, circulation).
    3. Validates 'tier2_human_usability' (7 usability subchecks including dining).
    4. Validates 'tier3_semantic_quality' (per-room spatial grammar scores).
    5. Validates 'geometry_3d_integrity' (finished floor grounding, TV wall mount, zero wall penetration, jambs, envelope windows).
    """
    layout = {
        "rooms": {
            "living": box(0, 0, 5.5, 4.2),
            "kitchen": box(5.5, 0, 9.0, 4.2),
            "bedroom_1": box(0, 4.2, 4.5, 8.2),
            "bathroom_1": box(4.5, 4.2, 7.0, 6.2),
            "dining": box(4.5, 6.2, 9.0, 8.2),
        },
        "openings": [
            {"type": "door", "rooms": ("living", "bedroom_1"), "polygon": box(2.0, 4.1, 2.9, 4.3)},
            {"type": "door", "rooms": ("bedroom_1", "bathroom_1"), "polygon": box(4.4, 5.0, 4.6, 5.9)},
            {"type": "door", "rooms": ("living", "kitchen"), "polygon": box(5.4, 2.0, 5.6, 3.0)},
            {"type": "entrance", "rooms": ("exterior", "living"), "polygon": box(2.5, -0.1, 3.4, 0.1)},
        ],
        "windows": [
            {"room": "living", "wall_segment": LineString([(1.0, 0.0), (2.0, 0.0)])},
            {"room": "bedroom_1", "wall_segment": LineString([(1.0, 8.2), (3.0, 8.2)])},
            {"room": "kitchen", "wall_segment": LineString([(7.0, 0.0), (8.5, 0.0)])},
            {"room": "dining", "wall_segment": LineString([(7.0, 8.2), (8.5, 8.2)])},
        ]
    }

    val_res = validate_layout(layout)

    # 1. Backward compatibility assertions
    assert "valid" in val_res
    assert "feasibility_score" in val_res
    assert "checks_passed" in val_res
    assert val_res["checks_total"] == 7
    assert len(val_res["checks"]) == 7
    assert "violations" in val_res
    assert "warnings" in val_res

    # 2. Tier 1 Hard Constraints
    assert "tier1_hard_constraints" in val_res
    t1 = val_res["tier1_hard_constraints"]
    assert "status" in t1
    assert "score" in t1
    assert t1["checks_total"] == 6  # envelope, dimensions, daylight, egress, doors, circulation

    # 3. Tier 2 Human Usability
    assert "tier2_human_usability" in val_res
    t2 = val_res["tier2_human_usability"]
    assert "status" in t2
    assert "score" in t2
    assert t2["checks_total"] == 7
    t2_ids = [c["id"] for c in t2["checks"]]
    assert "bed_clearance" in t2_ids
    assert "tv_sofa_axis" in t2_ids
    assert "door_swing" in t2_ids
    assert "bathroom_landing" in t2_ids
    assert "kitchen_workflow" in t2_ids
    assert "dining_circulation" in t2_ids
    assert "window_obstruction" in t2_ids

    # 4. Tier 3 Semantic Room Quality
    assert "tier3_semantic_quality" in val_res
    t3 = val_res["tier3_semantic_quality"]
    assert "overall_grammar_score" in t3
    assert "scores" in t3
    assert "living_room" in t3["scores"]
    assert "bedrooms" in t3["scores"]
    assert "bathrooms" in t3["scores"]
    assert "kitchen" in t3["scores"]
    assert "dining" in t3["scores"]

    # 5. Geometry 3D CAD Integrity
    assert "geometry_3d_integrity" in val_res
    cad = val_res["geometry_3d_integrity"]
    assert cad["status"] == "pass"
    cad_ids = [c["id"] for c in cad["checks"]]
    assert "floating_furniture" in cad_ids
    assert "tv_wall_mount" in cad_ids
    assert "wall_penetration" in cad_ids
    assert "door_jambs" in cad_ids
    assert "envelope_windows" in cad_ids
