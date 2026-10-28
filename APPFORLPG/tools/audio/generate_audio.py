import os
import json
import time
import hashlib
from gtts import gTTS

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(script_dir, "manifest.json")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Output directory inside Android assets
    android_assets_audio = os.path.join(script_dir, "..", "..", "app", "src", "main", "assets", "audio")
    android_assets_audio = os.path.abspath(android_assets_audio)

    voices = manifest.get("voices", {})
    items = manifest.get("items", [])

    generated_count = 0
    skipped_count = 0
    failed_count = 0

    index_data = {}

    for item in items:
        item_id = item["id"]
        index_data[item_id] = {}

        for lang, text in item["text"].items():
            lang_dir = os.path.join(android_assets_audio, lang)
            os.makedirs(lang_dir, exist_ok=True)

            file_path = os.path.join(lang_dir, f"{item_id}.mp3")
            voice_cfg = voices.get(lang, {"lang": lang, "tld": "com"})

            sha1 = hashlib.sha1((text + lang + voice_cfg.get("tld", "")).encode("utf-8")).hexdigest()
            index_data[item_id][lang] = {
                "file": f"audio/{lang}/{item_id}.mp3",
                "sha1": sha1
            }

            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                print(f"[SKIP] Existing audio for {item_id} ({lang})")
                skipped_count += 1
                continue

            print(f"[GENERATE] Generating {item_id} ({lang})...")
            try:
                tts = gTTS(text=text, lang=voice_cfg.get("lang", lang), tld=voice_cfg.get("tld", "com"))
                temp_path = file_path + ".tmp"
                tts.save(temp_path)

                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(temp_path, file_path)
                    index_data[item_id][lang]["bytes"] = os.path.getsize(file_path)
                    generated_count += 1
                    time.sleep(0.5) # Gentle pause between gTTS API requests
                else:
                    print(f"[ERROR] 0-byte generated file for {item_id} ({lang})")
                    failed_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to generate {item_id} ({lang}): {e}")
                failed_count += 1

    # Save audio index file
    index_file_path = os.path.join(android_assets_audio, "audio-index.json")
    with open(index_file_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    print("\n--- Audio Generation Summary ---")
    print(f"Generated: {generated_count}")
    print(f"Skipped:   {skipped_count}")
    print(f"Failed:    {failed_count}")
    print(f"Index:     {index_file_path}")

if __name__ == "__main__":
    main()
