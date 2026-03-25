#!/usr/bin/env python3
"""Translate entire <language name="English"> cells to Danish, preserving {STRVAR...} tags."""
from __future__ import annotations

import re
import time
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files" / "msgdata" / "msg"

VAR_RE = re.compile(r"\{[^}]+\}")


def protect(s: str) -> tuple[str, list[str]]:
    parts: list[str] = []

    def repl(m: re.Match) -> str:
        parts.append(m.group(0))
        return f"ZZZVAR{len(parts) - 1}ZZZ"

    return VAR_RE.sub(repl, s), parts


def restore(s: str, parts: list[str]) -> str:
    out = s
    for i, p in enumerate(parts):
        out = out.replace(f"ZZZVAR{i}ZZZ", p)
    return out


def translate_cell(translator: GoogleTranslator, s: str, delay: float) -> str:
    if not s.strip():
        return s
    body, parts = protect(s)
    time.sleep(delay)
    try:
        dan = translator.translate(body)
        if not dan:
            return s
        return restore(dan, parts)
    except Exception:
        return s


def process_file(path: Path, delay: float = 0.08) -> int:
    text = path.read_text(encoding="utf-8")
    translator = GoogleTranslator(source="en", target="da")
    n = 0

    def repl(m: re.Match) -> str:
        nonlocal n
        inner = m.group(1)
        if not inner.strip():
            return m.group(0)
        new = translate_cell(translator, inner, delay)
        if new != inner:
            n += 1
        return f'<language name="English">{new}</language>'

    new_text = re.sub(
        r'<language name="English">(.*?)</language>',
        repl,
        text,
        flags=re.DOTALL,
    )
    path.write_text(new_text, encoding="utf-8")
    return n


def main() -> None:
    import sys

    files = sys.argv[1:] or []
    for f in files:
        p = Path(f)
        if not p.is_absolute():
            p = MSG / p
        c = process_file(p)
        print(p.name, c, "cells")


if __name__ == "__main__":
    main()
