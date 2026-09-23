"""
Room-Specific Architectural Furniture Grammars for VoxAssist.
Implements:
1. Coupled Living Room Group Solver (TV + Console + Viewing Zone + Sofa + Table + Rug)
2. Adaptive Bathroom Candidate Solver (Door Landing + Vanity + WC + Enclosed Glass Shower)
3. Kitchen Work-Zone Solver (Cold Storage -> Prep -> Sink -> Prep -> Cooktop -> Upper Cabinets)
"""
import math
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from shapely.geometry import box, Polygon, Point, LineString
from shapely.ops import unary_union

try:
    from constraints.furniture_constants import (
        BATHROOM_ENTRY_LANDING, DOOR_CLEARANCE, DOOR_SWING_ANGLE_RAD,
        TV_VIEWING_RATIO_MIN, TV_VIEWING_RATIO_MAX, TV_MIN_DISTANCE, TV_MAX_DISTANCE,
        TV_MOUNT_CENTER_HEIGHT, MEDIA_CONSOLE_HEIGHT, MEDIA_CONSOLE_DEPTH,
        SOFA_DEPTH, COFFEE_TABLE_DISTANCE, SHOWER_SIZES, SHOWER_GLASS_HEIGHT,
        SHOWER_TRAY_CURB, VANITY_WIDTH, VANITY_DEPTH, VANITY_HEIGHT,
        WC_WIDTH, WC_DEPTH, WC_HEIGHT, WC_FRONT_CLEARANCE, WC_SIDE_CLEARANCE,
        VANITY_FRONT_CLEARANCE, SHOWER_ENTRY_CLEARANCE, COUNTER_DEPTH, COUNTER_HEIGHT,
        REFRIGERATOR_WIDTH, REFRIGERATOR_DEPTH, REFRIGERATOR_HEIGHT,
        SINK_WIDTH, COOKTOP_WIDTH, RANGE_HOOD_HEIGHT, UPPER_CABINET_DEPTH,
        UPPER_CABINET_BOTTOM, UPPER_CABINET_TOP
    )
except ImportError:
    try:
        from engine.constraints.furniture_constants import (
            BATHROOM_ENTRY_LANDING, DOOR_CLEARANCE, DOOR_SWING_ANGLE_RAD,
            TV_VIEWING_RATIO_MIN, TV_VIEWING_RATIO_MAX, TV_MIN_DISTANCE, TV_MAX_DISTANCE,
            TV_MOUNT_CENTER_HEIGHT, MEDIA_CONSOLE_HEIGHT, MEDIA_CONSOLE_DEPTH,
            SOFA_DEPTH, COFFEE_TABLE_DISTANCE, SHOWER_SIZES, SHOWER_GLASS_HEIGHT,
            SHOWER_TRAY_CURB, VANITY_WIDTH, VANITY_DEPTH, VANITY_HEIGHT,
            WC_WIDTH, WC_DEPTH, WC_HEIGHT, WC_FRONT_CLEARANCE, WC_SIDE_CLEARANCE,
            VANITY_FRONT_CLEARANCE, SHOWER_ENTRY_CLEARANCE, COUNTER_DEPTH, COUNTER_HEIGHT,
            REFRIGERATOR_WIDTH, REFRIGERATOR_DEPTH, REFRIGERATOR_HEIGHT,
            SINK_WIDTH, COOKTOP_WIDTH, RANGE_HOOD_HEIGHT, UPPER_CABINET_DEPTH,
            UPPER_CABINET_BOTTOM, UPPER_CABINET_TOP
        )
    except ImportError:
        from backend.engine.constraints.furniture_constants import (
            BATHROOM_ENTRY_LANDING, DOOR_CLEARANCE, DOOR_SWING_ANGLE_RAD,
            TV_VIEWING_RATIO_MIN, TV_VIEWING_RATIO_MAX, TV_MIN_DISTANCE, TV_MAX_DISTANCE,
            TV_MOUNT_CENTER_HEIGHT, MEDIA_CONSOLE_HEIGHT, MEDIA_CONSOLE_DEPTH,
            SOFA_DEPTH, COFFEE_TABLE_DISTANCE, SHOWER_SIZES, SHOWER_GLASS_HEIGHT,
            SHOWER_TRAY_CURB, VANITY_WIDTH, VANITY_DEPTH, VANITY_HEIGHT,
            WC_WIDTH, WC_DEPTH, WC_HEIGHT, WC_FRONT_CLEARANCE, WC_SIDE_CLEARANCE,
            VANITY_FRONT_CLEARANCE, SHOWER_ENTRY_CLEARANCE, COUNTER_DEPTH, COUNTER_HEIGHT,
            REFRIGERATOR_WIDTH, REFRIGERATOR_DEPTH, REFRIGERATOR_HEIGHT,
            SINK_WIDTH, COOKTOP_WIDTH, RANGE_HOOD_HEIGHT, UPPER_CABINET_DEPTH,
            UPPER_CABINET_BOTTOM, UPPER_CABINET_TOP
        )


