from num2words import num2words
from common import SLOW, NORMAL, FAST, tts_bytes, apply_speed, silence_bytes
import argparse
import tempfile
import os
import json
import unicodedata

SPEED = FAST
PAUSE_SECONDS = 0.5   # seconds of silence between ET and RU in the output (after speed is applied)

parser = argparse.ArgumentParser()
parser.add_argument("--limit",   type=int, default=None, metavar="N",
                    help="generate only the first N items per group (useful for testing)")
parser.add_argument("--lang",    choices=["et-ru", "ru-et", "et", "ru", "both"], default="et-ru",
                    help="language mode: 'et-ru' (ET then RU), 'ru-et' (RU then ET), 'et', or 'ru' (default: 'et-ru')")
args = parser.parse_args()

LIMIT = args.limit
LANG  = "et-ru" if args.lang == "both" else args.lang

OUTPUT_DIR = "output"

MONTHS = [
    # (days, ET nominative,  ET adessive,    RU genitive)
    (31, "jaanuar",   "jaanuaril",  "января"),
    (28, "veebruar",  "veebruaril", "февраля"),
    (31, "märts",     "märtsil",    "марта"),
    (30, "aprill",    "aprillil",   "апреля"),
    (31, "mai",       "mail",       "мая"),
    (30, "juuni",     "juunil",     "июня"),
    (31, "juuli",     "juulil",     "июля"),
    (31, "august",    "augustil",   "августа"),
    (30, "september", "septembril", "сентября"),
    (31, "oktoober",  "oktoobril",  "октября"),
    (30, "november",  "novembril",  "ноября"),
    (31, "detsember", "detsembril", "декабря"),
]

# --- number lists ---
cardinals = (
    list(range(1, 101)) +
    [1000, 10000, 100000, 1000000] +
    list(range(1980, 2031))
)

ordinals = (
    list(range(1, 101)) +
    [1000, 10000, 100000, 1000000] +
    list(range(1980, 2031))
)


# --- Estonian ordinal helpers ---
ET_ONES_ORDINAL = {1: "esimene", 2: "teine", 3: "kolmas", 4: "neljas",
                   5: "viies", 6: "kuues", 7: "seitsmes", 8: "kaheksas", 9: "üheksas"}
ET_ONES_GENITIVE = {1: "ühe", 2: "kahe", 3: "kolme", 4: "nelja",
                    5: "viie", 6: "kuue", 7: "seitsme", 8: "kaheksa", 9: "üheksa"}
ET_TENS_GENITIVE = {2: "kahekümne", 3: "kolmekümne", 4: "neljakümne",
                    5: "viiekümne", 6: "kuuekümne", 7: "seitsmekümne",
                    8: "kaheksakümne", 9: "üheksakümne"}
ET_HUNDREDS_CARDINAL = {1: "sada", 2: "kakssada", 3: "kolmsada",
                        4: "nelisada", 5: "viissada", 6: "kuussada",
                        7: "seitsesada", 8: "kaheksasada", 9: "üheksasada"}
ET_HUNDREDS_GENITIVE = {1: "saja", 2: "kahesaja", 3: "kolmesaja",
                        4: "neljasaja", 5: "viiesaja", 6: "kuuesaja",
                        7: "seitsmesaja", 8: "kaheksasaja", 9: "üheksasaja"}
ET_HUNDREDS_ORDINAL = {100: "sajas", 200: "kahesajas", 300: "kolmesajas",
                       400: "neljasajas", 500: "viiesajas", 600: "kuuesajas",
                       700: "seitsmesajas", 800: "kaheksasajas", 900: "üheksasajas"}


def et_cardinal_genitive(n):
    """Genitive form of an Estonian cardinal number."""
    if n == 0:
        return ""
    if 1 <= n <= 9:
        return ET_ONES_GENITIVE[n]
    if n == 10:
        return "kümne"
    if 11 <= n <= 19:
        return ET_ONES_GENITIVE[n - 10] + "teistkümne"
    if 20 <= n <= 99:
        tens, ones = divmod(n, 10)
        base = ET_TENS_GENITIVE[tens]
        return base if ones == 0 else f"{base} {ET_ONES_GENITIVE[ones]}"
    if 100 <= n <= 999:
        hundreds, rest = divmod(n, 100)
        base = ET_HUNDREDS_GENITIVE[hundreds]
        return base if rest == 0 else f"{base} {et_cardinal_genitive(rest)}"
    if 1000 <= n <= 999_999:
        thousands, rest = divmod(n, 1000)
        base = "tuhande" if thousands == 1 else f"{et_cardinal_genitive(thousands)} tuhande"
        return base if rest == 0 else f"{base} {et_cardinal_genitive(rest)}"
    if 1_000_000 <= n <= 999_999_999:
        millions, rest = divmod(n, 1_000_000)
        base = "miljoni" if millions == 1 else f"{et_cardinal_genitive(millions)} miljoni"
        return base if rest == 0 else f"{base} {et_cardinal_genitive(rest)}"
    return str(n)


