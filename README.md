# keelpaar_generator

Toolkit for generating Estonian–Russian audio vocabulary files using Google TTS or [Neurokõne](https://www.neurokone.ee) (Estonian neural TTS by TartuNLP).

## Prerequisites

```bash
brew install ffmpeg
pip install gtts num2words
```

## Scripts

### `voice_numbers.py` — number vocabulary

Generates audio files for cardinals, ordinals, and dates. Each number is spoken first in Estonian, then in Russian.

```bash
python voice_numbers.py [--limit N] [--lang {et-ru,ru-et,et,ru}] [--engine {google,neurokone}] [--voice NAME]
```

| Flag        | Description                                                                     | Default   |
|-------------|---------------------------------------------------------------------------------|-----------|
| `--limit N` | Generate only the first N items per group (for testing)                         | all       |
| `--lang`    | Language mode: `et-ru` (ET then RU), `ru-et` (RU then ET), `et` only, `ru` only | `et-ru`   |
| `--engine`  | TTS engine for Estonian (see [Engines and voices](#engines-and-voices))          | `google`  |
| `--voice`   | Neurokõne voice, or `random` for a different voice per item                     | `mari`    |

Each `--lang` mode writes to its own root folder (`output/et-ru/`, `output/ru-et/`, `output/et/`, `output/ru/`) so they don't overwrite each other. With `--engine neurokone` the folder also includes the voice, e.g. `output/et-ru_neurokone_mari/`.

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
python voice_text.py "tere maailm" output/hello.mp3 --engine neurokone --voice kalev
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
| `--engine`| `google` or `neurokone`            | `google` |
| `--voice` | Neurokõne voice                    | `mari`   |

---

## Engines and voices

- `google` — Google Translate TTS (via `gtts`), any language, one voice.
- `neurokone` — [Neurokõne](https://www.neurokone.ee) neural TTS (API: `https://api.tartunlp.ai/text-to-speech/v2`). **Estonian only** — Russian parts are still spoken by Google.

Neurokõne voices (pass the `--voice` value):

| `--voice`  | Voice        | Pitch (approx.) | Notes                                  |
|------------|--------------|-----------------|----------------------------------------|
| `albert`   | male         | ~105 Hz         |                                        |
| `indrek`   | male         | ~95 Hz          | slower pace                            |
| `kalev`    | male         | ~90 Hz          | lowest voice                           |
| `meelis`   | male         | ~110 Hz         |                                        |
| `peeter`   | male         | ~105 Hz         | brisk pace                             |
| `tambet`   | male         | ~145 Hz         | higher male voice, slower pace         |
| `kylli`    | female       | ~195 Hz         | slower pace                            |
| `liivika`  | female       | ~170 Hz         | lower female voice, fastest pace       |
| `mari`     | female       | ~235 Hz         | highest voice; **default**             |
| `vesta`    | female       | ~180 Hz         |                                        |
| `lee`      | —            | —               | listed by the API but times out (408)  |
| `luukas`   | —            | —               | listed by the API but times out (408)  |
| `random`   | mixed        |                 | different voice per item; skips `lee` and `luukas` |

The pitch and pace notes were measured from a sample sentence and are only a rough guide. Try voices quickly with:

```bash
python voice_text.py "Tere, kuidas läheb?" output/try_kalev.mp3 --engine neurokone --voice kalev
```

The neurokone.ee website only offers the first 10 voices. The API also lists `sulev` and `hella`, but they speak Võro, not Estonian, so they aren't included here.

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
common.py         ← shared TTS utilities (tts_bytes, neurokone_bytes, apply_speed, generate_audio)
voice_numbers.py  ← number vocabulary generator
voice_text.py     ← single-text generator
output/           ← generated MP3 files
```
