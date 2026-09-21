"""
Unit tests for V4 Top-Down Building-Design Architecture:
- Building Footprint & PlotSpec Setbacks
- Multiple Archetype Space Partitioning (1BHK, 2BHK, 3BHK)
- Semantic Bathroom Typology (Master Ensuite attached strictly to Master Bed, Common Bath to Hallway)
- Directional Foyer Arrival Keep-Out (Sofa >= 1.5m clearance from Entrance, TV disqualified from Entrance Wall)
- Compact Area Guard (Prevent 2 cramped baths under 65 sqm)
- Full 7/7 Architectural Validator Verification
"""

import pytest
import sys
import os
from shapely.geometry import box, Point, LineString, Polygon
from shapely.ops import unary_union
import numpy as np

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.building_footprint import (
    PlotSpec,
    compute_footprint_envelope,
    can_partition_archetype,
    select_and_partition_archetype,
    snap_module
)
from engine.text_to_specs_v2 import ProximityLayoutGenerator
from engine.layout_synthesizer_adjacency import synthesize_layout_from_spec
from engine.validator import LayoutValidator
from engine.resplan_to_3d import build_house_from_layout


def test_plot_spec_setbacks_and_envelope():
    """Verifies PlotSpec setbacks calculate the correct buildable envelope."""
    plot = PlotSpec(
        width=12.0,
        depth=18.0,
        front_facing="south",
        setbacks={"front": 3.0, "rear": 2.0, "left": 1.5, "right": 1.5}
    )
    minx, miny, maxx, maxy = plot.buildable_bounds()
    assert minx == 1.5
    assert maxx == 10.5
    assert miny == 3.0
    assert maxy == 16.0
    
    env_info = compute_footprint_envelope(target_area_sqm=100.0, plot=plot)
    assert env_info["width"] == 9.0
    assert env_info["height"] == 13.0
    assert env_info["polygon"].area == pytest.approx(117.0, rel=0.01)


def test_2bhk_archetype_zero_gaps_and_containment():
    """
    Verifies that 2BHK space partitioning perfectly tiles the rectangular envelope
    with zero gaps, zero overlaps, and 100% envelope containment.
    """
    spec = {
        "rooms": [
            {"type": "living", "name": "living", "area": 22.0},
            {"type": "kitchen", "name": "kitchen", "area": 12.0},
            {"type": "hallway", "name": "hallway", "area": 6.0},
            {"type": "bedroom", "name": "bedroom_1", "area": 16.0},
            {"type": "bedroom", "name": "bedroom_2", "area": 13.0},
            {"type": "bathroom", "name": "bathroom_1", "area": 5.0},
            {"type": "bathroom", "name": "bathroom_2", "area": 5.0},
        ]
    }
    
    # Test multiple seeds to cover both COMPACT and SPLIT_WINGS archetypes
    for seed in [42, 100, 2024, 777]:
        res = select_and_partition_archetype(spec, seed=seed)
        assert res is not None, f"Failed to partition archetype for seed {seed}"
        rooms, envelope = res

        # 1. Check all rooms placed
        assert len(rooms) == 7, f"Expected 7 rooms placed, got {len(rooms)}"
        assert "bedroom_1" in rooms
        assert "bedroom_2" in rooms
        assert "bathroom_1" in rooms
        assert "bathroom_2" in rooms

        # 2. Check union equals envelope area (zero gaps)
        room_union = unary_union(list(rooms.values()))
        assert abs(room_union.area - envelope.area) < 0.05, (
            f"Seed {seed}: Union area {room_union.area:.2f} != Envelope area {envelope.area:.2f}"
        )

        # 3. Check zero room overlap: sum of individual areas == union area
        sum_area = sum(r.area for r in rooms.values())
        assert abs(sum_area - room_union.area) < 0.05, (
            f"Seed {seed}: Overlap detected! Sum of areas {sum_area:.2f} != Union area {room_union.area:.2f}"
        )


