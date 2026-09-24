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
        UPPER_CABINET_BOTTOM, UPPER_CABINET_TOP,
        DOUBLE_BED_WIDTH, DOUBLE_BED_LENGTH, SINGLE_BED_WIDTH, SINGLE_BED_LENGTH,
        BED_HEADBOARD_HEIGHT, BED_MATTRESS_HEIGHT, NIGHTSTAND_WIDTH, NIGHTSTAND_DEPTH,
        NIGHTSTAND_HEIGHT, BED_SIDE_CLEARANCE, BED_FOOT_CLEARANCE,
        MASTER_WARDROBE_WIDTH, SECONDARY_WARDROBE_WIDTH, WARDROBE_DEPTH, WARDROBE_HEIGHT,
        WARDROBE_DOOR_CLEARANCE, DINING_TABLE_4S_WIDTH, DINING_TABLE_4S_DEPTH,
        DINING_TABLE_6S_WIDTH, DINING_TABLE_6S_DEPTH, DINING_TABLE_HEIGHT,
        DINING_CHAIR_WIDTH, DINING_CHAIR_DEPTH, DINING_CHAIR_HEIGHT, DINING_CHAIR_PULLOUT,
        DINING_WALKWAY_CLEARANCE, BREAKFAST_COUNTER_WIDTH, BREAKFAST_COUNTER_DEPTH,
        CORRIDOR_WIDTH, WINDOW_KEEP_OUT, PERIMETER_WALKWAY
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
            UPPER_CABINET_BOTTOM, UPPER_CABINET_TOP,
            DOUBLE_BED_WIDTH, DOUBLE_BED_LENGTH, SINGLE_BED_WIDTH, SINGLE_BED_LENGTH,
            BED_HEADBOARD_HEIGHT, BED_MATTRESS_HEIGHT, NIGHTSTAND_WIDTH, NIGHTSTAND_DEPTH,
            NIGHTSTAND_HEIGHT, BED_SIDE_CLEARANCE, BED_FOOT_CLEARANCE,
            MASTER_WARDROBE_WIDTH, SECONDARY_WARDROBE_WIDTH, WARDROBE_DEPTH, WARDROBE_HEIGHT,
            WARDROBE_DOOR_CLEARANCE, DINING_TABLE_4S_WIDTH, DINING_TABLE_4S_DEPTH,
            DINING_TABLE_6S_WIDTH, DINING_TABLE_6S_DEPTH, DINING_TABLE_HEIGHT,
            DINING_CHAIR_WIDTH, DINING_CHAIR_DEPTH, DINING_CHAIR_HEIGHT, DINING_CHAIR_PULLOUT,
            DINING_WALKWAY_CLEARANCE, BREAKFAST_COUNTER_WIDTH, BREAKFAST_COUNTER_DEPTH,
            CORRIDOR_WIDTH, WINDOW_KEEP_OUT, PERIMETER_WALKWAY
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
            UPPER_CABINET_BOTTOM, UPPER_CABINET_TOP,
            DOUBLE_BED_WIDTH, DOUBLE_BED_LENGTH, SINGLE_BED_WIDTH, SINGLE_BED_LENGTH,
            BED_HEADBOARD_HEIGHT, BED_MATTRESS_HEIGHT, NIGHTSTAND_WIDTH, NIGHTSTAND_DEPTH,
            NIGHTSTAND_HEIGHT, BED_SIDE_CLEARANCE, BED_FOOT_CLEARANCE,
            MASTER_WARDROBE_WIDTH, SECONDARY_WARDROBE_WIDTH, WARDROBE_DEPTH, WARDROBE_HEIGHT,
            WARDROBE_DOOR_CLEARANCE, DINING_TABLE_4S_WIDTH, DINING_TABLE_4S_DEPTH,
            DINING_TABLE_6S_WIDTH, DINING_TABLE_6S_DEPTH, DINING_TABLE_HEIGHT,
            DINING_CHAIR_WIDTH, DINING_CHAIR_DEPTH, DINING_CHAIR_HEIGHT, DINING_CHAIR_PULLOUT,
            DINING_WALKWAY_CLEARANCE, BREAKFAST_COUNTER_WIDTH, BREAKFAST_COUNTER_DEPTH,
            CORRIDOR_WIDTH, WINDOW_KEEP_OUT, PERIMETER_WALKWAY
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


