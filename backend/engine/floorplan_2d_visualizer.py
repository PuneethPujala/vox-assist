import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union, linemerge
import numpy as np
import os
import csv

# =========================
# COLORS (MODERN ARCHITECTURAL PALETTE)
# =========================
ROOM_COLORS = {
    "living": "#E8E8E8",     # Light Gray
    "bedroom": "#5DADE2",    # Sky Blue
    "kitchen": "#58D68D",    # Mint Green
    "bathroom": "#C39BD3",   # Lavender
    "balcony": "#7FB3D5",    # Steel Blue
    "dining": "#F8C471",     # Amber
    "study": "#F9E79F",      # Pale Yellow
    "pooja": "#FADBD8",      # Soft Pink
    "storage": "#AAB7B8",    # Slate Gray
    "utility": "#D5DBDB",    # Silver
    "garden": "#7DCEA0",     # Forest Green
}

# NEW WALL & DOOR COLORS
WALL_COLOR = "#8B4513"      # Saddle Brown
DOOR_COLOR = "#FFD700"      # Gold
DOOR_ARC_COLOR = "#FFA500"  # Orange for arc

def get_wall_segments(rooms):
    """Extract all wall segments from rooms"""
    segments = []
    for poly in rooms.values():
        coords = list(poly.exterior.coords)
        for i in range(len(coords) - 1):
            segments.append((coords[i], coords[i+1]))
    return segments


def find_door_on_segment(seg_start, seg_end, all_doors):
    """Check if any door is on this wall segment (robust projection)"""
    wall_line = LineString([seg_start, seg_end])
    
    for door_poly in all_doors:
        door_center = door_poly.centroid
        
        # Project door center onto wall line
        proj_point = wall_line.project(door_center)
        closest_point = wall_line.interpolate(proj_point)
        
        # Check if projection is within segment bounds (not extended line)
        if proj_point <= 0 or proj_point >= wall_line.length:
            continue
            
        # Check proximity to wall (tolerance for floating point / geometry error)
        if door_center.distance(closest_point) < 0.6:  # increased tolerance
            return door_center, door_poly
    
    return None, None


def draw_wall_with_door(ax, seg_start, seg_end, door_center, door_width=1.2, is_entrance=False):
    """Draw wall segment with door opening and arc.

    If is_entrance is True, use a distinct color to highlight the front door.
    """
    wall_vec = np.array(seg_end) - np.array(seg_start)
    wall_len = np.linalg.norm(wall_vec)
    
    if wall_len < 0.01:
        return
    
    wall_vec = wall_vec / wall_len
    
    # Project door onto wall
    door_vec = np.array([door_center.x, door_center.y]) - np.array(seg_start)
    t = np.dot(door_vec, wall_vec)
    t = max(door_width/2, min(wall_len - door_width/2, t))
    
    door_pos = np.array(seg_start) + t * wall_vec
    door_start = door_pos - (door_width / 2) * wall_vec
    door_end = door_pos + (door_width / 2) * wall_vec
    
    # Wall before door
    ax.plot([seg_start[0], door_start[0]], [seg_start[1], door_start[1]], 
           color=WALL_COLOR, linewidth=12, solid_capstyle='butt', zorder=3)
    
    # Wall after door
    ax.plot([door_end[0], seg_end[0]], [door_end[1], seg_end[1]], 
           color=WALL_COLOR, linewidth=12, solid_capstyle='butt', zorder=3)
    
    # Choose colors (highlight entrance differently)
    door_color = "#FF0000" if is_entrance else DOOR_COLOR
    door_arc_color = "#FF4500" if is_entrance else DOOR_ARC_COLOR

    # Door opening (white gap)
    ax.plot([door_start[0], door_end[0]], [door_start[1], door_end[1]],
            color='white', linewidth=3, zorder=4)

    # Door arc (gold/orange or highlighted)
    angle_deg = np.degrees(np.arctan2(wall_vec[1], wall_vec[0]))
    arc_radius = door_width * 0.9

    arc = Arc(door_start, arc_radius * 2, arc_radius * 2,
              angle=0, theta1=angle_deg, theta2=angle_deg + 90,
              color=door_arc_color, linewidth=2.5, zorder=5)
    ax.add_patch(arc)

    # Door panel line (gold or highlighted)
    perp = np.array([-wall_vec[1], wall_vec[0]])
    door_line_end = door_start + arc_radius * (wall_vec * np.cos(np.pi/2) + perp * np.sin(np.pi/2))

    ax.plot([door_start[0], door_line_end[0]],
            [door_start[1], door_line_end[1]],
            color=door_color, linewidth=3, zorder=5)


