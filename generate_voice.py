"""
Step 4: Free text-to-speech, per sentence for exact sync timing.

Supports both Hindi and English automatically based on the article language.

Hindi voices (edge-tts):
  Female: hi-IN-SwaraNeural   (natural, news-style)
  Male:   hi-IN-MadhurNeural

English voices:
  Female: en-US-AriaNeural
  Male:   en-US-GuyNeural
"""
import asyncio
import os
import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips


def detect_language(text: str) -> str:
    """Simple detection: if more than 20% chars are Devanagari, treat as Hindi."""
    devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    return "hi" if devanagari / max(len(text), 1) > 0.2 else "en"


def pick_voice(lang: str, gender: str = "female") -> str:
    voices = {
        "hi": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
        "en": {"female": "en-US-AriaNeural",  "male": "en-US-GuyNeural"},
    }
    return voices.get(lang, voices["en"])[gender]


async def _gen(text: str, path: str, voice: str):
    await edge_tts.Communicate(text, voice).save(path)


def generate_voice(text: str, out_path: str = "voice.mp3", voice: str = "en-US-AriaNeural") -> str:
    asyncio.run(_gen(text, out_path, voice))
    return out_path


def generate_voice_segments(sentences, out_dir: str = "voice_segments", lang: str = "en", gender: str = "female"):
    os.makedirs(out_dir, exist_ok=True)
    voice = pick_voice(lang, gender)
    print(f"  Using voice: {voice}")
    paths, durations = [], []
    for i, sentence in enumerate(sentences):
        path = os.path.join(out_dir, f"seg_{i}.mp3")
        asyncio.run(_gen(sentence, path, voice))
        dur = AudioFileClip(path).duration
        paths.append(path)
        durations.append(dur)
    return paths, durations


def combine_audio(paths, out_path: str = "voice_combined.mp3") -> str:
    clips = [AudioFileClip(p) for p in paths]
    combined = concatenate_audioclips(clips)
    combined.write_audiofile(out_path, logger=None)
    return out_path
