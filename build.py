#!/usr/bin/env python3
"""Static site generator for the Peipei portfolio (Python 3 standard library + macOS sips).

    python3 -I build.py            # build into docs/
    python3 -I build.py --serve    # build, then serve docs/ at http://localhost:8000

Edit text in content/site.json, styles in static/style.css. Output: docs/ (GitHub Pages publishes from /docs).
Image sources live in assets-src/ (exported from the Figma design file).
"""
import html
import time
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "docs")
SRC = os.path.join(ROOT, "assets-src")
LOGO_DIR = "/Users/mac/Documents/作品集/logo-anim/final"
WIDTHS = (800, 1600, 2400)
NEEDS_ALPHA = {"logo-foundation"}  # the only PNG with real transparency
PLACEHOLDERS = "--placeholders" in sys.argv
BUILD_VERSION = int(time.time())
SITE_URL = "https://balalapei-crypto.github.io/"  # set to the live address (e.g. "https://name.github.io/peipei-portfolio/") before publishing


def esc(s):
    return html.escape(s, quote=True)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def sips_size(path):
    out = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path])
    return (
        int(re.search(r"pixelWidth: (\d+)", out).group(1)),
        int(re.search(r"pixelHeight: (\d+)", out).group(1)),
    )


def make_image(src_rel, slug, name):
    """Create resized JPEG variants under public/assets/<slug>/ and describe them."""
    src = os.path.join(SRC, src_rel)
    w, h = sips_size(src)
    # only images that really use transparency stay PNG (checked once with OpenCV); every other PNG becomes a much smaller JPEG
    alpha = name in NEEDS_ALPHA and src.lower().endswith(".png") and "hasAlpha: yes" in run(["sips", "-g", "hasAlpha", src])
    ext = "png" if alpha else "jpg"
    widths = sorted(set([x for x in WIDTHS if x < w] + [min(w, WIDTHS[-1])]))
    # drop a variant that is almost the same size as the next one up (e.g. 1600 next to 1680)
    widths = [x for i, x in enumerate(widths) if i == len(widths) - 1 or widths[i + 1] > x * 1.2]
    out_dir = os.path.join(PUBLIC, "assets", slug)
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for tw in widths:
        fname = "%s-%d.%s" % (name, tw, ext)
        out = os.path.join(out_dir, fname)
        if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
            cmd = ["sips", "-s", "format", "png"] if alpha else ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70" if tw >= 2000 else ("74" if tw >= 1200 else "80")]
            if tw != w:
                cmd += ["--resampleWidth", str(tw)]
            run(cmd + [src, "--out", out])
        files.append(("assets/%s/%s" % (slug, fname), tw))
    return {"w": w, "h": h, "files": files}


