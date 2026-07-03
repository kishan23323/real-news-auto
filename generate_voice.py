"""
Per-sentence voice generation with optional progress callback.
"""
import asyncio, os
import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips


def detect_language(text):
    devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    return "hi" if devanagari / max(len(text), 1) > 0.2 else "en"


def pick_voice(lang, gender="female"):
    voices = {
        "hi": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
        "en": {"female": "en-US-AriaNeural",  "male": "en-US-GuyNeural"},
    }
    return voices.get(lang, voices["en"])[gender]


async def _gen(text, path, voice):
    await edge_tts.Communicate(text, voice).save(path)


def generate_voice(text, out_path="voice.mp3", voice="en-US-AriaNeural"):
    asyncio.run(_gen(text, out_path, voice))
    return out_path


def generate_voice_segments(sentences, out_dir="voice_segments",
                             lang="en", gender="female", progress_cb=None):
    """
    progress_cb(i, total, sentence) — called after each sentence is done.
    Lets the caller emit SSE updates so the connection stays alive.
    """
    os.makedirs(out_dir, exist_ok=True)
    voice = pick_voice(lang, gender)
    print(f"  Voice: {voice}")
    paths, durations = [], []
    total = len(sentences)
    for i, sentence in enumerate(sentences):
        path = os.path.join(out_dir, f"seg_{i}.mp3")
        asyncio.run(_gen(sentence, path, voice))
        dur = AudioFileClip(path).duration
        paths.append(path)
        durations.append(dur)
        if progress_cb:
            progress_cb(i + 1, total, sentence[:60])
    return paths, durations


def combine_audio(paths, out_path="voice_combined.mp3"):
    clips = [AudioFileClip(p) for p in paths]
    combined = concatenate_audioclips(clips)
    combined.write_audiofile(out_path, logger=None)
    return out_path
