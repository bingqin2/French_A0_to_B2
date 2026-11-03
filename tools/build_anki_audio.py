#!/usr/bin/env python3
"""Make a French pronunciation mp3 for every vocabulary word.

Uses the macOS French voice "Thomas" (say + ffmpeg). Files go to
词汇_Vocabulary/Anki/audio/ and are only made once. Afterwards build_vocab.py
adds a [sound:…] tag to each card in the Anki import files.
Usage: python3 tools/build_anki_audio.py
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_vocab  # noqa: E402
from build_vocab import AUDIO_DIR, RATE, VOICE, all_words, audio_name, speech_text  # noqa: E402


def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    made = total = 0
    for _, _, r in all_words():
        total += 1
        path = os.path.join(AUDIO_DIR, audio_name(r["fr"]))
        if os.path.exists(path):
            continue
        aiff = path[:-4] + ".aiff"
        subprocess.run(["say", "-v", VOICE, "-r", RATE, "-o", aiff, speech_text(r["fr"])], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", aiff,
                        "-ac", "1", "-b:a", "64k", path], check=True)
        os.remove(aiff)
        made += 1
    print(f"✓ audio: {made} new, {total} words in total ({os.path.relpath(AUDIO_DIR, build_vocab.ROOT)})")
    build_vocab.main()


if __name__ == "__main__":
    main()