def video_asset(rel):
    """Copy a prepared web video / poster from assets-src to docs/assets; returns the site-relative path."""
    src = os.path.join(SRC, rel)
    dst = os.path.join(PUBLIC, "assets", rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        shutil.copyfile(src, dst)
    return "assets/" + rel


def video_tag(v, label, extra=""):
    """Muted looping video that starts when scrolled into view (see main.js); the poster shows until then."""
    return ('<video class="autovid" muted loop playsinline preload="none" poster="{PREFIX}%s" aria-label="%s" %s>'
            '<source src="{PREFIX}%s" type="video/mp4"></video>') % (
                video_asset(v["poster"]), esc(label), extra, video_asset(v["src"]))


def prepare_brand():
    out_dir = os.path.join(PUBLIC, "assets", "brand")
    os.makedirs(out_dir, exist_ok=True)
    gif = os.path.join(out_dir, "pe.gif")
    src_gif = os.path.join(LOGO_DIR, "pei_logo_face_final.gif")
    small = os.path.join(ROOT, "assets-src", "brand", "pe-small.gif")  # 176 px, recoloured and re-encoded: 0.3 MB instead of 1.7 MB
    if os.path.exists(small):
        if not os.path.exists(gif) or os.path.getmtime(gif) < os.path.getmtime(small):
            shutil.copyfile(small, gif)
    elif not os.path.exists(gif) or os.path.getmtime(gif) < max(os.path.getmtime(src_gif), os.path.getmtime(os.path.join(ROOT, "tools", "patch_gif.py"))):
        run([sys.executable, "-I", os.path.join(ROOT, "tools", "patch_gif.py"), src_gif, gif])
    still = os.path.join(out_dir, "pe-still.png")
    if not os.path.exists(still):
        run(["sips", "-s", "format", "png", "--resampleWidth", "256",
             os.path.join(LOGO_DIR, "still_logo_transparent_1080.png"), "--out", still])
    icon = os.path.join(out_dir, "favicon.png")
    if not os.path.exists(icon):
        run(["sips", "-s", "format", "png", "--resampleWidth", "128",
             os.path.join(LOGO_DIR, "still_logo_blue_1080.png"), "--out", icon])


RUNE_CARDS = "/Users/mac/Desktop/portfolio-website/runa-review/cards/%02d.png"


def prepare_cards(nums, width):
    """Rune card faces resized to `width`; returns site-relative paths."""
    out_dir = os.path.join(PUBLIC, "assets", "home")
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for n in nums:
        src = RUNE_CARDS % n
        out = os.path.join(out_dir, "rune-%02d-%d.jpg" % (n, width))
        if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
            run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", "--resampleWidth", str(width), src, "--out", out])
        paths.append("assets/home/rune-%02d-%d.jpg" % (n, width))
    return paths


COVER_SRC = "/Users/mac/Desktop/portfolio-website/content/home-tiles/hero-30-covers-support/source-slot-%02d.png"


def prepare_covers():
    """30 individual book covers (width 420) for the animated hero."""
    out_dir = os.path.join(PUBLIC, "assets", "home")
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for n in range(1, 31):
        src = COVER_SRC % n
        out = os.path.join(out_dir, "cover-%02d.jpg" % n)
        if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
            run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                 "--resampleWidth", "420", src, "--out", out])
        paths.append("assets/home/cover-%02d.jpg" % n)
    return paths


