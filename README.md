# darlybot

로페봇(b300.vercel.app)과 `DJMAX RESPECT V` 사이를 연결해주는 로컬 브리지 프로그램입니다. 프로그램을 실행하면 `localhost` 에 작은 HTTP/WebSocket 서버가 열리고, 웹에서 곡 타일을 우클릭할 때 전송되는 곡 정보를 받아 게임 안에서 해당 곡을 빠르게 찾도록 키 입력을 자동으로 수행합니다.

> **주의**: 실제 게임 창 제어는 Windows 환경에서만 지원됩니다. 이 저장소는 개발 및 테스트 편의를 위해 기본적으로 `dry-run`(모의 실행) 모드로 동작하며, Windows + `pywin32` 가 설치된 환경에서만 실제 키 입력을 보냅니다.

## 주요 기능

- `곡순서.csv` 를 읽어 곡 제목과 알파벳 이동 키 사이의 매핑을 생성합니다.
- WebSocket API (`ws://localhost:8731/ws`) 를 통해 곡 제목을 전달받아 자동으로 이동 키 입력 시퀀스를 계산합니다.
- 계산된 시퀀스는 `DJMAX RESPECT V` 창에 전달되어 해당 곡으로 빠르게 이동합니다.
- `GET /status` 및 `GET /songs` 엔드포인트를 통해 프로그램 상태와 곡 목록을 확인할 수 있습니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate  # Windows에서는 .venv\\Scripts\\activate
pip install -e .[dev]
```

Windows 환경에서 실제 키 입력을 사용하려면 `pywin32` 패키지가 필수입니다. 위 명령으로 설치됩니다.

## 곡 순서 CSV 준비

기본으로 포함된 `곡순서.csv` 파일은 예시 데이터이며, 실제 게임 버전에 맞는 곡 목록으로 교체해야 합니다.

- 첫 번째 열의 제목만 사용됩니다. 첫 행이 `title` 또는 `곡명` 이면 헤더로 인식되어 자동으로 건너뜁니다.
- 각 행은 게임 내 정렬 순서를 그대로 따라야 합니다.
- 알파벳으로 시작하지 않는 제목은 해당 위치에서 바로 이동하도록 계산됩니다.

예시:

```csv
title
Airwave
Binary Sunset
Binary Star
Cradle
Dreamer
Dream On
Echo
```

## 실행

```bash
python -m darlybot --csv 곡순서.csv --host 127.0.0.1 --port 8731 --dry-run
```

주요 옵션:

- `--csv`: 곡순서 CSV 경로 (기본값: `./곡순서.csv`)
- `--host`, `--port`: 로컬 서버 바인딩 주소와 포트
- `--window-title`: `DJMAX RESPECT V` 창 제목 (다국어 버전의 경우 수정 필요)
- `--key-delay`: 위/아래 화살표 연타 간격(초)
- `--jump-delay`: 알파벳 점프 키 입력 후 대기 시간(초)
- `--dry-run`: 실제 키 입력 없이 로그만 출력 (리눅스/맥에서는 자동 활성화)

## Web API 개요

| 메서드 | 경로 | 설명 |
| ------ | ---- | ---- |
| `GET` | `/status` | 서버 동작 여부 및 곡/알파벳 정보 확인 |
| `GET` | `/songs` | 로드된 곡 제목 리스트 반환 |
| `WS` | `/ws` | WebSocket 연결. `navigate` 메시지를 통해 곡 이동 요청 |

### WebSocket 메시지 예시

- 클라이언트 → 서버

```json
{"type": "navigate", "title": "Binary Star"}
```

- 서버 → 클라이언트

```json
{"type": "navigate", "status": "done", "plan": {"title": "Binary Star", "letter": "b", "offset": 1, "keystrokes": ["b", "down"]}}
```

`status` 값은 `planning` → `done` 순으로 전송되며, 오류 시 `error` 와 함께 메시지를 제공합니다.

## 로페봇 연동 가이드

1. 위 명령으로 브리지 프로그램을 실행합니다 (`--dry-run` 없이 실행해야 실제 키 입력이 전송됩니다).
2. 브라우저에서 [b300.vercel.app](https://b300.vercel.app) 에 접속하면, 로컬 서버 WebSocket(`ws://localhost:8731/ws`) 연결 시 우클릭 기능을 활성화하도록 구현할 수 있습니다.
3. 곡 타일을 우클릭하면 웹에서 곡 제목을 전송하고, 브리지가 해당 곡으로 이동하는 키 입력을 실행합니다.

## 개발 및 테스트

```bash
pytest
```

리눅스/맥 환경에서 테스트 시 자동으로 `dry-run` 모드로 동작하여 키 입력은 발생하지 않습니다.

## 배포 (EXE 생성)

Windows 환경에서 PyInstaller 등을 사용하여 실행 파일로 패키징할 수 있습니다.

```bash
pip install pyinstaller
pyinstaller -F -n darlybot src/darlybot/__main__.py
```

생성된 `dist/darlybot.exe` 를 실행하면 됩니다.

## 라이선스

프로젝트 저작권은 원저작자에게 있으며, 별도의 라이선스가 명시되지 않은 상태입니다.
