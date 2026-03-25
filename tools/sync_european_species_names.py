#!/usr/bin/env python3
"""
Rewrite species message banks to EU-style localized names (German base, Danish letters).

Danish has no official Gen 4 species list in data files; German EU names are used as
the standard Roman-alphabet localization, with ä→Æ, ö→Ø, ü→Y for Danish typography.

Updates:
  - files/msgdata/msg/narc_0362.gmm  (species names)
  - files/msgdata/msg/narc_0363.gmm  (article + colored name for summaries)
  - files/msgdata/msg/narc_0615.gmm  (replace embedded ALL CAPS species tokens in flavor text)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(__file__).resolve().parent / "data" / "species_en_de.json"
MSG = ROOT / "files" / "msgdata" / "msg"


def de_to_display(de: str) -> str:
    if not de:
        return ""
    s = de.upper()
    table = str.maketrans({"Ä": "Æ", "Ö": "Ø", "Ü": "Y"})
    return s.translate(table)


def parse_gmm_rows(path: Path) -> list[tuple[str, int, str, str]]:
    """Return (row_id, index, window_ctx, english_inner) — first English node only."""
    text = path.read_text(encoding="utf-8")
    rows: list[tuple[str, int, str, str]] = []
    for m in re.finditer(
        r'<row id="([^"]+)" index="(\d+)">(.*?)</row>',
        text,
        re.DOTALL,
    ):
        block = m.group(3)
        wctx_m = re.search(
            r'<attribute name="window_context_name">([^<]*)</attribute>', block
        )
        en_m = re.search(
            r'<language name="English">([^<]*)</language>', block
        )
        if not wctx_m or not en_m:
            continue
        rows.append((m.group(1), int(m.group(2)), wctx_m.group(1), en_m.group(1)))
    return rows


def replace_row_english(text: str, row_id: str, new_english: str) -> str:
    pat = re.compile(
        rf'(<row id="{re.escape(row_id)}" index="\d+">\s*'
        r'<attribute name="window_context_name">[^<]*</attribute>\s*'
        r'<language name="English">)([^<]*)(</language>)',
        re.DOTALL,
    )
    return pat.sub(rf"\g<1>{new_english}\g<3>", text, count=1)


def build_0363_snippet(window_ctx: str, article: str, name: str) -> str:
    if window_ctx == "garbage":
        return ""  # caller handles garbage rows separately
    inner = f"{article} {{COLOR 255}}{name}{{COLOR 0}}"
    return inner


def main() -> int:
    if not DATA.is_file():
        print("Missing", DATA, file=sys.stderr)
        return 1

    names_json: list = json.loads(DATA.read_text(encoding="utf-8"))
    if len(names_json) < 494:
        print("species_en_de.json too short", file=sys.stderr)
        return 1

    p362 = MSG / "narc_0362.gmm"
    p363 = MSG / "narc_0363.gmm"
    p615 = MSG / "narc_0615.gmm"

    old362 = p362.read_text(encoding="utf-8")
    rows362 = parse_gmm_rows(p362)

    new_by_index: dict[int, str] = {}
    replace_pairs: list[tuple[str, str]] = []

    for row_id, idx, wctx, old_en in rows362:
        if idx == 0:
            new_by_index[idx] = old_en  # -----
            continue
        if idx >= 494:
            if idx == 494:
                nn = "ÆG"
            else:
                nn = "DÅRLIGT ÆG"
            new_by_index[idx] = nn
            replace_pairs.append((old_en, nn))
            continue

        entry = names_json[idx]
        if not entry or not entry.get("de"):
            new_by_index[idx] = old_en
            continue
        new_name = de_to_display(entry["de"])
        new_by_index[idx] = new_name
        if old_en != new_name:
            replace_pairs.append((old_en, new_name))

    t362 = old362
    for row_id, idx, wctx, old_en in rows362:
        if idx not in new_by_index:
            continue
        t362 = replace_row_english(t362, row_id, new_by_index[idx])
    p362.write_text(t362, encoding="utf-8")

    old363 = p363.read_text(encoding="utf-8")
    rows363 = parse_gmm_rows(p363)
    t363 = old363
    for row_id, idx, wctx, _ in rows363:
        if wctx == "garbage":
            continue
        name = new_by_index.get(idx)
        if name is None:
            continue
        article = "et" if idx in (494, 495) else "en"
        new_txt = build_0363_snippet("used", article, name)
        t363 = replace_row_english(t363, row_id, new_txt)
    p363.write_text(t363, encoding="utf-8")

    # narc_0615: substitute old species tokens (longest first)
    replace_pairs = list(dict.fromkeys(replace_pairs))  # dedupe, preserve order
    replace_pairs.sort(key=lambda p: len(p[0]), reverse=True)
    t615 = p615.read_text(encoding="utf-8")
    for old, new in replace_pairs:
        if not old or old == new:
            continue
        t615 = t615.replace(old, new)
    p615.write_text(t615, encoding="utf-8")

    print(f"Updated {p362.name}, {p363.name}, {p615.name}; {len(replace_pairs)} replacement kinds for flavor text.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