class Site:
    def __init__(self):
        with open(os.path.join(ROOT, "content", "site.json"), encoding="utf-8") as f:
            self.c = json.load(f)
        # drafts are only built for local previews (--placeholders), never for the published site
        self.projects = [p for p in self.c["projects"] if PLACEHOLDERS or not p.get("draft")]
        self.ready = [p for p in self.projects if p.get("ready")]

    # ---------- helpers ----------
    def href(self, prefix, target):
        if re.match(r"^(https?:|mailto:)", target):
            return target
        return prefix + target

    def ext_attrs(self, item):
        return ' target="_blank" rel="noopener"' if item.get("external") else ""

    def img_tag(self, slug, info, alt, sizes, eager=False):
        srcset = ", ".join("%s %dw" % (p, w) for p, w in info["files"])
        largest = info["files"][-1][0]
        return (
            '<img src="{src}" srcset="{ss}" sizes="{sz}" width="{w}" height="{h}" alt="{alt}" {load}>'
        ).format(
            src="{PREFIX}" + largest,
            ss=srcset.replace("assets/", "{PREFIX}assets/"),
            sz=sizes, w=info["w"], h=info["h"], alt=esc(alt),
            load='fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"',
        )

    # ---------- shared chrome ----------
    def header(self, current):
        def item_html(item, hidden):
            href = item["href"]
            if not re.match(r"^(https?:|mailto:)", href):
                href = "{PREFIX}" + href
            ext = self.ext_attrs(item)
            cur = ' aria-current="page"' if item["href"].strip("/") == current and not hidden else ""
            tab = ' tabindex="-1"' if hidden else ""
            return '<a href="%s"%s%s%s><span class="dot"></span>%s</a>' % (href, ext, cur, tab, esc(item["label"]))

        groups = ""
        for g in range(4):  # first group is the real nav, the rest only fill the loop
            hidden = g > 0
            inner = "".join(item_html(i, hidden) for i in self.c["nav"])
            groups += '<div class="marquee-group"%s>%s</div>' % (' aria-hidden="true"' if hidden else "", inner)
        return (
            '<header class="site-header">'
            '<a class="brand" href="{PREFIX}./" aria-label="Peipei, home">'
            '<img class="pe" src="{PREFIX}assets/brand/pe-still.png" width="88" height="88" alt="">'
            '<img class="pe pe-anim" src="{PREFIX}assets/brand/pe.gif?v=3" width="88" height="88" alt="" decoding="async"></a>'
            '<nav class="nav marquee" aria-label="Main"><div class="marquee-track">' + groups + '</div></nav>'
            '</header>'
        )

    def footer(self):
        return '<footer class="site-footer">%s</footer>' % esc(self.c["site"]["footer"])

    def page(self, depth, title, desc, body, body_class="", current=""):
        prefix = "../" * depth
        doc = (
            '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>%s</title>\n<meta name="description" content="%s">\n'
            '<meta name="theme-color" content="#171bff">\n'
            '<meta property="og:title" content="%s">\n<meta property="og:description" content="%s">\n'
            '<meta property="og:type" content="website">\n'
            '<link rel="icon" href="{PREFIX}assets/brand/favicon.png">\n'
            '<link rel="stylesheet" href="{PREFIX}style.css?v={VER}">\n</head>\n'
            '<body class="%s">\n<a class="skip-link" href="#main">Skip to content</a>\n%s\n'
            '<main id="main">\n%s\n</main>\n%s\n<script src="{PREFIX}main.js?v={VER}" defer></script>\n</body>\n</html>\n'
        ) % (esc(title), esc(desc), esc(title), esc(desc), body_class,
             self.header(current), body, self.footer())
        return doc.replace("{PREFIX}", prefix).replace("{VER}", str(BUILD_VERSION))

    # ---------- pages ----------
    def covers_media(self, covers, alt):
        books = ""
        for i in range(5):
            books += ('<span class="book"><img class="on" src="{PREFIX}%s" alt="" width="420" height="668" %s>'
                      '<img class="off" alt="" width="420" height="668" aria-hidden="true"></span>') % (
                          covers[(i * 6) % len(covers)], 'fetchpriority="high"' if i == 0 else "")
        return '<span class="media covers" data-covers="%s" role="img" aria-label="%s">%s</span>' % (
            ",".join("{PREFIX}" + c for c in covers), esc(alt), books)

    def flatlay_cells(self, slug, cards, box_src, center=7, box_pos="50% 55%"):
        box = make_image(box_src, slug, "flatlay-box")
        out = ""
        k = 0
        for idx in range(15):
            if idx == center:
                out += ('<span class="fl-box"><img src="{PREFIX}%s" alt="" width="%d" height="%d" '
                        'style="object-position:%s" loading="lazy"></span>') % (box["files"][0][0], box["w"], box["h"], box_pos)
            else:
                out += '<span class="fl-card"><img src="{PREFIX}%s" alt="" width="320" height="435" loading="lazy"></span>' % cards[k % len(cards)]
                k += 1
        return out

    def comp_html(self, slug, c):
        """CSS-built composition of card faces: flatlay, fan, row or grid."""
        kind = c["kind"]
        ar_w, ar_h = [float(x) for x in c.get("aspect", "4/3").split("/")]
        r = ar_w / ar_h
        cards = prepare_cards(c["cards"], 480 if kind != "flatlay" else 320)
        inner = ""
        card = lambda src, style: '<span class="cf-card" style="%s"><img src="{PREFIX}%s" alt="" width="480" height="652" loading="lazy"></span>' % (style, src)
        if kind == "flatlay":
            inner = '<span class="fl-grid">%s</span>' % self.flatlay_cells(slug, cards, c["box"]["src"], c.get("center", 7), c["box"].get("pos", "50% 55%"))
        elif kind == "fan":
            n = len(cards)
            w = c.get("w", 24)
            spread = c.get("spread", 76)
            for i, src in enumerate(cards):
                ang = -spread / 2 + spread * i / (n - 1)
                inner += card(src, "--w:%s%%;--x:%s%%;--y:%s%%;--r:%.1fdeg;--o:50%% 170%%;z-index:%d" % (w, 50 - w / 2, c.get("y", 8), ang, i))
        else:  # row / grid
            cols = c.get("cols", len(cards))
            rows = (len(cards) + cols - 1) // cols
            w, gx, gy = c.get("w", 24), c.get("gx", 3), c.get("gy", 3)
            h = w * r / 0.736
            x0 = (100 - (cols * w + (cols - 1) * gx)) / 2
            y0 = (100 - (rows * h + (rows - 1) * gy)) / 2
            tilts = c.get("tilts", [0] * len(cards))
            for i, src in enumerate(cards):
                cx, cy = i % cols, i // cols
                inner += card(src, "--w:%s%%;--x:%.2f%%;--y:%.2f%%;--r:%sdeg" % (w, x0 + cx * (w + gx), y0 + cy * (h + gy), tilts[i % len(tilts)]))
        bg = ";background:%s" % c["bg"] if c.get("bg") else ""
        return '<span class="comp %s" style="--ar:%s%s" role="img" aria-label="%s">%s</span>' % (kind, c.get("aspect", "4/3"), bg, esc(c["alt"]), inner)

    def home(self):
        h = self.c["home"]
        by_slug = {p["slug"]: p for p in self.projects}
        slots = list(h["slots"])
        covers = prepare_covers()[:29]  # slot 30 (India) is blank on the original, so it stays out of the rotation
        rows = ""
        n = 0
        for row in h["layout"]:
            cells = ""
            # tiles that will really be shown in this row (drafts and unfinished works are left out of a published build)
            entries = []
            for span in row["cols"]:
                slug = slots[n] if n < len(slots) else None
                n += 1
                p = by_slug.get(slug)
                if p and (p.get("ready") or PLACEHOLDERS):
                    entries.append([span, p])
            adapted = 0 < len(entries) < len(row["cols"]) and not row.get("hero")
            if adapted:  # a tile is missing: share the row evenly instead of leaving a hole
                share = 6 if len(entries) == 1 else 12 // len(entries)
                for e in entries:
                    e[0] = share
            for span, p in entries:
                img = p.get("cover") or p.get("hero")
                is_hero = bool(row.get("hero")) and p.get("hero_covers")
                cls = "tile" + (" feature" if row.get("hero") else "") + (" fill" if not adapted and ((row.get("fill") and span == 8) or row.get("fill_span") == span) else "")
                style = "grid-column:span %d;--ar:%s" % (span, row["aspect"])
                caption = esc(p["card_title"]) + (" | " + esc(p["tag"]) if p.get("tag") else "")
                label = '<span class="label">%s</span>' % caption
                linked = p.get("ready")
                open_tag = ('<a class="%s" style="%s" href="{PREFIX}%s/">' % (cls, style, p["slug"])) if linked \
                    else ('<div class="%s" style="%s">' % (cls, style))
                close_tag = "</a>" if linked else "</div>"
                if is_hero:
                    cells += open_tag + self.covers_media(covers, img["alt"]) + label + close_tag
                elif p.get("cover_video"):
                    cv = p["cover_video"]
                    media = '<span class="media">%s</span>' % video_tag(cv, cv["alt"])
                    cells += open_tag + media + label + close_tag
                elif p.get("cover_comp"):
                    media = '<span class="media">%s</span>' % self.comp_html(p["slug"], p["cover_comp"])
                    cells += open_tag + media + label + close_tag
                elif p.get("flatlay"):
                    cfg = p["flatlay"]
                    cards = prepare_cards(cfg["cards"], 320)
                    media = '<span class="media flatlay" role="img" aria-label="%s"><span class="fl-grid">%s</span></span>' % (
                        esc(cfg["alt"]), self.flatlay_cells(p["slug"], cards, cfg["box"]["src"], cfg.get("center", 7), cfg["box"].get("pos", "50% 55%")))
                    cells += open_tag + media + label + close_tag
                elif img:
                    info = make_image(img["src"], p["slug"], "cover")
                    sizes = "(min-width: 900px) %dvw, 100vw" % (round(span / 12 * 100))
                    tag = self.img_tag(p["slug"], info, "", sizes, eager=(n == 1))
                    if p.get("cover_padded"):
                        cells += open_tag + '<span class="media padded" style="background:%s">%s</span>' % (p["cover_padded"], tag) + label + close_tag
                    else:
                        cells += open_tag + '<span class="media">' + tag + "</span>" + label + close_tag
                elif PLACEHOLDERS:
                    cells += '<div class="%s empty" style="%s"><span class="media"><span class="no">%02d</span></span>%s</div>' % (
                        cls, style, n, label)
            if cells:
                rows += '<div class="home-row">%s</div>' % cells
        body = '<h1 class="sr-only">%s — %s</h1><section class="home-grid" aria-label="Work">%s</section>' % (
            esc(self.c["site"]["owner"]), esc(self.c["about"]["subtitle"]), rows)
        return self.page(0, self.c["site"]["title"], self.c["site"]["description"], body, "page-home")

    def about(self):
        a = self.c["about"]
        links = "".join('<a href="%s"%s>%s</a>' % (l["href"], self.ext_attrs(l), esc(l["label"])) for l in a["links"])
        bio = "".join("<p>%s</p>" % esc(t) for t in a["bio"])

        def section(title, rows, area):
            out = '<section class="about-section s-%s"><h2>%s</h2>' % (area, esc(title))
            for r in rows:
                d = r["detail"]
                d = "<br>".join(esc(x) for x in d) if isinstance(d, list) else esc(d)
                t = esc(r["title"])
                if r.get("href"):
                    t = '<a href="{PREFIX}%s">%s</a>' % (r["href"], t)
                out += '<div class="row"><div class="t">%s</div>%s</div>' % (t, ('<div class="d">%s</div>' % d) if d else "")
            return out + "</section>"

        if a.get("photo"):
            info = make_image(a["photo"], "about", "portrait")
            photo = '<figure class="portrait">%s</figure>' % self.img_tag(
                "about", info, "Chian-Pei Yang smiling in a green dress, with a pink sunset sky behind her", "(min-width: 900px) 340px, 100vw", True)
        else:
            photo = '<div class="portrait" role="img" aria-label="Portrait photo (to be added)">Portrait photo</div>'
        role = ('<p class="role">%s</p>' % esc(a["current_role"])) if a.get("current_role") else ""
        body = (
            '<div class="about-main">'
            '<div class="ag-head"><h1>%s<br>%s</h1><p class="name">%s</p><p class="sub">%s</p>%s</div>'
            '<div class="ag-bio bio">%s</div>%s%s%s%s</div>'
        ) % (esc(a["tagline"][0]), esc(a["tagline"][1]), esc(a["name"]), esc(a["subtitle"]), role, bio, photo,
             section("Education", a["education"], "ed"), section("Experience", a["experience"], "exp"),
             section("Current projects", a["projects"], "proj") if a.get("projects") else "")
        return self.page(1, "About — " + self.c["site"]["title"], self.c["site"]["description"],
                         body, "page-about", current="about")

    def figure(self, slug, im, kind, width=None, sizes=None, eager=False, crop=None):
        info = make_image(im["src"], slug, im["name"])
        tag = self.img_tag(slug, info, im["alt"], sizes or "(min-width: 1280px) 1184px, 100vw", eager)
        if crop:
            tag = tag.replace("<img ", '<img style="aspect-ratio:%s;object-fit:cover" ' % crop, 1)
        style = ' style="width:%s%%"' % width if width else ""
        return "<figure%s>%s</figure>" % (style, tag)

    def project(self, p):
        slug = p["slug"]
        title = (" " if p.get("title_size") == "line" else "<br>").join(esc(t) for t in p["title"])
        small = {"sm": " title-sm", "md": " title-md", "line": " title-line"}.get(p.get("title_size"), "")
        status = '<p class="status">%s</p>' % esc(p["status"]) if p.get("status") else ""
        body = (
            '<div class="backlink"><a href="{PREFIX}./">&larr; All work</a></div>'
            '<section class="project-head"><h1 class="%s">%s</h1><div class="intro">%s<p>%s</p>'
            '<p class="meta">%s</p></div></section>'
        ) % (small.strip(), title, status, esc(p["intro"]), esc(p["meta"]))

        if p.get("hero"):
            h = p["hero"]
            body += '<section class="hero">%s</section>' % self.figure(
                slug, h, "hero", width=h.get("width"), eager=True, crop=h.get("crop"))
        if p.get("hero_covers"):
            body += '<section class="hero hero-covers">%s</section>' % self.covers_media(
                prepare_covers()[:29], "Thirty book covers, one for each country, changing one at a time")

        paras = "".join("<p>%s</p>" % esc(t) for t in p["about"])
        role = "".join('<div><strong>%s</strong> — %s</div>' % (esc(k), esc(v)) for k, v in p.get("role", []))
        info = (
            '<section class="info"><h2>%s<br>%s</h2><div class="body">%s<div class="small-lines">%s</div></div></section>'
        ) % (esc(p["about_heading"][0]), esc(p["about_heading"][1]), paras, role)

        blocks = list(p["blocks"])
        if not any(x["type"] == "info" for x in blocks):
            blocks.insert(0, {"type": "info"})
        for blk in blocks:
            t = blk["type"]
            if t == "info":
                body += info
            elif t == "intro":
                body += '<section class="block intro"><h2>%s</h2>%s</section>' % (esc(blk["heading"]), ("<p>%s</p>" % esc(blk["text"])) if blk.get("text") else "")
            elif t == "panel":
                im = blk["image"]
                info = make_image(im["src"], slug, im["name"])
                tag = self.img_tag(slug, info, im["alt"], "(min-width: 900px) 480px, 60vw")
                body += '<section class="block panel" style="margin-top:%dpx"><div class="panel-box" style="background:%s;--ar:%s">%s</div></section>' % (
                    blk.get("mt", 32), blk.get("bg", "#ffffff"), blk.get("aspect", "1184 / 360"), tag)
            elif t == "cardgrid":
                nums = blk["cards"]
                cards = prepare_cards(nums, 320)
                cells = "".join('<span class="cg-card"><img src="{PREFIX}%s" alt="Rune card %d" width="320" height="435" loading="lazy"></span>' % (src, n)
                                for n, src in zip(nums, cards))
                body += '<section class="block cardgrid" style="margin-top:%dpx">%s</section>' % (blk.get("mt", 32), cells)
            elif t == "video":
                body += ('<section class="block vidblock%s" style="margin-top:%dpx"><figure style="--ar:%s">%s</figure></section>' % (
                    " bleed" if blk.get("bleed") else "", blk.get("mt", 32), blk.get("aspect", "16 / 9"), video_tag(blk, blk["label"])))
            elif t == "devices":
                lp, ph = blk["laptop"], blk.get("phone")
                phone = ('<figure class="phone"><div class="pscreen" style="--ar:%s">%s</div><i class="island"></i></figure>' % (
                    ph["aspect"], video_tag(ph, ph["label"]))) if ph else ""
                body += (
                    '<section class="block devices%s" style="margin-top:%dpx"><div class="stage">'
                    '<figure class="laptop"><div class="lid"><div class="lscreen" style="--ar:%s">%s</div><i class="cam"></i></div><div class="lbase"><i></i></div></figure>%s</div></section>') % (
                        "" if ph else " solo", blk.get("mt", 48), lp["aspect"], video_tag(lp, lp["label"]), phone)
            elif t == "flipcal":
                pages = []
                for k, im in enumerate(blk["images"]):
                    finfo = make_image(im["src"], slug, im["name"])
                    tag = self.img_tag(slug, finfo, im["alt"], "(min-width: 900px) 760px, 78vw")
                    pages.append(('<div class="fpage%s"%s><div class="ffront">%s</div>'
                                  '<div class="fback" aria-hidden="true"></div></div>') % (
                        " is-current" if k == 0 else "", ' aria-hidden="true"' if k else "", tag))
                body += ('<section class="block flipcal-block" style="margin-top:%dpx">'
                         '<div class="flipcal" data-flipcal style="--desk:%s;--ar:%s">'
                         '<div class="cal" style="--pa:%s;--cw:%s%%">'
                         '<div class="cal-rear" aria-hidden="true"></div><div class="cal-side" aria-hidden="true"></div>'
                         '<div class="cal-front" aria-hidden="true"></div><div class="cal-edges" aria-hidden="true"></div>'
                         '<div class="fstack">%s</div><div class="cal-rings" aria-hidden="true">%s</div>'
                         '</div></div></section>') % (
                    blk.get("mt", 32), blk.get("bg", "#f7f6f1"), blk.get("aspect", "1184 / 890"),
                    blk.get("page", "748 / 578"), blk.get("cw", 49), "".join(pages), "<i></i>" * 22)
            elif t == "carousel":
                slides = ""
                for k, im in enumerate(blk["images"]):
                    cinfo = make_image(im["src"], slug, im["name"])
                    tag = self.img_tag(slug, cinfo, im["alt"], "(min-width: 900px) 80vw, 100vw")
                    slides += '<figure class="slide%s">%s</figure>' % (" on" if k == 0 else "", tag)
                dots = "".join('<button type="button" aria-label="Show photo %d"%s></button>' % (
                    k + 1, ' class="on"' if k == 0 else "") for k in range(len(blk["images"])))
                body += ('<section class="block carousel-block" style="margin-top:%dpx"><div class="carousel" data-carousel style="--ar:%s">'
                         '%s<div class="dots">%s</div></div></section>') % (blk.get("mt", 32), blk.get("aspect", "3 / 2"), slides, dots)
            elif t == "stack":
                nums = blk["cards"]
                cards = prepare_cards(nums, 480)
                n = len(nums)
                spread = blk.get("spread", 62)
                cells = "".join(
                    '<span class="scard" style="--a:%.1fdeg;z-index:%d"><span class="face"><img src="{PREFIX}%s" alt="Rune card %d" width="480" height="652" loading="lazy"></span></span>' % (
                        -spread / 2 + spread * k / (n - 1), k, src, num)
                    for k, (num, src) in enumerate(zip(nums, cards)))
                body += '<section class="block stack-block" style="margin-top:%dpx"><div class="stack" data-stack>%s</div></section>' % (
                    blk.get("mt", 32), cells)
            elif t == "swatches":
                sw = "".join('<div class="swatch"><span class="chip" style="background:%s"></span><span class="swlabel">%s&nbsp; %s</span></div>' % (
                    s["hex"], esc(s["name"]), esc(s["hex"].upper())) for s in blk["items"])
                body += '<section class="block swatches" style="margin-top:%dpx">%s</section>' % (blk.get("mt", 56), sw)
            elif t == "mock":
                ims = "".join('<span class="mock-im" style="width:%s%%">%s</span>' % (
                    im["w"], self.img_tag(slug, make_image(im["src"], slug, im["name"]), im["alt"], blk.get("sizes", "(min-width: 900px) 640px, 60vw"))) for im in blk["images"])
                body += '<section class="block mock" style="margin-top:%dpx"><div class="mock-box%s" style="background:%s;--ar:%s;--gap:%s%%">%s</div></section>' % (
                    blk.get("mt", 32), " shadow" if blk.get("shadow") else "", blk.get("bg", "#eceae0"), blk.get("aspect", "1184 / 640"), blk.get("gap", 6.1), ims)
            elif blk.get("comp"):
                body += '<section class="block wide" style="margin-top:%dpx"><figure style="width:%s%%">%s</figure></section>' % (
                    blk.get("mt", 32), blk.get("width", 81), self.comp_html(slug, blk["comp"]))
            else:
                n = len(blk["images"])
                sizes = {"wide": "(min-width: 1280px) 960px, 100vw", "offset": "(min-width: 1280px) 983px, 100vw"}.get(
                    t, "(min-width: 900px) %dvw, 100vw" % round(100 / n))
                figs = "".join(self.figure(slug, im, t, width=blk.get("width") if t in ("wide", "offset") else None, sizes=sizes)
                               for im in blk["images"])
                cols = ' style="margin-top:%dpx;--cols:%d"' % (blk.get("mt", 32), n) if t in ("pair", "row") \
                    else ' style="margin-top:%dpx"' % blk.get("mt", 32)
                body += '<section class="block %s"%s>%s</section>' % ("row" if t in ("pair", "row") else t, cols, figs)

        def lines(rows):
            return "".join('<div><strong>%s</strong> — %s</div>' % (esc(k), esc(v)) for k, v in rows)

        body += '<section class="credits"><div>%s</div><div>%s</div></section>' % (
            lines(p["credits"]["left"]), lines(p["credits"]["right"]))

        i = self.ready.index(p)
        prev = self.ready[i - 1] if i > 0 else None
        nxt = self.ready[i + 1] if i + 1 < len(self.ready) else None
        if prev or nxt:
            body += '<nav class="prevnext" aria-label="Projects">'
            if prev:
                body += '<a class="prev" href="{PREFIX}%s/">&larr; Previous</a>' % prev["slug"]
            if nxt:
                body += '<a class="next" href="{PREFIX}%s/">Next: %s &rarr;</a>' % (nxt["slug"], esc(nxt["card_title"]))
            body += "</nav>"
        return self.page(1, "%s — %s" % (p["card_title"], self.c["site"]["name"]), p["description"], body,
                         "page-project" + (" page-dark" if p.get("dark") else ""))


