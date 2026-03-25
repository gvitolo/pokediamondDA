#!/usr/bin/env python3
"""
Translate <language name="English"> to Danish for narc_0300–0399 only where
text is detected as English. Skips narc_0362/363/364/382/383/384 entirely.
Preserves {…} tokens and \\n \\r \\f.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.exceptions import TranslationNotFound

try:
    from langdetect import detect_langs, LangDetectException
    from langdetect.detector_factory import DetectorFactory
except ImportError:
    print("pip install langdetect deep-translator", file=sys.stderr)
    raise

DetectorFactory.seed = 42

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files" / "msgdata" / "msg"

SKIP_FILES = {362, 363, 364, 382, 383, 384}
RANGE = range(300, 400)

TOKEN = re.compile(r"(\{[^}]+\}|\\[nrf]|POKé)")
LETTER_RE = re.compile(r"[A-Za-zÀ-ÿ]")


def protect(s: str) -> tuple[str, list[str]]:
    toks: list[str] = []

    def repl(m: re.Match[str]) -> str:
        toks.append(m.group(0))
        return f" __GF{len(toks) - 1:04d}__ "

    return TOKEN.sub(repl, s), toks


def unprotect(translated: str, toks: list[str]) -> str:
    out = translated
    for i, tok in enumerate(toks):
        out = out.replace(f" __GF{i:04d}__ ", tok)
        out = out.replace(f"__GF{i:04d}__", tok)
    return out


def strip_for_detect(s: str) -> str:
    """Remove STRVAR and control codes for language detection."""
    t = TOKEN.sub(" ", s)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def probably_english(s: str) -> bool:
    raw = s.strip()
    if not raw or not LETTER_RE.search(raw):
        return False
    if re.fullmatch(r"[X\s]+", raw):
        return False
    core = strip_for_detect(s)
    if len(core) < 8:
        # Short UI: English all-caps tokens etc.
        if re.search(
            r"\b(The|You|Would|Please|Press|Waiting|Error|Cannot|Unable|Hello|Good |Berry|Pokémon|Trainer|battle|trade)\b",
            s,
            re.I,
        ):
            return True
        if len(core) >= 3 and core.isascii() and re.search(r"[aeiouy]", core, re.I):
            try:
                langs = detect_langs(core)
                if langs and langs[0].lang == "en" and langs[0].prob >= 0.55:
                    return True
            except LangDetectException:
                pass
        return False
    try:
        langs = detect_langs(core)
        if not langs:
            return False
        top = langs[0]
        if top.lang != "en":
            return False
        if top.prob < 0.75:
            return False
        if len(langs) > 1 and langs[1].lang == "da" and langs[1].prob > 0.35:
            return False
        return True
    except LangDetectException:
        return False


def translate_protected(protected: str) -> str:
    g = GoogleTranslator(source="en", target="da")
    try:
        return g.translate(protected)
    except (TranslationNotFound, Exception):
        pass
    mm = MyMemoryTranslator(source="en", target="da")
    out = mm.translate(protected)
    if not out:
        raise RuntimeError("empty translation")
    return out


def translate_string(src: str) -> str:
    protected, toks = protect(src)
    if not LETTER_RE.search(protected.replace(" ", "")):
        return src
    last_err: Exception | None = None
    for attempt in range(6):
        try:
            da = translate_protected(protected)
            return unprotect(da, toks)
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"translate failed: {src[:80]!r}") from last_err


ROW_RE = re.compile(
    r'(<row id="[^"]+" index="(\d+)">\s*'
    r'<attribute name="window_context_name">[^<]*</attribute>\s*'
    r'<language name="English">)(.*?)(</language>)',
    re.DOTALL,
)


def process_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0

    def sub_row(m: re.Match[str]) -> str:
        nonlocal n
        inner = m.group(3)
        if not probably_english(inner):
            return m.group(0)
        new_inner = translate_string(inner)
        if new_inner != inner:
            n += 1
        return m.group(1) + new_inner + m.group(4)

    new_text = ROW_RE.sub(sub_row, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return n


def main() -> int:
    total_rows = 0
    files_changed = 0
    for i in RANGE:
        if i in SKIP_FILES:
            continue
        p = MSG / f"narc_{i:04d}.gmm"
        if not p.is_file():
            continue
        try:
            n = process_file(p)
        except Exception as e:
            print(f"FAIL {p.name}: {e}", file=sys.stderr)
            raise
        if n:
            files_changed += 1
            total_rows += n
            print(f"{p.name}: {n} rows", file=sys.stderr)
    print(f"Done: {files_changed} files, {total_rows} English rows translated", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
