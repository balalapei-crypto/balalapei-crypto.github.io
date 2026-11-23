#!/usr/bin/env python3
"""Download Figma raw images into site/assets-src/<slug>/ and report their sizes.

Usage: python3 -I fetch_assets.py <slug> <id:ext> [<id:ext> ...]
The <id> is the UUID at the end of https://www.figma.com/api/mcp/asset/<id>
"""
import os
import struct
import sys
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets-src")


def png_size(b):
    return struct.unpack(">II", b[16:24])


def jpeg_size(b):
    i = 2
    while i < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        marker = b[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        seglen = struct.unpack(">H", b[i + 2:i + 4])[0]
        i += 2 + seglen
    return None


def gif_size(b):
    return struct.unpack("<HH", b[6:10])


def main():
    slug = sys.argv[1]
    out = os.path.join(ROOT, slug)
    os.makedirs(out, exist_ok=True)
    for n, spec in enumerate(sys.argv[2:], 1):
        uid, ext = spec.split(":")
        req = urllib.request.Request(
            "https://www.figma.com/api/mcp/asset/" + uid,
            headers={"User-Agent": "curl/8.7.1", "Accept": "*/*"},
        )
        data = urllib.request.urlopen(req, timeout=60).read()
        if len(data) < 100:
            print("EMPTY/EXPIRED:", spec, len(data))
            continue
        name = "raw_%02d.%s" % (n, ext)
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)
        size = None
        if ext == "png":
            size = png_size(data)
        elif ext == "jpg":
            size = jpeg_size(data)
        elif ext == "gif":
            size = gif_size(data)
        print(name, size, len(data))


if __name__ == "__main__":
    main()
