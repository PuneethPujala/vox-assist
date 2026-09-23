import pytest
import numpy as np
from shapely.geometry import box, Polygon, Point, LineString
from shapely.ops import unary_union
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, 'engine'))

from engine.resplan_to_3d import build_house_from_layout
from engine.building_footprint import select_and_partition_archetype

def test_no_diagonal_wall_members_in_orthogonal_layout():
    """Regression test: Ensure no diagonal X-beams or diagonal wall slabs are generated."""
    rooms = {
        'living': box(0.0, 0.0, 8.8, 5.8),
        'kitchen': box(8.8, 0.0, 16.8, 2.8),
        'dining': box(8.8, 2.8, 16.8, 5.8),
        'hallway': box(0.0, 5.8, 14.4, 8.2),
        'bath_common': box(14.4, 5.8, 16.8, 8.2),
        'bed_2': box(8.4, 8.2, 16.8, 13.6),
        'bath_master': box(0.0, 11.6, 2.2, 13.6),
        'bed_master': Polygon([(0.0, 8.2), (8.4, 8.2), (8.4, 13.6), (2.2, 13.6), (2.2, 11.6), (0.0, 11.6)])
    }
    
    mesh = build_house_from_layout({'rooms': rooms}, visualize=False)
    assert mesh is not None
    
    verts = np.asarray(mesh.vertices)
    tris = np.asarray(mesh.triangles)
    
    diagonal_wall_faces = []
    for tri in tris:
        v = verts[tri]
        z_min = v[:, 2].min()
        z_max = v[:, 2].max()
        if z_min < 0.1 and z_max > 2.5:
            pts_base = v[v[:, 2] < 0.1][:, :2]
            if len(pts_base) >= 2:
                dx = abs(pts_base[0, 0] - pts_base[1, 0])
                dy = abs(pts_base[0, 1] - pts_base[1, 1])
                if dx > 0.25 and dy > 0.25:
                    diagonal_wall_faces.append((pts_base[0], pts_base[1]))
                    
    assert len(diagonal_wall_faces) == 0, (
        f"REGRESSION DETECTED: Found {len(diagonal_wall_faces)} diagonal wall faces cutting across rooms! "
        f"Sample: {diagonal_wall_faces[:3]}"
    )

def test_wall_mesh_does_not_cross_room_interiors():
    """Ensure no wall mesh segment penetrates the interior of any room polygon."""
    rooms = {
        'living': box(0.0, 0.0, 8.0, 6.0),
        'bed_1': box(0.0, 6.0, 4.0, 12.0),
        'bed_2': box(4.0, 6.0, 8.0, 12.0),
    }
    
    mesh = build_house_from_layout({'rooms': rooms}, visualize=False)
    assert mesh is not None
    
    verts = np.asarray(mesh.vertices)
    tris = np.asarray(mesh.triangles)
    
    for r_name, r_poly in rooms.items():
        interior_zone = r_poly.buffer(-0.25)
        if interior_zone.is_empty:
            continue
            
        for tri in tris:
            v = verts[tri]
            if v[:, 2].min() < 0.1 and v[:, 2].max() > 2.5:
                pts_base = v[v[:, 2] < 0.1][:, :2]
                if len(pts_base) >= 2:
                    wall_seg = LineString([pts_base[0], pts_base[1]])
                    if wall_seg.length > 0.5:
                        cross_len = wall_seg.intersection(interior_zone).length
                        assert cross_len < 0.05, (
                            f"Wall segment {pts_base[0]} -> {pts_base[1]} crosses interior of room {r_name} (cross_len={cross_len:.2f}m)!"
                        )

def test_archetype_3d_generation_has_zero_diagonal_walls():
    """Verify that synthesized 2BHK and 3BHK archetypes produce zero diagonal walls."""
    spec_2bhk = {
        "rooms": [
            {"type": "living", "name": "living", "area": 22.0},
            {"type": "kitchen", "name": "kitchen", "area": 12.0},
            {"type": "hallway", "name": "hallway", "area": 6.0},
            {"type": "bedroom", "name": "bedroom_1", "area": 16.0},
            {"type": "bedroom", "name": "bedroom_2", "area": 13.0},
            {"type": "bathroom", "name": "bathroom_1", "area": 5.0},
            {"type": "bathroom", "name": "bathroom_2", "area": 5.0},
        ]
    }
    for seed in [42, 100, 2024]:
        res = select_and_partition_archetype(spec_2bhk, seed=seed)
        assert res is not None
        rooms_2bhk, env = res
        
        mesh = build_house_from_layout({"rooms": rooms_2bhk}, visualize=False)
        assert mesh is not None
        
        verts = np.asarray(mesh.vertices)
        tris = np.asarray(mesh.triangles)
        
        diagonals = []
        for tri in tris:
            v = verts[tri]
            if v[:, 2].min() < 0.1 and v[:, 2].max() > 2.5:
                pts_base = v[v[:, 2] < 0.1][:, :2]
                if len(pts_base) >= 2:
                    dx = abs(pts_base[0, 0] - pts_base[1, 0])
                    dy = abs(pts_base[0, 1] - pts_base[1, 1])
                    if dx > 0.25 and dy > 0.25:
                        diagonals.append((pts_base[0], pts_base[1]))
                        
        assert len(diagonals) == 0, f"Found {len(diagonals)} diagonal walls in 2BHK archetype (seed={seed})!"


def test_no_windows_on_interior_shared_walls():
    """
    Verifies that exterior windows are strictly positioned on true external envelope walls
    and NEVER appear on interior partition walls facing another room.
    """
    rooms = {
        'living': box(0.0, 0.0, 7.0, 4.0),
        'kitchen': box(7.0, 0.0, 11.0, 4.0),
        'bedroom_1': box(0.0, 4.0, 4.0, 8.0),
        'bedroom_2': box(4.0, 4.0, 8.0, 8.0),
        'bathroom': box(8.0, 4.0, 11.0, 7.0),
    }
    layout = {'rooms': rooms}
    mesh = build_house_from_layout(layout, visualize=False)
    assert mesh is not None
    
    windows = layout.get("windows", [])
    assert len(windows) > 0, "Exterior windows should be generated on exterior walls"
    
    envelope = unary_union(list(rooms.values()))
    ext_boundary = envelope.boundary
    
    for w in windows:
        seg = w["wall_segment"]
        mid = seg.interpolate(0.5, normalized=True)
        dist_to_exterior = ext_boundary.distance(mid)
        assert dist_to_exterior < 0.05, (
            f"Window in room '{w['room']}' is placed on an interior wall! "
            f"Distance to exterior boundary: {dist_to_exterior:.2f}m. Segment: {list(seg.coords)}"
        )
        
        # Verify it doesn't touch the interior of another room
        for other_name, other_poly in rooms.items():
            if other_name == w["room"]:
                continue
            assert not other_poly.buffer(-0.05).contains(mid), (
                f"Window in room '{w['room']}' penetrates into room '{other_name}'!"
            )

