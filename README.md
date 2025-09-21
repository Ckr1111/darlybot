# RofeBot ↔ DJMAX Bridge

이 저장소는 로페봇(b300.vercel.app)에서 선택한 곡을 윈도우에서 실행 중인 **DJMAX RESPECT V** 클라이언트로 바로 전달해 주는 백그라운드 도구입니다. 프로그램이 실행되면 로페봇 웹 페이지에서 타일을 우클릭하는 것만으로 게임에서 대응하는 곡을 검색할 수 있습니다.

## 구성 요소

- `src/rofebot_bridge/` – CSV 로더, 곡 탐색 로직, Windows 키 입력 자동화를 포함한 파이썬 모듈
- `web/rofebot-bridge.user.js` – Tampermonkey 등에서 사용할 수 있는 사용자 스크립트. 우클릭 이벤트를 로컬 브리지 서버로 전달합니다.
- `data/song_order.sample.csv` – `곡순서.csv` 형식의 예시 파일
- `build_exe.bat` – Windows에서 PyInstaller를 이용해 단일 실행 파일을 만드는 스크립트 (선택 사항)

## 사전 준비

1. Windows 10/11 환경 (키 입력 자동화는 Windows 전용입니다)
2. Python 3.10 이상
3. `곡순서.csv` – 곡 번호(title number)와 제목(title)을 담은 UTF-8 CSV. 헤더가 있거나 없는 형태 모두 지원합니다.
4. DJMAX RESPECT V가 이미 실행 중인 상태

## 설치 및 실행

```powershell
# 저장소 클론
git clone <repo-url>
cd darlybot

# 필요한 패키지 설치 (Windows)
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -e .

# 브리지 서버 실행 (CSV 경로 지정)
python -m rofebot_bridge --csv "C:\경로\곡순서.csv"
```

기본적으로 서버는 `http://127.0.0.1:29184`에서 요청을 기다립니다. 게임 창 제목이 다르다면 `--window-title` 옵션으로 수정할 수 있습니다.

### 곡 데이터 확인

```powershell
# CSV를 불러와 목록만 확인
python -m rofebot_bridge --csv 곡순서.csv --list
```

### 단일 곡 테스트 (드라이런)

```powershell
python -m rofebot_bridge --csv 곡순서.csv --query "Binary World" --dry-run
```

`--dry-run` 옵션을 제거하면 실제로 게임 창을 포커싱하고 키 입력을 전송합니다.

## 웹 연동 (Tampermonkey 예시)

1. 브라우저 확장 프로그램(Tampermonkey 등)에 `web/rofebot-bridge.user.js` 파일을 추가합니다.
2. 스크립트 상단의 `TILE_SELECTOR`, `TITLE_SELECTOR`, `NUMBER_SELECTOR` 상수를 로페봇 페이지의 실제 구조에 맞게 조정합니다. (예: 타일이 `.record-card` 클래스를 사용한다면 `TILE_SELECTOR`에 `.record-card`를 추가)
3. 브리지 서버가 실행 중인 상태에서 로페봇 페이지를 새로고침합니다.
4. 원하는 곡 타일을 우클릭하면 브리지 서버가 해당 곡 정보를 받아 DJMAX 창으로 포커스를 옮기고 알파벳/방향키를 빠르게 입력합니다.

> **참고**: Tampermonkey 스크립트는 기본적으로 CORS가 허용된 `http://127.0.0.1:29184/select` 엔드포인트로 JSON 데이터를 전송합니다. 다른 포트/주소를 사용하면 스크립트의 `ENDPOINT` 값을 수정하세요.

## 실행 파일 만들기 (선택)

Windows에서 PyInstaller를 이용해 단일 실행 파일을 만들 수 있습니다.

```powershell
.\.venv\Scripts\activate
pip install pyinstaller
build_exe.bat
```

빌드가 끝나면 `dist/RofeBotDJMaxBridge.exe` 파일이 생성됩니다. 이 파일을 실행하면 백그라운드에서 브리지 서버가 실행됩니다.

## 환경 설정 옵션

| 옵션 | 설명 |
| --- | --- |
| `--csv` | 곡순서 CSV 파일 경로 |
| `--host` / `--port` | 로컬 HTTP 서버 주소와 포트 |
| `--window-title` | 포커싱할 게임 창 제목 (부분 일치 가능) |
| `--key-delay` | 키 사이 대기 시간 (초) |
| `--focus-delay` | 창 포커싱 후 대기 시간 (초) |
| `--dry-run` | 실제 키 입력 없이 동작 확인 |

## 개발자를 위한 테스트

```bash
$ python -m pip install -e .[dev]
$ python -m pytest
```

## 라이선스

이 저장소의 모든 코드는 MIT 라이선스를 따릅니다.
