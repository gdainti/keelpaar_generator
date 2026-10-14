from num2words import num2words
from common import SLOW, NORMAL, FAST, speech_bytes, apply_speed, silence_bytes, add_engine_args
import argparse
import tempfile
import os
import json

SPEED = FAST
PAUSE_SECONDS = 0.5   # silence between ET and RU in combined files (before speed is applied)

HOURS   = list(range(24))
MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

# --- Estonian dictionary mappings ---
# Nominative (kell kaks, pool kolm)
ET_NOM = {
    0: "null",    1: "üks",      2: "kaks",     3: "kolm",     4: "neli",
    5: "viis",    6: "kuus",     7: "seitse",   8: "kaheksa",  9: "üheksa",
    10: "kümme", 11: "üksteist", 12: "kaksteist", 13: "kolmteist", 14: "neliteist",
    15: "viisteist", 16: "kuusteist", 17: "seitseteist", 18: "kaheksateist",
    19: "üheksateist", 20: "kakskümmend", 21: "kakskümmend üks",
    22: "kakskümmend kaks", 23: "kakskümmend kolm",
    25: "kakskümmend viis", 30: "kolmkümmend", 35: "kolmkümmend viis",
    40: "nelikümmend", 45: "nelikümmend viis", 50: "viiskümmend", 55: "viiskümmend viis",
}

# Genitive (üle kahe = past two)
ET_GEN = {
    0: "nulli",  1: "ühe",    2: "kahe",   3: "kolme",  4: "nelja",
    5: "viie",   6: "kuue",   7: "seitsme", 8: "kaheksa", 9: "üheksa",
    10: "kümne", 11: "üheteistkümne", 12: "kaheteistkümne", 13: "kolmeteistkümne",
    14: "neljateistkümne", 15: "viieteistkümne", 16: "kuueteistkümne",
    17: "seitsmeteistkümne", 18: "kaheksateistkümne", 19: "üheksateistkümne",
    20: "kahekümne", 21: "kahekümne ühe", 22: "kahekümne kahe", 23: "kahekümne kolme",
}

# Terminative (kolmeni = to three)
ET_TERM = {
    0: "nullini",  1: "üheni",   2: "kaheni",  3: "kolmeni",  4: "neljani",
    5: "viieni",   6: "kuueni",  7: "seitsmeni", 8: "kaheksani", 9: "üheksani",
    10: "kümneni", 11: "üheteistkümneni", 12: "kaheteistkümneni", 13: "kolmeteistkümneni",
    14: "neljateistkümneni", 15: "viieteistkümneni", 16: "kuueteistkümneni",
    17: "seitsmeteistkümneni", 18: "kaheksateistkümneni", 19: "üheksateistkümneni",
    20: "kahekümneni", 21: "kahekümne üheni", 22: "kahekümne kaheni", 23: "kahekümne kolmeni",
}

# --- Russian dictionary mappings ---
RU_NEXT_GEN = {
    1: "первого", 2: "второго", 3: "третьего", 4: "четвёртого",
    5: "пятого", 6: "шестого", 7: "седьмого", 8: "восьмого",
    9: "девятого", 10: "десятого", 11: "одиннадцатого", 12: "двенадцатого",
}
RU_HOURS_NOM = {
    1: "час", 2: "два", 3: "три", 4: "четыре", 5: "пять",
    6: "шесть", 7: "семь", 8: "восемь", 9: "девять", 10: "десять",
    11: "одиннадцать", 12: "двенадцать",
}
RU_HOURS_WORDS = {
    0: "ноль", 1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять",
    6: "шесть", 7: "семь", 8: "восемь", 9: "девять", 10: "десять",
    11: "одиннадцать", 12: "двенадцать", 13: "тринадцать", 14: "четырнадцать",
    15: "пятнадцать", 16: "шестнадцать", 17: "семнадцать", 18: "восемнадцать",
    19: "девятнадцать", 20: "двадцать", 21: "двадцать один",
    22: "двадцать два", 23: "двадцать три",
}
RU_MINUTES_WORDS = {
    0: "ноль ноль", 5: "ноль пять", 10: "десять", 15: "пятнадцать",
    20: "двадцать", 25: "двадцать пять", 30: "тридцать", 35: "тридцать пять",
    40: "сорок", 45: "сорок пять", 50: "пятьдесят", 55: "пятьдесят пять",
}

