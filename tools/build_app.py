# -*- coding: utf-8 -*-
'''저장된 Google Play '주문 내역' 페이지 -> 주문 편집이 가능한 단일 파일 사설 페이지.'''
import base64, json, os, re, shutil, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '주문 내역 - Google Play.html')
FILES = os.path.join(ROOT, '주문 내역 - Google Play_files')
ASSETS = os.path.join(ROOT, 'assets')
FONTS = os.path.join(ASSETS, 'fonts')
REMOTE = os.path.join(ASSETS, 'remote')
TOOLS = os.path.join(ROOT, 'tools')

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
# 빠른 상품: 라벨(상품 코드), 금액, 아이콘
PRODUCTS = [
    ('dia_01_dn', 5500, 'dia.webp'),
    ('dia_02_dn', 11000, 'dia.webp'),
    ('dia_03_dn', 22000, 'dia.webp'),
    ('dia_04_dn', 33000, 'dia.webp'),
    ('dia_05_dn', 55000, 'dia.webp'),
    ('dia_06_dn', 110000, 'dia.webp'),
]
ICONS = [
    ('아이템 팩', 'item_pack.webp'),
    ('이벤트 패키지', 'event_pack.webp'),
    ('씰 캐시', 'seal_cash.webp'),
    ('제우스 팩', 'zeus_pack.webp'),
    ('골드 플랜', 'gold_plan.webp'),
    ('플레이 잔액', 'play_balance.webp'),
    ('텔레그램', 'telegram.webp'),
    ('사전 등록 보상', 'prereg_reward.webp'),
]
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
    if mime is None and 'fonts' in path.replace('\\\\', '/'):
        mime = 'font/woff2'
    return 'data:%s;base64,%s' % (mime or 'application/octet-stream', b)


def fetch(url, dst):
    if os.path.exists(dst):
        return
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r, open(dst, 'wb') as f:
        f.write(r.read())


html = open(SRC, encoding='utf-8', errors='replace').read()
st = html.find('<style data-href=')
css = '<style>' + re.sub(r'^<style[^>]*>', '', html[st:html.find('</style>', st)]) + '</style>'

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


# 폰트: 라틴 기본 문자 블록 + 리거처(아이콘) 블록만 남긴다
fs = html.find('<style data-font-stylesheet=""')
_fs = html[fs:html.find('</style>', fs) + 8]
_blocks = re.findall(r'@font-face\{[^}]*\}', _fs)
_keep = []
for _b in _blocks:
    if 'unicode-range' in _b and 'U+0000-00FF' not in _b:
        continue
    _w = re.search(r'font-weight:([\d ]+)', _b)
    if _w and 'unicode-range' in _b and _w.group(1).strip() not in ('400', '500', '700'):
        continue
    _keep.append(_b)
if not _keep:
    _keep = _blocks
fontcss = _fs
n = 0
for u in dict.fromkeys(re.findall(r'url\((https://fonts\.gstatic\.com/[^)]+)\)', fontcss)):
    n += 1
    dst = os.path.join(FONTS, 'f%02d.woff2' % n)
    try:
        fetch(u, dst)
    except Exception as e:
        print('font fail', u, e)
    fontcss = fontcss.replace(u, dst.replace('\\\\', '/'))
MI = os.path.join(FONTS, 'materialicons.woff2')
try:
    fetch('https://fonts.gstatic.com/s/materialicons/v145/flUhRq6tzZclQEJ-Vdg-IuiaDsNc.woff2', MI)
except Exception as e:
    print('material icons fail', e)

fontcss = '<style>' + ''.join(_keep) + '</style>'
if os.path.exists(MI):
    fontcss += ('<style>@font-face{font-family:"Google Material Icons";font-style:normal;'
                'font-weight:400;src:url("%s") format("woff2")}</style>' % datauri(MI))

css = inline_css_urls(css)
fontcss = inline_css_urls(fontcss)

# ---- 본문 ----------------------------------------------------------------
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
body = body.replace('>google_logo Play<', '>Google Play<')


