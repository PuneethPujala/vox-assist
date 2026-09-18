"""
Unit tests for unified architectural LayoutValidator.
Verifies that:
- Clean compliant layout achieves 100% feasibility score and all checks pass.
- Layout with envelope/dimension/egress violations fails gracefully with explicit check reports.
"""

import pytest
import sys
import os
from shapely.geometry import box

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.validator import LayoutValidator, validate_layout

def test_validator_clean_compliant_layout():
    # 2BHK clean compact layout within a 12m x 10m envelope:
    # Living: (0, 0) to (6, 5) -> 30 sqm (AR 1.2)
    # Kitchen: (6, 0) to (10, 4) -> 16 sqm (AR 1.0)
    # Bedroom 1: (0, 5) to (4.5, 9.5) -> 20.25 sqm (AR 1.1)
    # Bedroom 2: (4.5, 5) to (9, 9.5) -> 20.25 sqm (AR 1.1)
    # Bath: (9, 4) to (11, 7) -> 6 sqm
    
    envelope_poly = box(0, 0, 12, 10)
    
    layout = {
        "rooms": {
            "living": box(0, 0, 6, 5),
            "kitchen": box(6, 0, 10, 4),
            "bedroom_1": box(0, 5, 4.5, 9.5),
            "bedroom_2": box(4.5, 5, 9, 9.5),
            "bathroom_1": box(9, 4, 11, 7),
        }
    }
    
    report = validate_layout(layout, envelope_poly=envelope_poly)
    
    assert report["valid"] is True
    assert report["feasibility_score"] >= 90
    assert report["checks_passed"] == report["checks_total"]
    assert len(report["violations"]) == 0
    
    # Check that all 4 checks returned status "pass"
    for check in report["checks"]:
        assert check["status"] == "pass"

def test_validator_catches_all_pathological_violations():
    # Construct layout with:
    # 1. Spilling outside 10x10 envelope -> Bedroom 2 reaches x=15
    # 2. 8ft x 25ft narrow bedroom (AR > 3.0) -> Bedroom 2 is (10, 0) to (12.44, 7.62)
    # 3. Landlocked bedroom -> Bedroom 1 completely surrounded
    
    envelope_poly = box(0, 0, 10, 10)
    
    layout = {
        "rooms": {
            "living": box(0, 3, 4, 9),
            "dining": box(8, 3, 10, 9),
            "kitchen": box(3, 0, 9, 4),
            "storage": box(3, 8, 9, 10),
            # Landlocked Bedroom 1:
            "bedroom_1": box(4, 4, 8, 8),
            # Spilling & narrow Bedroom 2:
            "bedroom_2": box(10, 0, 12.44, 7.62),
        }
    }
    
    report = validate_layout(layout, envelope_poly=envelope_poly)
    
    assert report["valid"] is False
    assert report["feasibility_score"] < 60
    assert len(report["violations"]) >= 2
    
    check_statuses = {c["id"]: c["status"] for c in report["checks"]}
    assert check_statuses["envelope"] == "fail"
    assert check_statuses["dimensions"] == "fail"
    assert check_statuses["egress"] == "fail"
