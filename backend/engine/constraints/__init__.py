"""
Architectural Constraints Package for VoxAssist.
"""

from .jurisdiction_profiles import get_profile, DEFAULT_RESIDENTIAL
from .envelope import (
    compute_building_envelope,
    is_within_envelope,
    validate_envelope_containment,
)
from .room_dimensions import (
    validate_room_dimensions,
    validate_all_room_dimensions,
    compute_bounded_room_dimensions,
)
from .egress import (
    get_room_external_walls,
    get_room_external_wall_length,
    validate_bedroom_exterior_access,
)
from .wet_areas import (
    validate_wet_area_clustering,
    is_wet_room,
)
from .furniture import (
    validate_furniture_clearance,
    validate_bedroom_furniture_clearance,
)

__all__ = [
    "get_profile",
    "DEFAULT_RESIDENTIAL",
    "compute_building_envelope",
    "is_within_envelope",
    "validate_envelope_containment",
    "validate_room_dimensions",
    "validate_all_room_dimensions",
    "compute_bounded_room_dimensions",
    "get_room_external_walls",
    "get_room_external_wall_length",
    "validate_bedroom_exterior_access",
    "validate_wet_area_clustering",
    "is_wet_room",
    "validate_furniture_clearance",
    "validate_bedroom_furniture_clearance",
]

