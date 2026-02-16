import sys
import os

# Mock the path setup
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "backend", "engine"))

try:
    from backend.services.generation_service import generation_service
    print("SUCCESS: generation_service imported")
    from backend.engine.text_to_specs_v2 import ProximityLayoutGenerator
    print("SUCCESS: engine imported")
    import fastapi
    import uvicorn
    print(f"SUCCESS: fastapi {fastapi.__version__}, uvicorn {uvicorn.__version__}")
    import firebase_admin
    print(f"SUCCESS: firebase_admin {firebase_admin.__version__}")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