# ==============================================================================
# 1. COUPLED LIVING ROOM GROUP SOLVER
# ==============================================================================

def solve_living_room_group(
    room_poly: Polygon,
    door_polys: Optional[List[Polygon]] = None,
    openings: Optional[List[Dict[str, Any]]] = None,
    windows: Optional[List[Dict[str, Any]]] = None,
    foyer_keepout: Optional[Polygon] = None,
    protected_circ: Optional[Polygon] = None,
    wall_graph: Optional[Dict[Tuple[Tuple[float, float], Tuple[float, float]], List[str]]] = None,
    entrance_geom: Optional[Polygon] = None,
    scale: float = 1.0
) -> Dict[str, Any]:
    """
    Solves TV, media console, viewing axis, coffee table, rug, and sofa as
    a unified, coupled LivingRoomFurnitureGroup.
    """
    door_polys = door_polys or []
    openings = openings or []
    windows = windows or []

    minx, miny, maxx, maxy = room_poly.bounds
    cx, cy = room_poly.centroid.x, room_poly.centroid.y
    w, h = maxx - minx, maxy - miny

    walls = {
        "south": LineString([(minx, miny), (maxx, miny)]),
        "north": LineString([(minx, maxy), (maxx, maxy)]),
        "west":  LineString([(minx, miny), (minx, maxy)]),
        "east":  LineString([(maxx, miny), (maxx, maxy)]),
    }

    # Find entrance door geometry and wall
    entrance_wall = None
    entrance_centroid = None
    if entrance_geom is not None and not entrance_geom.is_empty:
        entrance_centroid = entrance_geom.centroid
        for w_side, w_line in walls.items():
            if entrance_geom.distance(w_line) < 0.45:
                entrance_wall = w_side
                break
    else:
        for op in openings:
            if op.get("type") == "entrance" or "exterior" in op.get("rooms", ()):
                ep = op.get("polygon")
                if ep and not ep.is_empty:
                    entrance_geom = ep
                    entrance_centroid = ep.centroid
                    for w_side, w_line in walls.items():
                        if ep.distance(w_line) < 0.45:
                            entrance_wall = w_side
                            break
                    break

    candidates = []
    rejection_log = []

    # TV physical dimensions
    tv_w = min(1.80 * scale, max(1.20, (w if w < h else h) * 0.40))
    console_d = MEDIA_CONSOLE_DEPTH * scale
    sofa_w = min(2.40 * scale, max(1.80, tv_w * 1.25))
    sofa_d = SOFA_DEPTH * scale

    for w_side, w_line in walls.items():
        reasons = []

        # 1. Entrance Wall Check
        if w_side == entrance_wall:
            reasons.append("Wall contains main entrance arrival threshold")

        # 2. Window Wall Check
        has_win = any(w_line.buffer(0.05).contains(win.get("wall_segment", LineString())) for win in windows)
        if has_win:
            reasons.append("Wall contains exterior daylighting window opening")

        # 3. Door Cut Check
        door_cuts = [dp for dp in door_polys if dp.intersects(w_line.buffer(0.25))]
        if len(door_cuts) >= 2:
            reasons.append(f"Wall is heavily fragmented by {len(door_cuts)} doorway cuts")

        # 4. Interior Wall status (bonus)
        is_interior = False
        if wall_graph:
            for (p1, p2), sharing in wall_graph.items():
                inter = LineString([p1, p2]).intersection(w_line.buffer(0.05))
                if inter.length > 0.5 and len(sharing) > 1:
                    is_interior = True
                    break

        # Adjust conversation center away from foyer arrival zone if present
        furn_cy = cy
        furn_cx = cx
        if foyer_keepout:
            fb = foyer_keepout.bounds
            if entrance_wall == "south" and cy - 1.2 * scale < fb[3]:
                furn_cy = min(maxy - 1.3 * scale, fb[3] + 1.2 * scale)
            elif entrance_wall == "north" and cy + 1.2 * scale > fb[1]:
                furn_cy = max(miny + 1.3 * scale, fb[1] - 1.2 * scale)
            elif entrance_wall == "west" and cx - 1.2 * scale < fb[2]:
                furn_cx = min(maxx - 1.3 * scale, fb[2] + 1.2 * scale)
            elif entrance_wall == "east" and cx + 1.2 * scale > fb[0]:
                furn_cx = max(minx + 1.3 * scale, fb[0] - 1.2 * scale)

        # Calculate Inward Normal and Optimal Viewing Distance
        if w_side == "south":
            normal = np.array([0.0, 1.0])
            room_depth = h
            tv_center = (furn_cx, miny + 0.05 + console_d / 2.0)
            wall_pt = miny
        elif w_side == "north":
            normal = np.array([0.0, -1.0])
            room_depth = h
            tv_center = (furn_cx, maxy - 0.05 - console_d / 2.0)
            wall_pt = maxy
        elif w_side == "west":
            normal = np.array([1.0, 0.0])
            room_depth = w
            tv_center = (minx + 0.05 + console_d / 2.0, furn_cy)
            wall_pt = minx
        else: # east
            normal = np.array([-1.0, 0.0])
            room_depth = w
            tv_center = (maxx - 0.05 - console_d / 2.0, furn_cy)
            wall_pt = maxx

        # Dynamic Viewing Distance: 2.2x TV width, bounded by room dimensions
        ideal_dist = tv_w * 2.2
        target_dist = min(TV_MAX_DISTANCE, max(TV_MIN_DISTANCE, min(ideal_dist, (room_depth - sofa_d - 0.80))))

        # If opposite wall has foyer arrival zone, ensure viewing distance avoids sofa encroachment
        if w_side == "north" and entrance_wall == "south" and foyer_keepout:
            max_dist_for_foyer = (maxy - 0.05 - console_d / 2.0) - (foyer_keepout.bounds[3] + sofa_d / 2.0 + 0.15)
            if max_dist_for_foyer >= TV_MIN_DISTANCE - 0.10:
                target_dist = min(target_dist, max_dist_for_foyer)
        elif w_side == "south" and entrance_wall == "north" and foyer_keepout:
            max_dist_for_foyer = (foyer_keepout.bounds[1] - sofa_d / 2.0 - 0.15) - (miny + 0.05 + console_d / 2.0)
            if max_dist_for_foyer >= TV_MIN_DISTANCE - 0.10:
                target_dist = min(target_dist, max_dist_for_foyer)

        if target_dist < TV_MIN_DISTANCE - 0.20:
            reasons.append(f"Room depth ({room_depth:.2f}m) insufficient for minimum TV-sofa viewing distance")

        # Compute Sofa Box
        sofa_center_x = tv_center[0] + normal[0] * target_dist
        sofa_center_y = tv_center[1] + normal[1] * target_dist

        if w_side in ["south", "north"]:
            sofa_box = box(sofa_center_x - sofa_w / 2.0, sofa_center_y - sofa_d / 2.0,
                           sofa_center_x + sofa_w / 2.0, sofa_center_y + sofa_d / 2.0)
            tv_box = box(tv_center[0] - tv_w / 2.0, min(tv_center[1] - console_d/2, wall_pt),
                         tv_center[0] + tv_w / 2.0, max(tv_center[1] + console_d/2, wall_pt))
        else:
            sofa_box = box(sofa_center_x - sofa_d / 2.0, sofa_center_y - sofa_w / 2.0,
                           sofa_center_x + sofa_d / 2.0, sofa_center_y + sofa_w / 2.0)
        # Check clearance to entrance door centroid and adapt position if needed
        if entrance_centroid:
            if sofa_box.distance(entrance_centroid) < 1.55:
                td_candidates = [target_dist, 2.4, 2.2, 2.0, 1.8]
                if w_side in ["west", "east"]:
                    lat_candidates = [furn_cy]
                    if entrance_centroid.y < cy:
                        lat_candidates.extend([min(maxy - sofa_w/2.0 - 0.20, furn_cy + delta) for delta in [0.2, 0.4, 0.6, 0.8]])
                    else:
                        lat_candidates.extend([max(miny + sofa_w/2.0 + 0.20, furn_cy - delta) for delta in [0.2, 0.4, 0.6, 0.8]])
                else:
                    lat_candidates = [furn_cx]
                    if entrance_centroid.x < cx:
                        lat_candidates.extend([min(maxx - sofa_w/2.0 - 0.20, furn_cx + delta) for delta in [0.2, 0.4, 0.6, 0.8]])
                    else:
                        lat_candidates.extend([max(minx + sofa_w/2.0 + 0.20, furn_cx - delta) for delta in [0.2, 0.4, 0.6, 0.8]])

                found_clear = False
                for lat in lat_candidates:
                    for td in td_candidates:
                        if td < TV_MIN_DISTANCE - 0.05:
                            continue
                        if w_side in ["south", "north"]:
                            scx = lat
                            scy = tv_center[1] + normal[1] * td
                            s_box = box(scx - sofa_w/2.0, scy - sofa_d/2.0, scx + sofa_w/2.0, scy + sofa_d/2.0)
                        else:
                            scx = tv_center[0] + normal[0] * td
                            scy = lat
                            s_box = box(scx - sofa_d/2.0, scy - sofa_w/2.0, scx + sofa_d/2.0, scy + sofa_w/2.0)

                        if s_box.distance(entrance_centroid) >= 1.55 and room_poly.buffer(0.05).contains(s_box):
                            sofa_box = s_box
                            sofa_center_x = scx
                            sofa_center_y = scy
                            target_dist = td
                            if w_side in ["west", "east"]:
                                furn_cy = lat
                                tv_center = (tv_center[0], furn_cy)
                                tv_box = box(min(tv_center[0] - console_d/2, wall_pt), tv_center[1] - tv_w / 2.0,
                                             max(tv_center[0] + console_d/2, wall_pt), tv_center[1] + tv_w / 2.0)
                            else:
                                furn_cx = lat
                                tv_center = (furn_cx, tv_center[1])
                                tv_box = box(tv_center[0] - tv_w / 2.0, min(tv_center[1] - console_d/2, wall_pt),
                                             tv_center[0] + tv_w / 2.0, max(tv_center[1] + console_d/2, wall_pt))
                            found_clear = True
                            break
                    if found_clear:
                        break

                if sofa_box.distance(entrance_centroid) < 1.50:
                    reasons.append(f"Sofa is within 1.50m arrival zone of main entrance ({sofa_box.distance(entrance_centroid):.2f}m)")

        # Foyer keep-out check
        if foyer_keepout and sofa_box.intersects(foyer_keepout):
            reasons.append("Sofa encroaches into front entrance foyer arrival zone")

        # Circulation spine check
        if protected_circ and sofa_box.intersects(protected_circ):
            reasons.append("Sofa intersects primary circulation corridor")

        # Room boundary containment check
        if not room_poly.buffer(0.05).contains(sofa_box):
            reasons.append("Sofa exceeds room boundaries")

        # Score candidate
        score = 100.0
        score -= len(reasons) * 50.0
        if is_interior:
            score += 20.0
        score += w_line.length * 2.0
        score -= len(door_cuts) * 15.0

        cand_data = {
            "wall": w_side,
            "score": score,
            "reasons": reasons,
            "tv_center": tv_center,
            "tv_box": tv_box,
            "tv_width": tv_w,
            "sofa_center": (sofa_center_x, sofa_center_y),
            "sofa_box": sofa_box,
            "sofa_width": sofa_w,
            "sofa_depth": sofa_d,
            "viewing_distance": target_dist,
            "normal": normal,
            "is_interior": is_interior,
            "valid": len(reasons) == 0
        }
        candidates.append(cand_data)
        if reasons:
            rejection_log.append(f"Wall {w_side}: {'; '.join(reasons)}")

    # Sort candidates by validity then score
    candidates.sort(key=lambda c: (c["valid"], c["score"]), reverse=True)
    best = candidates[0] if candidates else None

    # Compute coffee table and rug based on best candidate
    if best:
        n = best["normal"]
        tv_c = best["tv_center"]
        dist = best["viewing_distance"]
        
        # Coffee table sits ~0.45m in front of sofa
        table_c = (tv_c[0] + n[0] * (dist - 0.70 * scale), tv_c[1] + n[1] * (dist - 0.70 * scale))
        rug_c = (tv_c[0] + n[0] * (dist - 0.50 * scale), tv_c[1] + n[1] * (dist - 0.50 * scale))
        
        if best["wall"] in ["south", "north"]:
            table_box = box(table_c[0] - 0.50*scale, table_c[1] - 0.28*scale,
                            table_c[0] + 0.50*scale, table_c[1] + 0.28*scale)
            rug_box = box(rug_c[0] - 1.25*scale, rug_c[1] - 0.90*scale,
                          rug_c[0] + 1.25*scale, rug_c[1] + 0.90*scale)
        else:
            table_box = box(table_c[0] - 0.28*scale, table_c[1] - 0.50*scale,
                            table_c[0] + 0.28*scale, table_c[1] + 0.50*scale)
            rug_box = box(rug_c[0] - 0.90*scale, rug_c[1] - 1.25*scale,
                          rug_c[0] + 0.90*scale, rug_c[1] + 1.25*scale)
                          
        best["coffee_table_box"] = table_box
        best["rug_box"] = rug_box
        best["table_center"] = table_c
        best["rejection_log"] = rejection_log

    return best


