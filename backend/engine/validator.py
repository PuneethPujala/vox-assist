"""
Unified Architectural Validator for VoxAssist.
Evaluates floor-plan layouts against architectural constraints and returns structured
feasibility reports (feasibility_score, checks_passed, violations, details).
"""

from typing import Dict, Any, List, Optional
from shapely.geometry import Polygon
try:
    from constraints.jurisdiction_profiles import get_profile
    from constraints.envelope import validate_envelope_containment, compute_building_envelope
    from constraints.room_dimensions import validate_all_room_dimensions
    from constraints.egress import validate_bedroom_exterior_access
    from constraints.wet_areas import validate_wet_area_clustering
    from constraints.furniture import validate_furniture_clearance
    from constraints.human_usability import (
        validate_bathroom_single_access,
        validate_living_focal_orientation,
        validate_window_daylighting,
        validate_room_door_accessibility,
    )
    from constraints.circulation import validate_circulation_continuity
except ImportError:
    from engine.constraints.jurisdiction_profiles import get_profile
    from engine.constraints.envelope import validate_envelope_containment, compute_building_envelope
    from engine.constraints.room_dimensions import validate_all_room_dimensions
    from engine.constraints.egress import validate_bedroom_exterior_access
    from engine.constraints.wet_areas import validate_wet_area_clustering
    from engine.constraints.furniture import validate_furniture_clearance
    from engine.constraints.human_usability import (
        validate_bathroom_single_access,
        validate_living_focal_orientation,
        validate_window_daylighting,
        validate_room_door_accessibility,
    )
    from engine.constraints.circulation import validate_circulation_continuity

