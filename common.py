from gtts import gTTS
import io
import json
import random
import urllib.request
import subprocess
import tempfile
import time
import os

SLOW   = 0.75
NORMAL = 1.0
FAST   = 1.5


TTS_DELAY = 0.3   # seconds to wait after each TTS request to avoid rate limits


def tts_bytes(text, lang, delay=TTS_DELAY, retries=5, backoff=5):
    for attempt in range(retries):
        try:
            buf = io.BytesIO()
            gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
            if delay > 0:
                time.sleep(delay)
            return buf.getvalue()
        except Exception:
            if attempt == retries - 1:
                raise
            wait = backoff * (2 ** attempt)
            print(f"  [rate limited, retrying in {wait}s...]")
            time.sleep(wait)


NEUROKONE_URL = "https://api.tartunlp.ai/text-to-speech/v2"   # backend of https://www.neurokone.ee
NEUROKONE_VOICES = ["albert", "indrek", "kalev", "kylli", "liivika",
                    "mari", "meelis", "peeter", "tambet", "vesta"]   # Estonian voices; "lee", "luukas" time out
# lee and luukas are listed by the API but currently time out (HTTP 408), so 'random' skips them
NEUROKONE_RANDOM_VOICES = [v for v in NEUROKONE_VOICES if v not in ("lee", "luukas")]
ENGINES = ["google", "neurokone"]


def neurokone_bytes(text, voice, delay=TTS_DELAY, retries=5, backoff=5):
    """Estonian TTS via Neurokõne. Returns MP3 bytes (API returns WAV, converted with ffmpeg)."""
    payload = json.dumps({"text": text, "speaker": voice, "speed": 1}).encode("utf-8")
    req = urllib.request.Request(NEUROKONE_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                wav = resp.read()
            if delay > 0:
                time.sleep(delay)
            break
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = backoff * (2 ** attempt)
            print(f"  [neurokone request failed ({e}), retrying in {wait}s...]")
            time.sleep(wait)
    result = subprocess.run(
        ["ffmpeg", "-f", "wav", "-i", "pipe:0", "-ar", "22050", "-ac", "1",
         "-acodec", "libmp3lame", "-q:a", "2", "-f", "mp3", "pipe:1"],
        input=wav, check=True, capture_output=True,
    )
    return result.stdout


def resolve_voice(voice):
    """'random' picks a different Neurokõne voice on each call."""
    return random.choice(NEUROKONE_RANDOM_VOICES) if voice == "random" else voice


def speech_bytes(text, lang, engine="google", voice="mari"):
    """MP3 bytes for text. Neurokõne only speaks Estonian; other languages fall back to Google."""
    if engine == "neurokone" and lang == "et":
        return neurokone_bytes(text, resolve_voice(voice))
    return tts_bytes(text, lang)


def add_engine_args(parser):
    parser.add_argument("--engine", choices=ENGINES, default="google",
                        help="TTS engine for Estonian: 'google' or 'neurokone' (default: google)")
    parser.add_argument("--voice", choices=NEUROKONE_VOICES + ["random"], default="mari",
                        help="Neurokõne voice, or 'random' for a different voice per item (default: mari)")


def atempo_filter(speed):
    stages = []
    while speed > 2.0:
        stages.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        stages.append("atempo=0.5")
        speed *= 2.0
    stages.append(f"atempo={speed}")
    return ",".join(stages)


def apply_speed(src, dst, speed):
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-filter:a", atempo_filter(speed), dst],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def silence_bytes(duration):
    """Generate MP3 silence of the given duration in seconds."""
    result = subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
         "-t", str(duration), "-q:a", "9", "-acodec", "libmp3lame", "-f", "mp3", "pipe:1"],
        check=True, capture_output=True,
    )
    return result.stdout


def generate_audio(text, lang, output_path, speed=NORMAL, engine="google", voice="mari"):
    """Generate a single MP3 from text in the given language."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(speech_bytes(text, lang, engine, voice))
    if engine == "google":
        apply_speed(tmp_path, output_path, speed)
        os.unlink(tmp_path)
    else:
        os.replace(tmp_path, output_path)
