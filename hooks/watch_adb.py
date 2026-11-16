#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""에뮬레이터(게임) 로그를 실시간으로 따라가며 구매 코드를 기록한다.

모드에서 구매 시점에 아래 중 아무 형태로든 한 줄 남기면 된다.
  Log.d("DKSHOP", "PURCHASE dia_06_dn")
  print("PURCHASE dia_06_dn")
  시스템 로그 아무 데나 "dia_06_dn" 이 들어간 줄

실행:
  python hooks/watch_adb.py                    # logcat 실시간 감시
  python hooks/watch_adb.py --tag DKSHOP       # 해당 태그만
  python hooks/watch_adb.py --file /sdcard/dkshop.log   # 파일 로그를 tail
  python hooks/watch_adb.py --dry              # 기록 없이 매칭만 확인

adb 경로·시리얼·패턴은 hooks/watch.json 에서 읽는다. 없으면 자동으로 잡는다.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONF = os.path.join(HERE, 'watch.json')
sys.path.insert(0, HERE)
import log_purchase

DEFAULT_ADB = r'C:\LDPlayer\LDPlayer9\adb.exe'


def conf():
    if os.path.exists(CONF):
        with open(CONF, encoding='utf-8') as f:
            return json.load(f)
    return {}


def adb_bin(cfg):
    for p in (cfg.get('adb'), DEFAULT_ADB, 'adb'):
        if p == 'adb' or os.path.exists(p):
            return p
    raise SystemExit('adb 를 찾지 못했습니다. hooks/watch.json 의 "adb" 에 경로를 적어 주세요.')


def pick_serial(cfg, adb):
    if cfg.get('serial'):
        return cfg['serial']
    try:
        out = subprocess.run([adb, 'devices'], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return None
    for line in out.splitlines()[1:]:
        if line.strip().endswith('device'):
            serial = line.split()[0]
            print('기기 자동 선택:', serial)
            return serial
    raise SystemExit('연결된 기기가 없습니다. 에뮬레이터를 켜고 다시 실행하세요.')


def spawn(adb, serial, cfg, tag, file):
    base = [adb] + (['-s', serial] if serial else [])
    if file:
        return base + ['shell', 'tail', '-F', file]
    cmd = base + ['logcat', '-v', 'time']       # 전체 버퍼부터 받고 시작 시각 이전 라인은 버린다
    for t in (tag or []):
        cmd += ['-s', t]
    return cmd


def run(args):
    cfg = conf()
    adb = adb_bin(cfg)
    serial = None if args.any_serial else pick_serial(cfg, adb)
    pattern = args.pattern or cfg.get('pattern') or r'(dia_0\d_dn|dia_1\d_dn)'
    rx = re.compile(pattern)
    file = args.file or cfg.get('log_file')
    print('감시 시작 |', 'logcat' if not file else 'tail ' + file, '| 패턴:', rx.pattern)
    mark = time.strftime('%m-%d %H:%M:%S')      # 이 시각 이전 라인은 과거 로그라 무시

    while True:
        cmd = spawn(adb, serial, cfg, args.tag or cfg.get('tags'), file)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    encoding='utf-8', errors='replace', bufsize=1)
        except Exception as e:
            print('실행 실패:', e)
            time.sleep(2)
            continue

        for line in (proc.stdout or []):
            line = line.rstrip('\n')
            if not file and line[:18] and line[:18] < mark:
                continue
            m = rx.search(line)
            if not m:
                continue
            code = next((g for g in m.groups() if g), m.group(0))
            stamp = time.strftime('%H:%M:%S')
            if args.dry:
                print('[dry]', stamp, code, '|', line[:90])
                continue
            try:
                item = log_purchase.log(code, force=args.force)
                print(('[+] ' if item else '[=] ') + stamp, code, '|', line[:90])
            except Exception as e:
                print('[!]', stamp, code, e)

        proc.wait()
        print('adb 스트림이 끊겼습니다. 3초 뒤 다시 연결…')
        time.sleep(3)


def main():
    ap = argparse.ArgumentParser(description='에뮬레이터 로그 감시 → 구매 기록')
    ap.add_argument('--tag', action='append', help='logcat 태그 (여러 번 지정 가능)')
    ap.add_argument('--pattern', help='코드 추출 정규식')
    ap.add_argument('--file', help='로그 파일 경로(기기 내부). 지정하면 logcat 대신 tail')
    ap.add_argument('--serial', help='기기 시리얼 (기본: 자동)')
    ap.add_argument('--any-serial', action='store_true', help='시리얼 고정하지 않기')
    ap.add_argument('--force', action='store_true', help='중복 무시 시간 건너뛰기')
    ap.add_argument('--dry', action='store_true', help='기록 없이 매칭만 출력')
    a = ap.parse_args()
    if a.serial:
        c = conf()
        c['serial'] = a.serial
        with open(CONF, 'w', encoding='utf-8') as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
    run(a)


if __name__ == '__main__':
    main()
