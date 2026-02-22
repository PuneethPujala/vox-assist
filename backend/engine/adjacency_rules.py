"""
Adjacency rules for Indian residential layouts - Architecturally Sound Version

KEY PRINCIPLES:
1. Living room is the CORE/HUB - everything radiates from it
2. Rooms are organized in ZONES (public, private, service)
3. Privacy gradient: Public → Semi-public → Private → Service
4. No "pass-through" rooms - rooms are leaves or branches, not corridors

ZONES:
- Public: Living, Dining
- Semi-Public: Kitchen
- Private: Bedrooms
- Service: Bathrooms, Storage, Utility
"""

ADJACENCY_RULES = {
    "living": {
        "anchor": True,  # Core room - placed first
        "external": False,
        "aspect_ratio": 1.5,
        "prefer": {
            # Living room connects to main areas
            "kitchen": 4,      # High priority - open plan common (no door, just opening)
            "dining": 5,       # Very high - often combined space
            "bedroom": 3,      # Medium - access to private zone
            "balcony": 4,      # Direct access to balcony
        },
        "avoid": {
            # Living should NEVER directly touch service rooms
            "storage": True,
            "utility": True,
            "bathroom": True,  # ⚠️ CRITICAL: No direct living-bathroom connection
        }
    },
    
    "bedroom": {
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.2,
        "prefer": {
            # Bedrooms are LEAVES - they connect to living (hub) and their bathroom
            "living": 5,       # Must connect to hub for access
            "bathroom": 5,     # Attached bathroom
        },
        "avoid": {
            # Bedrooms should NEVER directly touch these
            "kitchen": True,       # Privacy violation
            "dining": True,        # Privacy violation
            "bedroom": True,       # Bedrooms don't connect to each other
            "storage": True,
            "utility": True,
        }
    },
    
    "kitchen": {
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.0,
        "prefer": {
            # Kitchen only connects to public/semi-public zones
            "living": 5,       # Primary connection (hub)
            "dining": 5,       # Essential for meal flow
            "storage": 3,      # Pantry access
            "utility": 2,      # If utility exists
        },
        "avoid": {
            # Kitchen should NEVER touch private zones
            "bedroom": True,       # Major privacy violation
            "bathroom": True,      # Hygiene concern
        }
    },
    
    "bathroom": {
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.0,
        "prefer": {
            # Bathrooms are TERMINAL NODES (leaves)
            "bedroom": 5,      # Attached bathroom (primary)
            "study": 4,        # Attached to study (acts like ensuite)
            "living": 3,       # Common bathroom (secondary)
        },
        "avoid": {
            # Bathrooms should NEVER be between rooms
            "kitchen": True,       # Hygiene concern
            "dining": True,        # Hygiene concern
            "bathroom": True,      # No bathroom-to-bathroom connections
            "storage": True,
        }
    },
    
    "dining": {
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.3,
        "prefer": {
            # Dining in public zone
            "living": 5,       # Often combined space
            "kitchen": 5,      # Essential for serving
        },
        "avoid": {
            # Dining should not touch private zones
            "bedroom": True,
            "bathroom": True,
            "storage": True,
        }
    },
    
    "storage": {
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.0,
        "prefer": {
            # Storage is service zone
            "kitchen": 4,      # Pantry
            "utility": 3,
        },
        "avoid": {
            # Storage should not be prominent
            "living": True,
            "bedroom": True,
            "dining": True,
        }
    },
    
    "utility": {
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.0,
        "prefer": {
            # Utility room in service zone
            "kitchen": 4,
            "storage": 3,
        },
        "avoid": {
            "living": True,
            "bedroom": True,
            "dining": True,
            "bathroom": True,
        }
    },
    
    "balcony": {
        "anchor": False,
        "external": True,  # Outside boundary
        "aspect_ratio": 2.0,
        "prefer": {
            # Balconies on exterior of main rooms
            "living": 4,
            "bedroom": 4,      # Master bedroom balcony
        },
        "avoid": {
            "kitchen": True,
            "bathroom": True,
            "storage": True,
        }
    },
    
    "garden": {
        "anchor": False,
        "external": True,
        "aspect_ratio": 1.8,
        "prefer": {
            # Garden adjacent to public spaces
            "living": 4,
            "dining": 3,
        },
        "avoid": {
            "bedroom": True,
            "bathroom": True,
            "kitchen": True,
        }
    },
    
    "study": {
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.2,
        "prefer": {
            # Study room in quiet zone
            "living": 3,
            "bedroom": 2,
            "bathroom": 4,
        },
        "avoid": {
            "kitchen": True,
        }
    },
    
    "pooja": {  # Prayer room (Indian homes)
        "anchor": False,
        "external": False,
        "aspect_ratio": 1.0,
        "prefer": {
            # Pooja room in peaceful location
            "living": 4,
        },
        "avoid": {
            "kitchen": True,
            "bathroom": True,      # Religious considerations
            "bedroom": True,
        }
    }
}

# Fallback for any new room type
DEFAULT_ROOM_RULES = {
    "anchor": False,
    "external": False,
    "aspect_ratio": 1.0,
    "prefer": {
        "living": 2,  # Default: connect to living room
    },
    "avoid": {}
}


# =========================
# ARCHITECTURAL VALIDATION
# =========================
def validate_adjacency(room_type_1, room_type_2):
    """
    Check if two room types should be adjacent based on architectural principles.
    Returns (is_valid, reason)
    """
    rules_1 = ADJACENCY_RULES.get(room_type_1, DEFAULT_ROOM_RULES)
    rules_2 = ADJACENCY_RULES.get(room_type_2, DEFAULT_ROOM_RULES)
    
    # Check if explicitly avoided
    if rules_1.get("avoid", {}).get(room_type_2):
        return False, f"{room_type_1} should not touch {room_type_2}"
    
    if rules_2.get("avoid", {}).get(room_type_1):
        return False, f"{room_type_2} should not touch {room_type_1}"
    
    # Check if preferred
    if room_type_2 in rules_1.get("prefer", {}):
        return True, "Preferred connection"
    
    if room_type_1 in rules_2.get("prefer", {}):
        return True, "Preferred connection"
    
    # Neutral - not preferred but not avoided
    return True, "Neutral connection"


# =========================
# ZONE CLASSIFICATION
# =========================
ROOM_ZONES = {
    "public": ["living", "dining", "hall"],
    "semi_public": ["kitchen"],
    "private": ["bedroom", "study"],
    "service": ["bathroom", "storage", "utility", "laundry"],
    "spiritual": ["pooja", "meditation"],
    "outdoor": ["balcony", "garden", "terrace"],
}

def get_room_zone(room_type):
    """Get the zone classification for a room type"""
    for zone, types in ROOM_ZONES.items():
        if room_type in types:
            return zone
    return "other"


# =========================
# ARCHITECTURAL CONSTRAINTS
# =========================
ARCHITECTURAL_RULES = {
    # Rule 1: Privacy gradient
    "privacy_gradient": {
        "public": 1,
        "semi_public": 2,
        "private": 3,
        "service": 4,
    },
    
    # Rule 2: Minimum distances (conceptual)
    "separation": {
        ("bedroom", "kitchen"): "Must not be adjacent",
        ("bathroom", "kitchen"): "Must not be adjacent",
        ("bathroom", "dining"): "Must not be adjacent",
    },
    
    # Rule 3: Required connections
    "must_connect_to_hub": ["kitchen", "bedroom", "dining"],
    
    # Rule 4: Terminal nodes (nothing should be behind these)
    "terminal_nodes": ["bathroom", "storage", "balcony"],
}