def et_ordinal(n):
    """Estonian ordinal number in nominative case."""
    if n in ET_ONES_ORDINAL:
        return ET_ONES_ORDINAL[n]
    if n == 10:
        return "kümnes"
    if 11 <= n <= 19:
        return ET_ONES_GENITIVE[n - 10] + "teistkümnes"
    if 20 <= n <= 99:
        tens, ones = divmod(n, 10)
        base = ET_TENS_GENITIVE[tens]
        return base + "s" if ones == 0 else f"{base} {ET_ONES_ORDINAL[ones]}"
    if 100 <= n <= 999:
        if n in ET_HUNDREDS_ORDINAL:
            return ET_HUNDREDS_ORDINAL[n]
        hundreds, rest = divmod(n, 100)
        return f"{ET_HUNDREDS_GENITIVE[hundreds]} {et_ordinal(rest)}"
    if 1000 <= n <= 999_999:
        thousands, rest = divmod(n, 1000)
        if rest == 0:
            return "tuhandes" if thousands == 1 else f"{et_cardinal_genitive(thousands)} tuhandes"
        prefix = "tuhande" if thousands == 1 else f"{et_cardinal_genitive(thousands)} tuhande"
        return f"{prefix} {et_ordinal(rest)}"
    if 1_000_000 <= n <= 999_999_999:
        millions, rest = divmod(n, 1_000_000)
        if rest == 0:
            return "miljones" if millions == 1 else f"{et_cardinal_genitive(millions)} miljonis"
        prefix = "miljoni" if millions == 1 else f"{et_cardinal_genitive(millions)} miljoni"
        return f"{prefix} {et_ordinal(rest)}"
    return str(n)

# --- Estonian cardinal helpers (num2words has no Estonian support) ---
ET_ONES_CARDINAL = {1: "üks",  2: "kaks",  3: "kolm",   4: "neli", 5: "viis",
                    6: "kuus", 7: "seitse", 8: "kaheksa", 9: "üheksa"}

def et_cardinal(n):
    """Estonian cardinal: 21 → kakskümmend üks, 1980 → tuhat üheksasada kaheksakümmend."""
    if n == 0: return "null"
    if n in ET_ONES_CARDINAL: return ET_ONES_CARDINAL[n]
    if n == 10: return "kümme"
    if 11 <= n <= 19: return ET_ONES_CARDINAL[n - 10] + "teist"
    if 20 <= n <= 99:
        tens, ones = divmod(n, 10)
        base = ET_ONES_CARDINAL[tens] + "kümmend"
        return base if ones == 0 else f"{base} {ET_ONES_CARDINAL[ones]}"
    if 100 <= n <= 999:
        hundreds, rest = divmod(n, 100)
        base = ET_HUNDREDS_CARDINAL[hundreds]
        return base if rest == 0 else f"{base} {et_cardinal(rest)}"
    if 1000 <= n <= 999_999:
        thousands, rest = divmod(n, 1000)
        base = "tuhat" if thousands == 1 else f"{et_cardinal(thousands)} tuhat"
        return base if rest == 0 else f"{base} {et_cardinal(rest)}"
    if 1_000_000 <= n <= 999_999_999:
        millions, rest = divmod(n, 1_000_000)
        base = "miljon" if millions == 1 else f"{et_cardinal(millions)} miljonit"
        return base if rest == 0 else f"{base} {et_cardinal(rest)}"
    return str(n)

def et_adessive_ordinal(n):
    """Estonian adessive: 'on the Nth of March' → teisel, kolmandal, kahekümne esimesel..."""
    words = et_ordinal(n).split()
    last = words[-1]
    if last.endswith('ne'):   last = last[:-2] + 'sel'   # esimene→esimesel, teine→teisel
    elif last.endswith('s'):  last = last[:-1] + 'ndal'  # kolmas→kolmandal, kümnes→kümnendal
    words[-1] = last
    return ' '.join(words)

def ru_ordinal_neuter(n):
    """Russian neuter nominative: 'today is the Nth' → второе, третье, двадцать первое..."""
    words = num2words(n, lang='ru', to='ordinal').split()
    last = words[-1]
    last = last[:-2] + ('ье' if last.endswith('ий') else 'ое')
    words[-1] = last
    return ' '.join(words)

def ru_ordinal_genitive(n):
    """Russian genitive: 'on the Nth' → второго, третьего, двадцать первого..."""
    words = num2words(n, lang='ru', to='ordinal').split()
    last = words[-1]
    last = last[:-2] + ('ьего' if last.endswith('ий') else 'ого')
    words[-1] = last
    return ' '.join(words)

