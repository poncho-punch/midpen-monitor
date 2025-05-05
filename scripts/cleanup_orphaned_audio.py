#!/usr/bin/env python3
"""
Deletes orphaned .mp3 files in data/audio/ that do not have a corresponding transcript (.json) in data/transcripts/.
Run this script periodically (e.g., via cron or as a background thread) to keep the audio directory clean.
"""
import os

AUDIO_DIR = "data/audio"
TRANSCRIPT_DIR = "data/transcripts"

def main():
    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")]
    transcript_bases = {os.path.splitext(f)[0] for f in os.listdir(TRANSCRIPT_DIR) if f.endswith(".json")}
    deleted = []
    for audio_file in audio_files:
        base = os.path.splitext(audio_file)[0]
        if base not in transcript_bases:
            audio_path = os.path.join(AUDIO_DIR, audio_file)
            try:
                os.remove(audio_path)
                deleted.append(audio_file)
                print(f"Deleted orphaned audio: {audio_file}")
            except Exception as e:
                print(f"Failed to delete {audio_file}: {e}")
    if not deleted:
        print("No orphaned audio files found.")

if __name__ == "__main__":
    main()
