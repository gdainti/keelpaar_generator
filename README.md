# keelpaar_generator

Toolkit for generating Estonian–Russian audio vocabulary files using Google TTS.

## Prerequisites

```bash
brew install ffmpeg
pip install gtts num2words
```

## Scripts

### `voice_numbers.py` — number vocabulary

Generates audio files for cardinals, ordinals, and dates. Each number is spoken first in Estonian, then in Russian.

```bash
python voice_numbers.py [--shuffle] [--limit N] [--lang {both,et,ru}]
```

| Flag        | Description                                             | Default |
|-------------|---------------------------------------------------------|---------|
| `--shuffle` | Randomise order before generating                       | off     |
| `--limit N` | Generate only the first N items per group (for testing) | all     |
| `--lang`    | Generate `both` languages, `et` only, or `ru` only     | `both`  |

When `--lang et` or `--lang ru` is used, files are saved with a `_et`/`_ru` suffix (e.g. `cardinal_1_et.mp3`) so they don't overwrite the full bilingual files.

**Output** — written to `output/` (created automatically):

| Prefix          | Contents                                              |
|-----------------|-------------------------------------------------------|
| `cardinal_N`    | 1–100, 1 000, 10 000, 100 000, 1 000 000, 1980–2030   |
| `ordinal_N`     | 1st–100th, same large numbers and years               |
| `date_MM_N`     | "2nd of March" form, all 12 months, correct day count |
| `date_on_MM_N`  | "on the 2nd of March" form (different grammar)        |

> **Note:** Existing files are skipped on re-runs. To regenerate a file, delete it from `output/` first (`rm output/cardinal_1.mp3` or `rm -rf output/` to regenerate everything).

---

### `voice_text.py` — arbitrary text

Generates a single MP3 from any text in any language.

**Option 1 — CLI:**
```bash
python voice_text.py "tere maailm" output/hello.mp3
python voice_text.py "привет мир" output/hello_ru.mp3 --lang ru
python voice_text.py "tere" output/hello.mp3 --speed 1.5
```

**Option 2 — paste directly in the file:**
```python
# --- inline config (set these to skip CLI args) ---
TEXT   = "tere maailm"
OUTPUT = "output/hello.mp3"
LANG   = "et"
SPEED  = FAST
```
Then just run `python voice_text.py` with no arguments.

| Flag      | Description                        | Default  |
|-----------|------------------------------------|----------|
| `--lang`  | Language code (`et`, `ru`, …)      | `et`     |
| `--speed` | Speed multiplier (see below)       | `1.0`    |

---

## Speed

Speed constants are defined in `common.py` and used by all scripts:

```python
SLOW   = 0.75
NORMAL = 1.0
FAST   = 1.5
```

Set `SPEED` near the top of whichever script you are running:

```python
SPEED = FAST   # ← change this
```

## Project structure

```
common.py         ← shared TTS utilities (tts_bytes, apply_speed, generate_audio)
voice_numbers.py  ← number vocabulary generator
voice_text.py     ← single-text generator
output/           ← generated MP3 files
```
