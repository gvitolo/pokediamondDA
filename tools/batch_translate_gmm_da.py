#!/usr/bin/env python3
"""Translate remaining English <language name="English"> cells to Danish. Cached."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files" / "msgdata" / "msg"
CACHE_PATH = ROOT / "tools" / ".gmm_da_translate_cache.json"

# Banks already localized or generated — do not machine-translate over them.
SKIP_NARC = frozenset(
    {
        362,
        363,
        364,
        382,
        383,
        384,
        559,  # trainer names from trdata.json
        565,
        588,
        614,
        615,
    }
)

EN_PATTERNS = [
    r"\bA good, high-performance\b",
    r"\bAn ultra-performance\b",
    r"\bA somewhat different\b",
    r"\bA device for catching\b",
    r"\bA special Poké Ball that\b",
    r"The foe'?s ",
    r"The wild ",
    r"\bA wild ",
    r"\bYou are\b",
    r"\bYou can't\b",
    r"\bYou have\b",
    r"\bIt reduced\b",
    r"\bIt will\b",
    r"\bIt was\b",
    r"\bIt's\b",
    r"\bIt is\b",
    r"\bIt can't\b",
    r"\bIt obtained\b",
    r"\bIt dug\b",
    r"\bIt blew\b",
    r"\bIt cut\b",
    r"\bIt maxed\b",
    r"\bIt switched\b",
    r"\bIt cured\b",
    r"\bIt wore\b",
    r"\bIt had\b",
    r"\bIt made\b",
    r"\bIt whipped\b",
    r"\bIt infatu\b",
    r"\bIt suppress\b",
    r"\bIt prevents\b",
    r"\bIt became\b",
    r"\bIt fell\b",
    r"\bIt regained\b",
    r"\bIt lost\b",
    r"\bIt snapped\b",
    r"\bIt flinched\b",
    r"\bIt woke\b",
    r"\bIt started\b",
    r"\bIt used\b",
    r"\bIt hurt\b",
    r"\bIt planted\b",
    r"\bIt sucked\b",
    r"\bIt sucked up\b",
    r"\bIt leech\b",
    r"\bIt anchored\b",
    r"\bIt endured\b",
    r"\bIt braced\b",
    r"\bIt charged\b",
    r"\bIt shuddered\b",
    r"\bIt identified\b",
    r"\bIt picked\b",
    r"\bIt stole\b",
    r"\bIt copied\b",
    r"\bIt transformed\b",
    r"\bIt sprang\b",
    r"\bIt bounced\b",
    r"\bIt vanished\b",
    r"\bIt took\b",
    r"\bIt laid\b",
    r"\bIt set\b",
    r"\bIt threw\b",
    r"\bIt snatched\b",
    r"\bIt swapped\b",
    r"\bIt encored\b",
    r"\bIt disabled\b",
    r"\bIt taunted\b",
    r"\bIt tormented\b",
    r"\bIt afflicted\b",
    r"\bIt sealed\b",
    r"\bIt grudge\b",
    r"\bIt snatched\b",
    r"\bcannot escape\b",
    r"\bcannot use\b",
    r"\bcan't use\b",
    r"\bcan't escape\b",
    r"\bno longer escape\b",
    r"\bwas prevented\b",
    r"\bwere prevented\b",
    r"\bhaving a nightmare\b",
    r"\bnightmare!\b",
    r"\bdown with it\b",
    r"\btook aim at\b",
    r"\bchallenged by\b",
    r"\bobtained one\b",
    r"\bobtained an\b",
    r"\bDJ:",
    r"\bMC:",
    r"Reporter:",
    r"Announcer:",
    r"\bHello,\b",
    r"\bThanks for\b",
    r"\bThank you\b",
    r"\bToday,\b",
    r"\bCongratulations\b",
    r"\bPlease wait\b",
    r"\bChoose \b",
    r"\bSelect \b",
    r"\bPress \b",
    r"Pokétch",
    r"Jubilife TV",
    r"Street Corner",
    r"Personality Checkup",
    r"Battle Tower Corner",
    r"Three Cheers for Poffin",
    r"Right-On Photo",
    r"Your Pokémon",
    r"Pokémon Corner",
    r"Contest Hall",
    r"\bgoing out\b",
    r"\bnationwide\b",
    r"\bPoffin Maniac\b",
    r"\bViewers,\b",
    r"\bAudience:\b",
    r"\bCredit to you\b",
    r"\bSee you again\b",
    r"\bLet's \b",
    r"\bLet’s \b",
    r"\bOh!\b",
    r"\bOh, wow\b",
    r"\bI see!\b",
    r"\bI'?d like\b",
    r"\bHow do you feel\b",
    r"\bHow do you do\b",
    r"\bWas this\b",
    r"\bAnd you\b",
    r"\bThey've\b",
    r"\bThey've just\b",
    r"\bHere come\b",
    r"\bThat's it\b",
    r"\bThat’s it\b",
    r"\bAll right,\b",
    r"\bKeep it real\b",
    r"\bWa-hey\b",
    r"\bBravo!\b",
    r"\bDarlings\b",
    r"\bexperts say\b",
    r"\bDid this analysis\b",
    r"\bOur experts\b",
    r"\bIn our interview\b",
    r"\bfeatured Trainer\b",
    r"\bimpromptu\b",
    r"\bcharged with\b",
    r"\bfervent passion\b",
    r"\bprized Pokémon\b",
    r"\bTake it away\b",
    r"\bracked up\b",
    r"\bstraight wins\b",
    r"\bmissed getting\b",
    r"\bbrokenhearted\b",
    r"\bharsh realities\b",
    r"\bget down!\b",
    r"\bbeloved\b",
    r"\bpride and joy\b",
    r"\bLet’s meet again\b",
    r"\bSorry to keep\b",
    r"\bThe Pokétch\b",
    r"\bfavorite Pokétch\b",
    r"\bapp too\b",
    r"\bshow off\b",
    r"\bWe'?re bringing\b",
    r"\bWe also got\b",
    r"\bword about\b",
    r"\bthoughts behind\b",
    r"\bbeauty of a photo\b",
    r"\boverlooked\b",
    r"\bcharm of\b",
    r"\bOwooooh\b",
    r"\bIf someone puts\b",
    r"\bI'?d like to cover\b",
    r"\bWhat do you say\b",
    r"\bType Checkup\b",
    r"\bpicked\nthe Normal type\b",
    r"\bNormal type as\b",
    r"\bFire type as\b",
    r"\bWater type as\b",
    r"\bElectric type as\b",
    r"\bGrass type as\b",
    r"\bIce type as\b",
    r"\bFighting type as\b",
    r"\bPoison type as\b",
    r"\bGround type as\b",
    r"\bFlying type as\b",
    r"\bPsychic type as\b",
    r"\bBug type as\b",
    r"\bRock type as\b",
    r"\bGhost type as\b",
    r"\bDragon type as\b",
    r"\bDark type as\b",
    r"\bSteel type as\b",
    r"\breturning guest\b",
    r"\bnot shaken\b",
    r"\bstirred,\nnot shaken\b",
    r"\bmouthwatering\b",
    r"\bBack next time\b",
    r"\bget cooking\b",
    r"\btake a cue\b",
    r"\bEating this would\b",
    r"\bjewelry box\b",
    r"\borchestra in my mouth\b",
    r"\btrampoline in my mouth\b",
    r"\bdearly love\b",
]

_EN_COMPILED = [re.compile(p, re.I) for p in EN_PATTERNS]

PLACEHOLDER_SPLIT = re.compile(r"(\{[^}]+\})")


def needs_translation(s: str) -> bool:
    if not s.strip():
        return False
    t = s.replace("\u2019", "'").replace("\u2018", "'")
    for rx in _EN_COMPILED:
        if rx.search(t):
            return True
    if re.search(r"\s[Tt]he\s", t) and len(t) > 14:
        return True
    if re.search(r"\b(you|your|with|from|this|that|have|been|will|would)\b", t) and re.search(
        r"\b(is|are|was|were|not|can't|cannot)\b", t, re.I
    ):
        return True
    return False


def translate_segment(translator: GoogleTranslator, seg: str, delay: float) -> str:
    if not seg:
        return seg
    if not re.search(r"[A-Za-z]{2,}", seg):
        return seg
    try:
        time.sleep(delay)
        out = translator.translate(seg)
        return out if out else seg
    except Exception:
        return seg


def translate_preserved(translator: GoogleTranslator, s: str, delay: float) -> str:
    parts = PLACEHOLDER_SPLIT.split(s)
    return "".join(
        p
        if (p.startswith("{") and p.endswith("}"))
        else translate_segment(translator, p, delay)
        for p in parts
    )


def load_cache() -> dict[str, str]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(c: dict[str, str]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


def process_file(
    path: Path, cache: dict[str, str], delay: float, *, translate_all_nonempty: bool = False
) -> int:
    text = path.read_text(encoding="utf-8")
    translator = GoogleTranslator(source="en", target="da")
    updates = 0

    def repl(m: re.Match) -> str:
        nonlocal updates
        inner = m.group(1)
        if not inner.strip():
            return m.group(0)
        if translate_all_nonempty:
            if inner.strip() in ("???", "-----", "-"):
                return m.group(0)
            if not re.search(r"[A-Za-z]", inner):
                return m.group(0)
        elif not needs_translation(inner):
            return m.group(0)
        if inner not in cache:
            cache[inner] = translate_preserved(translator, inner, delay)
        new_inner = cache[inner]
        if new_inner != inner:
            updates += 1
        return f'<language name="English">{new_inner}</language>'

    new_text = re.sub(
        r"<language name=\"English\">(.*?)</language>",
        repl,
        text,
        flags=re.DOTALL,
    )
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return updates


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="EN→DA for msg .gmm (cached Google Translate).")
    p.add_argument("--from", dest="n_from", type=int, default=0, help="First narc id (inclusive)")
    p.add_argument("--to", dest="n_to", type=int, default=9999, help="Last narc id (inclusive)")
    p.add_argument("--delay", type=float, default=0.02, help="Seconds between API segments")
    p.add_argument(
        "--all-nonempty",
        action="store_true",
        help="Translate every non-empty English cell (except ???/-----); use for item catalogs etc.",
    )
    args = p.parse_args()

    cache = load_cache()
    total = 0
    for n in range(args.n_from, args.n_to + 1):
        if n in SKIP_NARC:
            continue
        path = MSG / f"narc_{n:04d}.gmm"
        if not path.exists():
            continue
        u = process_file(
            path, cache, args.delay, translate_all_nonempty=args.all_nonempty
        )
        total += u
        print(f"narc_{n:04d}.gmm: {u} cells")
        save_cache(cache)
    print("done, total updated cells:", total)


if __name__ == "__main__":
    main()
