from common import SLOW, NORMAL, FAST, speech_bytes, apply_speed, add_engine_args
import argparse, os, tempfile, json

HOURS   = list(range(24))
MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

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


def fmt_digital(h, m):
    """kell 2:30"""
    return f"kell {h}:{m:02d}" if m else f"kell {h}"


def fmt_words(h, m):
    """kell kaks kolmkümmend"""
    return f"kell {ET_NOM[h]} {ET_NOM[m]}" if m else f"kell {ET_NOM[h]}"


def fmt_traditional(h, m):
    """pool kolm / veerand kolm / kolmveerand kolm / kümme minutit üle kahe / viis minutit kolmeni"""
    nh = (h + 1) % 24
    if m == 0:  return f"kell {ET_NOM[h]}"
    if m == 15: return f"veerand {ET_NOM[nh]}"
    if m == 30: return f"pool {ET_NOM[nh]}"
    if m == 45: return f"kolmveerand {ET_NOM[nh]}"
    if m < 30:  return f"{ET_NOM[m]} minutit üle {ET_GEN[h]}"
    return f"{ET_NOM[60 - m]} minutit {ET_TERM[nh]}"


def fmt_labi(h, m):
    """viis minutit kaks läbi / viis minutit kolmeni"""
    nh = (h + 1) % 24
    if m == 0:  return f"kell {ET_NOM[h]}"
    if m == 30: return f"pool {ET_NOM[nh]}"
    if m < 30:  return f"{ET_NOM[m]} minutit {ET_NOM[h]} läbi"
    return f"{ET_NOM[60 - m]} minutit {ET_TERM[nh]}"


def fmt_parast(h, m):
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


FORMATS = {
    "digital":     fmt_digital,
    "words":       fmt_words,
    "traditional": fmt_traditional,
    "labi":        fmt_labi,
    "parast":      fmt_parast,
}

parser = argparse.ArgumentParser(description="Generate Estonian time phrases as MP3s.")
parser.add_argument("--format", choices=list(FORMATS) + ["all"], default="all",
                    help="Time format (default: all)")
parser.add_argument("--limit", type=int, default=None, metavar="N",
                    help="Generate only first N times per format (useful for testing)")
add_engine_args(parser)
args = parser.parse_args()

ENGINE = args.engine
VOICE  = args.voice
SPEED  = FAST

SPEED_LABELS = {SLOW: "slow", NORMAL: "normal", FAST: "fast"}
speed_label  = SPEED_LABELS.get(SPEED, str(SPEED))

fmts         = list(FORMATS.items()) if args.format == "all" else [(args.format, FORMATS[args.format])]
engine_label = "google" if ENGINE == "google" else f"neurokone_{VOICE}"

times = [(h, m) for h in HOURS for m in MINUTES]
if args.limit:
    times = times[:args.limit]


def generate_item(text, output_path):
    if os.path.exists(output_path):
        return False
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(speech_bytes(text, "et", ENGINE, VOICE))
    if ENGINE == "google":
        apply_speed(tmp_path, output_path, SPEED)
        os.unlink(tmp_path)
    else:
        os.replace(tmp_path, output_path)
    return True


for fmt_name, fmt_fn in fmts:
    out_dir = os.path.join("output", f"times_{fmt_name}_{engine_label}_{speed_label}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"\n{fmt_name} / {engine_label} ({len(times)} items)")
    entries = []
    for h, m in times:
        text     = fmt_fn(h, m)
        filename = f"{h:02d}_{m:02d}.mp3"
        path     = os.path.join(out_dir, filename)
        generated = generate_item(text, path)
        status    = "→" if generated else "skip"
        print(f"  {status}  {h:02d}:{m:02d}  {text}")
        entries.append({"file": filename, "time": f"{h:02d}:{m:02d}", "text": text})
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"  saved → {out_dir}/")