def draw_2d_floorplan(layout, filename="floorplan_2d.png"):
    """Pure 2D floor plan from layout geometry"""

    rooms = layout["rooms"]
    doors_geom = layout.get("doors")
    entrance_geom = layout.get("entrance")

    # Extract door polygons
    all_doors = []
    if doors_geom and not doors_geom.is_empty:
        if isinstance(doors_geom, Polygon):
            all_doors = [doors_geom]
        elif isinstance(doors_geom, MultiPolygon):
            all_doors = list(doors_geom.geoms)
    
    # Setup figure
    fig, ax = plt.subplots(1, 1, figsize=(16, 12), facecolor='white')
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Get bounds
    all_coords = []
    for poly in rooms.values():
        all_coords.extend(list(poly.exterior.coords))
    
    xs = [c[0] for c in all_coords]
    ys = [c[1] for c in all_coords]
    margin = 3
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    
    # Draw room fills
    for room_name, poly in rooms.items():
        room_type = room_name.split("_")[0]
        color = ROOM_COLORS.get(room_type, "#F5F5F5")
        
        coords = list(poly.exterior.coords)
        polygon = patches.Polygon(coords, 
                                 facecolor=color,
                                 edgecolor='none',
                                 alpha=0.85,
                                 zorder=1)
        ax.add_patch(polygon)
    
    # Draw walls with doors
    wall_segments = get_wall_segments(rooms)

    for seg_start, seg_end in wall_segments:
        door_center, door_poly = find_door_on_segment(seg_start, seg_end, all_doors)

        if door_center:
            # Check if this is the entrance/front door
            is_entrance = bool(entrance_geom is not None and door_poly.equals(entrance_geom))
            # Wall has door - draw with opening
            draw_wall_with_door(ax, seg_start, seg_end, door_center, is_entrance=is_entrance)
        else:
            # Solid wall
            ax.plot([seg_start[0], seg_end[0]],
                    [seg_start[1], seg_end[1]],
                    color=WALL_COLOR, linewidth=12, solid_capstyle='butt', zorder=3)
    
    # Add room labels
    for room_name, poly in rooms.items():
        centroid = poly.centroid
        room_type = room_name.split("_")[0].upper()
        room_num = room_name.split("_")[1]
        
        label = f"{room_type}\n{room_num}"
        
        ax.text(centroid.x, centroid.y, label,
               ha='center', va='center',
               fontsize=13, fontweight='bold',
               color='#000000',
               bbox=dict(boxstyle='round,pad=0.6', 
                        facecolor='white', 
                        edgecolor='gray',
                        linewidth=1.5,
                        alpha=0.95),
               zorder=6)
    
    # Title
    ax.text(0.5, 0.98, "FLOOR PLAN",
           transform=ax.transAxes,
           ha='center', va='top',
           fontsize=24, fontweight='bold',
           color='#333333',
           bbox=dict(boxstyle='round,pad=0.8', 
                    facecolor='white', 
                    edgecolor=WALL_COLOR,
                    linewidth=3))
    
    plt.tight_layout()
    plt.savefig(filename, dpi=200, bbox_inches='tight', facecolor='white')

    print(f"📐 2D Floor plan: {filename}")
    print(f"   Rooms: {len(rooms)}")
    print(f"   Doors: {len(all_doors)}")

    plt.close()