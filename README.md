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
python voice_numbers.py [--limit N] [--lang {et-ru,ru-et,et,ru}]
```

| Flag        | Description                                                                     | Default   |
|-------------|---------------------------------------------------------------------------------|-----------|
| `--limit N` | Generate only the first N items per group (for testing)                         | all       |
| `--lang`    | Language mode: `et-ru` (ET then RU), `ru-et` (RU then ET), `et` only, `ru` only | `et-ru`   |

Each `--lang` mode writes to its own root folder (`output/et-ru/`, `output/ru-et/`, `output/et/`, `output/ru/`) so they don't overwrite each other.

**Output** — written to `output/<lang>/<category>/` (created automatically):

| Folder       | Contents                                              | Example file                          |
|--------------|-------------------------------------------------------|---------------------------------------|
| `cardinals/` | 1–100, 1 000, 10 000, 100 000, 1 000 000, 1980–2030   | `21_kakskümmend_üks.mp3`              |
| `ordinals/`  | 1st–100th, same large numbers and years               | `21_kahekümne_esimene.mp3`            |
| `dates/`     | "2nd of March" form, all 12 months, correct day count | `02.03_teine_märts.mp3`               |
| `dates_on/`  | "on the 2nd of March" form (different grammar)        | `02.03_teisel_märtsil.mp3`            |

**Filename format:** `<number>_<estonian text>.mp3` — the number (dates as `DD.MM`) is everything before the first `_`; the rest is the Estonian text with spaces replaced by `_`.

Each category folder also contains an `index.json` (`[{file, number, et, ru}, ...]`).

> **Note:** Existing files are skipped on re-runs. To regenerate a file, delete it first (or `rm -rf output/<lang>/` to regenerate a whole set).

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
| `--speed` | Speed multiplier (see below)       | `1.5`    |

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
