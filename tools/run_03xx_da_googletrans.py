#!/usr/bin/env python3
"""Translate narc_0300–0399 English GMM strings to Danish via googletrans (cached)."""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

from googletrans import Translator

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files" / "msgdata" / "msg"
CACHE = Path("/tmp/gmm_03xx_googletrans_da.json")

SKIP_FILES = {300, 314, 362, 363, 364, 382, 383, 384}
TOK = re.compile(r"\{[^}]+\}")
EN_BLOCK = re.compile(r'(<language name="English">)(.*?)(</language>)', re.DOTALL)


def only_ph(s: str) -> bool:
    t = s.strip()
    return not t or bool(TOK.fullmatch(t))


def load_cache() -> dict[str, str]:
    if CACHE.is_file():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(c: dict[str, str]) -> None:
    CACHE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


def collect_unique() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for n in range(300, 400):
        if n in SKIP_FILES:
            continue
        p = MSG / f"narc_{n:04d}.gmm"
        if not p.is_file():
            continue
        raw = p.read_text(encoding="utf-8")
        for m in EN_BLOCK.finditer(raw):
            body = m.group(2)
            if only_ph(body):
                continue
            if body not in seen:
                seen.add(body)
                out.append(body)
    return out


def apply_all(cache: dict[str, str]) -> int:
    total = 0
    for n in range(300, 400):
        if n in SKIP_FILES:
            continue
        p = MSG / f"narc_{n:04d}.gmm"
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")

        def repl(m: re.Match[str]) -> str:
            nonlocal total
            inner = m.group(2)
            if only_ph(inner):
                return m.group(0)
            da = cache.get(inner, inner)
            if da == inner:
                return m.group(0)
            total += 1
            return m.group(1) + da + m.group(3)

        new = EN_BLOCK.sub(repl, text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            print(f"wrote {p.name}", file=sys.stderr)
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-only", action="store_true")
    args = ap.parse_args()

    cache = load_cache()

    if args.apply_only:
        n = apply_all(cache)
        print(f"apply-only replacements={n}", file=sys.stderr)
        return 0

    tr = Translator()
    unique = collect_unique()
    pending = [s for s in unique if s not in cache]
    print(f"unique={len(unique)} pending={len(pending)} cached={len(cache)}", file=sys.stderr)

    for i, s in enumerate(pending):
        try:
            r = tr.translate(s, dest="da")
            cache[s] = r.text if r and r.text else s
        except Exception as e:
            print(f"fail {i}: {e!r} :: {s[:80]!r}", file=sys.stderr)
            time.sleep(30)
            try:
                r = tr.translate(s, dest="da")
                cache[s] = r.text if r and r.text else s
            except Exception:
                cache[s] = s
        if (i + 1) % 40 == 0:
            save_cache(cache)
            apply_all(cache)
            print(f"… translate {i + 1}/{len(pending)}", file=sys.stderr)
        time.sleep(random.uniform(1.6, 2.4))

    save_cache(cache)
    total = apply_all(cache)
    print(f"done replacements={total}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
