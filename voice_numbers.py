from num2words import num2words
from common import SLOW, NORMAL, FAST, tts_bytes, apply_speed, silence_bytes
import argparse
import tempfile
import os

SPEED = FAST
PAUSE_SECONDS = 0.5   # seconds of silence between ET and RU in the output (after speed is applied)

parser = argparse.ArgumentParser()
parser.add_argument("--limit",   type=int, default=None, metavar="N",
                    help="generate only the first N items per group (useful for testing)")
parser.add_argument("--lang",    choices=["both", "et", "ru"], default="both",
                    help="generate both languages (default), ET only, or RU only")
args = parser.parse_args()

LIMIT = args.limit
LANG    = args.lang

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
ET_ONES_ORDINAL      = {1: "esimene", 2: "teine",    3: "kolmas",   4: "neljas",
                        5: "viies",   6: "kuues",     7: "seitsmes", 8: "kaheksas", 9: "üheksas"}
ET_ONES_GENITIVE     = {1: "ühe",    2: "kahe",      3: "kolme",    4: "nelja",
                        5: "viie",   6: "kuue",       7: "seitsme",  8: "kaheksa",  9: "üheksa"}
ET_TENS_GENITIVE     = {2: "kahekümne",    3: "kolmekümne",   4: "nelikümne",
                        5: "viiekümne",    6: "kuuekümne",    7: "seitsmekümne",
                        8: "kaheksakümne", 9: "üheksakümne"}
ET_HUNDREDS_CARDINAL = {1: "sada",        2: "kakssada",     3: "kolmsada",
                        4: "nelisada",    5: "viissada",     6: "kuussada",
                        7: "seitsesada",  8: "kaheksasada",  9: "üheksasada"}
ET_HUNDREDS_ORDINAL  = {100: "sajas",       200: "kahesajas",    300: "kolmesajas",
                        400: "neljasajas",  500: "viiesajas",    600: "kuuesajas",
                        700: "seitsmesajas", 800: "kaheksasajas", 900: "üheksasajas"}
ET_LARGE_ORDINAL     = {1000: "tuhannes",   10000: "kümne tuhandes",
                        100000: "saja tuhandes", 1000000: "miljonas"}

def et_ordinal(n):
    if n in ET_LARGE_ORDINAL:    return ET_LARGE_ORDINAL[n]
    if n in ET_HUNDREDS_ORDINAL: return ET_HUNDREDS_ORDINAL[n]
    if n in ET_ONES_ORDINAL:     return ET_ONES_ORDINAL[n]
    if n == 10: return "kümnes"
    if 11 <= n <= 19: return ET_ONES_GENITIVE[n - 10] + "teistkümnes"
    if 20 <= n <= 99:
        tens, ones = divmod(n, 10)
        base = ET_TENS_GENITIVE[tens]
        return base + "s" if ones == 0 else f"{base} {ET_ONES_ORDINAL[ones]}"
    if 100 <= n <= 999:
        hundreds, rest = divmod(n, 100)
        return f"{ET_HUNDREDS_CARDINAL[hundreds]} {et_ordinal(rest)}"
    if 1000 <= n <= 1999:
        rest = n - 1000
        return "tuhannes" if rest == 0 else f"tuhat {et_ordinal(rest)}"
    if 2000 <= n <= 2999:
        rest = n - 2000
        return "kahe tuhandes" if rest == 0 else f"kahe tuhande {et_ordinal(rest)}"
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
def generate_batch(items, prefix):
    """items: list of (n, et_text, ru_text)"""
    if LIMIT is not None:
        items = items[:LIMIT]

    suffix = "" if LANG == "both" else f"_{LANG}"
    total = len(items)
    for i, (n, et_text, ru_text) in enumerate(items, 1):
        _generate_single(et_text, ru_text, f"{OUTPUT_DIR}/{prefix}_{n}{suffix}.mp3", i, total)

def _generate_single(et_text, ru_text, output_path, i=None, total=None):
    label = f"  {i}/{total}: " if i is not None else "  "
    if os.path.exists(output_path):
        print(f"{label}(skipped) {os.path.basename(output_path)}")
        return
    label_text = et_text if LANG == "et" else ru_text if LANG == "ru" else f"{et_text} / {ru_text}"
    print(f"{label}{label_text}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        if LANG in ("both", "et"):
            tmp.write(tts_bytes(et_text, 'et'))
        if LANG == "both":
            tmp.write(silence_bytes(PAUSE_SECONDS * SPEED))
        if LANG in ("both", "ru"):
            tmp.write(tts_bytes(ru_text, 'ru'))
    apply_speed(tmp_path, output_path, SPEED)
    os.unlink(tmp_path)


os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Generating cardinals...")
generate_batch(
    [(n, str(n), str(n)) for n in cardinals],
    prefix="cardinal",
)

print("Generating ordinals...")
generate_batch(
    [(n, et_ordinal(n), num2words(n, lang='ru', to='ordinal')) for n in ordinals],
    prefix="ordinal",
)

for i, (days, et_nom, et_ade, ru_gen) in enumerate(MONTHS, 1):
    key = f"{i:02d}"
    date_nums = list(range(1, days + 1))

    print(f"Generating dates — {et_nom} ({days} days)...")
    generate_batch(
        [(n, f"{et_ordinal(n)} {et_nom}", f"{ru_ordinal_neuter(n)} {ru_gen}") for n in date_nums],
        prefix=f"date_{key}",
    )
    generate_batch(
        [(n, f"{et_adessive_ordinal(n)} {et_ade}", f"{ru_ordinal_genitive(n)} {ru_gen}") for n in date_nums],
        prefix=f"date_on_{key}",
    )
