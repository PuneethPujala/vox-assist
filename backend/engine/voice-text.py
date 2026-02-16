import speech_recognition as sr
import whisper
import os
import tempfile
import sys
import winsound  # Windows only
# Or use `playsound` library for cross-platform beep

# --- FFmpeg Fix (Keep this if you are on Windows) ---
os.environ["PATH"] += os.pathsep + os.getcwd()

def listen_and_transcribe():
    print("Loading English-only Whisper model... (Optimizing for accuracy)")
    # 'base.en' is trained specifically for English, reducing errors.
    model = whisper.load_model("base.en")
    recognizer = sr.Recognizer()

    print("\n✅ System Ready.")

    while True:
        # 1. Ask the user (Terminal Interface)
        print("\n" + "="*50)
        user_input = input("🎤 Do you want to speak? (y/n): ").lower().strip()

        if user_input == 'n':
            print("Exiting program. Goodbye!")
            sys.exit()
            
        elif user_input == 'y':
            with sr.Microphone() as source:
                print("\nAdjusting for background noise... (stay quiet for 1 sec)")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # SETTINGS FOR ACCURACY
                # ---------------------
                # Energy: Sensitivity to sound (400 is standard)
                recognizer.energy_threshold = 400
                # Pause: How long silence (in seconds) implies the sentence is OVER.
                # 2.0 seconds prevents it from cutting you off while thinking.
                recognizer.pause_threshold = 2.0
                
                print(f"🔴 Listening... (I will stop if you are silent for 5 seconds)")
                
                try:
                    # 2. The 5-Second Rule
                    # timeout=5: If you don't START talking within 5s, it stops.
                    audio_data = recognizer.listen(source, timeout=5)
                    
                    print("✅ Processing English audio...")

                    # Save to temp file
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                        temp_audio.write(audio_data.get_wav_data())
                        temp_audio_path = temp_audio.name

                    # 3. Transcribe with English Optimization
                    # language='en': Forces the AI to only look for English words
                    result = model.transcribe(temp_audio_path, fp16=False, language='en')
                    text = result['text'].strip()

                    # Cleanup
                    os.remove(temp_audio_path)
                    
                    # Output
                    if text:
                        print(f"\n📝 Output: \"{text}\"")
                    else:
                        print("\n⚠️  No words detected.")

                except sr.WaitTimeoutError:
                    print("\n⏱️  Timeout! You didn't speak within 5 seconds.")
                
                except KeyboardInterrupt:
                    print("\n\n👋 Interrupted by user. Goodbye!")
                    sys.exit(0)

                except Exception as e:
                    print(f"\n❌ Error: {e}")
        
        else:
            print("Invalid input. Please type 'y' for Yes or 'n' for No.")

if __name__ == "__main__":
    listen_and_transcribe()