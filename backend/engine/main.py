from layout_synthesizer_adjacency import synthesize_layout_from_spec
from resplan_to_3d import build_house_from_layout
from floorplan_2d_visualizer import draw_2d_floorplan, get_wall_segments
from text_to_specs_v2 import ProximityLayoutGenerator
import sys
import random
import os
import csv

def _export_layout_to_csv(csv_path, spec, layout, total_area, image_filename):
    """Export a rich feature row for the generated layout to CSV."""

    rooms_spec = spec.get("rooms", [])
    rooms_geom = layout.get("rooms", {})
    adjacency = layout.get("adjacency", [])
    doors_geom = layout.get("doors")

    # Room counts / presence flags from spec
    n_bedrooms = sum(1 for r in rooms_spec if r["type"] == "bedroom")
    n_bathrooms = sum(1 for r in rooms_spec if r["type"] == "bathroom")
    has_kitchen = int(any(r["type"] == "kitchen" for r in rooms_spec))
    has_dining = int(any(r["type"] == "dining" for r in rooms_spec))
    has_balcony = int(any(r["type"] == "balcony" for r in rooms_spec))
    has_study = int(any(r["type"] == "study" for r in rooms_spec))
    has_store = int(any(r["type"] in ("storage", "store") for r in rooms_spec))

    # Helper to get first/second instance area for a room type
    def _areas_for_type(t):
        vals = [r["area"] for r in rooms_spec if r["type"] == t]
        vals += [0.0, 0.0]  # pad
        return vals[0], vals[1]

    living_area, _ = _areas_for_type("living")
    bedroom1_area, bedroom2_area = _areas_for_type("bedroom")
    kitchen_area, _ = _areas_for_type("kitchen")
    bathroom1_area, bathroom2_area = _areas_for_type("bathroom")
    balcony_area, _ = _areas_for_type("balcony")

    # Adjacency flags from layout adjacency list
    def _has_adj(type_a, type_b):
        wanted = {type_a, type_b}
        for r1, r2 in adjacency:
            t1 = r1.split("_")[0]
            t2 = r2.split("_")[0]
            if {t1, t2} == wanted:
                return 1
        return 0

    adj_living_bedroom = _has_adj("living", "bedroom")
    adj_living_kitchen = _has_adj("living", "kitchen")
    adj_living_bathroom = _has_adj("living", "bathroom")
    adj_bedroom_bathroom = _has_adj("bedroom", "bathroom")
    adj_kitchen_dining = _has_adj("kitchen", "dining")
    adj_living_balcony = _has_adj("living", "balcony")

    # Bedroom1 geometry (if present)
    b1_poly = rooms_geom.get("bedroom_1")
    if b1_poly is not None:
        cx, cy = b1_poly.centroid.x, b1_poly.centroid.y
        minx, miny, maxx, maxy = b1_poly.bounds
        bw = maxx - minx
        bh = maxy - miny
        brot = 0.0  # rooms are axis-aligned rectangles in this generator
        baspect = (bw / bh) if bh > 0 else 0.0
    else:
        cx = cy = bw = bh = brot = baspect = 0.0

    # Graph metrics on room adjacency graph
    nodes = list(rooms_geom.keys())
    neighbors = {n: set() for n in nodes}
    for r1, r2 in adjacency:
        if r1 in neighbors and r2 in neighbors:
            neighbors[r1].add(r2)
            neighbors[r2].add(r1)

    # BFS distances between all pairs
    def _bfs(start):
        from collections import deque
        dist = {start: 0}
        dq = deque([start])
        while dq:
            u = dq.popleft()
            for v in neighbors[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    dq.append(v)
        return dist

    all_dists = []
    for n in nodes:
        d = _bfs(n)
        for m, val in d.items():
            if m != n:
                all_dists.append(val)

    if all_dists:
        avg_path_length = sum(all_dists) / len(all_dists)
        max_path_length = max(all_dists)
    else:
        avg_path_length = 0.0
        max_path_length = 0.0

    dead_end_count = sum(1 for n in nodes if len(neighbors[n]) == 1)

    # Wall / door statistics
    wall_segments = get_wall_segments(rooms_geom) if rooms_geom else []
    total_walls = float(len(wall_segments)) if wall_segments else 1.0

    if doors_geom is None or doors_geom.is_empty:
        door_count = 0
    else:
        if hasattr(doors_geom, "geoms"):
            door_count = len(list(doors_geom.geoms))
        else:
            door_count = 1

    openness_ratio = door_count / total_walls

    # Exterior wall ratio: perimeter / area of all rooms combined
    total_area_geom = 0.0
    total_perimeter = 0.0
    for poly in rooms_geom.values():
        total_area_geom += poly.area
        total_perimeter += poly.length
    exterior_wall_ratio = (total_perimeter / total_area_geom) if total_area_geom > 0 else 0.0

    # High-level labels / priorities (placeholders for now)
    # style: 0=open, 1=closed, 2=mixed
    style = 2
    privacy_priority = 0.5
    sunlight_priority = 0.5
    circulation_priority = 0.5

    valid_plan = 1 if rooms_geom else 0
    privacy_score = 0.0
    daylight_score = 0.0
    circulation_score = 0.0
    efficiency_score = 0.0

    # Build CSV row
    row = {
        "image_file": image_filename,
        "total_area": float(total_area) if total_area is not None else 0.0,
        "n_bedrooms": n_bedrooms,
        "n_bathrooms": n_bathrooms,
        "has_kitchen": has_kitchen,
        "has_dining": has_dining,
        "has_balcony": has_balcony,
        "has_study": has_study,
        "has_store": has_store,
        "living_area": living_area,
        "bedroom1_area": bedroom1_area,
        "bedroom2_area": bedroom2_area,
        "kitchen_area": kitchen_area,
        "bathroom1_area": bathroom1_area,
        "bathroom2_area": bathroom2_area,
        "balcony_area": balcony_area,
        "style": style,
        "privacy_priority": privacy_priority,
        "sunlight_priority": sunlight_priority,
        "circulation_priority": circulation_priority,
        "adj_living_bedroom": adj_living_bedroom,
        "adj_living_kitchen": adj_living_kitchen,
        "adj_living_bathroom": adj_living_bathroom,
        "adj_bedroom_bathroom": adj_bedroom_bathroom,
        "adj_kitchen_dining": adj_kitchen_dining,
        "adj_living_balcony": adj_living_balcony,
        "bedroom1_x": cx,
        "bedroom1_y": cy,
        "bedroom1_w": bw,
        "bedroom1_h": bh,
        "bedroom1_rotation": brot,
        "bedroom1_aspect": baspect,
        "avg_path_length": avg_path_length,
        "max_path_length": max_path_length,
        "dead_end_count": dead_end_count,
        "openness_ratio": openness_ratio,
        "door_count": door_count,
        "exterior_wall_ratio": exterior_wall_ratio,
        "valid_plan": valid_plan,
        "privacy_score": privacy_score,
        "daylight_score": daylight_score,
        "circulation_score": circulation_score,
        "efficiency_score": efficiency_score,
    }

    fieldnames = list(row.keys())
    file_exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or f.tell() == 0:
            writer.writeheader()
        writer.writerow(row)


def main():
    print("\n" + "="*70)
    print("🏠 AI HOUSE LAYOUT GENERATOR (RANDOMIZED)")
    print("="*70)
    
    # -------------------------------
    # 1. Take user input
    # -------------------------------
    user_prompt = input("\n📝 Describe your house requirements:\n> ").strip()
    
    if not user_prompt:
        print("❌ No input provided. Exiting.")
        return

    # -------------------------------
    # 2. Convert text → structured rooms using AI
    # -------------------------------
    print("\n🤖 Processing your requirements with AI...")
    architect = ProximityLayoutGenerator()
    try:
        rooms = architect.generate_blueprint(user_prompt)
    except Exception as e:
        print(f"❌ AI generation failed: {e}")
        return

    if not rooms or not isinstance(rooms, list):
        print("❌ AI returned invalid or empty room list.")
        return

    # -------------------------------
    # 3. Convert into spec format + VALIDATE
    # -------------------------------
    spec = {"rooms": []}
    for i, room in enumerate(rooms):
        if not isinstance(room, dict):
            print(f"⚠️  Skipping invalid room entry #{i+1}")
            continue
        
        r_type = room.get("type")
        area = room.get("area")
        
        if not r_type or not isinstance(r_type, str) or not r_type.strip():
            print(f"⚠️  Room #{i+1} missing valid 'type' — skipping")
            continue
            
        if not (isinstance(area, (int, float)) and area > 0):
            print(f"⚠️  Room '{r_type}' has invalid area ({area}) — skipping")
            continue
        
        spec["rooms"].append({
            "type": r_type.strip().lower(),
            "area": float(area)
        })

    if not spec["rooms"]:
        print("❌ No valid rooms to generate layout. Exiting.")
        return

    print("\n" + "="*70)
    print("📋 GENERATED SPECIFICATION")
    print("="*70)
    for r in spec["rooms"]:
        print(f"   • {r['type'].upper()}: {r['area']} sq m")

    # -------------------------------
    # 4. Generate layout using architectural AI (with random seed for variation)
    # -------------------------------
    print("\n" + "="*70)
    print("🏗️  GENERATING ARCHITECTURAL LAYOUT")
    print("="*70)
    
    # Use random seed for variation (comment out for reproducible runs)
    random_seed = random.randint(1, 999999)
    print(f"   🎲 Random seed: {random_seed}")
    
    try:
        layout = synthesize_layout_from_spec(spec, {"RANDOM_SEED": random_seed})
    except Exception as e:
        print(f"❌ Layout synthesis failed: {e}")
        import traceback
        traceback.print_exc()
        return

    if not layout.get("rooms"):
        print("❌ Layout generation produced no rooms.")
        return

    print("\n📦 Rooms placed:")
    for r in layout["rooms"]:
        print(f"   • {r}")

    print("\n🔗 Room connections:")
    for a in layout["adjacency"]:
        print(f"   • {a[0]} ↔ {a[1]}")

    # -------------------------------
    # 5. Generate 2D Floor Plan
    # -------------------------------
    print("\n" + "="*70)
    print("📐 GENERATING 2D FLOOR PLAN")
    print("="*70)
    
    image_filename = "floorplan_2d.png"

    # Export dataset row before or after visualization
    total_area_meta = None
    if getattr(architect, "last_metadata", None) is not None:
        total_area_meta = architect.last_metadata.get("total_area")

    _export_layout_to_csv("layout_data.csv", spec, layout, total_area_meta, image_filename)

    try:
        draw_2d_floorplan(layout, image_filename)
    except Exception as e:
        print(f"⚠️  2D visualization failed: {e}")
        # Don't exit — 3D might still work

    # -------------------------------
    # 6. Build 3D house visualization
    # -------------------------------
    print("\n" + "="*70)
    print("🎨 GENERATING 3D MODEL")
    print("="*70)
    
    try:
        build_house_from_layout(layout)
    except Exception as e:
        print(f"❌ 3D generation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*70)
    print("✅ GENERATION COMPLETE!")
    print("="*70)
    print("\n📁 Outputs:")
    print("   • 2D Floor Plan: floorplan_2d.png")
    print("   • 3D Model: Interactive window (now closed)")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()