# 증권시장 동향 V1

표 중심 업무보고서 UI와 KIS/Telegram 조회 전용 수집기입니다. 주문·매매 기능과 AI 생성 기능은 포함하지 않습니다.

## 구성

- `app/main.py`: 로컬 웹/API 서버
- `app/services/`: 시장·Telegram·날짜별 보고서 저장 서비스
- `web/`: A4형 보고서 UI와 Excel TSV 복사
- `config/`: 종목·Telegram 채널·뉴스 키워드 설정
- `integrations/kis.py`: KIS OAuth 및 조회 전용 시세 API
- `scripts/`: 각 연결을 직접 확인하는 CLI
- `tests/`: 외부 API 호출 없는 단위 테스트

## 보안

`.env`, Telegram 세션, KIS 토큰 캐시는 Git에서 제외됩니다. 연결 스크립트는 키/토큰/세션 값을 출력하지 않습니다.

Telegram을 처음 사용하는 경우 `python scripts/create_telegram_session.py`로 대화형 인증을 마친 뒤 조회 스크립트를 실행합니다.

수집 채널, 발췌 길이, 마감시황 키워드는 `config/telegram_channels.json`에서 관리합니다. Telegram 분류는 관심종목명과 설정 문자열의 단순 포함 검색만 사용하며 AI API를 호출하지 않습니다.

## 실행

`python -m app.main` 실행 후 `http://127.0.0.1:8000`을 엽니다. Telegram 채널은 `config/telegram_channels.json`에 `{ "source": "표시명", "username": "channel" }` 형태로 추가합니다.

상시 서버 자동 실행 템플릿은 `deploy/`에 있습니다. `telegram-update.timer`가 한국시간 기준 30분마다 수집하며, 서버에서 Telegram 세션을 최초 1회 인증해야 합니다.
