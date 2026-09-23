"""
Central Architectural Standards & Dimensions for Furniture, Openings, and Clearances.
Single source of truth for both 3D placement solvers and constraint validators.
"""
import math

# ==============================================================================
# DOORS & OPENINGS
# ==============================================================================
DOOR_HEIGHT = 2.10              # Standard residential door header height (meters)
DOOR_CLEARANCE = 0.80           # Minimum clear corridor approach directly in front of door
BATHROOM_ENTRY_LANDING = 0.80   # Clear landing box (0.80m x 0.80m) inside bathroom door
DOOR_SWING_ANGLE_RAD = math.pi / 2.0  # 90 degrees for functional architectural clearance arc
RENDER_DOOR_SWING_DEG = 25.0    # Aesthetic open angle for 3D visualization only

ENTRY_DOOR_WIDTH = 1.00         # Main entrance exterior door width
INTERIOR_DOOR_WIDTH = 0.90      # Standard bedroom/hallway door width
BATH_DOOR_WIDTH = 0.75          # Bathroom door width
CASED_OPENING_WIDTH = 1.40      # Open cased portal width (living <-> kitchen / dining)

# ==============================================================================
# WINDOWS & DAYLIGHTING
# ==============================================================================
WINDOW_SILL_HEIGHT = 0.90       # Habitable room window sill height
WINDOW_HEAD_HEIGHT = 2.10       # Aligned with door header
BATH_WINDOW_SILL_HEIGHT = 1.50  # Privacy bathroom ventilator sill
WINDOW_KEEP_OUT = 0.80          # Inward daylight exclusion corridor depth (meters)

# ==============================================================================
# CIRCULATION & PASSAGEWAYS
# ==============================================================================
CORRIDOR_WIDTH = 0.90           # Minimum pedestrian hallway / spine width
CHAIR_PULL_OUT = 0.65           # Pull-out space behind dining chairs
PERIMETER_WALKWAY = 0.60        # Walkway clearance around beds and sofas

# ==============================================================================
# LIVING ROOM / TV-SOFA PAIRING
# ==============================================================================
TV_VIEWING_RATIO_MIN = 1.6      # Min viewing distance multiplier (distance / tv_width)
TV_VIEWING_RATIO_MAX = 3.2      # Max viewing distance multiplier
TV_MIN_DISTANCE = 1.80          # Hard minimum comfortable viewing distance (meters)
TV_MAX_DISTANCE = 3.20          # Hard maximum comfortable viewing distance (meters)
TV_MOUNT_CENTER_HEIGHT = 1.15   # Seated ergonomic eye-level TV screen center
MEDIA_CONSOLE_HEIGHT = 0.42     # Floor-mounted low TV credenza
MEDIA_CONSOLE_DEPTH = 0.40      # TV console depth
SOFA_DEPTH = 0.85               # Standard sofa depth
COFFEE_TABLE_DISTANCE = 0.45    # Gap between sofa and coffee table

# ==============================================================================
# BATHROOM FIXTURES & HUMAN CLEARANCES
# ==============================================================================
SHOWER_SIZES = [
    (0.90, 0.90),               # Compact square shower tray
    (0.90, 1.20),               # Standard rectangular walk-in shower
    (1.00, 1.20),               # Spacious walk-in shower
]
SHOWER_GLASS_HEIGHT = 1.95      # Tempered glass screen height
SHOWER_TRAY_CURB = 0.04         # Low-profile shower curb threshold

# Fixture dimensions
VANITY_WIDTH = 0.70             # Floating vanity width
VANITY_DEPTH = 0.48             # Floating vanity depth
VANITY_HEIGHT = 0.82            # Finished counter height

WC_WIDTH = 0.40                 # Porcelain toilet width
WC_DEPTH = 0.60                 # Bowl + cistern depth
WC_HEIGHT = 0.75                # Cistern height

# Fixture clearances
WC_FRONT_CLEARANCE = 0.55       # Legroom in front of toilet
WC_SIDE_CLEARANCE = 0.20        # Minimum gap from toilet side to wall or fixture
VANITY_FRONT_CLEARANCE = 0.60   # Clear standing space in front of basin
SHOWER_ENTRY_CLEARANCE = 0.65   # Clear entry into shower enclosure

# ==============================================================================
# KITCHEN WORK ZONES
# ==============================================================================
COUNTER_DEPTH = 0.60            # Base countertop depth
COUNTER_HEIGHT = 0.86           # Finished countertop height
REFRIGERATOR_WIDTH = 0.75       # Refrigerator tower width
REFRIGERATOR_DEPTH = 0.70       # Refrigerator depth
REFRIGERATOR_HEIGHT = 1.85      # Refrigerator height
SINK_WIDTH = 0.80               # Undermount double sink width
COOKTOP_WIDTH = 0.75            # 4-burner cooktop width
RANGE_HOOD_HEIGHT = 1.70        # Range hood bottom clearance
UPPER_CABINET_DEPTH = 0.35      # Wall-mounted upper cabinets
UPPER_CABINET_BOTTOM = 1.50     # Clearance above floor for upper cabinets
UPPER_CABINET_TOP = 2.15        # Top of upper cabinets aligned with door lintel
