from common import SLOW, NORMAL, FAST, generate_audio
import argparse

TEXT   = ""        # "tere maailm"
OUTPUT = ""        # "output/hello.mp3"
LANG   = "et"
SPEED  = FAST

if not TEXT or not OUTPUT:
    parser = argparse.ArgumentParser(description="Generate an MP3 from arbitrary text.")
    parser.add_argument("text",  help="Text to speak")
    parser.add_argument("output", help="Output MP3 file path")
    parser.add_argument("--lang",  default=LANG,  help=f"Language code (default: {LANG})")
    parser.add_argument("--speed", default=SPEED, type=float,
                        help=f"Speed — SLOW={SLOW}, NORMAL={NORMAL}, FAST={FAST} (default: {SPEED})")
    args = parser.parse_args()
    TEXT   = args.text
    OUTPUT = args.output
    LANG   = args.lang
    SPEED  = args.speed

generate_audio(TEXT, LANG, OUTPUT, SPEED)
print(f"Generated {OUTPUT}")
