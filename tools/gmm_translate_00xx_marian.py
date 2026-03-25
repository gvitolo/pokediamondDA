#!/usr/bin/env python3
"""
Translate English <language name="English"> text to Danish in narc_0000..0099 using
Helsinki-NLP Marian (en-da). Preserves {STRVAR...}, {COLOR...}, \\n, \\r, \\f, POKé,
GAME FREAK, Pokémon, [[...]] via ZZZP placeholders. Skips garbage rows.

Only runs Marian on strings that look English (needs_translation + extra heuristics)
so already-Danish cells are left unchanged.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import torch
from batch_translate_gmm_da import needs_translation
from langdetect import DetectorFactory, LangDetectException, detect
from transformers import MarianMTModel, MarianTokenizer

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files" / "msgdata" / "msg"

DetectorFactory.seed = 0

# Exact full-string replacements for short English UI Marian often leaves unchanged.
EXACT_UI_DA: dict[str, str] = {
    "ANVENDELSE": "BRUG",
    "TOSS": "KAST",
    "REGISTER": "REGISTRER",
    "GIVE": "GIV",
    "CHECK TAG": "TJEK MÆRKE",
    "CONFIRM": "BEKRÆFT",
    "WALK": "GÅ",
    "CANCEL": "ANNULLER",
    "CHECK": "TJEK",
    "DESELECT": "FRAVÆLG",
    "CLOSE BAG": "LUK TASKEN",
    "MONEY": "PENGE",
    "SHIFT": "SKIFT",
    "SUMMARY": "OVERSIGT",
    "CHECK MOVES": "TJEK TRÆK",
    "NEXT LV": "NÆSTE NV",
    "ATTACK": "ANGREB",
    "DEFENSE": "FORSVAR",
    "SP. ATK": "SP.-ANG.",
    "SP. DEF": "SP.-FORSVAR",
    "SPEED": "HASTIGHED",
    "POWER": "KRAFT",
    "ACCURACY": "PRÆCISION",
    "CATEGORY": "KATEGORI",
    "PHYSICAL": "FYSISK",
    "SPECIAL": "SPECIAL",
    "FORGET": "GLEM",
    "APPEAL PTS": "APPIL-POINT",
    "RESTORE": "GENDAN",
    "HEALERS": "HELING",
    "EDIT": "REDIGER",
    "QUIT": "AFSLUT",
    "SET": "VÆLG",
    "REMOVE": "FJERN",
    "OPEN": "ÅBN",
    "PLANT": "PLANTE",
    "MOVE": "TRÆK",
    "ITEM": "GENSTAND",
    "BAG": "TASKE",
    "JUMP": "SPRING",
    "MARK": "MÆRK",
    "PLACE": "PLADS",
    "SIMPLE": "SIMPEL",
    "WALLPAPER": "BAGGRUND",
    "DIAMOND": "DIAMANT",
    "PEARL": "PERLE",
    "SCHWITCH": "SKIFT",
    "TEAM GALACIC": "TEAM GALACTIC",
    "LISTE OVER LEADER": "LISTE OVER LEDERE",
    "TYPE": "TYPE",
    "INFO": "INFO",
    "STATUS": "STATUS",
}

RAW = re.compile(
    r"(\{[^}]+\}|\\n|\\r|\\f|POKé|GAME FREAK|Pokémon|\[\[[^\]]+\]\])"
)

_YOU_EN = re.compile(
    r"(?i)\b(you'?(?:re|ve|ll|d)|you are|you have|you can|your |can't |don't |doesn't |didn't |won't |what |where |when |which |who |why |how )\b"
)


def row_is_garbage(row: ET.Element) -> bool:
    attr = row.find('./attribute[@name="window_context_name"]')
    return attr is not None and (attr.text or "").strip() == "garbage"


def should_translate(s: str) -> bool:
    if not s or not s.strip():
        return False
    if needs_translation(s):
        return True
    t = s.strip()
    if re.search(r"\bThe (wild|foe)\b", t):
        return True
    if _YOU_EN.search(t):
        return True
    if re.search(r"\bDelete\b", t, re.I) or re.search(r"\bsaved data\b", t, re.I):
        return True
    compact = re.sub(r"\\[nrf]", "", t)
    # str.isupper() is True for "{STRVAR_1 1, 0}" — exclude brace/control cells.
    if "{" not in t and "}" not in t:
        if (
            compact.isascii()
            and compact.isupper()
            and re.search(r"[A-Z]{2,}", compact)
            and len(compact) <= 48
        ):
            return True
    if len(t) > 45:
        try:
            return detect(t) == "en"
        except LangDetectException:
            return False
    return False


def protect(s: str) -> tuple[str, list[str]]:
    ph: list[str] = []

    def repl(m: re.Match[str]) -> str:
        ph.append(m.group(0))
        return f"ZZZP{len(ph) - 1}ZZZ"

    return RAW.sub(repl, s), ph


def restore(s: str, ph: list[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        i = int(m.group(1))
        return ph[i] if 0 <= i < len(ph) else m.group(0)

    return re.sub(r"(?i)ZZZP(\d+)ZZZ", repl, s)


def translate_batch(
    strings: list[str],
    model: MarianMTModel,
    tok: MarianTokenizer,
    device: torch.device,
    batch_size: int = 10,
) -> list[str]:
    results: list[str] = []
    for start in range(0, len(strings), batch_size):
        chunk = strings[start : start + batch_size]
        prepped: list[tuple] = []
        for s in chunk:
            if not s.strip():
                prepped.append(("plain", s))
                continue
            p, ph = protect(s)
            if not re.search(r"[A-Za-z]", p):
                prepped.append(("plain", s))
                continue
            prepped.append(("mt", s, p, ph))

        mt_inputs = [x[2] for x in prepped if x[0] == "mt"]
        mt_out: list[str] = []
        if mt_inputs:
            enc = tok(mt_inputs, return_tensors="pt", padding=True, truncation=True, max_length=512)
            enc = {k: v.to(device) for k, v in enc.items()}
            with torch.inference_mode():
                gen = model.generate(**enc, max_length=512)
            mt_out = tok.batch_decode(gen, skip_special_tokens=True)
        mt_iter = iter(mt_out)

        for x in prepped:
            if x[0] == "plain":
                results.append(x[1])
            else:
                results.append(restore(next(mt_iter), x[3]))
    return results


def process_file(
    path: Path,
    model: MarianMTModel,
    tok: MarianTokenizer,
    device: torch.device,
    batch_size: int,
) -> bool:
    tree = ET.parse(path)
    root = tree.getroot()
    changed = False
    for row in root.findall("row"):
        if row_is_garbage(row):
            continue
        for el in row.findall("language"):
            if el.get("name") != "English":
                continue
            orig = el.text if el.text is not None else ""
            if not orig.strip():
                continue
            rep = EXACT_UI_DA.get(orig)
            if rep is not None and rep != orig:
                el.text = rep
                changed = True

    jobs: list[tuple[ET.Element, str]] = []
    for row in root.findall("row"):
        if row_is_garbage(row):
            continue
        for el in row.findall("language"):
            if el.get("name") != "English":
                continue
            orig = el.text if el.text is not None else ""
            if not orig.strip():
                continue
            if not should_translate(orig):
                continue
            jobs.append((el, orig))

    if jobs:
        originals = [t for _, t in jobs]
        translated = translate_batch(originals, model, tok, device, batch_size=batch_size)
        for (el, orig), new_t in zip(jobs, translated):
            if new_t != orig:
                el.text = new_t
                changed = True

    if changed:
        ET.indent(tree.getroot(), space="\t", level=0)
        tree.write(
            path,
            encoding="UTF-8",
            xml_declaration=True,
            default_namespace=None,
            method="xml",
        )
    return changed


def main() -> None:
    model_name = "Helsinki-NLP/opus-mt-en-da"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    model.to(device)
    model.eval()

    n_changed = 0
    for i in range(100):
        path = MSG / f"narc_{i:04d}.gmm"
        if not path.exists():
            continue
        try:
            if process_file(path, model, tok, device, batch_size=10):
                n_changed += 1
                print("updated", path.name, file=sys.stderr, flush=True)
        except ET.ParseError as e:
            print(f"SKIP parse {path.name}: {e}", file=sys.stderr)
    print(n_changed)


if __name__ == "__main__":
    main()