# ==============================================================================
# 2. ADAPTIVE BATHROOM CANDIDATE SOLVER
# ==============================================================================

def solve_bathroom_fixtures(
    room_poly: Polygon,
    door_polys: Optional[List[Polygon]] = None,
    windows: Optional[List[Dict[str, Any]]] = None,
    wall_graph: Optional[Dict[Tuple[Tuple[float, float], Tuple[float, float]], List[str]]] = None,
    scale: float = 1.0
) -> Dict[str, Any]:
    """
    Adaptive bathroom solver testing archetype candidate layouts:
    - Landing Zone: 0.80m x 0.80m clear box directly inside entrance door.
    - Door Swing: 90-degree functional clearance arc.
    - Fixture Sequence: Door -> Landing -> Vanity/Mirror -> WC -> Glass Enclosed Shower.
    - Full fixture-to-fixture & fixture-to-swing non-overlap.
    """
    door_polys = door_polys or []
    windows = windows or []

    minx, miny, maxx, maxy = room_poly.bounds
    cx, cy = room_poly.centroid.x, room_poly.centroid.y
    w, h = maxx - minx, maxy - miny

    # 1. Identify Door Location and Orientation
    door_wall = "bottom"
    door_center = (cx, miny)
    door_box_geom = None

    if door_polys:
        for dp in door_polys:
            if dp.intersects(room_poly.buffer(0.20)):
                dcx, dcy = dp.centroid.x, dp.centroid.y
                dists = {
                    "bottom": abs(dcy - miny),
                    "top": abs(dcy - maxy),
                    "left": abs(dcx - minx),
                    "right": abs(dcx - maxx)
                }
                door_wall = min(dists, key=dists.get)
                door_center = (dcx, dcy)
                door_box_geom = dp
                break

    # 2. Protected Entry Landing Box (0.80m x 0.80m) & Door Swing
    landing_dim = BATHROOM_ENTRY_LANDING
    dcx, dcy = door_center

    if door_wall == "bottom":
        landing_box = box(dcx - landing_dim/2.0, miny, dcx + landing_dim/2.0, miny + landing_dim)
        swing_box = box(max(minx, dcx - 0.75), miny, min(maxx, dcx + 0.75), miny + 0.75)
    elif door_wall == "top":
        landing_box = box(dcx - landing_dim/2.0, maxy - landing_dim, dcx + landing_dim/2.0, maxy)
        swing_box = box(max(minx, dcx - 0.75), maxy - 0.75, min(maxx, dcx + 0.75), maxy)
    elif door_wall == "left":
        landing_box = box(minx, dcy - landing_dim/2.0, minx + landing_dim, dcy + landing_dim/2.0)
        swing_box = box(minx, max(miny, dcy - 0.75), minx + 0.75, min(maxy, dcy + 0.75))
    else: # right
        landing_box = box(maxx - landing_dim, dcy - landing_dim/2.0, maxx, dcy + landing_dim/2.0)
        swing_box = box(maxx - 0.75, max(miny, dcy - 0.75), maxx, min(maxy, dcy + 0.75))

    protected_entry = unary_union([landing_box, swing_box])

    # 3. Parameterized Shower Sizes adapted to room dimensions and door wall
    if door_wall in ["bottom", "top"]:
        shower_w = 1.10 if w >= 2.3 else 0.90
        shower_d = 1.10 if h >= 2.5 else 0.90
    else:
        shower_w = 1.10 if w >= 2.5 else 0.90
        shower_d = 1.10 if h >= 2.3 else 0.90

    vw, vd = VANITY_WIDTH * scale, VANITY_DEPTH * scale
    tw, td = WC_WIDTH * scale, WC_DEPTH * scale

    # 4. Determine Candidate Shower Corners (away from door wall)
    if door_wall == "bottom":
        corners = [("left", "top"), ("right", "top")]
    elif door_wall == "top":
        corners = [("left", "bottom"), ("right", "bottom")]
    elif door_wall == "left":
        corners = [("right", "top"), ("right", "bottom")]
    else: # right
        corners = [("left", "top"), ("left", "bottom")]

    candidates = []

    for (cx_side, cy_side) in corners:
        sx1 = minx + 0.05 if cx_side == "left" else maxx - 0.05 - shower_w
        sx2 = sx1 + shower_w
        sy1 = miny + 0.05 if cy_side == "bottom" else maxy - 0.05 - shower_d
        sy2 = sy1 + shower_d
        s_box = box(sx1, sy1, sx2, sy2)

        opp_x_side = "right" if cx_side == "left" else "left"
        opp_y_side = "bottom" if cy_side == "top" else "top"

        opt_configs = []

        if door_wall in ["bottom", "top"]:
            # Config 1: Split (Vanity on side wall, WC on back wall next to shower)
            vx1 = maxx - 0.05 - vd if opp_x_side == "right" else minx + 0.05
            vx2 = vx1 + vd
            v_mid_y = cy
            v_box1 = box(vx1, v_mid_y - vw/2.0, vx2, v_mid_y + vw/2.0)

            tx1 = sx2 + 0.15 if cx_side == "left" else sx1 - 0.15 - tw
            tx2 = tx1 + tw
            ty1 = maxy - 0.05 - td if cy_side == "top" else miny + 0.05
            ty2 = ty1 + td
            t_box1 = box(tx1, ty1, tx2, ty2)

            opt_configs.append(("BATH_SPLIT", s_box, v_box1, t_box1, sx2 if cx_side == "left" else sx1))

            # Config 2: Compact (Vanity on back wall next to shower, WC on side wall)
            vx1_2 = sx2 + 0.15 if cx_side == "left" else sx1 - 0.15 - vw
            vx2_2 = vx1_2 + vw
            vy1_2 = maxy - 0.05 - vd if cy_side == "top" else miny + 0.05
            vy2_2 = vy1_2 + vd
            v_box2 = box(vx1_2, vy1_2, vx2_2, vy2_2)

            tx1_2 = maxx - 0.05 - td if opp_x_side == "right" else minx + 0.05
            tx2_2 = tx1_2 + td
            t_box2 = box(tx1_2, cy - tw/2.0, tx2_2, cy + tw/2.0)

            opt_configs.append(("BATH_COMPACT", s_box, v_box2, t_box2, sx2 if cx_side == "left" else sx1))

        else: # door on left or right wall
            # Config 1: Side / Back distribution
            vy1 = maxy - 0.05 - vd if opp_y_side == "top" else miny + 0.05
            vy2 = vy1 + vd
            v_box1 = box(cx - vw/2.0, vy1, cx + vw/2.0, vy2)

            ty1 = sy2 + 0.15 if cy_side == "bottom" else sy1 - 0.15 - tw
            ty2 = ty1 + tw
            tx1 = minx + 0.05 if cx_side == "left" else maxx - 0.05 - td
            tx2 = tx1 + td
            t_box1 = box(tx1, ty1, tx2, ty2)

            opt_configs.append(("BATH_SIDE", s_box, v_box1, t_box1, sx2 if cx_side == "left" else sx1))

        for name, sb, vb, tb, screen_x in opt_configs:
            reasons = []

            # Entry Landing and Door Swing checks
            if sb.intersects(protected_entry):
                reasons.append("Shower intersects doorway landing or swing arc")
            if vb.intersects(protected_entry):
                reasons.append("Vanity blocks doorway landing zone")
            if tb.intersects(protected_entry):
                reasons.append("Toilet bowl intersects door swing arc")

            # Fixture-to-fixture clearance
            if sb.intersects(vb):
                reasons.append("Shower enclosure collides with Vanity")
            if sb.intersects(tb):
                reasons.append("Shower enclosure collides with Toilet")
            if vb.intersects(tb.buffer(0.12)):
                reasons.append("Vanity and Toilet overlap or lack minimum clearance (<0.12m)")

            # Room containment
            if not room_poly.buffer(0.05).contains(sb):
                reasons.append("Shower tray exceeds room boundary")
            if not room_poly.buffer(0.05).contains(vb):
                reasons.append("Vanity exceeds room boundary")
            if not room_poly.buffer(0.05).contains(tb):
                reasons.append("Toilet exceeds room boundary")

            score = 100.0 - len(reasons) * 35.0
            # Privacy bonus: toilet center offset from door center
            tcx = (tb.bounds[0] + tb.bounds[2]) / 2.0
            if abs(tcx - dcx) > 0.40:
                score += 15.0

            candidates.append({
                "archetype": name,
                "score": score,
                "valid": len(reasons) == 0,
                "reasons": reasons,
                "shower_box": sb,
                "vanity_box": vb,
                "wc_box": tb,
                "landing_box": landing_box,
                "shower_screen_x": screen_x,
                "shower_size": (shower_w, shower_d)
            })

    candidates.sort(key=lambda c: (c["valid"], c["score"]), reverse=True)
    best = candidates[0] if candidates else None
    return best