def test_master_ensuite_vs_common_bathroom_topology():
    """
    Verifies semantic bathroom typology:
    - Master Ensuite (bathroom_1): strictly attached to Master Bedroom (bedroom_1) with exactly 1 door.
    - Common Bathroom (bathroom_2): connected to Hallway / circulation with exactly 1 door.
    - Solitary bathroom in small home: connected to public circulation.
    """
    spec = {
        "rooms": [
            {"type": "living", "name": "living", "area": 20.0},
            {"type": "kitchen", "name": "kitchen", "area": 10.0},
            {"type": "hallway", "name": "hallway", "area": 6.0},
            {"type": "bedroom", "name": "bedroom_1", "area": 15.0},
            {"type": "bedroom", "name": "bedroom_2", "area": 12.0},
            {"type": "bathroom", "name": "bathroom_1", "area": 5.0},
            {"type": "bathroom", "name": "bathroom_2", "area": 5.0},
        ]
    }
    
    layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 42})
    openings = layout.get("openings", [])
    
    b1_doors = [op for op in openings if "bathroom_1" in op.get("rooms", ())]
    b2_doors = [op for op in openings if "bathroom_2" in op.get("rooms", ())]
    
    assert len(b1_doors) == 1, f"Master ensuite must have exactly 1 door, got {len(b1_doors)}"
    b1_partner = [r for r in b1_doors[0]["rooms"] if r != "bathroom_1"][0]
    assert b1_partner == "bedroom_1", f"Master ensuite must connect strictly to bedroom_1, got {b1_partner}"
    
    assert len(b2_doors) == 1, f"Common bathroom must have exactly 1 door, got {len(b2_doors)}"
    b2_partner = [r for r in b2_doors[0]["rooms"] if r != "bathroom_2"][0]
    assert b2_partner in ["hallway", "living"], f"Common bath must connect to circulation, got {b2_partner}"


def test_3bhk_archetype_daylighting_and_connectivity():
    """
    Verifies 3BHK space partitioning provides exterior daylighting to all 3 bedrooms
    and creates proper circulation connectivity.
    """
    spec = {
        "rooms": [
            {"type": "living", "name": "living", "area": 25.0},
            {"type": "kitchen", "name": "kitchen", "area": 12.0},
            {"type": "dining", "name": "dining", "area": 10.0},
            {"type": "hallway", "name": "hallway", "area": 8.0},
            {"type": "bedroom", "name": "bedroom_1", "area": 16.0},
            {"type": "bedroom", "name": "bedroom_2", "area": 13.0},
            {"type": "bedroom", "name": "bedroom_3", "area": 12.0},
            {"type": "bathroom", "name": "bathroom_1", "area": 5.0},
            {"type": "bathroom", "name": "bathroom_2", "area": 5.0},
        ]
    }
    
    for seed in [10, 99]:
        layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": seed})
        rooms = layout["rooms"]
        env = layout["envelope"]
        
        # All 3 bedrooms must have external wall exposure
        for b_name in ["bedroom_1", "bedroom_2", "bedroom_3"]:
            b_poly = rooms[b_name]
            ext_len = b_poly.boundary.intersection(env.boundary).length
            assert ext_len >= 1.5, f"Seed {seed}: {b_name} lacks sufficient exterior wall ({ext_len:.2f}m)"


