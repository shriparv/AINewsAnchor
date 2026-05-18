import asyncio
import os
import shutil
from modules.tts import (
    generate_kokoro_tts, generate_piper_tts, generate_edge_tts,
    VOICES_KOKORO, VOICES_PIPER, VOICES_EDGE
)

async def test_all_voices():
    test_text = "Hello! I am testing this voice for your AI news anchor. Do you like how I sound?"
    output_dir = "output/voice_tests"
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    print("🎙️ Starting Batch Voice Test...")
    print(f"📁 All samples will be saved to: {os.path.abspath(output_dir)}\n")

    # 1. Test Kokoro Voices
    print("--- Testing Kokoro Voices (Local) ---")
    for v in VOICES_KOKORO:
        path = os.path.join(output_dir, f"kokoro_{v}.mp3")
        try:
            print(f"  🔊 Generating Kokoro: {v}...")
            await generate_kokoro_tts(test_text, v, path)
        except Exception as e:
            print(f"  ❌ Failed Kokoro {v}: {e}")

    # 2. Test Piper Voices
    print("\n--- Testing Piper Voices (Local) ---")
    for v in VOICES_PIPER:
        path = os.path.join(output_dir, f"piper_{v}.wav") # Piper outputs wav usually
        try:
            print(f"  🔊 Generating Piper: {v}...")
            await generate_piper_tts(test_text, v, path)
        except Exception as e:
            print(f"  ❌ Failed Piper {v}: {e}")

    # 3. Test Edge Voices
    print("\n--- Testing Edge Voices (Cloud) ---")
    for v in VOICES_EDGE:
        path = os.path.join(output_dir, f"edge_{v}.mp3")
        json_path = path + ".json"
        try:
            print(f"  🔊 Generating Edge: {v}...")
            await generate_edge_tts(test_text, v, path, json_path)
        except Exception as e:
            print(f"  ❌ Failed Edge {v}: {e}")

    print(f"\n✅ All tests complete! Check the '{output_dir}' folder to listen to them all.")
    os.startfile(os.path.abspath(output_dir))

if __name__ == "__main__":
    asyncio.run(test_all_voices())
