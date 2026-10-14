# keelpaar_generator

Toolkit for generating Estonian–Russian audio vocabulary files using Google TTS or [Neurokõne](https://www.neurokone.ee) (Estonian neural TTS by TartuNLP).

## Prerequisites

```bash
brew install ffmpeg
pip install gtts num2words
```

## Scripts

### `voice_numbers.py` — number vocabulary

Generates audio files for cardinals, ordinals, and dates.

```bash
python voice_numbers.py [--limit N] [--langs et,ru,en] [--combined] [--engine {google,neurokone}] [--voice NAME]
```

| Flag         | Description                                                                     | Default   |
|--------------|---------------------------------------------------------------------------------|-----------|
| `--limit N`  | Generate only the first N items per group (for testing)                         | all       |
| `--langs`    | Comma-separated languages to generate: `et,ru`, `et`, `ru`, `en`                | `et,ru`   |
| `--combined` | Also generate ET+gap+RU audio in `<category>/et-ru/`                            | false     |
| `--engine`   | TTS engine for Estonian (see [Engines and voices](#engines-and-voices))          | `google`  |
| `--voice`    | Neurokõne voice, or `random` for a different voice per item                     | `mari`    |

**Output** — written to `output/<category>/<lang>/` (or `output/neurokone_<voice>/<category>/<lang>/`):
- `output/<category>/<lang>/<number>.mp3` (e.g. `output/cardinals/et/21.mp3`)
- `output/<category>/et-ru/<number>.mp3` (if `--combined`)
- `output/<category>/index.json` (includes `file`, `number`, `et`, `ru`, `en`)

---

### `voice_time.py` — time phrases

Generates audio files for time phrases across all 24 hours and 5-minute intervals.

```bash
python voice_time.py [--format {traditional,digital,words,labi,parast,all}] [--limit N] [--langs et,ru,en] [--combined] [--engine {google,neurokone}] [--voice NAME]
```

| Flag         | Description                                                                     | Default   |
|--------------|---------------------------------------------------------------------------------|-----------|
| `--format`   | Time format: `traditional`, `digital`, `words`, `labi`, `parast`, or `all`      | `all`     |
| `--limit N`  | Generate only the first N items per format (for testing)                        | all       |
| `--langs`    | Comma-separated languages to generate: `et,ru`, `et`, `ru`, `en`                | `et,ru`   |
| `--combined` | Also generate ET+gap+RU audio in `<category>/et-ru/`                            | false     |
| `--engine`   | TTS engine for Estonian (see [Engines and voices](#engines-and-voices))          | `google`  |
| `--voice`    | Neurokõne voice, or `random` for a different voice per item                     | `mari`    |

**Formats & Categories:**
- `times_traditional` — traditional forms (ET: *pool kolm*, *veerand kolm*; RU: *половина третьего*, *четверть третьего*; EN: *half past two*, *quarter past two*)
- `times_digital` — digital readouts (ET: *kell 14:30*; RU: *14:30*; EN: *14:30*)
- `times_words` — full words (ET: *kell kaks kolmkümmend*; RU: *два тридцать*; EN: *two thirty*)
- `times_labi` — colloquial Estonian "läbi" (ET: *viis minutit kaks läbi*; RU: *пять минут третьего*; EN: *five past two*)
- `times_parast` — colloquial Estonian "enne / pärast pool" (ET: *viis minutit pärast pool kolm*; RU: *без двадцати пяти три*; EN: *twenty-five to three*)

**Output** — written to `output/<category>/<lang>/` (or `output/neurokone_<voice>/<category>/<lang>/`):
- `output/times_<format>/<lang>/<HH_MM>.mp3` (e.g. `output/times_traditional/et/02_30.mp3`)
- `output/times_<format>/et-ru/<HH_MM>.mp3` (if `--combined`)
- `output/times_<format>/index.json` (includes `file`, `time`, `number`, `et`, `ru`, `en`)

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
