#!/usr/bin/env python3
"""
Rewrite <language name="English"> from git HEAD (English) → Danish for narc_0200–0299.
Uses the same placeholder preservation as batch_translate_gmm_da ({...} segments untouched).
Caches in tools/.gmm_da_translate_cache.json (keys = source English strings).
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator

from batch_translate_gmm_da import load_cache, save_cache, translate_preserved

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files" / "msgdata" / "msg"
CACHE_PATH = ROOT / "tools" / ".gmm_da_translate_cache.json"
DELAY = 0.02


def row_english_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for rm in re.finditer(
        r"<row\b[^>]*>.*?</row>", text, flags=re.DOTALL | re.IGNORECASE
    ):
        em = re.search(
            r'<language\s+name="English">(.*?)</language>',
            rm.group(0),
            flags=re.DOTALL,
        )
        if not em:
            continue
        abs_start = rm.start() + em.start(1)
        abs_end = rm.start() + em.end(1)
        spans.append((abs_start, abs_end, em.group(1)))
    return spans


def git_head_text(rel: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{rel}"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None


def head_string_to_da(ht: str, cache: dict[str, str], translator: GoogleTranslator) -> str:
    if not ht.strip():
        return ht
    if re.fullmatch(r"[X\s]+", ht.strip()):
        return ht
    if ht in cache:
        return cache[ht]
    cache[ht] = translate_preserved(translator, ht, DELAY)
    return cache[ht]


def process_file(narc_id: int, cache: dict[str, str], translator: GoogleTranslator) -> bool:
    name = f"narc_{narc_id:04d}.gmm"
    path = MSG / name
    rel = f"files/msgdata/msg/{name}"
    if not path.exists():
        return False
    head = git_head_text(rel)
    if head is None:
        print(f"SKIP {name}: no HEAD", file=sys.stderr)
        return False
    cur = path.read_text(encoding="utf-8")
    h_spans = row_english_spans(head)
    c_spans = row_english_spans(cur)
    if len(h_spans) != len(c_spans):
        print(
            f"WARN {name}: English slot count head={len(h_spans)} cur={len(c_spans)}",
            file=sys.stderr,
        )
        return False

    replacements: list[tuple[int, int, str]] = []
    for (_hs, _he, ht), (cs, ce, _ct) in zip(h_spans, c_spans):
        new_text = head_string_to_da(ht, cache, translator)
        replacements.append((cs, ce, new_text))

    out = cur
    for start, end, new_inner in sorted(replacements, key=lambda x: -x[0]):
        out = out[:start] + new_inner + out[end:]
    if out != cur:
        path.write_text(out, encoding="utf-8")
        return True
    return False


def main() -> None:
    translator = GoogleTranslator(source="en", target="da")
    cache = load_cache()
    changed: list[int] = []
    for n in range(200, 300):
        did = process_file(n, cache, translator)
        if did:
            changed.append(n)
        save_cache(cache)
        print(f"narc_{n:04d}.gmm", "UPDATED" if did else "unchanged")
    print("---")
    print(f"Updated {len(changed)} files, cache entries: {len(cache)}")
    print("Touched:", ",".join(f"{x:04d}" for x in changed))


if __name__ == "__main__":
    main()