class LayoutValidator:
    @staticmethod
    def validate_layout(
        layout: Dict[str, Any],
        envelope_poly: Optional[Polygon] = None,
        profile_name: str = "DEFAULT"
    ) -> Dict[str, Any]:
        """
        Executes comprehensive architectural validation on a synthesized layout.
        
        Args:
            layout: Dict containing 'rooms' (Dict[str, Polygon]) and optional metadata.
            envelope_poly: Predefined building envelope polygon. If None, derived from net room area.
            profile_name: Code profile identifier.
            
        Returns:
            Dict matching the architectural_check schema:
            {
                "valid": bool,
                "feasibility_score": int (0-100),
                "checks_passed": int,
                "checks_total": int,
                "checks": List[Dict],
                "violations": List[str],
                "warnings": List[str]
            }
        """
        profile = get_profile(profile_name)
        rooms = layout.get("rooms", {})
        
        if not rooms:
            return {
                "valid": False,
                "feasibility_score": 0,
                "checks_passed": 0,
                "checks_total": 7,
                "checks": [],
                "violations": ["Layout contains no rooms"],
                "warnings": []
            }
            
        # Extract valid Shapely Polygons
        active_rooms: Dict[str, Polygon] = {
            k: v for k, v in rooms.items()
            if v is not None and not v.is_empty and isinstance(v, Polygon)
        }
        
        if not active_rooms:
            return {
                "valid": False,
                "feasibility_score": 0,
                "checks_passed": 0,
                "checks_total": 7,
                "checks": [],
                "violations": ["No valid geometric polygons found in layout"],
                "warnings": []
            }

        checks: List[Dict[str, Any]] = []
        violations: List[str] = []
        warnings: List[str] = []
        
        # -------------------------------------------------------------
        # CHECK 1: Building Envelope Containment (HARD)
        # -------------------------------------------------------------
        if envelope_poly is None:
            # Derive target envelope from actual room area
            total_net_area = sum(p.area for p in active_rooms.values())
            circ_factor = profile.get("envelope", {}).get("circulation_factor", 0.20)
            env_data = compute_building_envelope(total_net_area, aspect_ratio=1.20, circulation_factor=circ_factor)
            envelope_poly = env_data["polygon"]
            
        env_valid, overflow_sqm, overflow_rooms = validate_envelope_containment(
            active_rooms, envelope_poly
        )
        
        if env_valid:
            checks.append({
                "id": "envelope",
                "name": "Building Envelope",
                "status": "pass",
                "details": f"All {len(active_rooms)} rooms contained within footprint ({round(envelope_poly.area, 1)}m² envelope)"
            })
        else:
            violations.append(
                f"Rooms extend outside envelope: {', '.join(overflow_rooms)} ({overflow_sqm}m² overflow)"
            )
            checks.append({
                "id": "envelope",
                "name": "Building Envelope",
                "status": "fail",
                "details": f"{len(overflow_rooms)} room(s) overflow envelope by {overflow_sqm}m²"
            })

        # -------------------------------------------------------------
        # CHECK 2: Room Dimensions & Aspect Ratios (HARD)
        # -------------------------------------------------------------
        dims_valid, per_room_dims, dim_violations = validate_all_room_dimensions(
            active_rooms, profile
        )
        
        critical_dim_failures = []
        mild_dim_warnings = []
        
        for r_res in per_room_dims:
            if not r_res["valid"]:
                for v in r_res["violations"]:
                    if "Aspect ratio" in v or "Clear width" in v:
                        critical_dim_failures.append(f"{r_res['room']}: {v}")
                    else:
                        mild_dim_warnings.append(f"{r_res['room']}: {v}")
                        
        if len(critical_dim_failures) == 0:
            if len(mild_dim_warnings) == 0:
                checks.append({
                    "id": "dimensions",
                    "name": "Room Dimensions & Proportions",
                    "status": "pass",
                    "details": f"All {len(active_rooms)} rooms satisfy habitable width and aspect ratio limits"
                })
            else:
                warnings.extend(mild_dim_warnings)
                checks.append({
                    "id": "dimensions",
                    "name": "Room Dimensions & Proportions",
                    "status": "warn",
                    "details": f"Dimensions meet width/aspect rules with slight area variance ({len(mild_dim_warnings)} rooms)"
                })
        else:
            violations.extend(critical_dim_failures)
            checks.append({
                "id": "dimensions",
                "name": "Room Dimensions & Proportions",
                "status": "fail",
                "details": f"{len(critical_dim_failures)} room(s) violate habitable proportions or minimum width"
            })

        # -------------------------------------------------------------
        # CHECK 3: Bedroom Exterior Light & Egress (HARD)
        # -------------------------------------------------------------
        egress_res = validate_bedroom_exterior_access(active_rooms, profile)
        
        if egress_res["valid"]:
            b_count = egress_res["bedrooms_checked"]
            checks.append({
                "id": "egress",
                "name": "Bedroom Exterior Light & Egress",
                "status": "pass",
                "details": f"All {b_count} bedroom(s) have direct exterior wall exposure (avg {round(sum(egress_res['wall_lengths'].values()) / max(1, b_count), 1)}m)"
            })
        else:
            violations.extend(egress_res["violations"])
            checks.append({
                "id": "egress",
                "name": "Bedroom Exterior Light & Egress",
                "status": "fail",
                "details": f"{len(egress_res['landlocked_bedrooms'])} bedroom(s) lack required exterior wall exposure"
            })

        # -------------------------------------------------------------
        # CHECK 4: Door Clearance & Openings (SOFT)
        # -------------------------------------------------------------
        entrance = layout.get("entrance")
        doors = layout.get("doors")
        openings = layout.get("openings", [])
        door_status = "pass"
        door_details = "Code-compliant main entrance and interior door openings placed"
        
        # 1. Test bathroom single access constraint
        bath_access = validate_bathroom_single_access(active_rooms, doors if doors is not None else openings)
        if not bath_access["valid"]:
            door_status = "fail"
            door_details = f"{len(bath_access['violations'])} pass-through bathroom(s) detected: multiple entrances compromise privacy"
            violations.extend(bath_access["violations"])
            
        # 2. Test room door accessibility (no landlocked rooms, solitary bath common access)
        if doors is not None or openings or "doors" in layout or "openings" in layout:
            access_res = validate_room_door_accessibility(active_rooms, doors_input=doors, openings=openings)
            if not access_res["valid"]:
                door_status = "fail"
                door_details = access_res["details"]
                violations.extend(access_res["violations"])
            if access_res.get("warnings"):
                warnings.extend(access_res["warnings"])

        if door_status == "pass":
            if ("doors" in layout or "entrance" in layout or "openings" in layout) and not entrance and len(active_rooms) > 1:
                door_status = "warn"
                door_details = "Layout lacks a designated exterior entry door"
                warnings.append(door_details)
            elif entrance:
                door_details = "Main entrance placed on exterior wall; direct circulation access for all rooms with single private bathroom entries"
            
        checks.append({
            "id": "doors",
            "name": "Door Clearance & Openings",
            "status": door_status,
            "details": door_details
        })

        # -------------------------------------------------------------
        # CHECK 5: Core Circulation & Zoning (SOFT)
        # -------------------------------------------------------------
        living_rooms = [k for k in active_rooms if k.startswith("living")]
        bedrooms = [k for k in active_rooms if k.startswith("bedroom")]
        
        circulation_pass = True
        circ_details = "Public living core connects directly to functional zones"
        
        if not living_rooms and len(active_rooms) > 2:
            circulation_pass = False
            circ_details = "Missing central public circulation hub (Living Room)"
            warnings.append(circ_details)
        else:
            focal_res = validate_living_focal_orientation(active_rooms, doors)
            if not focal_res["valid"]:
                warnings.append(focal_res["details"])
                circ_details = focal_res["details"]
            elif len(bedrooms) > 1:
                circ_details = f"{len(bedrooms)} bedrooms properly isolated from service entries; living room accommodates focal media wall"

            if openings:
                cont_res = validate_circulation_continuity(active_rooms, openings, entrance)
                if not cont_res["valid"]:
                    warnings.append(cont_res["details"])
                    circ_details = cont_res["details"]
                    circulation_pass = False
                elif circ_details == "Public living core connects directly to functional zones":
                    circ_details = cont_res["details"]
            
        checks.append({
            "id": "circulation",
            "name": "Circulation & Zoning",
            "status": "pass" if circulation_pass else "warn",
            "details": circ_details
        })

        # -------------------------------------------------------------
        # CHECK 6: Wet-Wall Clustering (SOFT)
        # -------------------------------------------------------------
        wet_res = validate_wet_area_clustering(active_rooms)
        checks.append({
            "id": "wet_wall",
            "name": "Wet-Wall Clustering",
            "status": wet_res["status"],
            "details": wet_res["details"]
        })
        if wet_res["warnings"]:
            warnings.extend(wet_res["warnings"])

        # -------------------------------------------------------------
        # CHECK 7: Furniture Clearance & Usability (SOFT)
        # -------------------------------------------------------------
        windows_data = layout.get("windows")
        if windows_data is None:
            try:
                from engine.window_generator import generate_windows
                windows_data = generate_windows(active_rooms, doors_geom=doors, entrance_geom=entrance)
            except Exception:
                try:
                    from window_generator import generate_windows
                    windows_data = generate_windows(active_rooms, doors_geom=doors, entrance_geom=entrance)
                except Exception:
                    windows_data = None

        furn_res = validate_furniture_clearance(
            active_rooms,
            openings=openings,
            doors=doors,
            windows=windows_data,
            placed_furniture=layout.get("furniture"),
            entrance=entrance
        )
        checks.append({
            "id": "furniture",
            "name": "Furniture Clearance & Usability",
            "status": furn_res["status"],
            "details": furn_res["details"],
            "subchecks": furn_res.get("subchecks", [])
        })
        if furn_res.get("warnings"):
            warnings.extend(furn_res["warnings"])

        # -------------------------------------------------------------
        # COMPUTE FEASIBILITY SCORE & AGGREGATE
        # -------------------------------------------------------------
        checks_passed = sum(1 for c in checks if c["status"] == "pass")
        checks_warn = sum(1 for c in checks if c["status"] == "warn")
        checks_total = len(checks)
        
        # Hard constraints strictly determine overall validity
        overall_valid = len(violations) == 0
        
        # Score calculation: weighted sum across all 7 checks
        raw_score = ((checks_passed * 1.0) + (checks_warn * 0.65)) / max(1, checks_total) * 100
        feasibility_score = max(0, min(100, int(round(raw_score))))
        
        return {
            "valid": overall_valid,
            "feasibility_score": feasibility_score,
            "checks_passed": checks_passed,
            "checks_total": checks_total,
            "checks": checks,
            "violations": violations,
            "warnings": warnings,
            "envelope_area": round(envelope_poly.area, 1)
        }

def validate_layout(
    layout: Dict[str, Any],
    envelope_poly: Optional[Polygon] = None,
    profile_name: str = "DEFAULT"
) -> Dict[str, Any]:
    """Convenience wrapper for LayoutValidator.validate_layout."""
    return LayoutValidator.validate_layout(layout, envelope_poly, profile_name)
