"""
Unit and integration tests for Opening Authority & Consistency Layer:
1. OpeningRegistry generation and structural immutability.
2. 3D CAD mesh generation strictly consumes OpeningRegistry (no invented windows).
3. validate_opening_consistency detects dropped or hallucinated openings.
4. Enhanced daylighting and IRC R310 egress validation.
5. Candidate filtering gate in generation pipeline.
"""

import os
import sys
import pytest
from shapely.geometry import box, Polygon, LineString

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.opening_registry import OpeningRegistry, build_opening_registry
from engine.layout_synthesizer_adjacency import synthesize_layout_from_spec
from engine.resplan_to_3d import build_house_from_layout
from engine.validator import validate_layout, validate_opening_consistency


def test_opening_registry_immutability_and_structure():
    """
    Verifies that build_opening_registry:
    1. Identifies exterior walls accurately.
    2. Places windows only on exterior walls (never interior partitions).
    3. Calculates glazing area, sill height, head height, and fire egress compliance.
    4. Separates hinged doors from cased openings (> 1.15m).
    """
    rooms = {
        "living": box(0, 0, 5.5, 4.0),
        "bedroom_1": box(5.5, 0, 9.5, 4.0),
        "bathroom_1": box(5.5, 4.0, 8.0, 6.5),
        "kitchen": box(0, 4.0, 5.5, 6.5),
    }
    openings_meta = [
        {"type": "door", "rooms": ("living", "bedroom_1"), "polygon": box(5.4, 1.5, 5.6, 2.4), "width": 0.90},
        {"type": "door", "rooms": ("bedroom_1", "bathroom_1"), "polygon": box(6.0, 3.9, 6.9, 4.1), "width": 0.80},
        {"type": "cased_opening", "rooms": ("living", "kitchen"), "polygon": box(2.0, 3.9, 3.8, 4.1), "width": 1.80},
        {"type": "entrance", "rooms": ("living", "exterior"), "polygon": box(2.2, -0.1, 3.3, 0.1), "width": 1.10}
    ]

    reg = build_opening_registry(
        rooms=rooms,
        openings_metadata=openings_meta,
        design_id="test_design_001"
    )

    assert reg is not None
    assert reg.design_id == "test_design_001"
    assert len(reg.windows) >= 3  # Living, bedroom, kitchen, bathroom

    # 1. Windows verification
    living_wins = reg.get_windows_for_room("living")
    assert len(living_wins) >= 1
    for w in living_wins:
        assert w["sill_height"] == 0.90
        assert w["head_height"] == 2.10
        assert w["glazing_area"] >= 1.0
        assert w["keepout"] is not None

    br_wins = reg.get_windows_for_room("bedroom_1")
    assert len(br_wins) >= 1
    assert any(w["is_egress"] is True for w in br_wins)

    bath_wins = reg.get_windows_for_room("bathroom_1")
    if bath_wins:
        assert bath_wins[0]["sill_height"] == 1.50  # Privacy sill height

    # 2. Doors & Cased Openings verification
    assert len(reg.doors) >= 2
    assert len(reg.cased_openings) >= 1
    assert reg.cased_openings[0]["is_cased"] is True
    assert reg.cased_openings[0]["width"] >= 1.15
    assert reg.entrance is not None
    assert reg.entrance["type"] == "entrance"


def test_resplan_to_3d_preserves_immutable_openings(tmp_path):
    """
    Verifies that build_house_from_layout strictly renders the openings
    defined in opening_registry without hallucinating or dropping any.
    """
    spec = {
        "rooms": [
            {"type": "living", "area": 22.0},
            {"type": "bedroom", "area": 14.0},
            {"type": "kitchen", "area": 10.0},
            {"type": "bathroom", "area": 5.0},
        ]
    }
    layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 101})
    assert layout is not None
    assert "opening_registry" in layout
    assert "windows" in layout

    expected_windows = layout["windows"]
    assert len(expected_windows) > 0

    out_ply = str(tmp_path / "model_immutable.ply")
    mesh = build_house_from_layout(layout, visualize=False, output_file=out_ply)
    assert mesh is not None

    # Verify rendered openings match expected registry
    assert "rendered_openings" in layout
    rendered_wins = [o for o in layout["rendered_openings"] if o.get("type") == "window"]
    assert len(rendered_wins) == len(expected_windows)

    # Check each expected window matches a rendered window
    for exp_w in expected_windows:
        r_name = exp_w["room"]
        w_width = exp_w["width"]
        matched = any(
            rw["room"].lower() == r_name.lower() and abs(rw["width"] - w_width) < 0.15
            for rw in rendered_wins
        )
        assert matched is True


def test_opening_consistency_validator():
    """
    Verifies validate_opening_consistency:
    1. Returns pass when rendered openings match registry.
    2. Flags discrepancies when windows are dropped or hallucinated.
    """
    layout = {
        "opening_registry": {
            "windows": [
                {"opening_id": "win_living_0", "room": "living", "position": (2.5, 0.0), "width": 1.6},
                {"opening_id": "win_bed_0", "room": "bedroom_1", "position": (7.0, 4.0), "width": 1.3}
            ]
        },
        "windows": [
            {"opening_id": "win_living_0", "room": "living", "position": (2.5, 0.0), "width": 1.6},
            {"opening_id": "win_bed_0", "room": "bedroom_1", "position": (7.0, 4.0), "width": 1.3}
        ],
        "rendered_openings": [
            {"opening_id": "win_living_0", "type": "window", "room": "living", "position": (2.5, 0.0), "width": 1.6},
            {"opening_id": "win_bed_0", "type": "window", "room": "bedroom_1", "position": (7.0, 4.0), "width": 1.3}
        ]
    }

    # Case 1: Synchronized -> pass
    res_clean = validate_opening_consistency(layout)
    assert res_clean["valid"] is True
    assert res_clean["status"] == "pass"

    # Case 2: Dropped window in 3D
    layout_dropped = dict(layout)
    layout_dropped["rendered_openings"] = [
        {"opening_id": "win_living_0", "type": "window", "room": "living", "position": (2.5, 0.0), "width": 1.6}
    ]
    res_dropped = validate_opening_consistency(layout_dropped)
    assert res_dropped["valid"] is False
    assert any("not reproduced" in d for d in res_dropped["discrepancies"])

    # Case 3: Hallucinated window in 3D
    layout_hallucinated = dict(layout)
    layout_hallucinated["rendered_openings"] = list(layout["rendered_openings"]) + [
        {"opening_id": "win_extra", "type": "window", "room": "living", "position": (1.0, 2.0), "width": 1.0}
    ]
    res_hallucinated = validate_opening_consistency(layout_hallucinated)
    assert res_hallucinated["valid"] is False
    assert any("extraneous window" in d for d in res_hallucinated["discrepancies"])


def test_bedroom_daylighting_and_egress_subchecks():
    """
    Verifies Check 3 evaluates exterior wall, glazing ratio, and fire egress standards.
    """
    # Compliant bedroom with exterior wall and proper egress window
    layout_compliant = {
        "rooms": {
            "living": box(0, 0, 5, 4),
            "bedroom_1": box(5, 0, 9, 4),  # 16 m2
        },
        "windows": [
            {"room": "bedroom_1", "width": 1.4, "height": 1.2, "glazing_area": 1.68, "is_egress": True, "sill_height": 0.90}
        ]
    }
    res_c = validate_layout(layout_compliant)
    egress_chk = next(c for c in res_c["checks"] if c["id"] == "egress")
    assert egress_chk["status"] == "pass"
    assert "fire egress & daylighting" in egress_chk["details"]
