import whisper
import logging
import os

logger = logging.getLogger(__name__)

# Ensure ffmpeg.exe from root directory is accessible via PATH
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = root_dir + os.pathsep + os.environ.get("PATH", "")

def transcribe_audio(file_path: str, model=None) -> str:
    """
    Transcribes an audio file to text using Whisper base.en model.
    Accepts a pre-loaded model for performance. Falls back to loading if not provided.
    Returns transcribed text string, or empty string on failure.
    """
    try:
        if model is None:
            logger.warning("[VOICE] ⚠️  Whisper model not pre-loaded — loading fresh. This will be slow.")
            print("[VOICE] ⚠️  Whisper model not pre-loaded — loading fresh. This will be slow.")
            model = whisper.load_model("base.en")

        print(f"[VOICE] 🎙️  Starting transcription for file: {file_path}")
        result = model.transcribe(file_path, fp16=False, language='en')
        text = result['text'].strip()

        if not text:
            print("[VOICE] ⚠️  Transcription returned empty — no speech detected in audio.")
            return ""

        print(f"[VOICE] ✅  Transcription successful: \"{text[:80]}\"")
        return text

    except FileNotFoundError:
        print(f"[VOICE] ❌  ERROR — Audio file not found at path: {file_path}")
        logger.error(f"[VOICE] Audio file not found: {file_path}")
        return ""

    except Exception as e:
        print(f"[VOICE] ❌  ERROR — Transcription failed: {str(e)}")
        logger.error(f"[VOICE] Transcription failed: {e}")
        return ""