# --- English dictionary mappings ---
EN_HOURS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}
EN_HOURS_WORDS = {h: num2words(h, lang="en") for h in range(24)}
EN_MINUTES_WORDS = {
    0: "o'clock", 5: "oh five", 10: "ten", 15: "fifteen",
    20: "twenty", 25: "twenty-five", 30: "thirty", 35: "thirty-five",
    40: "forty", 45: "forty-five", 50: "fifty", 55: "fifty-five",
}


# --- Format functions ---

def fmt_digital_words_et(h, m):
    """Exact words for digital time: kell null, kell null null viis, kell neliteist kolmkümmend"""
    if m == 0:
        return f"kell {ET_NOM[h]}"
    if m == 5:
        return f"kell {ET_NOM[h]} null viis"
    return f"kell {ET_NOM[h]} {ET_NOM[m]}"


def fmt_digital_words_ru(h, m):
    """Exact words for digital time: ноль ноль, ноль ноль пять, четырнадцать тридцать"""
    if m == 0:
        return "ноль ноль" if h == 0 else f"{RU_HOURS_WORDS[h]} ноль ноль"
    if m == 5:
        return f"{RU_HOURS_WORDS[h]} ноль пять"
    return f"{RU_HOURS_WORDS[h]} {RU_MINUTES_WORDS[m]}"


def fmt_digital_words_en(h, m):
    """Exact words for digital time: zero zero, zero oh five, fourteen thirty"""
    if m == 0:
        if h == 0:
            return "zero zero"
        return f"{EN_HOURS_WORDS[h]} o'clock" if h <= 12 else f"{EN_HOURS_WORDS[h]} hundred"
    if m == 5:
        return f"{EN_HOURS_WORDS[h]} oh five"
    return f"{EN_HOURS_WORDS[h]} {EN_MINUTES_WORDS[m]}"


def fmt_words_et(h, m):
    """kell kaks kolmkümmend"""
    return f"kell {ET_NOM[h]} {ET_NOM[m]}" if m else f"kell {ET_NOM[h]}"


def fmt_words_ru(h, m):
    if m == 0:
        return RU_HOURS_WORDS[h]
    return f"{RU_HOURS_WORDS[h]} {RU_MINUTES_WORDS[m]}"


def fmt_words_en(h, m):
    if m == 0:
        if 1 <= h <= 12:
            return f"{EN_HOURS_WORDS[h]} o'clock"
        elif h == 0:
            return "zero"
        else:
            return f"{EN_HOURS_WORDS[h]} hundred"
    return f"{EN_HOURS_WORDS[h]} {EN_MINUTES_WORDS[m]}"


def fmt_traditional_et(h, m):
    """pool kolm / veerand kolm / kolmveerand kolm / kümme minutit üle kahe / viis minutit kolmeni"""
    nh = (h + 1) % 24
    if m == 0:  return f"kell {ET_NOM[h]}"
    if m == 15: return f"veerand {ET_NOM[nh]}"
    if m == 30: return f"pool {ET_NOM[nh]}"
    if m == 45: return f"kolmveerand {ET_NOM[nh]}"
    if m < 30:  return f"{ET_NOM[m]} minutit üle {ET_GEN[h]}"
    return f"{ET_NOM[60 - m]} minutit {ET_TERM[nh]}"


def fmt_traditional_ru(h, m):
    h12 = h % 12 or 12
    nh12 = (h % 12) + 1
    if m == 0:
        if h12 == 1:
            return "час"
        elif h12 in (2, 3, 4):
            return f"{RU_HOURS_NOM[h12]} часа"
        else:
            return f"{RU_HOURS_NOM[h12]} часов"
    if m == 15: return f"четверть {RU_NEXT_GEN[nh12]}"
    if m == 30: return f"половина {RU_NEXT_GEN[nh12]}"
    if m == 45: return f"без четверти {RU_HOURS_NOM[nh12]}"
    if m == 5:  return f"пять минут {RU_NEXT_GEN[nh12]}"
    if m == 10: return f"десять минут {RU_NEXT_GEN[nh12]}"
    if m == 20: return f"двадцать минут {RU_NEXT_GEN[nh12]}"
    if m == 25: return f"двадцать пять минут {RU_NEXT_GEN[nh12]}"
    if m == 35: return f"без двадцати пяти {RU_HOURS_NOM[nh12]}"
    if m == 40: return f"без двадцати {RU_HOURS_NOM[nh12]}"
    if m == 50: return f"без десяти {RU_HOURS_NOM[nh12]}"
    if m == 55: return f"без пяти {RU_HOURS_NOM[nh12]}"


