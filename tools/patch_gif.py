#!/usr/bin/env python3
"""Recolour the Pe GIF's background to the exact site blue by editing its colour tables.

The exported GIF background is rgb(17,26,255); the site blue is #171bff = rgb(23,27,255).
Palette entries within a few steps of the old background are rewritten, so the animation
blends into the header with no visible square. Pixel data is untouched.

The last frame's delay is extended by HOLD_LAST centiseconds, so the face rests a moment
before the loop returns to the start.

Usage: python3 -I patch_gif.py <in.gif> <out.gif>
"""
import struct
import sys

OLD = (17, 26, 255)
NEW = (23, 27, 255)
TOL = 8
HOLD_LAST = 100  # +1 second on the last frame


def patch_table(data, pos, n):
    changed = 0
    for i in range(pos, pos + n, 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        if abs(r - OLD[0]) <= TOL and abs(g - OLD[1]) <= TOL and abs(b - OLD[2]) <= 12:
            data[i], data[i + 1], data[i + 2] = NEW
            changed += 1
    return changed


def skip_subblocks(data, pos):
    while data[pos] != 0:
        pos += data[pos] + 1
    return pos + 1


def patch(src, dst):
    data = bytearray(open(src, "rb").read())
    assert data[:3] == b"GIF", "not a GIF"
    flags = data[10]
    pos = 13
    changed = 0
    last_gce = None
    if flags & 0x80:
        n = 3 * (2 ** ((flags & 7) + 1))
        changed += patch_table(data, pos, n)
        pos += n
    while pos < len(data):
        b = data[pos]
        if b == 0x21:  # extension
            if data[pos + 1] == 0xF9:
                last_gce = pos
            pos = skip_subblocks(data, pos + 2)
        elif b == 0x2C:  # image
            f = data[pos + 9]
            pos += 10
            if f & 0x80:
                n = 3 * (2 ** ((f & 7) + 1))
                changed += patch_table(data, pos, n)
                pos += n
            pos += 1  # LZW minimum code size
            pos = skip_subblocks(data, pos)
        elif b == 0x3B:
            break
        else:
            raise ValueError("unexpected byte 0x%02x at %d" % (b, pos))
    if last_gce is not None and HOLD_LAST:
        delay = data[last_gce + 4] | (data[last_gce + 5] << 8)
        delay = min(delay + HOLD_LAST, 65535)
        data[last_gce + 4], data[last_gce + 5] = delay & 255, delay >> 8
    open(dst, "wb").write(data)
    return changed


if __name__ == "__main__":
    print("palette entries changed:", patch(sys.argv[1], sys.argv[2]))
