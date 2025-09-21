# Ropebot ↔ DJMAX Bridge

이 저장소는 로페봇(b300.vercel.app)과 PC에서 실행 중인 **DJMAX RESPECT V**를 연결하는 로컬 브리지를 제공합니다. 프로그램을 실행하면 로컬 HTTP 서버가 열리고, 로페봇에서 타일을 우클릭했을 때 해당 곡으로 이동하도록 게임 클라이언트에 빠르게 키 입력을 전송합니다.

## 구성 요소

- `곡순서.csv` : 곡 타일 번호(titleNumber)와 제목(title)을 한 줄씩 기록한 CSV 파일입니다. 파일에 적힌 순서대로 각 알파벳 그룹의 곡 순번이 계산됩니다. 필요에 맞게 자유롭게 교체할 수 있습니다.
- `src/djmax_router/` : 곡 목록을 로드하고, DJMAX 창에 포커스를 맞춘 뒤 알파벳과 방향키 입력을 보내는 파이썬 코드입니다.

## 동작 방식

1. `곡순서.csv`를 불러와 알파벳별로 곡을 묶고, 같은 알파벳 내에서는 CSV에 적힌 순서를 유지합니다.
2. 로컬 HTTP 서버(`http://127.0.0.1:47815`)에서 다음 엔드포인트를 제공합니다.
   - `GET /status` : 서버 상태와 로드된 곡 개수를 반환합니다.
   - `GET /songs?group=a` : 전체 곡 목록 또는 특정 알파벳 그룹 목록을 반환합니다.
   - `POST /play` : JSON 페이로드(예: `{ "tileId": "0123" }` 또는 `{ "title": "Far East Princess" }`)를 받아 해당 곡으로 이동하기 위한 키 입력을 전송합니다.
3. `POST /play`를 받으면 먼저 곡 제목의 첫 글자(알파벳)를 입력하고, 같은 알파벳 그룹에서 목표 곡까지 필요한 만큼 아래 방향키(`↓`)를 빠르게 전송합니다.

> **참고**: 윈도우 전용 기능이므로, Windows가 아닌 OS에서는 자동으로 "dry-run" 모드가 활성화되어 실제 키 입력 대신 로깅만 수행합니다.

## 실행 방법

### 1. 파이썬으로 직접 실행

1. Python 3.10 이상을 설치합니다.
2. 필요한 패키지를 설치합니다.
   ```powershell
   pip install -r requirements.txt
   ```
3. `곡순서.csv`를 원하는 내용으로 수정합니다.
4. 프로그램을 실행합니다.
   ```powershell
   python -m djmax_router --log-level INFO
   ```
   기본적으로 `127.0.0.1:47815`에서 서버가 시작됩니다.

5. 로페봇에서 사용할 JavaScript(예시):
   ```javascript
   async function triggerSong(tileId) {
     await fetch('http://127.0.0.1:47815/play', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ tileId })
     });
   }
   ```

### 2. 실행 파일(.exe) 만들기

Windows 환경에서 다음 명령으로 단일 실행 파일을 만들 수 있습니다.

```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --name RopebotDjmaxBridge src/djmax_router/main.py
```

빌드가 끝나면 `dist/RopebotDjmaxBridge.exe`가 생성됩니다. 실행 파일과 **같은 폴더**에 최신 `곡순서.csv`를 복사하면, 추가 인자 없이도 곡 목록이 자동으로 로드됩니다.

> PyInstaller로 빌드할 때 다른 리소스를 함께 묶고 싶다면 `--add-data "곡순서.csv;."` 옵션을 추가할 수 있습니다.

### 3. 옵션

- `--host` : 바인드할 인터페이스를 지정합니다. (기본값 `127.0.0.1`)
- `--port` : 서버 포트를 지정합니다. (기본값 `47815`)
- `--csv` : 기본 위치 대신 다른 CSV 파일을 명시적으로 지정합니다.
- `--dry-run` : 실제 키 입력 대신 로깅만 수행합니다. (테스트용)
- `--log-level` : 로깅 레벨(`DEBUG`, `INFO`, `WARNING`, 등)

## 곡 데이터 형식

`곡순서.csv`는 UTF-8 인코딩의 헤더 포함 CSV 파일이어야 하며, 최소한 `titleNumber`와 `title` 열이 필요합니다. 추가 열(`tileId` 등)을 포함해도 무방하며, 빈 줄은 무시됩니다.

예시:

```csv
titleNumber,title,tileId
0001,Airwave,airwave
0002,Back to the Future,back-to-the-future
0003,Collision,collision
```

- `titleNumber` : 로페봇 타일 ID와 일치하도록 설정하세요.
- `title` : 게임 내 곡 제목.
- `tileId` : 웹 타일에서 전달되는 ID가 `titleNumber`와 다를 경우에 사용합니다.

## 개발 팁

- 서버가 정상적으로 실행 중인지 확인하려면 브라우저에서 `http://127.0.0.1:47815/status`로 접속해보세요.
- `--dry-run` 옵션을 사용하면 DJMAX가 설치되지 않은 PC에서도 동작을 검증할 수 있습니다.
- Windows 방화벽에서 로컬 포트 접근이 차단되지 않았는지 확인하세요.

## 라이선스

이 프로젝트는 MIT License로 배포됩니다.
