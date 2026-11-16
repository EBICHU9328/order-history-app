#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index.html 을 로컬 네트워크에 서빙하는 최소 서버.

  python serve.py            # http://localhost:8000
  python serve.py 8080       # 포트 지정
  python serve.py 8000 0.0.0.0   # 같은 네트워크의 다른 기기에서도 접속 허용

표준 라이브러리만 사용한다. 캐시를 꺼서 수정 사항이 바로 반영된다.
"""
import http.server
import os
import socketserver
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
HOST = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    os.chdir(DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print("serving %s on http://%s:%d" % (DIR, HOST, PORT))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