def prune_assets():
    """Delete files in docs/assets that no page, stylesheet or script refers to (leftovers from earlier builds)."""
    refs = set()
    for dirpath, _, names in os.walk(PUBLIC):
        for n in names:
            if n.endswith((".html", ".css", ".js")):
                with open(os.path.join(dirpath, n), encoding="utf-8", errors="ignore") as f:
                    refs.update(re.findall(r"assets/[^\"'\s,)?#]+", f.read()))
    removed = 0
    base = os.path.join(PUBLIC, "assets")
    for dirpath, _, names in os.walk(base):
        for n in names:
            rel = "assets/" + os.path.relpath(os.path.join(dirpath, n), base).replace(os.sep, "/")
            if rel not in refs:
                os.remove(os.path.join(dirpath, n))
                removed += 1
    for dirpath, dirs, names in os.walk(base, topdown=False):
        if not os.listdir(dirpath):
            os.rmdir(dirpath)
    print("pruned %d unused asset files" % removed)


def purge_drafts():
    """A production build removes any draft page (and its media) left behind by an earlier preview build."""
    with open(os.path.join(ROOT, "content", "site.json"), encoding="utf-8") as f:
        projects = json.load(f)["projects"]
    live = {p["slug"] for p in projects if not p.get("draft")}
    for p in projects:
        if not p.get("draft"):
            continue
        folders = {p["slug"]}
        text = json.dumps(p)
        for m in re.finditer(r'"(?:src|poster)": "([^/"]+)/', text):
            folders.add(m.group(1))
        shutil.rmtree(os.path.join(PUBLIC, p["slug"]), ignore_errors=True)
        for fo in folders - live:
            shutil.rmtree(os.path.join(PUBLIC, "assets", fo), ignore_errors=True)
            print("removed draft media", fo)