# ==============================================================================
# 4. BEDROOM COHESIVE GROUP SOLVER
# ==============================================================================

def solve_bedroom_furniture_group(
    room_poly: Polygon,
    room_name: str = "bedroom",
    door_polys: Optional[List[Polygon]] = None,
    windows: Optional[List[Dict[str, Any]]] = None,
    window_exclusion_polys: Optional[List[Polygon]] = None,
    wall_graph: Optional[Dict[Tuple[Tuple[float, float], Tuple[float, float]], List[str]]] = None,
    scale: float = 1.0,
    room_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Solves cohesive bedroom layout:
    1. Headboard on solid interior focal wall (strictly never on a window wall).
    2. Symmetrical bedside nightstands flanking headboard.
    3. Wardrobe sized to room type (1.80m Master, 1.20m Secondary) on alternate solid wall.
    4. Wardrobe strictly avoids window daylighting keep-out zones and door swings.
    5. Maintains walking perimeter clearance (>= 0.70m sides, >= 0.80m foot) and wardrobe door clearance (>= 0.60m).
    """
    door_polys = door_polys or []
    windows = windows or []
    window_exclusion_polys = window_exclusion_polys or []

    minx, miny, maxx, maxy = room_poly.bounds
    cx, cy = room_poly.centroid.x, room_poly.centroid.y
    w, h = maxx - minx, maxy - miny
    area = room_poly.area

    # Master vs Secondary classification
    type_or_name = f"{room_type or ''} {room_name}".lower()
    is_master = any(k in type_or_name for k in ["master", "primary", "_1"]) or area >= 13.0
    bed_type = "double" if (area >= 10.0 or is_master) else "single"
    bed_w = (DOUBLE_BED_WIDTH if bed_type == "double" else SINGLE_BED_WIDTH) * scale
    bed_l = (DOUBLE_BED_LENGTH if bed_type == "double" else SINGLE_BED_LENGTH) * scale
    head_d = 0.10 * scale
    head_h = BED_HEADBOARD_HEIGHT
    mat_h = BED_MATTRESS_HEIGHT
    ns_w = NIGHTSTAND_WIDTH * scale
    ns_d = NIGHTSTAND_DEPTH * scale
    target_wardrobe_w = (MASTER_WARDROBE_WIDTH if is_master else SECONDARY_WARDROBE_WIDTH) * scale
    wardrobe_d = WARDROBE_DEPTH * scale

    walls = {
        "south": LineString([(minx, miny), (maxx, miny)]),
        "north": LineString([(minx, maxy), (maxx, maxy)]),
        "west":  LineString([(minx, miny), (minx, maxy)]),
        "east":  LineString([(maxx, miny), (maxx, maxy)]),
    }

    # Aggregate window keep-outs and segments
    win_keepouts = list(window_exclusion_polys)
    for win in windows:
        w_room = win.get("room")
        if w_room and w_room != room_name:
            continue
        ko = win.get("keepout")
        if ko and not ko.is_empty:
            win_keepouts.append(ko)
        seg = win.get("wall_segment")
        if seg and not seg.is_empty:
            win_keepouts.append(seg.buffer(0.35))
    win_union = unary_union(win_keepouts) if win_keepouts else Polygon()

    # Aggregate doors touching room
    room_doors = [dp for dp in door_polys if dp.intersects(room_poly.buffer(0.25))]

    # Classify walls
    wall_info = {}
    for w_side, w_line in walls.items():
        # Check window intersection
        has_win = False
        if not win_union.is_empty and w_line.buffer(0.12).intersects(win_union):
            has_win = True
        for win in windows:
            seg = win.get("wall_segment")
            if seg and not seg.is_empty and seg.intersects(w_line.buffer(0.12)):
                has_win = True
                break

        # Check door cuts
        cuts = [dp for dp in room_doors if dp.intersects(w_line.buffer(0.35))]

        # Check interior partition status via wall_graph
        is_interior = False
        if wall_graph:
            for (p1, p2), sharing in wall_graph.items():
                inter = LineString([p1, p2]).intersection(w_line.buffer(0.08))
                if inter.length > 0.40 and len(sharing) > 1:
                    is_interior = True
                    break

        wall_info[w_side] = {
            "has_win": has_win,
            "door_cuts": cuts,
            "is_interior": is_interior,
            "length": w_line.length
        }

    # Evaluate Headboard Candidates
    candidates = []
    for w_side, w_line in walls.items():
        winfo = wall_info[w_side]
        reasons = []

        if winfo["has_win"]:
            reasons.append(f"Wall {w_side} has exterior window openings (headboards must not block daylighting)")

        # Center placement along wall
        if w_side == "south":
            bed_cx = cx
            head_box = box(bed_cx - bed_w/2.0 - 0.05*scale, miny + 0.02, bed_cx + bed_w/2.0 + 0.05*scale, miny + head_d + 0.02)
            mat_box = box(bed_cx - bed_w/2.0, miny + head_d + 0.02, bed_cx + bed_w/2.0, miny + bed_l)
            bed_box = box(bed_cx - bed_w/2.0, miny + 0.02, bed_cx + bed_w/2.0, miny + bed_l)
            foot_dist = maxy - (miny + bed_l)
            side_dist = min(bed_cx - bed_w/2.0 - minx, maxx - (bed_cx + bed_w/2.0))
            # Nightstands
            ns_left = box(bed_cx - bed_w/2.0 - 0.05*scale - ns_w, miny + 0.02, bed_cx - bed_w/2.0 - 0.05*scale, miny + 0.02 + ns_d)
            ns_right = box(bed_cx + bed_w/2.0 + 0.05*scale, miny + 0.02, bed_cx + bed_w/2.0 + 0.05*scale + ns_w, miny + 0.02 + ns_d)
        elif w_side == "north":
            bed_cx = cx
            head_box = box(bed_cx - bed_w/2.0 - 0.05*scale, maxy - head_d - 0.02, bed_cx + bed_w/2.0 + 0.05*scale, maxy - 0.02)
            mat_box = box(bed_cx - bed_w/2.0, maxy - bed_l, bed_cx + bed_w/2.0, maxy - head_d - 0.02)
            bed_box = box(bed_cx - bed_w/2.0, maxy - bed_l, bed_cx + bed_w/2.0, maxy - 0.02)
            foot_dist = (maxy - bed_l) - miny
            side_dist = min(bed_cx - bed_w/2.0 - minx, maxx - (bed_cx + bed_w/2.0))
            ns_left = box(bed_cx - bed_w/2.0 - 0.05*scale - ns_w, maxy - 0.02 - ns_d, bed_cx - bed_w/2.0 - 0.05*scale, maxy - 0.02)
            ns_right = box(bed_cx + bed_w/2.0 + 0.05*scale, maxy - 0.02 - ns_d, bed_cx + bed_w/2.0 + 0.05*scale + ns_w, maxy - 0.02)
        elif w_side == "west":
            bed_cy = cy
            head_box = box(minx + 0.02, bed_cy - bed_w/2.0 - 0.05*scale, minx + head_d + 0.02, bed_cy + bed_w/2.0 + 0.05*scale)
            mat_box = box(minx + head_d + 0.02, bed_cy - bed_w/2.0, minx + bed_l, bed_cy + bed_w/2.0)
            bed_box = box(minx + 0.02, bed_cy - bed_w/2.0, minx + bed_l, bed_cy + bed_w/2.0)
            foot_dist = maxx - (minx + bed_l)
            side_dist = min(bed_cy - bed_w/2.0 - miny, maxy - (bed_cy + bed_w/2.0))
            ns_left = box(minx + 0.02, bed_cy - bed_w/2.0 - 0.05*scale - ns_w, minx + 0.02 + ns_d, bed_cy - bed_w/2.0 - 0.05*scale)
            ns_right = box(minx + 0.02, bed_cy + bed_w/2.0 + 0.05*scale, minx + 0.02 + ns_d, bed_cy + bed_w/2.0 + 0.05*scale + ns_w)
        else: # east
            bed_cy = cy
            head_box = box(maxx - head_d - 0.02, bed_cy - bed_w/2.0 - 0.05*scale, maxx - 0.02, bed_cy + bed_w/2.0 + 0.05*scale)
            mat_box = box(maxx - bed_l, bed_cy - bed_w/2.0, maxx - head_d - 0.02, bed_cy + bed_w/2.0)
            bed_box = box(maxx - bed_l, bed_cy - bed_w/2.0, maxx - 0.02, bed_cy + bed_w/2.0)
            foot_dist = (maxx - bed_l) - minx
            side_dist = min(bed_cy - bed_w/2.0 - miny, maxy - (bed_cy + bed_w/2.0))
            ns_left = box(maxx - 0.02 - ns_d, bed_cy - bed_w/2.0 - 0.05*scale - ns_w, maxx - 0.02, bed_cy - bed_w/2.0 - 0.05*scale)
            ns_right = box(maxx - 0.02 - ns_d, bed_cy + bed_w/2.0 + 0.05*scale, maxx - 0.02, bed_cy + bed_w/2.0 + 0.05*scale + ns_w)

        # Check door collisions with bed
        for dp in winfo["door_cuts"]:
            if dp.intersects(bed_box):
                reasons.append("Bed directly collides with doorway opening")
            elif dp.distance(bed_box) < 0.30:
                reasons.append("Bed restricts immediate doorway passage")

        # Nightstands containment and validation
        valid_nightstands = []
        for ns in [ns_left, ns_right]:
            if room_poly.buffer(0.05).contains(ns) and not any(dp.intersects(ns) for dp in room_doors):
                if win_union.is_empty or not ns.intersects(win_union):
                    valid_nightstands.append(ns)

        if not room_poly.buffer(0.05).contains(bed_box):
            reasons.append("Bed exceeds room boundary")

        if foot_dist < 0.65:
            reasons.append(f"Insufficient foot clearance ({foot_dist:.2f}m < 0.70m)")

        # Scoring
        score = 100.0
        if winfo["has_win"]:
            score -= 500.0  # strictly disqualify window walls
        if winfo["is_interior"]:
            score += 25.0
        if len(winfo["door_cuts"]) == 0:
            score += 20.0
        else:
            score -= len(winfo["door_cuts"]) * 20.0
        score += len(valid_nightstands) * 10.0
        if side_dist >= BED_SIDE_CLEARANCE:
            score += 15.0
        if foot_dist >= BED_FOOT_CLEARANCE:
            score += 10.0
        score -= len(reasons) * 40.0

        candidates.append({
            "wall": w_side,
            "score": score,
            "valid": len(reasons) == 0 and not winfo["has_win"],
            "reasons": reasons,
            "bed_box": bed_box,
            "headboard_box": head_box,
            "mattress_box": mat_box,
            "nightstand_boxes": valid_nightstands,
            "foot_dist": foot_dist,
            "side_dist": side_dist
        })

    candidates.sort(key=lambda c: (c["valid"], c["score"]), reverse=True)
    best_headboard = candidates[0] if candidates else None

    # Step 2: Solve Wardrobe on Alternate Solid Wall
    best_wardrobe = None
    if best_headboard:
        h_wall = best_headboard["wall"]
        b_box = best_headboard["bed_box"]
        candidate_wardrobe_walls = [s for s in ["south", "north", "west", "east"] if s != h_wall]

        wardrobe_candidates = []
        for w_side in candidate_wardrobe_walls:
            winfo = wall_info[w_side]
            if winfo["has_win"]:
                continue  # Never on window wall

            w_len_target = target_wardrobe_w
            # Check length availability
            wall_span = w if w_side in ["south", "north"] else h
            cuts = winfo["door_cuts"]

            # Try placement along w_side
            # Try sizing: target, then compact 1.20, then 1.00
            for w_curr_w in [w_len_target, SECONDARY_WARDROBE_WIDTH * scale, 1.00 * scale]:
                if w_curr_w > wall_span - 0.40:
                    continue

                # Test 3 positions: near min corner, center, near max corner
                if w_side in ["south", "north"]:
                    py_w = miny + 0.02 if w_side == "south" else maxy - 0.02 - wardrobe_d
                    pos_list = [minx + 0.10, cx - w_curr_w / 2.0, maxx - 0.10 - w_curr_w]
                else:
                    px_w = minx + 0.02 if w_side == "west" else maxx - 0.02 - wardrobe_d
                    pos_list = [miny + 0.10, cy - w_curr_w / 2.0, maxy - 0.10 - w_curr_w]

                for p_coord in pos_list:
                    if w_side in ["south", "north"]:
                        wb = box(p_coord, py_w, p_coord + w_curr_w, py_w + wardrobe_d)
                        # Door clearance box (0.60m into room)
                        if w_side == "south":
                            w_door_box = box(p_coord, py_w + wardrobe_d, p_coord + w_curr_w, py_w + wardrobe_d + WARDROBE_DOOR_CLEARANCE)
                        else:
                            w_door_box = box(p_coord, py_w - WARDROBE_DOOR_CLEARANCE, p_coord + w_curr_w, py_w)
                    else:
                        wb = box(px_w, p_coord, px_w + wardrobe_d, p_coord + w_curr_w)
                        if w_side == "west":
                            w_door_box = box(px_w + wardrobe_d, p_coord, px_w + wardrobe_d + WARDROBE_DOOR_CLEARANCE, p_coord + w_curr_w)
                        else:
                            w_door_box = box(px_w - WARDROBE_DOOR_CLEARANCE, p_coord, px_w, p_coord + w_curr_w)

                    # Collision checks
                    overlaps_bed = wb.intersects(b_box.buffer(0.20))
                    overlaps_ns = any(wb.intersects(ns.buffer(0.10)) for ns in best_headboard["nightstand_boxes"])
                    overlaps_door = any(wb.intersects(dp.buffer(0.25)) for dp in room_doors)
                    overlaps_win = (not win_union.is_empty) and wb.intersects(win_union)
                    contained = room_poly.buffer(0.05).contains(wb)
                    door_clearance_ok = not w_door_box.intersects(b_box)

                    if not overlaps_bed and not overlaps_ns and not overlaps_door and not overlaps_win and contained:
                        w_score = 100.0 + (w_curr_w * 10.0)
                        if door_clearance_ok:
                            w_score += 20.0
                        if winfo["is_interior"]:
                            w_score += 15.0
                        wardrobe_candidates.append({
                            "wall": w_side,
                            "box": wb,
                            "door_clearance_box": w_door_box,
                            "width": w_curr_w,
                            "score": w_score,
                            "door_clearance_ok": door_clearance_ok
                        })

        if wardrobe_candidates:
            wardrobe_candidates.sort(key=lambda c: (c["door_clearance_ok"], c["score"]), reverse=True)
            best_wardrobe = wardrobe_candidates[0]

    # Build response payload
    overall_score = best_headboard["score"] if best_headboard else 0.0
    if best_wardrobe:
        overall_score = min(100.0, (overall_score + best_wardrobe["score"]) / 2.0)
    else:
        overall_score = max(0.0, overall_score - 20.0)

    # Walking aisle polys around bed
    aisle_polys = []
    if best_headboard:
        bb = best_headboard["bed_box"]
        aisle_polys.append(bb.buffer(PERIMETER_WALKWAY))

    return {
        "wall": best_headboard["wall"] if best_headboard else None,
        "headboard_wall": best_headboard["wall"] if best_headboard else None,
        "wardrobe_wall": best_wardrobe["wall"] if best_wardrobe else None,
        "score": round(max(0.0, min(100.0, overall_score)), 1),
        "valid": best_headboard["valid"] if best_headboard else False,
        "bed_box": best_headboard["bed_box"] if best_headboard else None,
        "bed_type": bed_type,
        "headboard_box": best_headboard["headboard_box"] if best_headboard else None,
        "mattress_box": best_headboard["mattress_box"] if best_headboard else None,
        "nightstand_boxes": best_headboard["nightstand_boxes"] if best_headboard else [],
        "wardrobe_box": best_wardrobe["box"] if best_wardrobe else None,
        "wardrobe_door_clearance_box": best_wardrobe["door_clearance_box"] if best_wardrobe else None,
        "wardrobe_width": best_wardrobe["width"] if best_wardrobe else 0.0,
        "walking_aisle_polys": aisle_polys,
        "reasons": best_headboard.get("reasons", []) if best_headboard else ["Could not solve bedroom headboard"]
    }


# ==============================================================================
# 5. DINING ZONE GROUP SOLVER
# ==============================================================================

def solve_dining_zone_group(
    dining_poly: Polygon,
    kitchen_poly: Optional[Polygon] = None,
    door_polys: Optional[List[Polygon]] = None,
    openings: Optional[List[Dict[str, Any]]] = None,
    protected_circ: Optional[Polygon] = None,
    foyer_keepout: Optional[Polygon] = None,
    living_group: Optional[Dict[str, Any]] = None,
    is_compact: bool = False,
    scale: float = 1.0
) -> Dict[str, Any]:
    """
    Solves dining furniture group:
    1. Default 4-seater (1.20m x 0.80m) or 6-seater (1.60m x 0.90m if area >= 14m2).
    2. Fallback to breakfast counter (1.20m x 0.50m) if compact < 65m2 and space restricts corridor.
    3. Chair pull-out envelope (0.65m buffer around table).
    4. Pedestrian walkway (>= 0.90m clear perimeter behind pulled chairs).
    5. Adjacency to kitchen opening / pass-through.
    6. Non-collision with living group, primary circulation spine, and foyer arrival.
    """
    door_polys = door_polys or []
    openings = openings or []

    minx, miny, maxx, maxy = dining_poly.bounds
    cx, cy = dining_poly.centroid.x, dining_poly.centroid.y
    w, h = maxx - minx, maxy - miny
    area = dining_poly.area

    # Determine table archetype
    if area >= 14.0 and not is_compact:
        t_w = DINING_TABLE_6S_WIDTH * scale
        t_d = DINING_TABLE_6S_DEPTH * scale
        chair_count = 6
        archetype = "DINING_6S"
    elif is_compact and (w < 2.5 or h < 2.5):
        t_w = BREAKFAST_COUNTER_WIDTH * scale
        t_d = BREAKFAST_COUNTER_DEPTH * scale
        chair_count = 2
        archetype = "BREAKFAST_COUNTER"
    else:
        t_w = DINING_TABLE_4S_WIDTH * scale
        t_d = DINING_TABLE_4S_DEPTH * scale
        chair_count = 4
        archetype = "DINING_4S"

    # Direction towards kitchen if known
    target_cx, target_cy = cx, cy
    if kitchen_poly and not kitchen_poly.is_empty:
        kcx, kcy = kitchen_poly.centroid.x, kitchen_poly.centroid.y
        # Shift towards kitchen boundary by ~25% of room dimension
        target_cx = cx + 0.25 * (kcx - cx)
        target_cy = cy + 0.25 * (kcy - cy)
        # Clamp within room bounds with buffer
        target_cx = max(minx + t_w/2.0 + 0.50, min(maxx - t_w/2.0 - 0.50, target_cx))
        target_cy = max(miny + t_d/2.0 + 0.50, min(maxy - t_d/2.0 - 0.50, target_cy))

    # Candidate table center positions
    candidate_centers = [
        (target_cx, target_cy),
        (cx, cy),
        (cx + 0.3 * (maxx - cx), cy),
        (cx - 0.3 * (cx - minx), cy),
        (cx, cy + 0.3 * (maxy - cy)),
        (cx, cy - 0.3 * (cy - miny)),
        (cx + 0.35 * (maxx - cx), cy + 0.35 * (maxy - cy)),
        (cx - 0.35 * (cx - minx), cy + 0.35 * (maxy - cy)),
        (cx + 0.35 * (maxx - cx), cy - 0.35 * (cy - miny)),
        (cx - 0.35 * (cx - minx), cy - 0.35 * (cy - miny)),
    ]

    best_cand = None
    candidates = []

    for tcx, tcy in candidate_centers:
        for orient in ["horizontal", "vertical"]:
            cur_w = t_w if orient == "horizontal" else t_d
            cur_d = t_d if orient == "horizontal" else t_w

            t_box = box(tcx - cur_w/2.0, tcy - cur_d/2.0, tcx + cur_w/2.0, tcy + cur_d/2.0)
            pullout_box = t_box.buffer(DINING_CHAIR_PULLOUT)
            walkway_box = t_box.buffer(DINING_CHAIR_PULLOUT + DINING_WALKWAY_CLEARANCE)

            reasons = []

            # 1. Room containment
            if not dining_poly.buffer(0.05).contains(t_box):
                reasons.append("Dining table extends outside room boundary")

            # 2. Door clearance
            for dp in door_polys:
                if dp.intersects(pullout_box):
                    reasons.append("Chair pull-out encroaches into doorway clearance")

            # 3. Foyer arrival keepout
            if foyer_keepout and not foyer_keepout.is_empty and t_box.intersects(foyer_keepout):
                reasons.append("Dining table encroaches into foyer arrival zone")

            # 4. Protected circulation spine
            if protected_circ and not protected_circ.is_empty and t_box.intersects(protected_circ):
                reasons.append("Dining table obstructs primary circulation spine")

            # 5. Living room group non-clash
            if living_group:
                for f_key in ["sofa_box", "coffee_table_box", "tv_box", "rug_box"]:
                    fb = living_group.get(f_key)
                    if fb and not fb.is_empty and pullout_box.intersects(fb):
                        reasons.append(f"Dining chair pull-out clashes with living {f_key.replace('_box', '')}")

            # Chairs generation
            cw = DINING_CHAIR_WIDTH * scale
            cd = DINING_CHAIR_DEPTH * scale
            chairs = []
            if orient == "horizontal":
                # Top and bottom long sides
                if chair_count == 4:
                    offsets = [-cur_w * 0.25, cur_w * 0.25]
                elif chair_count == 6:
                    offsets = [-cur_w * 0.33, 0.0, cur_w * 0.33]
                else: # 2 chairs
                    offsets = [0.0]

                for off in offsets:
                    # Bottom side chair
                    chairs.append(box(tcx + off - cw/2.0, tcy - cur_d/2.0 - cd, tcx + off + cw/2.0, tcy - cur_d/2.0))
                    if chair_count > 2:
                        # Top side chair
                        chairs.append(box(tcx + off - cw/2.0, tcy + cur_d/2.0, tcx + off + cw/2.0, tcy + cur_d/2.0 + cd))
            else: # vertical
                if chair_count == 4:
                    offsets = [-cur_d * 0.25, cur_d * 0.25]
                elif chair_count == 6:
                    offsets = [-cur_d * 0.33, 0.0, cur_d * 0.33]
                else:
                    offsets = [0.0]

                for off in offsets:
                    chairs.append(box(tcx - cur_w/2.0 - cd, tcy + off - cw/2.0, tcx - cur_w/2.0, tcy + off + cw/2.0))
                    if chair_count > 2:
                        chairs.append(box(tcx + cur_w/2.0, tcy + off - cw/2.0, tcx + cur_w/2.0 + cd, tcy + off + cw/2.0))

            score = 100.0 - len(reasons) * 35.0
            if foyer_keepout and not foyer_keepout.is_empty and t_box.intersects(foyer_keepout):
                score -= 500.0
            if protected_circ and not protected_circ.is_empty and t_box.intersects(protected_circ):
                score -= 300.0
            if kitchen_poly and not kitchen_poly.is_empty:
                dist_k = t_box.distance(kitchen_poly)
                if dist_k < 2.0:
                    score += 15.0

            cand_data = {
                "archetype": archetype,
                "score": max(0.0, min(100.0, score)),
                "valid": len(reasons) == 0,
                "reasons": reasons,
                "table_box": t_box,
                "pullout_box": pullout_box,
                "walkway_box": walkway_box,
                "chair_boxes": chairs,
                "table_center": (tcx, tcy),
                "orientation": orient,
                "chair_count": len(chairs)
            }
            candidates.append(cand_data)

    candidates.sort(key=lambda c: (c["valid"], c["score"]), reverse=True)
    best_cand = candidates[0] if candidates else None
    return best_cand


# ==============================================================================
# 6. GLOBAL FURNITURE LAYOUT COLLISION SOLVER
# ==============================================================================

def solve_global_furniture_layout(
    room_groups: Dict[str, Dict[str, Any]],
    protected_circ: Optional[Polygon] = None,
    foyer_keepout: Optional[Polygon] = None,
    wall_thickness: float = 0.15
) -> Dict[str, Any]:
    """
    Executes a global cross-room furniture verification pass:
    1. Collects all placed furniture pieces from all room groups.
    2. Detects pairwise cross-room clashes (e.g. living sofa vs dining chairs).
    3. Validates that no furniture chokes the primary circulation spine.
    4. Validates that no furniture invades the front foyer arrival zone.
    5. Returns unified collision report and global layout score.
    """
    items = []
    for r_name, group in room_groups.items():
        if not group or not isinstance(group, dict):
            continue
        # Living room group items
        for k in ["tv_box", "sofa_box", "coffee_table_box", "rug_box"]:
            b = group.get(k)
            if b and not b.is_empty:
                items.append({"room": r_name, "type": k.replace("_box", ""), "poly": b})
        # Bedroom items
        for k in ["headboard_box", "mattress_box", "wardrobe_box"]:
            b = group.get(k)
            if b and not b.is_empty:
                items.append({"room": r_name, "type": k.replace("_box", ""), "poly": b})
        if not group.get("mattress_box") and group.get("bed_box"):
            items.append({"room": r_name, "type": "bed", "poly": group["bed_box"]})
        for ns in group.get("nightstand_boxes", []):
            if ns and not ns.is_empty:
                items.append({"room": r_name, "type": "nightstand", "poly": ns})
        # Dining items
        if "table_box" in group and group["table_box"] and not group["table_box"].is_empty:
            items.append({"room": r_name, "type": "dining_table", "poly": group["table_box"]})
        for ch in group.get("chair_boxes", []):
            if ch and not ch.is_empty:
                items.append({"room": r_name, "type": "dining_chair", "poly": ch})
        # Bathroom items
        for k in ["vanity_box", "wc_box", "shower_box"]:
            b = group.get(k)
            if b and not b.is_empty:
                items.append({"room": r_name, "type": k.replace("_box", ""), "poly": b})
        # Kitchen items
        for k in ["counter_box", "fridge_box", "sink_box", "cooktop_box"]:
            b = group.get(k)
            if b and not b.is_empty:
                items.append({"room": r_name, "type": k.replace("_box", ""), "poly": b})

    conflicts = []
    # 1. Pairwise inter-group clashes (excluding pieces within the same group that legitimately touch like rug/sofa or bed/headboard)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            it1, it2 = items[i], items[j]
            p1, p2 = it1["poly"], it2["poly"]
            # Allow items within same room of complementary types (bed/mattress, sofa/rug)
            if it1["room"] == it2["room"]:
                types = {it1["type"], it2["type"]}
                if "bed" in types and ("headboard" in types or "mattress" in types):
                    continue
                if "headboard" in types and "mattress" in types:
                    continue
                if "rug" in types:
                    continue
                if "kitchen_counter" in types or "counter" in types:
                    continue

            if p1.intersects(p2):
                inter = p1.intersection(p2)
                if inter.area > 0.02:
                    conflicts.append(
                        f"Cross-object clash between {it1['room']}:{it1['type']} and {it2['room']}:{it2['type']} ({round(inter.area, 2)}m² overlap)"
                    )

    # 2. Circulation spine clash
    if protected_circ and not protected_circ.is_empty:
        for it in items:
            if it["type"] in ["rug"]:  # Flat rugs may sit on circulation boundary
                continue
            if it["poly"].intersects(protected_circ):
                inter = it["poly"].intersection(protected_circ)
                if inter.area > 0.05:
                    conflicts.append(f"{it['room']}:{it['type']} obstructs protected circulation corridor")

    # 3. Foyer arrival keepout clash
    if foyer_keepout and not foyer_keepout.is_empty:
        for it in items:
            if it["poly"].intersects(foyer_keepout):
                inter = it["poly"].intersection(foyer_keepout)
                if inter.area > 0.05:
                    conflicts.append(f"{it['room']}:{it['type']} encroaches into front entrance foyer arrival zone")

    score = max(0, 100 - len(conflicts) * 25)
    return {
        "valid": len(conflicts) == 0,
        "score": score,
        "conflicts": conflicts,
        "placed_count": len(items),
        "items": items
    }

