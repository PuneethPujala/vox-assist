import sys
print(f"Python: {sys.executable}")

try:
    import torch
    print(f"Torch version: {torch.__version__}")
    print("Torch OK")
except Exception as e:
    print(f"Torch FAILED: {e}")

try:
    import whisper
    m = whisper.load_model("base.en")
    print("Whisper OK")
except Exception as e:
    print(f"Whisper FAILED: {e}")