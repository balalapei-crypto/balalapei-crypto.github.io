#!/usr/bin/env python3
"""Rename downloaded Figma raw images (raw_NN.ext) to their layer names by fingerprint.

Fingerprint = (byte length, sampled checksum) computed by the same formula inside Figma:
    s = 0; for i in range(0, len(b), 97): s = (s + b[i] * ((i % 251) + 1)) % 4294967291

Usage: python3 -I match_assets.py <slug> < fingerprints.json
  fingerprints.json = [{"n": "layer-name", "len": 12345, "sum": 67890}, ...]
Files that match nothing (the Pe logo) are left as raw_NN.ext.
"""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets-src")


def fingerprint(b):
    s = 0
    for i in range(0, len(b), 97):
        s = (s + b[i] * ((i % 251) + 1)) % 4294967291
    return len(b), s


def main():
    slug = sys.argv[1]
    wanted = json.load(sys.stdin)
    folder = os.path.join(ROOT, slug)
    by_fp = {}
    for w in wanted:
        by_fp.setdefault((w["len"], w["sum"]), []).append(w["n"])
    matched = set()
    for path in sorted(glob.glob(os.path.join(folder, "raw_*"))):
        data = open(path, "rb").read()
        names = by_fp.get(fingerprint(data))
        ext = os.path.splitext(path)[1]
        if names:
            name = names[0]
            os.rename(path, os.path.join(folder, name + ext))
            matched.add(name)
            print("matched", os.path.basename(path), "->", name + ext)
        else:
            print("no match (logo?)", os.path.basename(path))
    missing = [w["n"] for w in wanted if w["n"] not in matched]
    if missing:
        print("NOT FOUND:", missing)


if __name__ == "__main__":
    main()