# --- generation ---
# Layout:   output/<lang>/<category>/<number>_<estonian_text>.mp3
#   e.g.    output/et-ru/cardinals/21_kakskümmend_üks.mp3
#           output/et-ru/dates/02.03_teine_märts.mp3
# Parsing:  number = everything before the first "_", ET text = the rest with "_" → " ".
# Each category folder also gets an index.json with {file, number, et, ru} per item.
LANG_DIR = LANG
LEGACY_SUFFIX = "" if LANG == "et-ru" else f"_{LANG}"

index = {}   # category → list of entries for index.json


def make_filename(number, et_text):
    text = unicodedata.normalize("NFC", et_text).strip().replace("/", "-")
    return f"{number}_{'_'.join(text.split())}.mp3"


def item(number, et_text, ru_text, legacy_name, et_speech=None, ru_speech=None):
    """number: the answer as shown in the filename ("21", "02.03").
    et_text / ru_text: written words. *_speech: what TTS reads (defaults to the text).
    legacy_name: old flat filename (without suffix/extension) for migrating existing files."""
    return dict(number=number, et=et_text, ru=ru_text, legacy=legacy_name,
                et_speech=et_speech or et_text, ru_speech=ru_speech or ru_text)


def generate_batch(items, category):
    if LIMIT is not None:
        items = items[:LIMIT]

    out_dir = os.path.join(OUTPUT_DIR, LANG_DIR, category)
    os.makedirs(out_dir, exist_ok=True)
    total = len(items)
    for i, it in enumerate(items, 1):
        filename = make_filename(it["number"], it["et"])
        output_path = os.path.join(out_dir, filename)
        legacy_path = os.path.join(OUTPUT_DIR, f"{it['legacy']}{LEGACY_SUFFIX}.mp3")
        if not os.path.exists(output_path) and os.path.exists(legacy_path):
            os.replace(legacy_path, output_path)   # reuse previously generated audio
        _generate_single(it["et_speech"], it["ru_speech"], output_path, i, total)
        index.setdefault(category, []).append(
            {"file": filename, "number": it["number"], "et": it["et"], "ru": it["ru"]})


def write_indexes():
    for category, entries in index.items():
        path = os.path.join(OUTPUT_DIR, LANG_DIR, category, "index.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)


def _generate_single(et_text, ru_text, output_path, i=None, total=None):
    label = f"  {i}/{total}: " if i is not None else "  "
    if os.path.exists(output_path):
        print(f"{label}(skipped) {os.path.basename(output_path)}")
        return
    if LANG == "et":
        label_text = et_text
    elif LANG == "ru":
        label_text = ru_text
    elif LANG == "ru-et":
        label_text = f"{ru_text} / {et_text}"
    else:
        label_text = f"{et_text} / {ru_text}"
    print(f"{label}{label_text}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        if LANG == "et":
            tmp.write(tts_bytes(et_text, 'et'))
        elif LANG == "ru":
            tmp.write(tts_bytes(ru_text, 'ru'))
        elif LANG == "ru-et":
            tmp.write(tts_bytes(ru_text, 'ru'))
            tmp.write(silence_bytes(PAUSE_SECONDS * SPEED))
            tmp.write(tts_bytes(et_text, 'et'))
        else:  # et-ru
            tmp.write(tts_bytes(et_text, 'et'))
            tmp.write(silence_bytes(PAUSE_SECONDS * SPEED))
            tmp.write(tts_bytes(ru_text, 'ru'))
    apply_speed(tmp_path, output_path, SPEED)
    os.unlink(tmp_path)


print("Generating cardinals...")
generate_batch(
    # TTS still reads the digits (as before); filename/index get the written words
    [item(str(n), et_cardinal(n), num2words(n, lang='ru'), f"cardinal_{n}",
          et_speech=str(n), ru_speech=str(n)) for n in cardinals],
    category="cardinals",
)

print("Generating ordinals...")
generate_batch(
    [item(str(n), et_ordinal(n), num2words(n, lang='ru', to='ordinal'), f"ordinal_{n}")
     for n in ordinals],
    category="ordinals",
)

for i, (days, et_nom, et_ade, ru_gen) in enumerate(MONTHS, 1):
    key = f"{i:02d}"
    date_nums = list(range(1, days + 1))

    print(f"Generating dates — {et_nom} ({days} days)...")
    generate_batch(
        [item(f"{n:02d}.{key}", f"{et_ordinal(n)} {et_nom}", f"{ru_ordinal_neuter(n)} {ru_gen}",
              f"date_{key}_{n}") for n in date_nums],
        category="dates",
    )
    generate_batch(
        [item(f"{n:02d}.{key}", f"{et_adessive_ordinal(n)} {et_ade}", f"{ru_ordinal_genitive(n)} {ru_gen}",
              f"date_on_{key}_{n}") for n in date_nums],
        category="dates_on",
    )

write_indexes()