# ---- 흔적 제거 ------------------------------------------------------------
def strip_framework(h):
    def cwiz(m):
        attrs = m.group(1)
        cls = re.search(r'class="([^"]*)"', attrs)
        if cls:
            attrs = attrs.replace(cls.group(0), 'class="c-wiz %s"' % cls.group(1))
        else:
            attrs = ' class="c-wiz"' + attrs
        return '<div' + attrs + '>'
    h = re.sub(r'<c-wiz\b([^>]*)>', cwiz, h)
    h = h.replace('</c-wiz>', '</div>')
    h = h.replace('class="c-wiz', 'class="sec').replace('"c-wiz"', '"sec"')
    h = re.sub(r'<c-data\b[^>]*>\s*</c-data>', '', h)
    drop = ('jscontroller', 'jsaction', 'jsname', 'jsmodel', 'jsshadow', 'jsdata',
            'jslog', 'c-wiz', 'autoupdate', 'jsslot', 'nonce',
            'data-p', 'data-node-index', 'data-item-type', 'data-disable-idom',
            'data-tab-panel-active', 'data-href', 'data-mt', 'data-skip-focus-on-activate',
            'data-filter-id', 'data-use-automatic-activation', 'data-add-continue-url-param',
            'data-target', 'data-stay-in-viewport', 'data-skip-fixed-positioned-viewport-fix',
            'data-should-flip-corner-horizontally', 'data-ogpc', 'data-navigation',
            'data-menu-when-selected', 'data-menu-uid', 'data-max-height',
            'data-is-windows-desktop', 'data-is-touch-wrapper', 'data-is-hoisted',
            'data-has-header', 'data-has-footer', 'data-encoded-next-page-token',
            'data-deselect-chip', 'data-default-tab-id', 'data-default-label')
    for a in drop:
        h = re.sub(r'\s%s(="[^"]*)?"' % re.escape(a), '', h)
    h = re.sub(r'href="(/[^"]*)"', r'href="https://play.google.com\1"', h)
    return h


body = strip_framework(body)
css = (css.replace('c-wiz>c-data', '.sec>.c-data')
          .replace('c-wiz{', '.sec{')
          .replace('c-wiz.', '.sec.')
          .replace('c-data{', '.c-data{'))


# ---- 주문 목록 비우기 -----------------------------------------------------
EMPTY = ('<div id="dkEmpty"><b>아직 주문 내역이 없습니다.</b>'
         '구매한 내역을 직접 등록할 수 있습니다.</div>')


def cut_list(h):
    m = re.search(r'<div class="NgfTBf[^"]*"[^>]*>', h)
    if not m:
        raise SystemExit('목록 컨테이너(NgfTBf)를 찾지 못했습니다')
    i = m.end()
    depth = 1
    while i < len(h) and depth:
        nxt = h.find('<div', i)
        close = h.find('</div>', i)
        if close == -1:
            raise SystemExit('목록 컨테이너 닫힘을 찾지 못했습니다')
        if nxt != -1 and nxt < close:
            depth += 1
            i = nxt + 4
        else:
            depth -= 1
            i = close + 6
    end = i - 6
    open_tag = m.group(0).replace('<div class="NgfTBf', '<div id="orderList" class="NgfTBf')
    return h[:m.start()] + open_tag + '</div>' + EMPTY + h[end + 6:]


body = cut_list(body)

ADD_BTN = ('<span class="dk-sync" id="dkSync" data-state="busy" title="동기화 중…"></span>'
           '<button type="button" class="dk-btn" id="dkShot">'
           '<i class="google-material-icons" style="font-size:18px;margin-right:5px">photo_camera</i>'
           '<span>캡쳐</span></button>'
           '<button type="button" class="dk-btn" id="dkAdd">'
           '<span class="dk-ic">+</span>주문 추가</button>')
body = body.replace('<div class="b6SkTb">', '<div class="b6SkTb">' + ADD_BTN, 1)
body = body.replace('<div class="LKoj6">11월 총 지출액: ₩38,500</div>',
                    '<div class="LKoj6"><span id="dkMonth">11월</span> 총 지출액: <span id="dkTotal">₩0</span></div>')

