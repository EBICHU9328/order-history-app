# -*- coding: utf-8 -*-
"""저장된 Google Play '주문 내역' 페이지를 단일 파일 사설 페이지로 변환한다.

- 원본: 주문 내역 - Google Play.html (+ _files 자산)
- 출력: index.html (스크립트 제거, 이미지·폰트·아이콘 모두 data URI 내장)
"""
import base64, os, re, shutil, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '주문 내역 - Google Play.html')
FILES = os.path.join(ROOT, '주문 내역 - Google Play_files')
ASSETS = os.path.join(ROOT, 'assets')
FONTS = os.path.join(ASSETS, 'fonts')
REMOTE = os.path.join(ASSETS, 'remote')

MAP = {
    'unnamed.webp': 'dia.webp',
    'unnamed(1).webp': 'dia_1000.webp',
    'unnamed(2).webp': 'play_balance.webp',
    'unnamed(3).webp': 'telegram.webp',
    'unnamed(4).webp': 'prereg_reward.webp',
    'unnamed(5).webp': 'event_pack.webp',
    'unnamed(6).webp': 'zeus_pack.webp',
    'unnamed(7).webp': 'seal_cash.webp',
    'unnamed(8).webp': 'item_pack.webp',
    'unnamed(9).webp': 'gold_plan.webp',
    'unnamed.gif': 'profile.gif',
    'korea.png': 'korea.png',
}
MIME = {'.webp': 'image/webp', '.png': 'image/png', '.gif': 'image/gif',
        '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.ico': 'image/x-icon'}

for d in (ASSETS, FONTS, REMOTE):
    os.makedirs(d, exist_ok=True)
for old, new in MAP.items():
    s = os.path.join(FILES, old)
    if os.path.exists(s):
        shutil.copyfile(s, os.path.join(ASSETS, new))


def datauri(path):
    with open(path, 'rb') as f:
        b = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lower()
    mime = MIME.get(ext)
    if mime is None and 'fonts' in path.replace('\\', '/'):
        mime = 'font/woff2'       # 확장자 없는 폰트 키트 URL
    return 'data:%s;base64,%s' % (mime or 'application/octet-stream', b)


def fetch(url, dst):
    if os.path.exists(dst):
        return
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r, open(dst, 'wb') as f:
        f.write(r.read())


html = open(SRC, encoding='utf-8', errors='replace').read()

# ---- 스타일 블록(구글 플레이 CSS) 추출 -------------------------------------
st = html.find('<style data-href=')
css = html[st:html.find('</style>', st) + 8]

# ---- 원격 자원 로컬화 ------------------------------------------------------
REMOTE_MAP = {}
count = [0]


def localize(u):
    if u in REMOTE_MAP:
        return REMOTE_MAP[u]
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', u.rsplit('/', 1)[-1])[-60:]
    if os.path.splitext(name)[1].lower() not in MIME:
        name += '.bin'
    dst = os.path.join(REMOTE, 'r%02d_%s' % (count[0] + 1, name))
    count[0] += 1
    try:
        fetch(u, dst)
    except Exception as e:
        print('remote fail', u, e)
        REMOTE_MAP[u] = u
        return u
    REMOTE_MAP[u] = dst
    return dst


def inline_css_urls(txt):
    def sub(m):
        u = m.group(1).strip('\'"')
        if u.startswith('data:'):
            return m.group(0)
        if u.startswith('http'):
            p = localize(u)
        elif os.path.isabs(u) or re.match(r'^[A-Za-z]:/', u):
            p = u
        else:
            p = os.path.join(ROOT, u)
        if not os.path.exists(p) or os.path.isdir(p):
            return m.group(0)
        return 'url("%s")' % datauri(p)
    return re.sub(r'url\(([^)]+)\)', sub, txt)


