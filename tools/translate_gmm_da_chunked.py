#!/usr/bin/env python3
"""Danish for narc_00XX.gmm: mechanical narc_0000; else Argos per \\n/\\r/\\f segment + token protect."""
from __future__ import annotations

import re
from pathlib import Path

import argostranslate.translate as argos_translate
from langdetect import LangDetectException, detect_langs

MSG_DIR = Path(__file__).resolve().parents[1] / "files" / "msgdata" / "msg"

EN_MIXED = re.compile(
    r"(?i)(?<!')\b("
    r"the|you|your|yours|this|that|these|those|what|when|where|which|who|why|how|"
    r"have|has|had|will|would|could|should|can|may|they|them|their|there|here|"
    r"with|from|into|about|after|before|been|being|something|everything|nothing|"
    r"please|thank|thanks|sorry|hello|goodbye|yes|sir|young|friend|"
    r"don't|can't|won't|doesn't|didn't|isn't|aren't|haven't|hasn't|hadn't|"
    r"i'm|you're|we're|they're|i've|you've|we've|they've|"
    r"it's|that's|there's|here's|what's|who's|i'll|you'll|we'll|they'll|"
    r"awakened|fainted|defeated|received|obtained|trainer|player|"
    r"underground|explorer|sphere|treasure|tunnel|digging|mentor|spelunker|"
    r"youngster|challenge|secret|base|gift|mission|reward|wireless|"
    r"button|screen|because|although|though|while|until|unless|whether|"
    r"inside|outside|together|alone|everyone|someone|anywhere|perhaps|"
    r"maybe|probably|actually|certainly|definitely|really|understand|"
    r"remember|continue|include|anything|my|me|we|us|our|he|she|his|her|"
    r"not|and|but|if|then|get|got|go|going|went|gone|come|came|see|saw|seen|"
    r"know|knew|think|thought|want|need|like|make|made|take|took|taken|"
    r"give|gave|given|tell|told|find|found|call|called|try|tried|"
    r"ask|asked|help|helped|work|worked|seem|seemed|wait|waited|"
    r"stop|stopped|start|started|turn|turned|walk|walked|run|ran|"
    r"bring|brought|learn|taught|lose|lost|send|sent|pay|paid|"
    r"buy|bought|sell|sold|win|won|fight|fought|choose|chose|press|"
    r"use|using|wild|foe|battle|caught|gain|way|time|day|year|"
    r"today|tomorrow|yesterday|first|next|last|again|still|even|only|"
    r"just|also|too|well|sure|ready|good|bad|great|nice|easy|hard|"
    r"full|empty|new|old|big|small|hm|hmm|oh|ah|wow|hey|hi|bye|ok|okay|"
    r"yeah|woman|boy|girl|kid|guys|thing|things|stuff|door|wall|room|"
    r"place|world|water|light|dark|important|possible|impossible|"
    r"little|children|people|must|shall|any|some|many|much|more|most|"
    r"other|another|each|every|such|same|different|already|always|"
    r"never|sometimes|often|soon|later|now|then|very|quite|both|either|"
    r"neither|down|up|off|back|away|open|close|closed|keep|kept|put|"
    r"let|lets|mean|means|leave|left|feel|felt|show|showed|hear|heard|"
    r"play|played|move|moved|live|lived|believe|happen|happened|"
    r"sit|sat|stand|stood|fall|fell|meet|met|set|read|allow|add|grow|"
    r"grew|offer|offered|die|died|expect|expected|build|built|stay|stayed|"
    r"cut|kill|killed|remain|remained|suggest|suggested|raise|raised|"
    r"pass|passed|require|required|report|reported|decide|decided|"
    r"pull|pulled|push|pushed|watch|watched|follow|followed|"
    r"create|created|speak|spoke|spoken|spend|spent|throw|threw|draw|drew|"
    r"leader|trainers|certified|gym|worldwide|trading|global|station|"
    r"magazines|handbook|adorable|absolutely|correct|ding|mystery"
    r")\b"
)

DK_MARK = re.compile(r"[æøåÆØÅ]")
DK_HINT = re.compile(
    r"(?i)\b(og|er|det|som|en|et|at|ikke|til|med|har|du|jeg|sig|fra|blev|kun|også|efter|før|ved|"
    r"være|den|der|de|dig|mig|hvor|hvis|når|eller|ind|ud|op|ned|ingen|alle|"
    r"noget|kunne|ville|skulle|måtte|må|burde|dette|din|dine|jeres|vores|"
    r"sin|sit|sine|brugt|vilde|fjendens|fjende|spiller|bekræfter|"
    r"skraldespand|kapsel|vælg|gerne|fjernet|skift|plads|redigere|forlade|"
    r"sæt|flytte|landskab|venner|skov|ørken|savanne|vulkan|hule|strand|"
    r"kontrol|maskine|dokument|præstation|opnået|gennemført|succes)\b"
)

