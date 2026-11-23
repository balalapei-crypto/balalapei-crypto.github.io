#!/usr/bin/env python3
"""離線、唯讀的上線檢查。Python 3.9+；python3 -I check_site.py [public]

結束碼：0 = 無 FAIL（允許 WARN）；1 = 檢查失敗；2 = 參數錯誤。
MB 採十進位（1 MB = 1,000,000 bytes）。不執行 JS、不請求外部網址。
"""

import argparse
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


DEFAULT_PUBLIC = Path('/Users/mac/Desktop/portfolio-website/site/docs')
LARGE_FILE_BYTES = 1_500_000
# 已知動畫：仍列 WARN，白名單僅補充原因，不隱藏超標。
KNOWN_LARGE = {'assets/brand/pe.gif': '已知品牌動畫，約 1.7 MB'}
FOOTER = '© Peipei Yang 2026'
CSS_TOKEN = re.compile(
    r'/\*.*?\*/|url\(\s*(?:"(?:\\.|[^"\\])*"|'
    r"'(?:\\.|[^'\\])*'|(?:\\.|[^)\\])*)\s*\)|"
    r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|'
    r'@font-face\b|[{}]', re.I | re.S)
CSS_ESCAPE = re.compile(r'\\([0-9a-fA-F]{1,6}\s?|\r\n|[\n\r\f]|.)', re.S)


def css_unescape(value):
    def replace(match):
        token = match.group(1)
        if token[0] in '\r\n\f':
            return ''
        if re.fullmatch(r'[0-9a-fA-F]{1,6}\s?', token):
            code = int(token.strip(), 16)
            return chr(code) if 0 < code <= 0x10ffff else '\ufffd'
        return token
    return CSS_ESCAPE.sub(replace, value)


def srcset_urls(value):
    """按 HTML srcset 候選項切分，保留 URL 內逗號（如 data URL）。"""
    pos = 0
    while pos < len(value):
        while pos < len(value) and (value[pos].isspace() or value[pos] == ','):
            pos += 1
        start = pos
        while pos < len(value) and not value[pos].isspace():
            pos += 1
        url = value[start:pos]
        if not url:
            break
        yield url.rstrip(',')
        if url.endswith(','):
            continue
        depth = 0
        while pos < len(value):
            char = value[pos]
            pos += 1
            if char == '(':
                depth += 1
            elif char == ')':
                depth = max(0, depth - 1)
            elif char == ',' and depth == 0:
                break


