#!/usr/bin/env python3
"""產生 GitHub Pages 的附加檔案（僅使用 Python 標準函式庫）。

404 可能在任意深度的錯誤網址下送出，無法用 ../ 推算網站根目錄。
有 site_url 時，以絕對的 <base> 定位，再以相對 href 引用 style.css 與首頁；
沒有 site_url 時，不猜根目錄、不載入可能指錯的外部 CSS，顯示純文字返回指引。
內嵌 CSS 保留網站色彩、字型變數與備援字型，確保樣式載入失敗仍可閱讀。
本模組只產生檔案，不會修改 build.py，也不會連網。
"""

from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET


def _site_root(site_url):
    if site_url is None:
        return None
    parts = urlsplit(site_url)
    if (parts.scheme not in ("https", "http") or not parts.netloc
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or "\\" in site_url
            or any(unquote(p) in (".", "..") for p in parts.path.split("/"))):
        raise ValueError("site_url 必須是含完整網站子路徑的 http(s) 網址，不含查詢或片段。")
    return site_url.rstrip("/") + "/"


def _page_path(page):
    parts = urlsplit(page)
    if (parts.scheme or parts.netloc or parts.query or parts.fragment
            or page.startswith("/") or "\\" in page
            or any(unquote(p) in (".", "..") for p in page.split("/"))):
        raise ValueError("pages 必須是網站內相對路徑，例如 about/。")
    return quote(page, safe="/%-._~")


def write_extras(out_dir, site_url=None, pages=None):
    """覆寫 404.html、robots.txt、.nojekyll；有正式網址時另寫 sitemap.xml。

    site_url 例：https://peipei.github.io/peipei-portfolio/。
    pages 預設僅首頁；呼叫端應傳入所有實際公開頁面，例如 ["", "about/", "zaza/"]。
    未提供網址時會移除輸出資料夾中舊的 sitemap.xml，避免留下過期網址。
    """
    root = _site_root(site_url)
    paths = list(dict.fromkeys(_page_path(p) for p in ([""] if pages is None else pages)))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    head = ""
    if root:
        head = ('<base href="%s">\n<link rel="stylesheet" href="style.css">\n'
                % escape(root, quote=True))
        home = '<a class="home" href="./">回首頁 / Back to home</a>'
    else:
        home = '<p class="hint">返回首頁：請開啟你原本收到的作品集首頁網址。</p>'
    document = '''<!doctype html>
<!-- 404 的路徑取捨：有正式網址時以 base 固定根目錄，href 仍為相對路徑；
     未知正式網址時只顯示文字指引，避免深層錯誤路徑造成錯誤返回連結。 -->
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>404 — 找不到這個頁面 | Peipei</title>
%s<style>
body { margin: 0; min-height: 100vh; display: grid; place-items: center;
  background: #171bff; color: #fff;
  font: 400 18px/1.85 var(--sans, 'Manrope', system-ui, sans-serif); }
main { width: min(38rem, 100%%); box-sizing: border-box; padding: 48px 24px; }
h1 { margin: 0; color: #ffe546; font-weight: 500; line-height: 1;
  font-size: clamp(96px, 24vw, 180px);
  font-family: var(--serif, 'Cormorant Garamond', Georgia, serif); }
h2 { font-size: 26px; margin: 24px 0 12px; }
p { margin: 0 0 24px; }
a.home { display: inline-block; color: #ffe546; text-underline-offset: 6px; }
a:focus-visible { outline: 3px solid #ffe546; outline-offset: 6px; }
.hint { color: #ffe546; overflow-wrap: anywhere; }
</style>
</head>
<body><main>
<h1>404</h1>
<h2>這個頁面暫時找不到。</h2>
<p>網址可能有誤，或頁面已經搬家了。</p>
%s
</main></body>
</html>
''' % (head, home)
    (out / "404.html").write_text(document, encoding="utf-8")
    robots = "User-agent: *\nAllow: /\n"
    if root:
        robots += "\nSitemap: " + root + "sitemap.xml\n"
    (out / "robots.txt").write_text(robots, encoding="utf-8")
    (out / ".nojekyll").write_bytes(b"")
    sitemap = out / "sitemap.xml"
    if root:
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        ET.register_namespace("", namespace)
        tree = ET.Element("{%s}urlset" % namespace)
        for page in paths:
            item = ET.SubElement(tree, "{%s}url" % namespace)
            ET.SubElement(item, "{%s}loc" % namespace).text = root + page
        ET.ElementTree(tree).write(str(sitemap), encoding="utf-8", xml_declaration=True)
    elif sitemap.exists():
        sitemap.unlink()


if __name__ == "__main__":
    # 範例兼自測；所有輸出只存在臨時資料夾，結束時自動清除。
    with TemporaryDirectory(prefix="peipei-extras-") as temporary:
        out = Path(temporary)
        url = "https://peipei.github.io/peipei-portfolio/"
        pages = ["", "about/", "zaza/"]
        write_extras(out, site_url=url, pages=pages)
        first = {p.name: p.read_bytes() for p in out.iterdir()}
        write_extras(out, site_url=url, pages=pages)
        assert first == {p.name: p.read_bytes() for p in out.iterdir()}
        print("PASS：重複執行結果一致（覆寫成功）")
        assert set(first) == {"404.html", "robots.txt", "sitemap.xml", ".nojekyll"}
        assert (out / ".nojekyll").stat().st_size == 0
        print("PASS：產生 .nojekyll、404.html、robots.txt、sitemap.xml")
        html = (out / "404.html").read_text(encoding="utf-8")
        assert '<base href="' + url + '">' in html
        assert 'href="style.css"' in html and 'href="./"' in html
        print("PASS：404 使用正式網站 base，相對樣式與首頁連結可處理深層錯誤網址")
        locations = [element.text for element in ET.parse(out / "sitemap.xml").iter()
                     if element.tag.endswith("}loc")]
        assert locations == [url + page for page in pages]
        assert "Sitemap: " + url + "sitemap.xml" in (out / "robots.txt").read_text()
        print("PASS：sitemap 包含首頁、about/、zaza/，robots 指向正確 sitemap")
        write_extras(out)
        html = (out / "404.html").read_text(encoding="utf-8")
        assert '<base href=' not in html and '<a ' not in html
        assert 'href="style.css"' not in html
        assert not (out / "sitemap.xml").exists()
        assert "Sitemap:" not in (out / "robots.txt").read_text()
        print("PASS：未提供 site_url 時顯示純文字指引，並移除舊 sitemap")
        for bad_url, bad_pages in [("javascript:alert(1)", [""]), (url, ["../escape/"])]:
            try:
                write_extras(out, bad_url, bad_pages)
            except ValueError:
                pass
            else:
                raise AssertionError("應拒絕不合法網址或頁面路徑")
        print("PASS：拒絕不合法網站網址與跨出根目錄的頁面路徑")
    print("自測完成；臨時資料夾已清除。")