EXACT_SKIP = frozenset({"GAME FREAK"})

TOKEN_RE = re.compile(
    r"\{[^}]+\}|\\[nrf]|"
    r"Poké Ball|Pokédex|Pokémon|Pokétch|Pokéwatch|PokéRadar|"
    r"POKéBALL|POKéMON|POKéDEX|POKé|"
    r"poké ball|pokémon|pokétch|pokédex",
    re.IGNORECASE,
)

LANG_BLOCK_RE = re.compile(r'<language name="English">([^<]*)</language>', re.DOTALL)


def en_mixed_match(t: str) -> bool:
    norm = t.replace("\u2019", "'").replace("\u2018", "'")
    return bool(EN_MIXED.search(norm))


def protect(s: str) -> tuple[str, list[str]]:
    tokens: list[str] = []

    def repl(m: re.Match[str]) -> str:
        tokens.append(m.group(0))
        return f"PPPk{len(tokens) - 1:03d}kPPP"

    return TOKEN_RE.sub(repl, s), tokens


def unprotect(s: str, tokens: list[str]) -> str:
    for i, tok in enumerate(tokens):
        s = s.replace(f"PPPk{i:03d}kPPP", tok, 1)
    return s


def mechanical(s: str) -> str:
    return s.replace(r" used\n", r" brugt\n").replace(r" Used\n", r" Brugt\n")


def mechanical_narc_0000_full(inner: str) -> str:
    t = mechanical(inner)
    t = t.replace("The wild ", "Det vilde ")
    t = t.replace("The foe's ", "Fjendens ")
    t = t.replace("The foe\u2019s ", "Fjendens ")
    return t


def no_letters_outside_tokens(t: str) -> bool:
    rem = TOKEN_RE.sub("", t)
    return not re.search(r"[A-Za-zæøåÆØÅ]", rem)


def ambiguous_is_english(t: str) -> bool:
    sample = t[: min(400, len(t))]
    try:
        cand = detect_langs(sample)[0]
        return cand.lang == "en" and cand.prob >= 0.72
    except LangDetectException:
        return True


def should_translate(t: str) -> bool:
    if not t.strip():
        return False
    has_dk = bool(DK_MARK.search(t) or DK_HINT.search(t))
    has_en = en_mixed_match(t)
    if has_dk and not has_en:
        return False
    if has_en:
        return True
    if len(t) <= 30:
        return False
    return ambiguous_is_english(t)


def translate_segment(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    prot, toks = protect(text)
    try:
        out = argos_translate.translate(prot, "en", "da")
    except Exception:
        return text
    return unprotect(out, toks)


def translate_chunked(s: str) -> str:
    parts = re.split(r"(\\[nrf])", s)
    out: list[str] = []
    for p in parts:
        if re.fullmatch(r"\\[rfn]", p):
            out.append(p)
        elif not p.strip():
            out.append(p)
        else:
            out.append(translate_segment(p))
    return "".join(out)


def process_inner(path: Path, inner: str) -> tuple[str, bool]:
    orig = inner
    if path.name == "narc_0000.gmm":
        t = mechanical_narc_0000_full(inner)
        return t, t != orig

    t = mechanical(inner)
    mech_changed = t != inner
    if t.strip() in EXACT_SKIP:
        return t, mech_changed
    if not t.strip():
        return t, mech_changed
    if no_letters_outside_tokens(t):
        return t, mech_changed
    if not should_translate(t):
        return t, mech_changed
    new_t = translate_chunked(t)
    if "PPPk" in new_t:
        new_t = t
    return new_t, mech_changed or (new_t != orig)


def process_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        inner = m.group(1)
        new_inner, row_changed = process_inner(path, inner)
        if row_changed:
            changed = True
        return f'<language name="English">{new_inner}</language>'

    new_raw = LANG_BLOCK_RE.sub(repl, raw)
    if changed:
        path.write_text(new_raw, encoding="utf-8")
    return changed


def main() -> None:
    n = 0
    for i in range(100):
        p = MSG_DIR / f"narc_{i:04d}.gmm"
        if not p.exists():
            continue
        if process_file(p):
            n += 1
        print(f"narc_{i:04d}.gmm total_changed_files={n}", flush=True)
    print(f"changed_files={n}", flush=True)


if __name__ == "__main__":
    main()