def fmt_traditional_en(h, m):
    h12 = h % 12 or 12
    nh12 = (h % 12) + 1
    if m == 0:  return f"{EN_HOURS[h12]} o'clock"
    if m == 15: return f"quarter past {EN_HOURS[h12]}"
    if m == 30: return f"half past {EN_HOURS[h12]}"
    if m == 45: return f"quarter to {EN_HOURS[nh12]}"
    if m == 5:  return f"five past {EN_HOURS[h12]}"
    if m == 10: return f"ten past {EN_HOURS[h12]}"
    if m == 20: return f"twenty past {EN_HOURS[h12]}"
    if m == 25: return f"twenty-five past {EN_HOURS[h12]}"
    if m == 35: return f"twenty-five to {EN_HOURS[nh12]}"
    if m == 40: return f"twenty to {EN_HOURS[nh12]}"
    if m == 50: return f"ten to {EN_HOURS[nh12]}"
    if m == 55: return f"five to {EN_HOURS[nh12]}"


def fmt_labi_et(h, m):
    """viis minutit kaks läbi / viis minutit kolmeni"""
    nh = (h + 1) % 24
    if m == 0:  return f"kell {ET_NOM[h]}"
    if m == 30: return f"pool {ET_NOM[nh]}"
    if m < 30:  return f"{ET_NOM[m]} minutit {ET_NOM[h]} läbi"
    return f"{ET_NOM[60 - m]} minutit {ET_TERM[nh]}"


def fmt_parast_et(h, m):
    """viis minutit pärast pool kolm / viis minutit enne pool kolm"""
    nh = (h + 1) % 24
    if m == 0:  return f"kell {ET_NOM[h]}"
    if m == 15: return f"veerand {ET_NOM[nh]}"
    if m == 30: return f"pool {ET_NOM[nh]}"
    if m == 45: return f"kolmveerand {ET_NOM[nh]}"
    if m == 20: return f"kümme minutit enne pool {ET_NOM[nh]}"
    if m == 25: return f"viis minutit enne pool {ET_NOM[nh]}"
    if m == 35: return f"viis minutit pärast pool {ET_NOM[nh]}"
    if m == 40: return f"kümme minutit pärast pool {ET_NOM[nh]}"
    if m < 30:  return f"{ET_NOM[m]} minutit üle {ET_GEN[h]}"
    return f"{ET_NOM[60 - m]} minutit {ET_TERM[nh]}"


def make_filename(h, m):
    return f"{h:02d}_{m:02d}.mp3"


def item(h, m, et_text, ru_text, en_text, et_speech=None, ru_speech=None, en_speech=None):
    time_str = f"{h:02d}:{m:02d}"
    filename = make_filename(h, m)
    return dict(time=time_str, filename=filename, et=et_text, ru=ru_text, en=en_text,
                et_speech=et_speech or et_text,
                ru_speech=ru_speech or ru_text,
                en_speech=en_speech or en_text)


def build_digital_items():
    return [
        item(
            h, m,
            et_text=fmt_digital_words_et(h, m),
            ru_text=fmt_digital_words_ru(h, m),
            en_text=fmt_digital_words_en(h, m),
            et_speech=fmt_digital_words_et(h, m),
            ru_speech=fmt_digital_words_ru(h, m),
            en_speech=fmt_digital_words_en(h, m),
        )
        for h in HOURS for m in MINUTES
    ]


def build_words_items():
    return [
        item(h, m, fmt_words_et(h, m), fmt_words_ru(h, m), fmt_words_en(h, m))
        for h in HOURS for m in MINUTES
    ]


def build_traditional_items():
    return [
        item(h, m, fmt_traditional_et(h, m), fmt_traditional_ru(h, m), fmt_traditional_en(h, m))
        for h in HOURS for m in MINUTES
    ]


def build_labi_items():
    return [
        item(h, m, fmt_labi_et(h, m), fmt_traditional_ru(h, m), fmt_traditional_en(h, m))
        for h in HOURS for m in MINUTES
    ]