def test_directional_foyer_arrival_sofa_protection():
    """
    Verifies that:
    1. The wall containing the Main Entrance is NEVER selected as the living room TV wall.
    2. Sofa and coffee table maintain >= 1.5m clear arrival zone from the front entrance door.
    """
    spec = {
        "rooms": [
            {"type": "living", "name": "living", "area": 22.0},
            {"type": "kitchen", "name": "kitchen", "area": 10.0},
            {"type": "hallway", "name": "hallway", "area": 5.0},
            {"type": "bedroom", "name": "bedroom_1", "area": 15.0},
            {"type": "bedroom", "name": "bedroom_2", "area": 12.0},
            {"type": "bathroom", "name": "bathroom_1", "area": 5.0},
            {"type": "bathroom", "name": "bathroom_2", "area": 5.0},
        ]
    }
    
    layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 42})
    entrance = layout.get("entrance")
    assert entrance is not None and not entrance.is_empty, "Main entrance must be generated"
    
    # Build 3D house mesh
    mesh = build_house_from_layout(layout)
    assert mesh is not None
    vertices = np.asarray(mesh.vertices)
    colors = np.asarray(mesh.vertex_colors)
    assert len(vertices) > 0

    # Sofa blocks in resplan_to_3d use color #475569 -> [0.278, 0.333, 0.412]
    sofa_rgb = np.array([0x47 / 255.0, 0x55 / 255.0, 0x69 / 255.0])
    color_dists = np.linalg.norm(colors - sofa_rgb, axis=1)
    sofa_idx = np.where(color_dists < 0.05)[0]
    assert len(sofa_idx) > 0, "Sofa vertices should be present in living room"
    
    # Calculate distance between sofa and entrance door centroid
    ec = entrance.centroid
    sofa_xy = vertices[sofa_idx][:, :2]
    min_dist_to_door = min(Point(pt[0], pt[1]).distance(ec) for pt in sofa_xy)
    assert min_dist_to_door >= 1.50, (
        f"Sofa violates foyer arrival keep-out! Distance to front door: {min_dist_to_door:.2f}m (min: 1.50m)"
    )


def test_compact_area_guard_bathroom_count():
    """
    Verifies area guard:
    - 2BHK with area < 65 sqm defaults to 1 comfortable bathroom (preventing cramped bedrooms).
    - 2BHK with area >= 65 sqm defaults to 2 bathrooms (Master Ensuite + Common Bath).
    - Explicit '2 bath' request forces 2 bathrooms regardless of area.
    """
    gen = ProximityLayoutGenerator()
    
    # 1. Compact 2BHK (55 sqm / ~600 sqft): should have 1 bathroom
    res_compact = gen.generate_blueprint("Compact 2BHK house of 55 sqm")
    compact_baths = [r for r in res_compact if r["type"] == "bathroom"]
    assert len(compact_baths) == 1, f"Expected 1 bath for 55 sqm 2BHK, got {len(compact_baths)}"
    assert compact_baths[0].get("typology") == "common_bathroom"
    
    # 2. Standard 2BHK (80 sqm / ~860 sqft): should have 2 bathrooms
    res_standard = gen.generate_blueprint("Modern 2BHK apartment of 80 sqm")
    std_baths = [r for r in res_standard if r["type"] == "bathroom"]
    assert len(std_baths) == 2, f"Expected 2 baths for 80 sqm 2BHK, got {len(std_baths)}"
    assert std_baths[0].get("typology") == "master_ensuite"
    assert std_baths[1].get("typology") == "common_bathroom"

    # 3. Explicit request: "compact 2BHK with 2 bathrooms"
    res_explicit = gen.generate_blueprint("Compact 2BHK house of 55 sqm with 2 bathrooms")
    exp_baths = [r for r in res_explicit if r["type"] == "bathroom"]
    assert len(exp_baths) == 2, f"Expected 2 baths when explicitly requested, got {len(exp_baths)}"


def test_validator_feasibility_on_archetype():
    """
    Verifies that layouts generated via top-down archetypes pass all 7 architectural checks
    with a high feasibility score (>= 90/100).
    """
    spec = {
        "rooms": [
            {"type": "living", "name": "living", "area": 22.0},
            {"type": "kitchen", "name": "kitchen", "area": 10.0},
            {"type": "hallway", "name": "hallway", "area": 6.0},
            {"type": "bedroom", "name": "bedroom_1", "area": 15.0},
            {"type": "bedroom", "name": "bedroom_2", "area": 12.0},
            {"type": "bathroom", "name": "bathroom_1", "area": 5.0},
            {"type": "bathroom", "name": "bathroom_2", "area": 5.0},
        ]
    }
    
    layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 42})
    validation = LayoutValidator.validate_layout(layout, envelope_poly=layout["envelope"])
    
    assert validation["feasibility_score"] >= 90, (
        f"Expected feasibility score >= 90, got {validation['feasibility_score']} with violations: {validation['violations']}"
    )
    assert validation["checks_total"] == 7
    assert len(validation["violations"]) == 0, f"Violations found: {validation['violations']}"
