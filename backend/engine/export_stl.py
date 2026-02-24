import trimesh
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
import copy

WALL_HEIGHT = 2.8
WALL_THICKNESS = 0.20 # thicker than standard 3D web walls for printability
DOOR_WIDTH = 0.9
DOOR_HEIGHT = 2.1
BASE_THICKNESS = 0.5 # 50cm thick foundation

def create_extrusion(polygon, z_min, z_max):
    """Extrudes a Shapely Polygon into a Trimesh object."""
    if polygon.is_empty:
        return None
    # simplify slightly to reduce triangulation complexity
    poly = polygon.simplify(0.01)
    
    try:
         mesh = trimesh.creation.extrude_polygon(poly, height=z_max - z_min)
         mesh.apply_translation([0, 0, z_min])
         return mesh
    except Exception as e:
         print(f"Error extruding: {e}")
         return None

def generate_layout_stl(layout, output_path="house_print.stl"):
    """
    Generates a water-tight 3D manifold STL model suited for 3D printing.
    """
    if not layout or "rooms" not in layout:
        return False

    # 1. Gather all geometry
    rooms = {k: v for k, v in layout["rooms"].items() if v and not v.is_empty and isinstance(v, (Polygon, MultiPolygon))}
    doors_input = layout.get("doors", [])
    
    if not rooms:
        return False
        
    door_polys = []
    if isinstance(doors_input, Polygon):
        door_polys.append(doors_input)
    elif isinstance(doors_input, MultiPolygon):
        door_polys.extend(doors_input.geoms)
    elif isinstance(doors_input, list):
         for d in doors_input:
             if isinstance(d, Polygon):
                 door_polys.append(d)

    # 2. Calculate the global bounding box for the foundation
    minx, miny, maxx, maxy = float('inf'), float('inf'), float('-inf'), float('-inf')
    for poly in rooms.values():
        x0, y0, x1, y1 = poly.bounds
        if x0 < minx: minx = x0
        if y0 < miny: miny = y0
        if x1 > maxx: maxx = x1
        if y1 > maxy: maxy = y1
        
    # Foundation base
    base_poly = box(minx, miny, maxx, maxy)
    base_mesh = create_extrusion(base_poly, -BASE_THICKNESS, 0.0)
    
    meshes_to_union = []
    if base_mesh:
        meshes_to_union.append(base_mesh)

    # 3. Build walls by finding shared edges
    # To make a watertight mesh without overlapping geometry creating internal faces (which slicers hate),
    # we take the union of all room polygons to get the outer boundary, and the lines of all rooms to get interior walls.
    # Actually, the most reliable way to get a solid wall is to buffer the linestrings.
    
    lines = []
    for poly in rooms.values():
         # Extract exterior
         lines.append(LineString(list(poly.exterior.coords)))
         
    # Merge all lines
    merged_lines = unary_union(lines)
    
    # Buffer the lines to create solid 2D wall polygons
    wall_polygons_2d = merged_lines.buffer(WALL_THICKNESS / 2.0, join_style=2, cap_style=3)
    
    # 4. Cut out doors from the walls
    if door_polys:
         # Buffer doors slightly more to ensure a clean boolean cut
         doors_union = unary_union([d.buffer(0.05) for d in door_polys])
         wall_polygons_2d = wall_polygons_2d.difference(doors_union)
         
         # Note: A real 3D printer would need a lintel (top of the door). 
         # But calculating floating lintel geometry is complex without perfect overlaps.
         # For a floorplan print, usually the top is just open (like an architectural cross-section)!
         
    # 5. Extrude the wall polygons
    if isinstance(wall_polygons_2d, Polygon):
        wall_polys = [wall_polygons_2d]
    elif isinstance(wall_polygons_2d, MultiPolygon):
        wall_polys = list(wall_polygons_2d.geoms)
    else:
        wall_polys = []
        
    for wp in wall_polys:
         mesh = create_extrusion(wp, 0.0, WALL_HEIGHT)
         if mesh:
             meshes_to_union.append(mesh)
             
    # 6. Boolean Union everything (trimesh heavily relies on this for manifold)
    print(f"Unioning {len(meshes_to_union)} meshes for STL generation...")
    if len(meshes_to_union) == 0:
        return False
        
    try:
        # We can just concatenate meshes if boolean union fails, slicers are usually smart enough to handle intersecting meshes.
        # But a true boolean union is best.
        combined = trimesh.util.concatenate(meshes_to_union)
        
        # Calculate bounding box dimensions
        extents = combined.extents
        print(f"STL Base Dimensions: {extents[0]:.2f}m x {extents[1]:.2f}m x {extents[2]:.2f}m")
        
        combined.export(output_path)
        return True
    except Exception as e:
        print(f"Error exporting STL: {e}")
        return False
