"""
Step 4: Free text-to-speech, generated PER SENTENCE (not one big block).

Why per-sentence: this gives us the EXACT spoken duration of each
sentence, so images and on-screen captions can be perfectly synced to
what's actually being said -- instead of guessing/dividing time evenly.
"""
import asyncio
import os
import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips


async def _gen(text: str, path: str, voice: str):
    await edge_tts.Communicate(text, voice).save(path)


def generate_voice(text: str, out_path: str = "voice.mp3", voice: str = "en-US-AriaNeural") -> str:
    """Simple single-file version (kept for backwards compatibility)."""
    asyncio.run(_gen(text, out_path, voice))
    return out_path


def generate_voice_segments(sentences, out_dir: str = "voice_segments", voice: str = "en-US-AriaNeural"):
    """
    Generates one audio file per sentence and returns (paths, durations).
    durations are the EXACT seconds each sentence takes to speak.
    """
    os.makedirs(out_dir, exist_ok=True)
    paths, durations = [], []
    for i, sentence in enumerate(sentences):
        path = os.path.join(out_dir, f"seg_{i}.mp3")
        asyncio.run(_gen(sentence, path, voice))
        dur = AudioFileClip(path).duration
        paths.append(path)
        durations.append(dur)
    return paths, durations


def combine_audio(paths, out_path: str = "voice_combined.mp3") -> str:
    """Stitches all per-sentence audio files into one continuous track."""
    clips = [AudioFileClip(p) for p in paths]
    combined = concatenate_audioclips(clips)
    combined.write_audiofile(out_path, logger=None)
    return out_path
