import pytest
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from engine.layout_synthesizer_adjacency import synthesize_layout_from_spec
from engine.validator import validate_layout

def test_synthesize_1bhk():
    spec = {
        "rooms": [
            {"type": "living", "area": 22.0},
            {"type": "kitchen", "area": 10.0},
            {"type": "bedroom", "area": 14.0},
            {"type": "bathroom", "area": 5.0},
        ]
    }
    result = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 42})
    assert "rooms" in result
    assert len(result["rooms"]) >= 4
    assert result.get("envelope") is not None
    
    # Run architectural validation
    val = validate_layout(result, envelope_poly=result["envelope"])
    assert val["valid"] is True
    assert val["feasibility_score"] >= 75
    assert val["checks_passed"] >= 3

def test_synthesize_2bhk():
    spec = {
        "rooms": [
            {"type": "living", "area": 25.0},
            {"type": "dining", "area": 12.0},
            {"type": "kitchen", "area": 11.0},
            {"type": "bedroom", "area": 15.0},
            {"type": "bedroom", "area": 14.0},
            {"type": "bathroom", "area": 5.0},
            {"type": "bathroom", "area": 5.0},
        ]
    }
    result = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 123})
    assert "rooms" in result
    assert len(result["rooms"]) >= 6
    
    val = validate_layout(result, envelope_poly=result["envelope"])
    assert val["valid"] is True
    assert val["feasibility_score"] >= 70

def test_synthesize_3bhk():
    spec = {
        "rooms": [
            {"type": "living", "area": 28.0},
            {"type": "dining", "area": 14.0},
            {"type": "kitchen", "area": 12.0},
            {"type": "hallway", "area": 8.0},
            {"type": "bedroom", "area": 16.0},
            {"type": "bedroom", "area": 14.0},
            {"type": "bedroom", "area": 13.0},
            {"type": "bathroom", "area": 6.0},
            {"type": "bathroom", "area": 5.0},
            {"type": "bathroom", "area": 5.0},
        ]
    }
    result = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 999})
    assert "rooms" in result
    assert len(result["rooms"]) >= 8
    
    val = validate_layout(result, envelope_poly=result["envelope"])
    assert val["valid"] is True
    assert val["feasibility_score"] >= 70

def test_synthesize_4bhk():
    spec = {
        "rooms": [
            {"type": "living", "area": 32.0},
            {"type": "dining", "area": 16.0},
            {"type": "kitchen", "area": 14.0},
            {"type": "hallway", "area": 10.0},
            {"type": "bedroom", "area": 18.0},
            {"type": "bedroom", "area": 15.0},
            {"type": "bedroom", "area": 14.0},
            {"type": "bedroom", "area": 13.0},
            {"type": "bathroom", "area": 6.0},
            {"type": "bathroom", "area": 5.0},
            {"type": "bathroom", "area": 5.0},
            {"type": "utility", "area": 4.0},
        ]
    }
    result = synthesize_layout_from_spec(spec, {"RANDOM_SEED": 777})
    assert "rooms" in result
    assert len(result["rooms"]) >= 10
    
    val = validate_layout(result, envelope_poly=result["envelope"])
    assert val["valid"] is True
    assert val["feasibility_score"] >= 70

