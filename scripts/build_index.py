#!/usr/bin/env python3
"""Validate every theme under themes/ and regenerate index.json and thumbnails.

MonkSynth's theme gallery reads index.json and fetches files from this repo,
so the index is the contract between the two. Run this after adding or
changing a theme:

    pip install pillow
    python scripts/build_index.py          # rewrite index.json and thumb.png files
    python scripts/build_index.py --check  # validate only, write nothing (PR CI)

On main, CI runs the full build and commits the result, so contributors don't
have to regenerate the index themselves (thumbnail bytes can differ between
Pillow versions, which is also why --check doesn't compare them).
"""

import argparse
import hashlib
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"
INDEX = ROOT / "index.json"

SCHEMA = 1
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

# Files a theme may contain. The plugin only downloads names on this list.
THEME_PNGS = [
    "background.png",
    "monk-strip.png",
    "knob-left.png",
    "knob-right.png",
    "fader-down-large.png",
    "fader-down-sm.png",
    "fader-right-sm.png",
    "info.png",
]
OPTIONAL_FILES = ["credits.txt"]
REQUIRED = ["theme.json", "background.png", "monk-strip.png"]
THUMB = "thumb.png"

# Keep in sync with the plugin's download limits.
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_THEME_BYTES = 24 * 1024 * 1024

META_FIELDS = ["name", "author", "version", "description", "url"]

# The monk sprite sheet is a 5x6 grid of 311x311 frames in 314 px columns,
# ordered down each column. Frame 5 is the idle pose.
FRAME = 311
COLUMN = 314
IDLE_FRAME = 5

# Thumbnails are 112x112 (56 pt at 2x): the monk's face over the background,
# cropped the same way the gallery mockup does.
THUMB_SIZE = 112
THUMB_SCALE = 0.44
BG_OFFSET = (-22, -8)
MONK_ORIGIN = (22, 4)  # where the plugin draws the monk on the background


def fail(errors, theme_id, msg):
    errors.append(f"{theme_id}: {msg}")


def load_meta(theme_dir, errors):
    tid = theme_dir.name
    try:
        meta = json.loads((theme_dir / "theme.json").read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fail(errors, tid, f"theme.json is not valid JSON ({e})")
        return None
    if not isinstance(meta, dict):
        fail(errors, tid, "theme.json must be an object")
        return None
    out = {}
    for key in META_FIELDS:
        val = meta.get(key, "")
        if not isinstance(val, str):
            fail(errors, tid, f"theme.json '{key}' must be a string")
            continue
        if "\n" in val or '"' in val:
            # The plugin's theme.json reader handles single-line strings
            # without escaped quotes only.
            fail(errors, tid, f"theme.json '{key}' must be one line with no double quotes")
        out[key] = val.strip()
    if not out.get("name"):
        fail(errors, tid, "theme.json needs a 'name'")
    if out.get("url") and not re.match(r"^https?://", out["url"]):
        fail(errors, tid, "theme.json 'url' must start with http:// or https://")
    return out


def check_images(theme_dir, errors):
    tid = theme_dir.name
    bg = Image.open(theme_dir / "background.png")
    if bg.size != (360, 510):
        fail(errors, tid, f"background.png must be 360x510, is {bg.size[0]}x{bg.size[1]}")
    strip = Image.open(theme_dir / "monk-strip.png")
    if strip.size[1] != FRAME * 6 or strip.size[0] < COLUMN * 4 + FRAME:
        fail(errors, tid, f"monk-strip.png must be a 5x6 grid of 311x311 frames, is {strip.size[0]}x{strip.size[1]}")
    for name in ("knob-left.png", "knob-right.png"):
        p = theme_dir / name
        if p.exists():
            w, h = Image.open(p).size
            if h != w * 60:
                fail(errors, tid, f"{name} must be a 60-frame vertical filmstrip, is {w}x{h}")


def make_thumb(theme_dir):
    bg = Image.open(theme_dir / "background.png").convert("RGBA")
    strip = Image.open(theme_dir / "monk-strip.png").convert("RGBA")

    col, row = divmod(IDLE_FRAME, 6)
    frame = strip.crop((col * COLUMN, row * FRAME, col * COLUMN + FRAME, (row + 1) * FRAME))
    full = bg.copy()
    full.alpha_composite(frame, MONK_ORIGIN)

    w = round(full.size[0] * THUMB_SCALE)
    h = round(full.size[1] * THUMB_SCALE)
    scaled = full.resize((w, h), Image.LANCZOS)
    thumb = Image.new("RGBA", (THUMB_SIZE, THUMB_SIZE), (14, 13, 11, 255))
    left, top = -BG_OFFSET[0], -BG_OFFSET[1]
    thumb.alpha_composite(scaled, (0, 0), (left, top, left + THUMB_SIZE, top + THUMB_SIZE))
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def file_entry(path, data=None):
    data = path.read_bytes() if data is None else data
    return {"name": path.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def build(check):
    errors = []
    stale = []
    themes = []

    for theme_dir in sorted(p for p in THEMES.iterdir() if p.is_dir()):
        tid = theme_dir.name
        if not ID_RE.match(tid):
            fail(errors, tid, "folder name must be lowercase letters, digits and dashes (max 40)")
            continue
        names = {p.name for p in theme_dir.iterdir() if not p.name.startswith(".")}
        allowed = set(THEME_PNGS + OPTIONAL_FILES + ["theme.json", THUMB])
        for extra in sorted(names - allowed):
            fail(errors, tid, f"unexpected file '{extra}' (allowed: {', '.join(sorted(allowed - {THUMB}))})")
        missing = [r for r in REQUIRED if r not in names]
        if missing:
            fail(errors, tid, f"missing {', '.join(missing)}")
            continue

        meta = load_meta(theme_dir, errors)
        if meta is None:
            continue
        check_images(theme_dir, errors)

        thumb = make_thumb(theme_dir)
        thumb_path = theme_dir / THUMB
        if not thumb_path.exists() or thumb_path.read_bytes() != thumb:
            stale.append(str(thumb_path.relative_to(ROOT)))
            if not check:
                thumb_path.write_bytes(thumb)

        files = []
        for name in ["theme.json"] + THEME_PNGS + OPTIONAL_FILES:
            p = theme_dir / name
            if p.exists():
                entry = file_entry(p)
                if entry["size"] > MAX_FILE_BYTES:
                    fail(errors, tid, f"{name} is {entry['size']} bytes (max {MAX_FILE_BYTES})")
                files.append(entry)
        total = sum(f["size"] for f in files)
        if total > MAX_THEME_BYTES:
            fail(errors, tid, f"theme is {total} bytes (max {MAX_THEME_BYTES})")

        entry = {"id": tid}
        entry.update({k: v for k, v in meta.items() if v})
        entry["thumb"] = file_entry(thumb_path, thumb)
        entry["size"] = total
        entry["files"] = files
        themes.append(entry)

    if errors:
        print("Theme problems:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    themes.sort(key=lambda t: t["name"].lower())
    index = json.dumps({"schema": SCHEMA, "themes": themes}, indent=2, ensure_ascii=False) + "\n"
    if not INDEX.exists() or INDEX.read_text(encoding="utf-8") != index:
        stale.append("index.json")
        if not check:
            INDEX.write_text(index, encoding="utf-8")

    print(f"{len(themes)} themes OK" + ("" if check else f", updated: {', '.join(stale) or 'nothing'}"))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate themes only; write nothing")
    sys.exit(build(ap.parse_args().check))
