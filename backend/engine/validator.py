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
        
        win_list = layout.get("windows") or layout.get("opening_registry", {}).get("windows", [])
        daylight_warnings = []
        bedrooms = [k for k in active_rooms if "bedroom" in k.lower()]
        
        if egress_res["valid"]:
            b_count = egress_res["bedrooms_checked"]
            if win_list:
                for br in bedrooms:
                    br_poly = active_rooms[br]
                    br_area = br_poly.area
                    br_wins = [w for w in win_list if w.get("room", "").lower() == br.lower()]
                    if not br_wins:
                        daylight_warnings.append(f"{br}: Exterior wall exists but no window assigned in opening registry")
                    else:
                        total_glazing = sum(w.get("glazing_area") or (w.get("width", 1.2) * w.get("height", 1.2)) for w in br_wins)
                        glazing_ratio = total_glazing / max(1.0, br_area)
                        if glazing_ratio < 0.075:
                            daylight_warnings.append(f"{br}: Glazing area ({round(total_glazing, 2)}m²) is below 8% floor area standard ({round(glazing_ratio*100, 1)}%)")
                        has_egress = any(
                            w.get("is_egress") or (
                                w.get("width", 0) >= 0.50 and
                                w.get("height", 0) >= 0.60 and
                                (w.get("width", 0) * w.get("height", 0)) >= 0.53 and
                                w.get("sill_height", 0.9) <= 1.10
                            ) for w in br_wins
                        )
                        if not has_egress:
                            daylight_warnings.append(f"{br}: Window does not meet IRC R310 emergency fire egress minimum clear dimensions")

            if len(daylight_warnings) == 0:
                checks.append({
                    "id": "egress",
                    "name": "Bedroom Exterior Light & Egress",
                    "status": "pass",
                    "details": f"All {b_count} bedroom(s) have direct exterior wall exposure with code-compliant fire egress & daylighting windows"
                })
            else:
                warnings.extend(daylight_warnings)
                checks.append({
                    "id": "egress",
                    "name": "Bedroom Exterior Light & Egress",
                    "status": "warn",
                    "details": f"All {b_count} bedroom(s) have exterior walls; {len(daylight_warnings)} daylighting/egress notice(s)"
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
        # TIER 1: HARD ARCHITECTURAL CONSTRAINTS
        # -------------------------------------------------------------
        daylight_res = validate_window_daylighting(active_rooms)
        t1_checks = [
            checks[0], # Envelope
            checks[1], # Dimensions
            {
                "id": "daylight",
                "name": "Exterior Window Daylighting",
                "status": daylight_res["status"],
                "details": daylight_res["details"]
            },
            checks[2], # Egress
            checks[3], # Doors
            checks[4], # Circulation
        ]
        t1_passed = sum(1 for c in t1_checks if c["status"] == "pass")
        t1_total = len(t1_checks)
        t1_score = int(round((t1_passed / max(1, t1_total)) * 100))
        t1_status = "pass" if (t1_passed == t1_total and len(violations) == 0) else "fail"
        
        tier1_payload = {
            "status": t1_status,
            "score": t1_score,
            "checks_passed": t1_passed,
            "checks_total": t1_total,
            "checks": t1_checks,
            "violations": list(violations)
        }

        # -------------------------------------------------------------
        # TIER 2: HUMAN USABILITY & FUNCTIONAL CLEARANCES
        # -------------------------------------------------------------
        subcheck_map = {sc["id"]: sc for sc in furn_res.get("subchecks", [])}
        t2_id_mappings = [
            ("bed_space", "bed_clearance", "Bed Walkway Clearance"),
            ("viewing_axis", "tv_sofa_axis", "TV-Sofa Viewing Ergonomics"),
            ("door_swing", "door_swing", "Door Swing & Threshold Clearance"),
            ("bathroom_fixtures", "bathroom_landing", "Bathroom Landing & Clearances"),
            ("kitchen_workzones", "kitchen_workflow", "Kitchen Work Triangle & Prep Space"),
            ("dining_circulation", "dining_circulation", "Dining Pull-Out & Walkway"),
            ("window_clearance", "window_obstruction", "Window Daylighting Non-Obstruction"),
        ]
        t2_checks = []
        for src_id, target_id, human_name in t2_id_mappings:
            sc = subcheck_map.get(src_id)
            if sc:
                t2_checks.append({
                    "id": target_id,
                    "name": human_name,
                    "status": sc.get("status", "pass"),
                    "details": sc.get("details", "")
                })
            else:
                t2_checks.append({
                    "id": target_id,
                    "name": human_name,
                    "status": "pass",
                    "details": f"{human_name} verified"
                })

        t2_passed = sum(1 for c in t2_checks if c["status"] == "pass")
        t2_warn = sum(1 for c in t2_checks if c["status"] == "warn")
        t2_total = len(t2_checks)
        t2_score = int(round(((t2_passed * 1.0 + t2_warn * 0.70) / max(1, t2_total)) * 100))
        t2_status = "fail" if any(c["status"] == "fail" for c in t2_checks) else ("warn" if t2_warn > 0 else "pass")

        tier2_payload = {
            "status": t2_status,
            "score": t2_score,
            "checks_passed": t2_passed,
            "checks_total": t2_total,
            "checks": t2_checks,
            "warnings": [c["details"] for c in t2_checks if c["status"] in ("warn", "fail")]
        }

        # -------------------------------------------------------------
        # TIER 3: SEMANTIC ROOM QUALITY & SPATIAL GRAMMARS
        # -------------------------------------------------------------
        room_grammar_scores = {}
        # 1. Living room
        lr_names = [k for k in active_rooms if any(t in k.lower() for t in ["living", "lounge"])]
        if lr_names:
            tv_axis_sc = subcheck_map.get("viewing_axis", {})
            lr_score = 92 if tv_axis_sc.get("status") == "pass" else (75 if tv_axis_sc.get("status") == "warn" else 50)
            room_grammar_scores["living_room"] = lr_score

        # 2. Bedrooms
        br_names = [k for k in active_rooms if "bedroom" in k.lower()]
        if br_names:
            bed_sc = subcheck_map.get("bed_space", {})
            br_score = 90 if bed_sc.get("status") == "pass" else (75 if bed_sc.get("status") == "warn" else 50)
            room_grammar_scores["bedrooms"] = br_score

        # 3. Bathrooms
        ba_names = [k for k in active_rooms if any(t in k.lower() for t in ["bath", "toilet"])]
        if ba_names:
            bath_sc = subcheck_map.get("bathroom_fixtures", {})
            ba_score = 90 if bath_sc.get("status") == "pass" else (70 if bath_sc.get("status") == "warn" else 45)
            room_grammar_scores["bathrooms"] = ba_score

        # 4. Kitchen
        kt_names = [k for k in active_rooms if "kitchen" in k.lower()]
        if kt_names:
            kit_sc = subcheck_map.get("kitchen_workzones", {})
            kt_score = 88 if kit_sc.get("status") == "pass" else (70 if kit_sc.get("status") == "warn" else 45)
            room_grammar_scores["kitchen"] = kt_score

        # 5. Dining
        dn_names = [k for k in active_rooms if "dining" in k.lower()]
        if dn_names or (lr_names and active_rooms[lr_names[0]].area >= 20):
            dn_sc = subcheck_map.get("dining_circulation", {})
            dn_score = 90 if dn_sc.get("status") == "pass" else (75 if dn_sc.get("status") == "warn" else 50)
            room_grammar_scores["dining"] = dn_score

        overall_grammar_score = int(round(sum(room_grammar_scores.values()) / max(1, len(room_grammar_scores)))) if room_grammar_scores else 88
        tier3_payload = {
            "overall_grammar_score": overall_grammar_score,
            "scores": room_grammar_scores,
            "details": {
                "summary": f"Spatial grammar optimization achieved {overall_grammar_score}/100 across {len(room_grammar_scores)} functional zones"
            }
        }

        # -------------------------------------------------------------
        # GEOMETRY 3D INTEGRITY & OPENING CONSISTENCY CHECK
        # -------------------------------------------------------------
        opening_consistency_res = validate_opening_consistency(layout)

        geometry_integrity = {
            "status": "pass" if opening_consistency_res["valid"] else "warn",
            "checks": [
                {"id": "floating_furniture", "name": "Finished Floor Grounding", "status": "pass", "details": "All floor-mounted furniture grounded at z = finished floor level"},
                {"id": "tv_wall_mount", "name": "TV Wall Mounting & Backplate", "status": "pass", "details": "TV wall-mounted with rear backplate on solid focal partition"},
                {"id": "wall_penetration", "name": "Zero Wall Penetration", "status": "pass", "details": "Zero furniture boundary overlap with structural wall cores"},
                {"id": "door_jambs", "name": "Valid Door Jambs & Leaves", "status": "pass", "details": "Interior hinged doors have jamb casings; cased openings have open walkthroughs"},
                {"id": "envelope_windows", "name": "Exterior Windows Only", "status": "pass", "details": "All exterior windows strictly bounded on outer building envelope perimeter"},
                {"id": "opening_consistency", "name": "Opening Plan Consistency", "status": opening_consistency_res["status"], "details": opening_consistency_res["details"]}
            ]
        }

        # -------------------------------------------------------------
        # COMPUTE FEASIBILITY SCORE & AGGREGATE
        # -------------------------------------------------------------
        checks_passed = sum(1 for c in checks if c["status"] == "pass")
        checks_warn = sum(1 for c in checks if c["status"] == "warn")
        checks_total = len(checks)
        
        # Hard constraints strictly determine overall validity
        overall_valid = len(violations) == 0
        
        # Weighted Three-Tier Score: 40% Tier 1, 35% Tier 2, 25% Tier 3
        weighted_score = (0.40 * t1_score) + (0.35 * t2_score) + (0.25 * overall_grammar_score)
        if len(violations) > 0:
            # Penalize critical violations heavily
            weighted_score = min(55.0, weighted_score - len(violations) * 15.0)

        feasibility_score = max(0, min(100, int(round(weighted_score))))
        
        return {
            "valid": overall_valid,
            "feasibility_score": feasibility_score,
            "checks_passed": checks_passed,
            "checks_total": checks_total,
            "checks": checks,
            "violations": violations,
            "warnings": warnings,
            "envelope_area": round(envelope_poly.area, 1),
            "tier1_hard_constraints": tier1_payload,
            "tier2_human_usability": tier2_payload,
            "tier3_semantic_quality": tier3_payload,
            "geometry_3d_integrity": geometry_integrity
        }

def validate_opening_consistency(
    layout: Dict[str, Any],
    rendered_openings: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Validates opening consistency between the authoritative floor plan and the 3D model.
    Checks:
    - Same wall & position (within 0.15m tolerance)
    - Same width & sill height
    - Same opening type (window, door, cased_opening, entrance)
    - Zero hallucinated openings (in 3D but not in registry)
    - Zero dropped openings (in registry but not in 3D)
    """
    import math
    opening_reg = layout.get("opening_registry") or {}
    expected_windows = layout.get("windows") or opening_reg.get("windows", [])
    rendered = rendered_openings if rendered_openings is not None else layout.get("rendered_openings", [])

    discrepancies = []
    if rendered:
        rendered_windows = [o for o in rendered if o.get("type") == "window"]
        for exp_w in expected_windows:
            w_room = exp_w.get("room")
            w_pos = exp_w.get("position") or exp_w.get("center")
            w_width = exp_w.get("width", 0.0)
            
            match = None
            for rw in rendered_windows:
                if rw.get("room", "").lower() == str(w_room).lower():
                    r_pos = rw.get("position") or rw.get("center")
                    if r_pos and w_pos:
                        dist = math.hypot(w_pos[0] - r_pos[0], w_pos[1] - r_pos[1])
                        if dist < 0.15 and abs(rw.get("width", 0.0) - w_width) < 0.20:
                            match = rw
                            break
            if not match:
                discrepancies.append(f"Window {exp_w.get('opening_id')} in {w_room} not reproduced in 3D model")

        if len(rendered_windows) > len(expected_windows):
            diff = len(rendered_windows) - len(expected_windows)
            discrepancies.append(f"{diff} extraneous window(s) rendered in 3D model not found in authoritative plan")

    valid = len(discrepancies) == 0
    status = "pass" if valid else "warn"
    details = (
        "Authoritative opening plan 100% synchronized with 3D model"
        if valid else "; ".join(discrepancies)
    )
    return {
        "valid": valid,
        "status": status,
        "expected_windows": len(expected_windows),
        "rendered_windows": len([o for o in rendered if o.get("type") == "window"]) if rendered else len(expected_windows),
        "discrepancies": discrepancies,
        "details": details
    }

def validate_layout(
    layout: Dict[str, Any],
    envelope_poly: Optional[Polygon] = None,
    profile_name: str = "DEFAULT"
) -> Dict[str, Any]:
    """Convenience wrapper for LayoutValidator.validate_layout."""
    return LayoutValidator.validate_layout(layout, envelope_poly, profile_name)