def build_parast_items():
    return [
        item(h, m, fmt_parast_et(h, m), fmt_traditional_ru(h, m), fmt_traditional_en(h, m))
        for h in HOURS for m in MINUTES
    ]


FORMATS = {
    "traditional": build_traditional_items,
    "digital":     build_digital_items,
    "words":       build_words_items,
    "labi":        build_labi_items,
    "parast":      build_parast_items,
}

# --- CLI and Configuration ---
parser = argparse.ArgumentParser(description="Generate time phrases as MP3s.")
parser.add_argument("--format", choices=list(FORMATS) + ["all"], default="all",
                    help="time format: digital, words, traditional, labi, parast, or all (default: all)")
parser.add_argument("--limit", type=int, default=None, metavar="N",
                    help="generate only the first N items per group (useful for testing)")
parser.add_argument("--combined", action="store_true",
                    help="also generate ET+gap+RU audio in <category>/et-ru/")
parser.add_argument("--langs", default="et,ru",
                    help="comma-separated languages to generate: et, ru, en (default: et,ru)")
add_engine_args(parser)
args = parser.parse_args()

LIMIT    = args.limit
ENGINE   = args.engine
VOICE    = args.voice
COMBINED = args.combined
LANGS    = set(args.langs.split(","))

OUTPUT_DIR = "output"
BASE_DIR   = OUTPUT_DIR if ENGINE == "google" else os.path.join(OUTPUT_DIR, f"neurokone_{VOICE}")

index = {}   # category → list of entries for index.json


def generate_batch(items, category):
    if LIMIT is not None:
        items = items[:LIMIT]

    lang_dirs = {}
    for lang in LANGS:
        d = os.path.join(BASE_DIR, category, lang)
        os.makedirs(d, exist_ok=True)
        lang_dirs[lang] = d
    if COMBINED:
        combined_dir = os.path.join(BASE_DIR, category, "et-ru")
        os.makedirs(combined_dir, exist_ok=True)

    total = len(items)
    for i, it in enumerate(items, 1):
        filename = it["filename"]

        for lang, d in lang_dirs.items():
            _generate_lang(it[f"{lang}_speech"], lang, os.path.join(d, filename),
                           it[lang], i, total)
        if COMBINED:
            combined_path = os.path.join(combined_dir, filename)
            old = os.path.join(BASE_DIR, category, filename)
            if not os.path.exists(combined_path) and os.path.exists(old):
                os.replace(old, combined_path)
            _generate_combined(it["et_speech"], it["ru_speech"],
                               it["et"], it["ru"], combined_path, i, total)

        index.setdefault(category, []).append(
            {"file": filename, "time": it["time"], "number": it["time"],
             "et": it["et"], "ru": it["ru"], "en": it["en"]})


def write_indexes():
    for category, entries in index.items():
        path = os.path.join(BASE_DIR, category, "index.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)


def _generate_lang(speech_text, lang, output_path, display_text, i, total):
    label = f"  {i}/{total} {lang.upper()}: "
    if os.path.exists(output_path):
        print(f"{label}(skipped) {os.path.basename(output_path)}")
        return
    print(f"{label}{display_text}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(speech_bytes(speech_text, lang, ENGINE, VOICE))
    if ENGINE == "google":
        apply_speed(tmp_path, output_path, SPEED)
        os.unlink(tmp_path)
    else:
        os.replace(tmp_path, output_path)


def _generate_combined(et_speech, ru_speech, et_display, ru_display, output_path, i, total):
    label = f"  {i}/{total} ET+RU: "
    if os.path.exists(output_path):
        print(f"{label}(skipped) {os.path.basename(output_path)}")
        return
    print(f"{label}{et_display} / {ru_display}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(speech_bytes(et_speech, 'et', ENGINE, VOICE))
        tmp.write(silence_bytes(PAUSE_SECONDS * SPEED))
        tmp.write(speech_bytes(ru_speech, 'ru', ENGINE, VOICE))
    if ENGINE == "google":
        apply_speed(tmp_path, output_path, SPEED)
        os.unlink(tmp_path)
    else:
        os.replace(tmp_path, output_path)


selected_formats = list(FORMATS.items()) if args.format == "all" else [(args.format, FORMATS[args.format])]

for fmt_name, build_fn in selected_formats:
    category = f"times_{fmt_name}"
    print(f"\nGenerating {category}...")
    items = build_fn()
    generate_batch(items, category=category)

write_indexes()
print("\nDone!")