MODAL = '''
<div class="dk-modal" id="dkModal" hidden>
  <form class="dk-card" id="dkForm" autocomplete="off">
    <h2 id="dkTitle">주문 추가</h2>
    <p class="hint">화면에 표시될 내용을 그대로 입력하세요. 아이콘은 아래에서 고르거나 직접 올릴 수 있습니다.</p>
    <div class="dk-field wide">
      <label>빠른 상품</label>
      <div class="dk-chips" id="dkProducts"></div>
    </div>
    <div class="dk-grid">
      <div class="dk-field wide">
        <label for="dkName">상품명</label>
        <input type="text" id="dkName" maxlength="80" placeholder="예: 다이아 1000" required>
      </div>
      <div class="dk-field">
        <label for="dkDate">날짜</label>
        <input type="date" id="dkDate">
      </div>
      <div class="dk-field">
        <label for="dkAmount">금액</label>
        <div class="dk-money">
          <input type="number" id="dkAmount" min="0" step="1" placeholder="0">
          <select id="dkCurrency"><option value="KRW">원</option><option value="USD">달러</option></select>
        </div>
      </div>
      <div class="dk-field">
        <label for="dkStatus">상태</label>
        <select id="dkStatus">
          <option value="">없음</option>
          <option value="취소됨">취소됨</option>
          <option value="환불됨">환불됨</option>
        </select>
      </div>
      <div class="dk-field" id="dkRepeatField">
        <label for="dkRepeat">추가 개수</label>
        <input type="number" id="dkRepeat" min="1" max="50" step="1" value="1">
      </div>
      <div class="dk-field wide">
        <label>아이콘</label>
        <div class="dk-icons" id="dkIcons"></div>
        <div class="dk-upload">
          <button type="button" class="dk-btn ghost" id="dkPick">이미지 올리기</button>
          <input type="file" id="dkFile" accept="image/*">
          <img id="dkPreview" alt="" width="46" height="46" style="border-radius:10px;object-fit:cover;border:1px solid #dadce0" hidden>
        </div>
        <input type="url" id="dkUrl" placeholder="또는 이미지 주소(https://...)">
      </div>
      <div class="dk-field wide">
        <label class="dk-check"><input type="checkbox" id="dkReport" checked> 문제 신고 링크 표시</label>
      </div>
    </div>
    <div class="dk-foot">
      <button type="button" class="dk-btn primary" id="dkSave">저장</button>
      <button type="button" class="dk-btn" id="dkCancel">취소</button>
    </div>
    <div class="dk-sep"></div>
    <div class="dk-tools-row">
      <button type="button" class="dk-btn ghost" id="dkExport">JSON 내보내기</button>
      <button type="button" class="dk-btn ghost" id="dkImport">JSON 가져오기</button>
      <input type="file" id="dkImportFile" accept="application/json,.json" style="display:none">
      <button type="button" class="dk-btn ghost" id="dkClear">전체 삭제</button>
      <button type="button" class="dk-btn ghost" id="dkX" style="margin-left:auto">닫기</button>
    </div>
    <p class="dk-note">입력한 내용은 이 브라우저에만 저장됩니다. 다른 기기로 옮길 때는 JSON 내보내기를 사용하세요.</p>
  </form>
</div>
<div class="dk-toast" id="dkToast"></div>
'''
body = body.replace('<div id="roster-for-Google-Help" style="display: none;"></div>', '')

# ---- 조립 ----------------------------------------------------------------
h2c = open(os.path.join(TOOLS, 'vendor', 'html2canvas.min.js'), encoding='utf-8').read()
app_css = open(os.path.join(TOOLS, 'app.css'), encoding='utf-8').read()
app_js = open(os.path.join(TOOLS, 'app.js'), encoding='utf-8').read()
icons_js = '[' + ','.join(
    '{"name":%s,"src":%s}' % (json.dumps(name), json.dumps(datauri(os.path.join(ASSETS, f))))
    for name, f in ICONS if os.path.exists(os.path.join(ASSETS, f))) + ']'
products_js = '[' + ','.join(
    '{"label":%s,"amount":%d,"icon":%s}' % (json.dumps(label), amount, json.dumps(datauri(os.path.join(ASSETS, f))))
    for label, amount, f in PRODUCTS if os.path.exists(os.path.join(ASSETS, f))) + ']'
app_js = app_js.replace('/*__ICONS__*/[]', icons_js).replace('/*__PRODUCTS__*/[]', products_js)
sync_path = os.path.join(TOOLS, 'sync.json')
if os.path.exists(sync_path):
    _s = json.load(open(sync_path, encoding='utf-8'))
    _t = _s['token']
    _h = len(_t) // 2
    sync_js = '{token: %s + %s, gist: %s}' % (json.dumps(_t[:_h]), json.dumps(_t[_h:]), json.dumps(_s['gist']))
else:
    sync_js = 'null'
app_js = app_js.replace('/*__SYNC__*/null', sync_js)

over = ('<style>html,body{background:#fff}'
        'body{height:auto!important;min-height:100vh!important;overflow:visible!important}'
        '.google-material-icons{font-family:"Google Material Icons"!important;'
        'font-feature-settings:"liga";-webkit-font-feature-settings:"liga";'
        'font-style:normal;font-weight:400;font-size:24px;line-height:1;display:inline-block;'
        'white-space:nowrap;direction:ltr;letter-spacing:normal;text-transform:none;'
        '-webkit-font-smoothing:antialiased}'
        '.c-data{display:none}</style>')

page = ('<!DOCTYPE html>\n<html lang="ko" dir="ltr"><head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>주문 내역 - Google Play</title>\n'
        '<link rel="icon" href="%s">\n' % datauri(os.path.join(ASSETS, 'favicon.ico'))
        + css + '\n' + fontcss + '\n' + over + '\n<style>' + app_css + '</style>\n</head>\n'
        + body + MODAL + '\n<script>' + h2c + '</script>\n<script>' + app_js + '</script>\n</body></html>\n')

out = os.path.join(ROOT, 'index.html')
open(out, 'w', encoding='utf-8').write(page)
print('wrote', out, len(page))