# 폰트 스타일시트: 라틴 기본 문자 블록만 남기고 나머지 서브셋은 버린다
# (한글은 원래도 시스템 글꼴로 렌더링되므로 시릴/그리스/베트남 서브셋은 불필요)
fs = html.find('<style data-font-stylesheet=""')
_fs = html[fs:html.find('</style>', fs) + 8]
_blocks = re.findall(r'@font-face\{[^}]*\}', _fs)
_keep = []
for _b in _blocks:
    if 'unicode-range' in _b and 'U+0000-00FF' not in _b:
        continue
    _w = re.search(r'font-weight:([\d ]+)', _b)
    if _w and _b.count('unicode-range') and _w.group(1).strip() not in ('400', '500', '700'):
        continue
    _keep.append(_b)
fontcss = '<style>' + ''.join(_keep) + '</style>' if _keep else _fs
n = 0
for u in dict.fromkeys(re.findall(r'url\((https://fonts\.gstatic\.com/[^)]+)\)', fontcss)):
    n += 1
    dst = os.path.join(FONTS, 'f%02d.woff2' % n)
    try:
        fetch(u, dst)
    except Exception as e:
        print('font fail', u, e)
    fontcss = fontcss.replace(u, dst.replace('\\', '/'))

# 머티리얼 아이콘(드롭다운 화살표 등)
MI = os.path.join(FONTS, 'materialicons.woff2')
try:
    fetch('https://fonts.gstatic.com/s/materialicons/v145/flUhRq6tzZclQEJ-Vdg-IuiaDsNc.woff2', MI)
    fontcss += ('<style>@font-face{font-family:"Google Material Icons";font-style:normal;'
                'font-weight:400;src:url(%s) format("woff2")}</style>' % datauri(MI))
except Exception as e:
    print('material icons fail', e)

css = inline_css_urls(css)
fontcss = inline_css_urls(fontcss)

# ---- 본문 ------------------------------------------------------------------
b = html.find('<body')
body = html[b:html.find('</body>', b)]
body = re.sub(r'<script\b[^>]*>.*?</script>', '', body, flags=re.S)
body = re.sub(r'<script\b[^>]*/>', '', body)
body = re.sub(r'\sdata-(?:atf|iml)="[^"]*"', '', body)
body = re.sub(r'\s(?:srcset|data-src)="[^"]*"', '', body)
body = re.sub(r'https://(?:play-lh|lh\d(?:\.googleusercontent)?)[^"\' ]+', '', body)
body = body.replace('./주문 내역 - Google Play_files/', 'assets/')
for old, new in MAP.items():
    body = body.replace('assets/' + old, 'assets/' + new)


def inline_img(m):
    p = os.path.join(ROOT, m.group(1))
    return 'src="%s"' % (datauri(p) if os.path.exists(p) else m.group(1))


body = re.sub(r'src="(assets/[^"]+)"', inline_img, body)
# 로고 워드마크: 'google_logo' 리거처 글꼴이 없으므로 일반 텍스트로 대체
body = body.replace('>google_logo Play<', '>Google Play<')

over = ('<style>html,body{background:#fff}'
        'body{height:auto!important;min-height:100vh!important;overflow:visible!important}'
        '.google-material-icons{font-family:"Google Material Icons"!important;'
        'font-feature-settings:"liga";-webkit-font-feature-settings:"liga";'
        'font-style:normal;font-weight:400;font-size:24px;line-height:1;display:inline-block;'
        'white-space:nowrap;direction:ltr;letter-spacing:normal;text-transform:none;'
        '-webkit-font-smoothing:antialiased}</style>')

page = ('<!DOCTYPE html>\n<html lang="ko" dir="ltr"><head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>주문 내역 - Google Play</title>\n'
        '<link rel="icon" href="%s">\n<base href="./">\n' % datauri(os.path.join(ASSETS, 'favicon.ico'))
        + css + '\n' + fontcss + '\n' + over + '\n</head>\n' + body + '\n</body></html>\n')

out = os.path.join(ROOT, 'index.html')
open(out, 'w', encoding='utf-8').write(page)
print('wrote', out, len(page))
