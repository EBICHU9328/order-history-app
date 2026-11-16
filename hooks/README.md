# 구매 기록 훅

게임(모드)에서 결제가 일어난 순간 이 훅을 부르면, 결제 페이지에 그 항목이 자동으로 올라간다.
페이지는 3초 안에 자동 반영되므로, 폰이나 다른 PC에서도 곧바로 보인다.

## 1. 가장 단순한 방법 — 명령 한 줄

    python hooks/log_purchase.py dia_06_dn

모드에서 프로세스를 하나 띄울 수 있으면 이걸 그대로 부르면 된다.

## 2. HTTP 로 받기 (모드가 HTTP 를 쏠 수 있을 때)

    python hooks/log_purchase.py --serve --port 8770

    POST http://127.0.0.1:8770/purchase     {"code": "dia_06_dn"}
    GET  http://127.0.0.1:8770/codes        사용 가능한 코드와 금액
    GET  http://127.0.0.1:8770/health

- 로컬(127.0.0.1)만 열린다. 외부에는 노출되지 않는다.
- **에뮬레이터(안드로이드) 안에서 호출할 때**는 PC 로 포트를 넘겨야 한다:

      adb reverse tcp:8770 tcp:8770

  그러면 게임 쪽에서는 `http://127.0.0.1:8770/purchase` 를 그대로 쓰면 된다.
- 같은 코드가 3초 안에 두 번 오면 중복으로 보고 건너뛴다. 강제로 넣으려면 `{"code":"dia_06_dn","force":true}`.

## 3. 로그 감시 (모드가 로그만 남길 때)

    python hooks/watch_log.py --file "C:\경로\game.log" --pattern "dia_0\d_dn"

감시할 경로/패턴은 `hooks/watch.json` 에 적어 두면 `python hooks/watch_log.py` 만으로 돌아간다.
로그 한 줄에 상품 코드가 있으면 그 줄을 읽어 기록한다.

## 코드·금액 바꾸기

`hooks/purchase_codes.json` 만 고치면 된다.

    "dia_06_dn": { "title": "dia_06_dn", "amount": 110000, "icon": "dia.webp" }

- `title` 은 화면에 찍히는 상품명, `amount` 는 원 단위 정수, `icon` 은 `assets/` 안 파일명.
- 새 상품을 넣으려면 같은 형식으로 한 줄 추가하면 된다. 페이지의 '빠른 상품' 목록과는 별개다.

## 확인

    python hooks/log_purchase.py --codes
    python hooks/log_purchase.py dia_01_dn --force

넣은 뒤 https://ebichu9328.github.io/order-history-app/ 을 열어 두면 3초 안에 목록에 나타난다.