class Checker:
    def __init__(self, root):
        self.root = root.resolve()
        self.counts = Counter()
        self.external = defaultdict(set)
        self.anchors = 0

    def location(self, path, line=None):
        try:
            label = str(path.relative_to(self.root)) or '.'
        except ValueError:
            label = str(path)
        return '{}:{}'.format(label, line) if line else label

    def report(self, status, path, message, line=None):
        self.counts[status] += 1
        print('{} [{}] {}'.format(status, self.location(path, line), message))

    def require(self, condition, path, message, line=None):
        self.report('PASS' if condition else 'FAIL', path, message, line)

    def reference(self, path, line, url, kind):
        url = url.strip()
        if url.startswith('/'):
            self.report('FAIL', path, '{} 使用絕對路徑：{}'.format(kind, url), line)
            if url.startswith('//'):
                self.external[url].add(self.location(path, line))
            return False
        if url.startswith('#'):
            self.anchors += 1
            return True
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            self.report('FAIL', path, '{} 無效 URL：{} ({})'.format(kind, url, exc), line)
            return False
        if parsed.scheme or parsed.netloc:
            # data/blob 是內嵌或執行期資源，沒有可檢查的磁碟檔案。
            if parsed.scheme.lower() not in ('data', 'blob'):
                self.external[url].add(self.location(path, line))
            if parsed.scheme.lower() == 'javascript':
                self.report('WARN', path, '{} 無法靜態驗證：{}'.format(kind, url), line)
            return True
        decoded = unquote(parsed.path)
        if decoded.startswith('/'):
            self.report('FAIL', path, '{} 解碼後為絕對路徑：{}'.format(kind, url), line)
            return False
        target = (path.parent / decoded).resolve() if decoded else path
        try:
            target.relative_to(self.root)
        except ValueError:
            self.report('FAIL', path, '{} 指向 public 外：{}'.format(kind, url), line)
            return False
        if target.is_dir():
            target = (target / 'index.html').resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            self.report('FAIL', path, '{} index.html 指向 public 外：{}'.format(kind, url), line)
            return False
        if not target.is_file():
            self.report('FAIL', path, '{} 找不到檔案：{} → {}'.format(
                kind, url, self.location(target)), line)
            return False
        return True

    def css(self, path, text, first_line=1):
        checked = 0
        failed = 0
        fonts = 0
        font_failed = 0
        depth = 0
        font_depth = None
        pending_font = False
        for match in CSS_TOKEN.finditer(text):
            token = match.group()
            if token.startswith('/*') or token.startswith(('"', "'")):
                continue
            if token.lower() == '@font-face':
                pending_font = True
            elif token == '{':
                depth += 1
                if pending_font:
                    font_depth = depth
                    pending_font = False
            elif token == '}':
                if font_depth == depth:
                    font_depth = None
                depth -= 1
            elif token.lower().startswith('url('):
                raw = token[4:-1].strip()
                if raw.startswith(('"', "'")):
                    raw = raw[1:-1]
                line = first_line + text.count('\n', 0, match.start())
                is_font = font_depth is not None
                ok = self.reference(path, line, css_unescape(raw),
                                    '@font-face url' if is_font else 'CSS url')
                checked += 1
                failed += not ok
                fonts += is_font
                font_failed += is_font and not ok
        self.report('FAIL' if failed else 'PASS', path,
                    'CSS url：{} 筆，{} 筆失敗'.format(checked, failed), first_line)
        self.report('FAIL' if font_failed else 'PASS', path,
                    '@font-face：{} 筆 URL，{} 筆失敗'.format(fonts, font_failed), first_line)

    def scan(self):
        if not self.root.is_dir():
            self.report('FAIL', self.root, 'public 資料夾不存在')
            return
        files = sorted(path for path in self.root.rglob('*') if path.is_file())
        html_count = 0
        total = 0
        for path in files:
            try:
                path.resolve().relative_to(self.root)
            except ValueError:
                self.report('FAIL', path, '符號連結指向 public 外，略過讀取')
                continue
            try:
                size = path.stat().st_size
                total += size
                relative = path.relative_to(self.root)
                if relative.parts[0] == 'assets' and size > LARGE_FILE_BYTES:
                    reason = KNOWN_LARGE.get(relative.as_posix(), '請評估壓縮')
                    self.report('WARN', path, '資產 {:.3f} MB > 1.5 MB；{}'.format(
                        size / 1_000_000, reason))
                data = path.read_bytes()
                try:
                    text = data.decode('utf-8-sig')
                except UnicodeDecodeError:
                    if path.suffix.lower() in ('.html', '.css', '.js', '.json', '.svg'):
                        self.report('FAIL', path, '文字檔案不是有效 UTF-8')
                    continue
                if '\x00' in text:
                    continue
                remnants = list(re.finditer(r'\{PREFIX\}|TODO|lorem', text, re.I))
                for match in remnants:
                    self.report('FAIL', path, '殘留字樣：{}'.format(match.group()),
                                text.count('\n', 0, match.start()) + 1)
                if not remnants:
                    self.report('PASS', path, '無 {PREFIX}／TODO／lorem 殘留')
                if path.suffix.lower() == '.html':
                    html_count += 1
                    parser = Page(self, path)
                    parser.feed(text)
                    parser.close()
                    parser.finish()
                elif path.suffix.lower() == '.css':
                    self.css(path, text)
            except (OSError, ValueError) as exc:
                self.report('FAIL', path, '無法完成檢查：{}'.format(exc))
        self.require(html_count > 0, self.root, 'HTML 頁面數：{}'.format(html_count))
        self.report('PASS', self.root, 'public 總大小：{:,} bytes ({:.3f} MB)，{} 個檔案'.format(
            total, total / 1_000_000, len(files)))
        self.report('PASS', self.root, 'assets 單檔大小檢查完成（門檻 1.5 MB，超標另列 WARN）')


