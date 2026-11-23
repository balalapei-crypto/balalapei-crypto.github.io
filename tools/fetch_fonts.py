#!/usr/bin/env python3
"""Self-host Manrope (400/600) and Cormorant Garamond (500): download the latin
subset woff2 files from Google Fonts into static/fonts and write static/fonts.css.
Run once; the output is committed with the site."""
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "static", "fonts")
CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Manrope:wght@400;600&family=Cormorant+Garamond:wght@500&display=swap"
)
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60).read()


def main():
    os.makedirs(OUT, exist_ok=True)
    css = get(CSS_URL).decode("utf-8")
    blocks = re.findall(r"/\* (\S+) \*/\s*(@font-face \{.*?\})", css, re.S)
    result = []
    seen = set()
    for subset, block in blocks:
        if subset != "latin":
            continue
        family = re.search(r"font-family: '([^']+)'", block).group(1)
        weight = re.search(r"font-weight: ([^;]+);", block).group(1).strip()
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        fname = "%s-%s-latin.woff2" % (family.replace(" ", ""), weight.replace(" ", "-"))
        if fname in seen:
            continue
        seen.add(fname)
        with open(os.path.join(OUT, fname), "wb") as f:
            f.write(get(url))
        rng = re.search(r"unicode-range: ([^;]+);", block).group(1)
        result.append(
            "@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;"
            "src:url(fonts/%s) format('woff2');unicode-range:%s}" % (family, weight, fname, rng)
        )
        print("saved", fname)
    with open(os.path.join(OUT, "..", "fonts.css"), "w") as f:
        f.write("\n".join(result) + "\n")


if __name__ == "__main__":
    main()
