import json
import math

# ==========================================================
# LOAD LEARNED PRIORS
# ==========================================================
# These are statistical / learned constraints from past layouts
# They are NOT a layout generator by themselves.
# They only define realistic SHAPES for rooms.
# ==========================================================

try:
    with open("layout_priors.json", "r") as f:
        PRIORS = json.load(f)
except FileNotFoundError:
    PRIORS = {}

# Fallback aspect ratio if nothing is learned
DEFAULT_RATIO = 1.3


# ==========================================================
# CORE SHAPE LOGIC
# ==========================================================
def rectangle_from_area(area, aspect_ratio=DEFAULT_RATIO):
    """
    Given:
        area (float): room area (sqft or sq units)
        aspect_ratio (float): width / height

    Returns:
        (width, height) respecting the area
    """
    width = math.sqrt(area * aspect_ratio)
    height = area / width
    return width, height


def apply_priors(room_type, requested_area):
    """
    Applies learned priors (min/max area, aspect ratio)
    without changing topology or adjacency logic.

    Returns:
        (final_area, aspect_ratio)
    """
    prior = PRIORS.get(room_type, {})

    area = requested_area

    # Clamp area if bounds exist
    if "min_area" in prior:
        area = max(area, prior["min_area"])
    if "max_area" in prior:
        area = min(area, prior["max_area"])

    ratio = prior.get("mean_aspect_ratio", DEFAULT_RATIO)

    return area, ratio


# ==========================================================
# PUBLIC UTILITY (USED BY ADJACENCY SYNTHESIZER)
# ==========================================================
def room_dimensions(room_type, area):
    """
    This is the ONLY function other modules should import.

    Example:
        w, h = room_dimensions("bedroom", 400)

    It applies priors + computes rectangle dimensions.
    """
    final_area, ratio = apply_priors(room_type, area)
    return rectangle_from_area(final_area, ratio)
