#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""구매 1건을 결제 페이지에 기록하는 훅.

세 가지로 쓸 수 있다.

  1) 명령 한 줄
       python hooks/log_purchase.py dia_06_dn
  2) HTTP 로 받기(게임 스크립트·adb 리버스용, 로컬만 열림)
       python hooks/log_purchase.py --serve --port 8770
       → POST http://127.0.0.1:8770/purchase  {"code":"dia_06_dn"}
       → GET  http://127.0.0.1:8770/codes     (사용 가능한 코드/금액 확인)
  3) 로그 파일 감시
       hooks/watch_log.py 참고

기록은 사이트와 같은 저장소(gist)에 바로 들어가고, 열려 있는 페이지는 3초 안에 받아 간다.
"""
import argparse
import base64
import datetime
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODES = os.path.join(ROOT, 'hooks', 'purchase_codes.json')
SYNC = os.path.join(ROOT, 'tools', 'sync.json')
ASSETS = os.path.join(ROOT, 'assets')
API = 'https://api.github.com/gists/'
FILE = 'orders.json'
DEDUPE_SEC = 3          # 같은 코드가 연달아 들어올 때 중복 무시 시간
_last = {}


def load_sync():
    with open(SYNC, encoding='utf-8') as f:
        cfg = json.load(f)
    if not cfg.get('token') or not cfg.get('gist'):
        raise SystemExit('tools/sync.json 에 token/gist 가 없습니다')
    return cfg


def load_codes():
    with open(CODES, encoding='utf-8') as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith('_')}


def icon_uri(name):
    path = os.path.join(ASSETS, name)
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        return 'data:image/webp;base64,' + base64.b64encode(f.read()).decode()


def api(cfg, method='GET', payload=None):
    req = urllib.request.Request(
        API + cfg['gist'], method=method,
        headers={'Authorization': 'token ' + cfg['token'],
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json'},
        data=json.dumps(payload).encode() if payload else None)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def log(code, force=False, note=None):
    """구매 1건을 기록한다. 성공하면 추가된 항목을 돌려준다."""
    codes = load_codes()
    if code not in codes:
        raise SystemExit('알 수 없는 코드: %s (사용 가능: %s)' % (code, ', '.join(codes)))

    now = time.time()
    if not force and code in _last and now - _last[code] < DEDUPE_SEC:
        return None
    _last[code] = now

    cfg = load_sync()
    spec = codes[code]

    for attempt in range(4):
        data = api(cfg)
        content = (data.get('files', {}).get(FILE) or {}).get('content') or '{}'
        orders = json.loads(content).get('orders', [])

        item = {
            'id': 'p' + format(int(now * 1000), 'x'),
            'title': spec['title'],
            'date': datetime.date.today().isoformat(),
            'amount': int(spec['amount']),
            'currency': 'KRW',
            'status': None,
            'report': True,
            'icon': icon_uri(spec.get('icon', '')),
        }
        if note:
            item['title'] = spec['title']
        orders.append(item)

        try:
            api(cfg, 'PATCH', {'files': {FILE: {'content': json.dumps({'orders': orders})}}})
            return item
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(0.4 + attempt * 0.4)   # 다른 기기와 겹쳤을 때 다시 읽고 재시도
    return None


# ── HTTP 모드 ─────────────────────────────────────────────────────────────────
def serve(port):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def _json(self, code, body):
            raw = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path.startswith('/codes'):
                return self._json(200, load_codes())
            if self.path.startswith('/health'):
                return self._json(200, {'ok': True})
            self._json(404, {'error': 'not found'})

        def do_POST(self):
            if not self.path.startswith('/purchase'):
                return self._json(404, {'error': 'not found'})
            length = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(length).decode() if length else '{}'
            try:
                body = json.loads(raw) if raw.strip().startswith('{') else {'code': raw.strip()}
            except Exception:
                return self._json(400, {'error': 'bad json'})
            code = (body.get('code') or '').strip()
            if not code:
                return self._json(400, {'error': 'code 필요'})
            try:
                item = log(code, force=bool(body.get('force')))
            except SystemExit as e:
                return self._json(400, {'error': str(e)})
            except Exception as e:
                return self._json(502, {'error': str(e)})
            if item is None:
                return self._json(200, {'ok': True, 'skipped': 'duplicate'})
            self._json(200, {'ok': True, 'item': item['title'], 'amount': item['amount']})

        def log_message(self, format, *args):
            sys.stderr.write('%s - %s\n' % (self.address_string(), format % args))

    print('listening on http://127.0.0.1:%d  (POST /purchase)' % port)
    print('  adb 로 게임(에뮬레이터)에서 쓰려면: adb reverse tcp:%d tcp:%d' % (port, port))
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()


def main():
    ap = argparse.ArgumentParser(description='구매 1건 기록')
    ap.add_argument('code', nargs='?', help='상품 코드 (예: dia_06_dn)')
    ap.add_argument('--serve', action='store_true', help='HTTP 로 받기')
    ap.add_argument('--port', type=int, default=8770)
    ap.add_argument('--force', action='store_true', help='중복 무시 시간 건너뛰기')
    ap.add_argument('--codes', action='store_true', help='코드 목록 출력')
    a = ap.parse_args()

    if a.codes:
        print(json.dumps(load_codes(), ensure_ascii=False, indent=2))
        return
    if a.serve:
        serve(a.port)
        return
    if not a.code:
        ap.print_help()
        return
    item = log(a.code, force=a.force)
    print('기록됨' if item else '중복이라 건너뜀', a.code)


if __name__ == '__main__':
    main()
