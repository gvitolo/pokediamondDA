#!/usr/bin/env python3
"""Translate <language name="English"> cells that are still English, even if the file reads as Danish overall."""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from deep_translator import GoogleTranslator
from langdetect import LangDetectException, detect

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files/msgdata/msg"

# narc_0500–0618 skips (localized / generated)
SKIP_IDS = {559, 565, 588, 614, 615}

ESC_OR_BRACE = re.compile(
    r"(\{[^}]+\}|\\n|\\r|\\f|POKé|GAME FREAK)"
)

_spec = importlib.util.spec_from_file_location(
    "_batch_da", ROOT / "tools/batch_translate_gmm_da.py"
)
_batch = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_batch)
needs_translation = _batch.needs_translation


def cleaned_for_detect(s: str) -> str:
    t = re.sub(r"\{[^}]+\}|\\[nrf]", " ", s)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def cell_needs_da(s: str) -> bool:
    """Langdetect == en, plus needs_translation for longer strings (cuts false positives)."""
    raw = (s or "").strip()
    if not raw:
        return False
    if re.fullmatch(r"[X\s]+", raw):
        return False
    t = cleaned_for_detect(s)
    if not t:
        return False
    if re.search(r"[æøåÆØÅ]", t):
        return False
    if not re.search(r"[A-Za-z]", t):
        return False
    if len(t) > 24 and re.search(
        r"\b(og|jeg|det|har|ikke|vil|kan|med|fra|som|når|hvor|hvad|din|dig|jer|være|blev|også|kunne|skal|måtte)\b",
        t.lower(),
    ):
        return False
    sample = t[:500]
    try:
        is_en = detect(sample) == "en"
    except LangDetectException:
        is_en = False
    if not is_en:
        return False
    if len(t) >= 16:
        return needs_translation(raw)
    return True


def split_protected(s: str) -> list[str]:
    return ESC_OR_BRACE.split(s)


def translate_segment(
    seg: str, translator: GoogleTranslator, cache: dict[str, str]
) -> str:
    if not seg:
        return seg
    lead_m = re.match(r"^(\s*)", seg)
    trail_m = re.search(r"(\s*)$", seg)
    lead = lead_m.group(1) if lead_m else ""
    trail = trail_m.group(1) if trail_m else ""
    core = seg[len(lead) : len(seg) - len(trail)] if trail else seg[len(lead) :]
    if not core:
        return seg
    if core in cache:
        tcore = cache[core]
    else:
        tcore = core
        for attempt in range(5):
            try:
                t = translator.translate(core)
                if t is not None:
                    tcore = t
                    break
            except Exception:
                pass
            time.sleep(1.5 * (attempt + 1))
        cache[core] = tcore
        time.sleep(0.025)
    return lead + tcore + trail


def translate_message(s: str, translator: GoogleTranslator, cache: dict[str, str]) -> str:
    parts = split_protected(s)
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        if ESC_OR_BRACE.fullmatch(p):
            out.append(p)
        else:
            out.append(translate_segment(p, translator, cache))
    return "".join(out)


def row_is_garbage(row: ET.Element) -> bool:
    attr = row.find('./attribute[@name="window_context_name"]')
    return attr is not None and (attr.text or "").strip() == "garbage"


def process_file(path: Path, translator: GoogleTranslator, cache: dict[str, str]) -> bool:
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
            if not cell_needs_da(orig):
                continue
            new_t = translate_message(orig, translator, cache)
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
    lo, hi = 500, 618
    start_n = int(os.environ.get("GMM_DA_START", str(lo)))
    end_n = int(os.environ.get("GMM_DA_END", str(hi)))
    start_n = max(lo, start_n)
    end_n = min(hi, end_n)
    translator = GoogleTranslator(source="en", target="da")
    cache: dict[str, str] = {}
    changed_ids: list[int] = []
    for n in range(start_n, end_n + 1):
        if n in SKIP_IDS:
            continue
        path = MSG / f"narc_{n:04d}.gmm"
        if not path.exists():
            continue
        print(f"narc_{n:04d}.gmm ...", file=sys.stderr, flush=True)
        try:
            if process_file(path, translator, cache):
                changed_ids.append(n)
                print(f"UPDATED narc_{n:04d}.gmm", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"FAIL narc_{n:04d}.gmm: {e}", file=sys.stderr)
            raise
    print(",".join(f"{x:04d}" for x in changed_ids))
    print(len(changed_ids), "files changed", file=sys.stderr)


if __name__ == "__main__":
    main()