class Page(HTMLParser):
    def __init__(self, checker, path):
        super().__init__(convert_charrefs=True)
        self.checker = checker
        self.path = path
        self.title = []
        self.in_title = False
        self.lang = False
        self.description = False
        self.h1 = 0
        self.main = False
        self.nav = False
        self.skip = False
        self.footer_depth = 0
        self.footers = []
        self.footer_text = []
        self.style_line = None
        self.style_text = []
        self.references = 0
        self.reference_failures = 0
        self.images = 0
        self.image_failures = 0
        self.decorative = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        line = self.getpos()[0]
        if tag == 'html':
            self.lang = bool((attrs.get('lang') or '').strip())
        elif tag == 'title':
            self.in_title = True
        elif tag == 'meta' and (attrs.get('name') or '').lower() == 'description':
            self.description |= bool((attrs.get('content') or '').strip())
        elif tag == 'h1':
            self.h1 += 1
        elif tag == 'main' and attrs.get('id') == 'main':
            self.main = True
        elif tag == 'nav' and (attrs.get('aria-label') or '').strip():
            self.nav = True
        elif tag == 'a' and attrs.get('href') == '#main':
            self.skip = True
        elif tag == 'footer':
            self.footer_depth += 1
        elif tag == 'style':
            self.style_line = line
            self.style_text = []
        if tag == 'base' and not str(self.path).endswith('404.html'):
            self.checker.report('FAIL', self.path, '<base> 會改變相對路徑，請移除後檢查', line)
        if tag == 'img':
            self.images += 1
            problems = []
            if 'alt' not in attrs or attrs['alt'] is None:
                problems.append('缺少 alt 屬性值')
            elif not attrs['alt'].strip():
                self.decorative.append(line)
            for attr in ('width', 'height'):
                if not (attrs.get(attr) or '').strip():
                    problems.append('缺少 ' + attr)
            if problems:
                self.image_failures += 1
                self.checker.report('FAIL', self.path, '<img> ' + '；'.join(problems), line)
        # 除必要項目外，也涵蓋 iframe/audio 等元素的 href/src。
        for attr in ('href', 'src'):
            if attr in attrs:
                self.references += 1
                self.reference_failures += not self.checker.reference(
                    self.path, line, attrs[attr] or '', '{} {}'.format(tag, attr))
        if tag in ('img', 'source') and 'srcset' in attrs:
            for url in srcset_urls(attrs['srcset'] or ''):
                self.references += 1
                self.reference_failures += not self.checker.reference(
                    self.path, line, url, tag + ' srcset')
        if 'style' in attrs:
            # 無 url 的版面屬性不產生多餘輸出。
            if re.search(r'url\s*\(', attrs['style'] or '', re.I):
                self.checker.css(self.path, attrs['style'], line)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        elif tag == 'footer' and self.footer_depth:
            self.footer_depth -= 1
            if not self.footer_depth:
                self.footers.append(' '.join(''.join(self.footer_text).split()))
                self.footer_text = []
        elif tag == 'style' and self.style_line is not None:
            self.checker.css(self.path, ''.join(self.style_text), self.style_line)
            self.style_line = None

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.footer_depth:
            self.footer_text.append(data)
        if self.style_line is not None:
            self.style_text.append(data)

    def finish(self):
        c = self.checker
        checks = [
            (bool(''.join(self.title).strip()), '非空白 <title>'),
            (self.lang, '<html lang>'),
            (self.h1 == 1, '<h1> 恰好一個（實際 {}）'.format(self.h1)),
        ]
        # 404.html is a standalone utility page (inline styles, no site chrome), so only the basics apply
        if Path(str(self.path)).name != '404.html':
            checks += [
                (self.description, '非空白 meta description'),
                (self.skip, 'skip link 指向 #main'),
                (self.main, '<main id="main">'),
                (self.nav, '<nav aria-label>'),
                (self.footers == [FOOTER], '頁尾為「{}」'.format(FOOTER)),
            ]
        for condition, label in checks:
            c.require(condition, self.path, label)
        c.report('FAIL' if self.reference_failures else 'PASS', self.path,
                 'HTML 連結／資源：{} 筆，{} 筆失敗'.format(
                     self.references, self.reference_failures))
        c.report('FAIL' if self.image_failures else 'PASS', self.path,
                 '圖片 alt／width／height：{} 張，{} 張失敗'.format(
                     self.images, self.image_failures))
        if self.decorative:
            c.report('WARN', self.path, '裝飾圖 alt=""：{} 張（行 {}）'.format(
                len(self.decorative), ', '.join(map(str, self.decorative))))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('public', nargs='?', type=Path, default=DEFAULT_PUBLIC,
                        help='要檢查的 public 資料夾')
    args = parser.parse_args(argv)
    checker = Checker(args.public)
    print('檢查根目錄：{}'.format(checker.root))
    checker.scan()
    print('\n外部連結清單（不連網，已略過存在性檢查）：')
    if not checker.external:
        print('  （無）')
    for url, locations in sorted(checker.external.items()):
        print('  {} [{}]'.format(url, ', '.join(sorted(locations))))
    print('略過純錨點：{} 筆'.format(checker.anchors))
    print('\n摘要：PASS {}／WARN {}／FAIL {}'.format(
        checker.counts['PASS'], checker.counts['WARN'], checker.counts['FAIL']))
    return 1 if checker.counts['FAIL'] else 0


if __name__ == '__main__':
    sys.exit(main())
