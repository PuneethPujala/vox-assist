"""
Architectural constraint profiles for VoxAssist.
Decouples hardcoded dimensions from solver logic to support flexible, defensible residential standards.
All dimensions are in metric units (meters, square meters).
"""

from typing import Dict, Any

DEFAULT_RESIDENTIAL: Dict[str, Any] = {
    "name": "Default Residential Standard",
    "description": "Architecturally sound baseline for modern residential floor-plans",
    "envelope": {
        "circulation_factor": 0.15,          # 15% allowance for corridors / walls
        "min_aspect_ratio": 1.0,             # Min envelope width/height ratio
        "max_aspect_ratio": 1.5,             # Max envelope width/height ratio
        "max_overflow_tolerance_sqm": 0.05,  # Floating point area overflow threshold
    },
    "room_dimensions": {
        "living": {
            "min_area": 14.0,           # ~150 sqft
            "min_width": 3.2,           # ~10.5 ft
            "max_aspect_ratio": 1.8,
        },
        "bedroom": {
            "min_area": 9.0,            # ~97 sqft
            "min_width": 2.8,           # ~9.2 ft
            "max_aspect_ratio": 1.6,
        },
        "kitchen": {
            "min_area": 5.0,            # ~54 sqft
            "min_width": 2.0,           # ~6.6 ft (allows galley kitchen)
            "max_aspect_ratio": 2.2,
        },
        "bathroom": {
            "min_area": 2.5,            # ~27 sqft
            "min_width": 1.2,           # ~4.0 ft
            "max_aspect_ratio": 2.0,
        },
        "dining": {
            "min_area": 7.0,            # ~75 sqft
            "min_width": 2.4,           # ~7.9 ft
            "max_aspect_ratio": 1.8,
        },
        "study": {
            "min_area": 6.0,            # ~65 sqft
            "min_width": 2.2,           # ~7.2 ft
            "max_aspect_ratio": 1.8,
        },
        "balcony": {
            "min_area": 2.0,            # ~22 sqft
            "min_width": 1.0,           # ~3.3 ft
            "max_aspect_ratio": 3.0,
        },
        "storage": {
            "min_area": 1.5,            # ~16 sqft
            "min_width": 1.0,
            "max_aspect_ratio": 2.5,
        },
        "utility": {
            "min_area": 2.0,
            "min_width": 1.2,
            "max_aspect_ratio": 2.5,
        },
        "hallway": {
            "min_area": 2.0,
            "min_width": 0.9,           # ~3.0 ft code minimum circulation clear width
            "max_aspect_ratio": 6.0,
        }
    },
    "egress": {
        "min_exterior_wall_length": 1.5, # Minimum meters of continuous exterior wall for fire egress/daylight
        "required_rooms": ["bedroom"],
    },
    "wet_areas": {
        "wet_types": ["kitchen", "bathroom", "utility"],
        "max_recommended_cluster_distance": 5.0, # meters between wet nodes before warning
    }
}

PROFILES: Dict[str, Dict[str, Any]] = {
    "DEFAULT": DEFAULT_RESIDENTIAL,
}

def get_profile(profile_name: str = "DEFAULT") -> Dict[str, Any]:
    return PROFILES.get(profile_name.upper(), DEFAULT_RESIDENTIAL)
