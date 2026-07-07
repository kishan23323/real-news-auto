"""
Per-sentence voice generation with optional progress callback.
"""
import asyncio, os, time
import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips

# edge-tts talks to Microsoft's speech service over a websocket. Two
# separate failure modes show up as "stuck forever" if you don't guard
# against them:
#   1) A single call's connection stalls (flaky network) -> timeout+retry.
#   2) Firing many requests back-to-back gets silently throttled by
#      Microsoft's free TTS endpoint -> a small delay between segments.
SEGMENT_TIMEOUT = 25    # seconds to wait for a single sentence before retrying
MAX_RETRIES     = 4     # attempts per sentence before raising
PACE_DELAY      = 1.5   # seconds to wait between segments, to avoid throttling


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


def _gen_with_retry(text, path, voice, on_retry=None):
    """Run _gen with a timeout, retrying with backoff. Raises on final failure."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            asyncio.run(asyncio.wait_for(_gen(text, path, voice), timeout=SEGMENT_TIMEOUT))
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return
            last_err = RuntimeError("edge-tts produced an empty audio file")
        except Exception as e:
            last_err = e
        if on_retry:
            on_retry(attempt, MAX_RETRIES, last_err)
        if attempt < MAX_RETRIES:
            time.sleep(min(3 * attempt, 15))
    raise RuntimeError(
        f"Voice generation failed after {MAX_RETRIES} attempts for voice '{voice}': {last_err}. "
        "This is almost always Microsoft's free edge-tts endpoint throttling/stalling "
        "requests that come in too fast, or a connection hiccup. Try again in a "
        "minute, or reduce how many sentences are sent per run."
    )


def generate_voice(text, out_path="voice.mp3", voice="en-US-AriaNeural"):
    _gen_with_retry(text, out_path, voice)
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

        if progress_cb:
            progress_cb(i, total, f"generating segment {i+1}/{total}...")

        _gen_with_retry(sentence, path, voice, on_retry=lambda a, m, e, _i=i: (
            progress_cb(i, total, f"segment {_i+1}/{total} retry {a}/{m}: {e}") if progress_cb else None
        ))

        dur = AudioFileClip(path).duration
        paths.append(path)
        durations.append(dur)
        if progress_cb:
            progress_cb(i + 1, total, sentence[:60])

        # pace requests so we don't get throttled by hitting the TTS
        # endpoint back-to-back for 20+ sentences in a row
        if i < total - 1:
            time.sleep(PACE_DELAY)
    return paths, durations


def combine_audio(paths, out_path="voice_combined.mp3"):
    clips = [AudioFileClip(p) for p in paths]
    combined = concatenate_audioclips(clips)
    combined.write_audiofile(out_path, logger=None)
    return out_path
