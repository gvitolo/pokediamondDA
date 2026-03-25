#!/usr/bin/env python3
"""
Batch-translate <language name="English"> to Danish for narc_0300–0399.
Skips 0362, 0363, 0364, 0382, 0383, 0384. For narc_0314, skips row indices 56–74
(already Danish). Preserves {…} and \\n/\\r/\\f.

Uses Google via deep_translator, MyMemory fallback; cache under /tmp.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.exceptions import TranslationNotFound

ROOT = Path(__file__).resolve().parents[1]
MSG = ROOT / "files" / "msgdata" / "msg"
CACHE = Path("/tmp/pokediamond_gmm_da_03xx_cache.json")

SKIP_FILES = {362, 363, 364, 382, 383, 384}
RANGE = range(300, 400)
NARC_0314_SKIP_INDICES = set(range(56, 75))

TOKEN = re.compile(r"(\{[^}]+\}|\\[nrf])")
ROW_RE = re.compile(
    r'(<row id="[^"]+" index="(\d+)">\s*'
    r'<attribute name="window_context_name">[^<]*</attribute>\s*'
    r'<language name="English">)(.*?)(</language>)',
    re.DOTALL,
)

cache_lock = threading.Lock()
LETTER_RE = re.compile(r"[A-Za-zÀ-ÿÆØÅæøå]")


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


def load_cache() -> dict[str, str]:
    if CACHE.is_file():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(c: dict[str, str]) -> None:
    tmp = CACHE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE)


def translate_protected(protected: str) -> str:
    g = GoogleTranslator(source="en", target="da")
    try:
        return g.translate(protected)
    except (TranslationNotFound, Exception):
        pass
    mm = MyMemoryTranslator(source="en", target="da")
    out = mm.translate(protected)
    if not out:
        raise RuntimeError(f"MyMemory empty for {protected[:120]!r}")
    return out


def translate_string(src: str, cache: dict[str, str]) -> str:
    with cache_lock:
        if src in cache:
            return cache[src]
    protected, toks = protect(src)
    if not LETTER_RE.search(protected):
        with cache_lock:
            cache[src] = src
        return src
    last_err: Exception | None = None
    for attempt in range(8):
        try:
            da = translate_protected(protected)
            out = unprotect(da, toks)
            with cache_lock:
                cache[src] = out
            return out
        except Exception as e:
            last_err = e
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"translate failed: {src[:100]!r}") from last_err


def worker(args: tuple[str, dict[str, str]]) -> None:
    s, cache = args
    translate_string(s, cache)


def main() -> int:
    paths: list[Path] = []
    for n in RANGE:
        if n in SKIP_FILES:
            continue
        p = MSG / f"narc_{n:04d}.gmm"
        if p.is_file():
            paths.append(p)

    cache = load_cache()
    unique: list[str] = []
    seen: set[str] = set()

    for p in paths:
        narc_314 = p.name == "narc_0314.gmm"
        text = p.read_text(encoding="utf-8")
        for m in ROW_RE.finditer(text):
            idx = int(m.group(2))
            if narc_314 and idx in NARC_0314_SKIP_INDICES:
                continue
            s = m.group(3)
            if s not in seen:
                seen.add(s)
                unique.append(s)

    pending = [s for s in unique if s not in cache]
    total = len(unique)
    print(f"{len(pending)} pending / {total} unique strings", file=sys.stderr)

    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(worker, (s, cache)): s for s in pending}
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done % 80 == 0:
                save_cache(cache)
                print(f"… {done} / {len(pending)}", file=sys.stderr)

    save_cache(cache)

    for p in paths:
        narc_314 = p.name == "narc_0314.gmm"
        text = p.read_text(encoding="utf-8")

        def sub_row(m: re.Match[str]) -> str:
            idx = int(m.group(2))
            if narc_314 and idx in NARC_0314_SKIP_INDICES:
                return m.group(0)
            inner = m.group(3)
            return m.group(1) + cache.get(inner, inner) + m.group(4)

        p.write_text(ROW_RE.sub(sub_row, text), encoding="utf-8")

    print(f"wrote {len(paths)} files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