# ==============================================================================
# 3. KITCHEN WORK-ZONE SOLVER
# ==============================================================================

def solve_kitchen_workzones(
    room_poly: Polygon,
    door_polys: Optional[List[Polygon]] = None,
    openings: Optional[List[Dict[str, Any]]] = None,
    windows: Optional[List[Dict[str, Any]]] = None,
    wall_graph: Optional[Dict[Tuple[Tuple[float, float], Tuple[float, float]], List[str]]] = None,
    scale: float = 1.0
) -> Dict[str, Any]:
    """
    Solves kitchen layout into functional work zones:
    Cold Storage (Fridge) -> Prep Counter -> Washing (Sink) -> Prep -> Cooking (Cooktop + Hood)
    Supports One-Wall, L-Shaped, and Open-Plan configurations.
    """
    door_polys = door_polys or []
    openings = openings or []
    windows = windows or []

    minx, miny, maxx, maxy = room_poly.bounds
    cx, cy = room_poly.centroid.x, room_poly.centroid.y
    w, h = maxx - minx, maxy - miny

    walls = {
        "south": LineString([(minx, miny), (maxx, miny)]),
        "north": LineString([(minx, maxy), (maxx, maxy)]),
        "west":  LineString([(minx, miny), (minx, maxy)]),
        "east":  LineString([(maxx, miny), (maxx, maxy)]),
    }

    # Find longest solid wall with least door cuts for main counter run
    wall_scores = {}
    for w_side, w_line in walls.items():
        door_cuts = sum(1 for dp in door_polys if dp.intersects(w_line.buffer(0.25)))
        has_win = any(w_line.buffer(0.05).contains(win.get("wall_segment", LineString())) for win in windows)
        score = w_line.length * 2.0 - door_cuts * 25.0
        # Windows are great above kitchen sinks! Don't penalize window walls heavily
        if has_win:
            score += 5.0
        wall_scores[w_side] = score

    best_counter_wall = max(wall_scores.items(), key=lambda x: x[1])[0]

    counter_d = COUNTER_DEPTH * scale
    fridge_w = REFRIGERATOR_WIDTH * scale
    fridge_d = REFRIGERATOR_DEPTH * scale
    sink_w = SINK_WIDTH * scale
    cook_w = COOKTOP_WIDTH * scale

    # Position Counter Along best_counter_wall
    if best_counter_wall == "north":
        c_x1, c_x2 = minx + 0.10, maxx - 0.10
        c_y1, c_y2 = maxy - counter_d - 0.05, maxy - 0.05
        fridge_box = box(c_x1, maxy - fridge_d - 0.05, c_x1 + fridge_w, maxy - 0.05)
        sink_cx = c_x1 + fridge_w + 0.80 * scale
        cooktop_cx = c_x2 - 0.70 * scale
        sink_pos = (sink_cx, (c_y1 + c_y2) / 2.0)
        cooktop_pos = (cooktop_cx, (c_y1 + c_y2) / 2.0)
    elif best_counter_wall == "south":
        c_x1, c_x2 = minx + 0.10, maxx - 0.10
        c_y1, c_y2 = miny + 0.05, miny + counter_d + 0.05
        fridge_box = box(c_x1, miny + 0.05, c_x1 + fridge_w, miny + fridge_d + 0.05)
        sink_cx = c_x1 + fridge_w + 0.80 * scale
        cooktop_cx = c_x2 - 0.70 * scale
        sink_pos = (sink_cx, (c_y1 + c_y2) / 2.0)
        cooktop_pos = (cooktop_cx, (c_y1 + c_y2) / 2.0)
    elif best_counter_wall == "west":
        c_x1, c_x2 = minx + 0.05, minx + counter_d + 0.05
        c_y1, c_y2 = miny + 0.10, maxy - 0.10
        fridge_box = box(minx + 0.05, c_y1, minx + fridge_d + 0.05, c_y1 + fridge_w)
        sink_cy = c_y1 + fridge_w + 0.80 * scale
        cooktop_cy = c_y2 - 0.70 * scale
        sink_pos = ((c_x1 + c_x2) / 2.0, sink_cy)
        cooktop_pos = ((c_x1 + c_x2) / 2.0, cooktop_cy)
    else: # east
        c_x1, c_x2 = maxx - counter_d - 0.05, maxx - 0.05
        c_y1, c_y2 = miny + 0.10, maxy - 0.10
        fridge_box = box(maxx - fridge_d - 0.05, c_y1, maxx - 0.05, c_y1 + fridge_w)
        sink_cy = c_y1 + fridge_w + 0.80 * scale
        cooktop_cy = c_y2 - 0.70 * scale
        sink_pos = ((c_x1 + c_x2) / 2.0, sink_cy)
        cooktop_pos = ((c_x1 + c_x2) / 2.0, cooktop_cy)

    counter_box = box(c_x1, c_y1, c_x2, c_y2)
    sink_box = box(sink_pos[0] - sink_w/2.0, sink_pos[1] - counter_d*0.35,
                   sink_pos[0] + sink_w/2.0, sink_pos[1] + counter_d*0.35)
    cooktop_box = box(cooktop_pos[0] - cook_w/2.0, cooktop_pos[1] - counter_d*0.35,
                      cooktop_pos[0] + cook_w/2.0, cooktop_pos[1] + counter_d*0.35)

    return {
        "counter_wall": best_counter_wall,
        "counter_box": counter_box,
        "fridge_box": fridge_box,
        "sink_box": sink_box,
        "cooktop_box": cooktop_box,
        "sink_center_x": sink_pos[0],
        "cooktop_center_x": cooktop_pos[0],
        "sink_pos": sink_pos,
        "cooktop_pos": cooktop_pos,
        "counter_depth": counter_d
    }
