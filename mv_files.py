import os
import shutil

source_dir = "."
target_dir = "backend/engine"

# Ensure target directory exists
os.makedirs(target_dir, exist_ok=True)

# Files/Extensions to move
extensions = [".py", ".csv", ".json", ".ply"]
directories = ["plan_pngs", "ResPlan_Extracted"]

# List of files to ignore (do not move these)
ignore_files = ["backend", "frontend", "mv_files.py", "venv", ".git", ".gitignore"]

for item in os.listdir(source_dir):
    if item in ignore_files or item.startswith("."):
        continue

    src_path = os.path.join(source_dir, item)
    
    if os.path.isdir(src_path):
        if item in directories:
            # Move directory
            shutil.move(src_path, os.path.join(target_dir, item))
            print(f"Moved directory: {item}")
    else:
        # Check extension
        _, ext = os.path.splitext(item)
        if ext in extensions:
             # Move file
            shutil.move(src_path, os.path.join(target_dir, item))
            print(f"Moved file: {item}")

# Create __init__ files
with open("backend/__init__.py", "w") as f:
    pass
with open("backend/engine/__init__.py", "w") as f:
    pass

print("Restructuring complete.")
