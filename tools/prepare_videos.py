#!/usr/bin/env python3
"""Compress screen recordings into small web videos (H.264 mp4) plus a poster image each.

Uses the macOS tools avconvert, qlmanage and sips only. Output goes to assets-src/<slug>/.
Source recordings stay outside the site folder and are never uploaded.

Usage: python3 -I prepare_videos.py            # converts every entry of JOBS that is missing
       python3 -I prepare_videos.py --force    # rebuild all
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets-src", "migrant-voice")
SRC = "/Users/mac/Documents/作品集/移工之聲網站"

# name, source file, preset, start (s), duration (s or None)
JOBS = [
    ("entrance", "入口動畫.mov", "Preset1280x720", None, None),
    ("home", "首頁.mov", "Preset1280x720", 0.0, 5.4),  # stops before the face-to-face portrait strip scrolls into view (~5.8 s)
    ("wall", "攝影牆.mov", "Preset1280x720", None, None),
    ("mobile", "手機版.mov", "Preset960x540", None, None),
    ("wall-loop", "攝影牆.mov", "Preset960x540", 2.0, 4.0),  # short loop for the home tile
]


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def poster(mp4, jpg):
    tmp = tempfile.mkdtemp()
    try:
        run(["qlmanage", "-t", "-s", "1600", "-o", tmp, mp4])
        png = os.path.join(tmp, os.path.basename(mp4) + ".png")
        run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80", png, "--out", jpg])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    for name, src, preset, start, dur in JOBS:
        mp4 = os.path.join(OUT, name + ".mp4")
        jpg = os.path.join(OUT, name + ".jpg")
        if force or not os.path.exists(mp4):
            cmd = ["avconvert", "--preset", preset, "--source", os.path.join(SRC, src), "--output", mp4, "--replace"]
            if start is not None:
                cmd += ["--start", str(start)]
            if dur is not None:
                cmd += ["--duration", str(dur)]
            run(cmd)
        if force or not os.path.exists(jpg):
            poster(mp4, jpg)
        print("%-10s %6.1f MB  %s" % (name, os.path.getsize(mp4) / 1e6, jpg))


if __name__ == "__main__":
    main()
