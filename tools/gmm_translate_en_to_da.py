#!/usr/bin/env python3
"""
Translate <language name="English"> to Danish in GMM files (narc_0000–0099).
Uses offline Argos (en→da). Splits on {…}, \\n, \\r, \\f, POKé, GAME FREAK so those are never translated.
"""
from __future__ import annotations

import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

import argostranslate.translate as argos

MSG_DIR = "/Users/giuseppe/pokediamondDA/files/msgdata/msg"
ESC_OR_BRACE = re.compile(
    r"(\{[^}]+\}|\\n|\\r|\\f|POKé|GAME FREAK)"
)
RANGE_GLOB = f"{MSG_DIR}/narc_00[0-9][0-9].gmm"


def split_protected(s: str) -> list[str]:
    return ESC_OR_BRACE.split(s)


def translate_segment(seg: str, cache: dict[str, str]) -> str:
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
        tcore = argos.translate(core, "en", "da")
        cache[core] = tcore
    return lead + tcore + trail


def translate_message(s: str, cache: dict[str, str]) -> str:
    parts = split_protected(s)
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        if ESC_OR_BRACE.fullmatch(p):
            out.append(p)
        else:
            out.append(translate_segment(p, cache))
    return "".join(out)


def row_is_garbage(row: ET.Element) -> bool:
    attr = row.find('./attribute[@name="window_context_name"]')
    return attr is not None and (attr.text or "").strip() == "garbage"


def process_file(path: str, cache: dict[str, str]) -> bool:
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
            new_t = translate_message(orig, cache).replace("\u0027", "\u2019")
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
    start_id = int(os.environ.get("GMM_DA_MIN_ID", "0"))
    paths = sorted(glob.glob(RANGE_GLOB))
    paths = [p for p in paths if int(os.path.basename(p)[5:9]) >= start_id]
    cache: dict[str, str] = {}
    n_changed = 0
    for p in paths:
        if process_file(p, cache):
            n_changed += 1
            print("updated", p, file=sys.stderr, flush=True)
    print(n_changed)


if __name__ == "__main__":
    main()
