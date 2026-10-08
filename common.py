from gtts import gTTS
import io
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


def generate_audio(text, lang, output_path, speed=NORMAL):
    """Generate a single MP3 from text in the given language."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(tts_bytes(text, lang))
    apply_speed(tmp_path, output_path, speed)
    os.unlink(tmp_path)