def write(rel, content):
    path = os.path.join(PUBLIC, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", rel)


def main():
    os.makedirs(PUBLIC, exist_ok=True)
    prepare_brand()
    site = Site()
    if not PLACEHOLDERS:
        purge_drafts()
    # static files
    css = open(os.path.join(ROOT, "static", "fonts.css"), encoding="utf-8").read()
    css += open(os.path.join(ROOT, "static", "style.css"), encoding="utf-8").read()
    write("style.css", css)
    shutil.copy(os.path.join(ROOT, "static", "main.js"), os.path.join(PUBLIC, "main.js"))
    shutil.copytree(os.path.join(ROOT, "static", "fonts"), os.path.join(PUBLIC, "fonts"), dirs_exist_ok=True)
    write("index.html", site.home())
    write("about/index.html", site.about())
    for p in site.ready:
        write("%s/index.html" % p["slug"], site.project(p))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from extras import write_extras
    pages = [""] + ["about/"] + ["%s/" % p["slug"] for p in site.ready]
    write_extras(PUBLIC, site_url=SITE_URL, pages=pages)
    prune_assets()
    if "--serve" in sys.argv:
        os.chdir(PUBLIC)
        os.execvp("python3", ["python3", "-m", "http.server", "8000"])


if __name__ == "__main__":
    main()
