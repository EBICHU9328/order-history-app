#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""게임 로그를 따라가며 구매 코드가 찍히면 자동 기록한다.

모드에서 HTTP 를 못 붙일 때 쓰는 방식. 로그 한 줄에 상품 코드가 들어 있으면 된다.

  python hooks/watch_log.py --file "C:\path\game.log" --pattern "dia_0\d_dn"
  python hooks/watch_log.py --file game.log --codes dia_06_dn   # 이 코드만 감시

감시 규칙은 hooks/watch.json 에 저장해 두고 `python hooks/watch_log.py` 만 실행해도 된다.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONF = os.path.join(HERE, 'watch.json')
sys.path.insert(0, HERE)
import log_purchase


def load_conf():
    if os.path.exists(CONF):
        with open(CONF, encoding='utf-8') as f:
            return json.load(f)
    return {}


def follow(path, pattern, codes, interval):
    rx = re.compile(pattern)
    known = set(codes or [])
    if known:
        rx = re.compile('|'.join('(%s)' % re.escape(c) for c in known))

    while not os.path.exists(path):
        print('파일 대기 중:', path)
        time.sleep(2)

    f = open(path, encoding='utf-8', errors='replace')
    f.seek(0, os.SEEK_END)
    print('감시 시작:', path, '| 패턴:', rx.pattern)
    buf = ''
    while True:
        chunk = f.read()
        if not chunk:
            time.sleep(interval)
            continue
        buf += chunk
        while '\n' in buf:
            line, buf = buf.split('\n', 1)
            m = rx.search(line)
            if m:
                code = next((g for g in m.groups() if g), m.group(0))
                try:
                    item = log_purchase.log(code)
                    print('+' if item else '=', code, line.strip()[:80])
                except Exception as e:
                    print('!', code, e)


def main():
    conf = load_conf()
    ap = argparse.ArgumentParser(description='로그 감시 → 자동 기록')
    ap.add_argument('--file', default=conf.get('file'))
    ap.add_argument('--pattern', default=conf.get('pattern', r'dia_0\d_dn'))
    ap.add_argument('--codes', nargs='*', default=conf.get('codes'))
    ap.add_argument('--interval', type=float, default=conf.get('interval', 0.5))
    a = ap.parse_args()
    if not a.file:
        raise SystemExit('--file 로 로그 경로를 주거나 hooks/watch.json 에 file 을 적어 두세요')
    follow(a.file, a.pattern, a.codes, a.interval)


if __name__ == '__main__':
    main()
