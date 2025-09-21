# Darlybot Helper

로페봇([b300.vercel.app](https://b300.vercel.app))과 PC에서 실행 중인 **DJMAX RESPECT V** 사이를 연결해 주는 로컬 도우미입니다. 프로그램을 켜면 로컬 HTTP API가 열리며, 로페봇에서 곡을 선택했을 때 게임 안에서 해당 곡까지 빠르게 이동하기 위한 키 입력(`A~Z`, 방향키)을 자동으로 전송합니다.

> ⚠️  실제 DJMAX 클라이언트로 키 입력을 보내려면 Windows 환경에서 실행해야 하며 `DJMAX RESPECT V.exe`가 이미 실행 중이어야 합니다.

## 구성 요소

- `곡순서.csv` : 게임 내 곡 순서를 정의하는 데이터. 첫 번째 열은 `title_number`, 두 번째 열은 `title`입니다. 저장소에는 예시 데이터가 포함되어 있으며 실제 사용 시에는 최신 곡 순서로 교체하세요.
- Python 애플리케이션 : CSV를 읽어 곡 위치를 계산하고, HTTP API를 통해 외부 명령을 받아 DJMAX 창으로 키 입력을 전송합니다.
- (선택) 브라우저 사용자 스크립트 : 로페봇 타일을 우클릭했을 때 로컬 API를 호출하도록 도와줍니다. `scripts/darlybot-userscript.js` 파일을 Tampermonkey 등에 등록하여 사용할 수 있습니다.

## 설치 및 실행

1. Python 3.10 이상과 [Poetry](https://python-poetry.org/) 혹은 `pip` 환경을 준비합니다.
2. 프로젝트 의존성을 설치합니다.

   ```bash
   pip install -e .
   # 또는 개발용 설치: pip install -e .[dev]
   ```

3. 애플리케이션을 실행합니다.

   ```bash
   python -m darlybot --csv /경로/곡순서.csv
   # 또는 설치 후에는 darlybot 명령을 직접 사용할 수 있습니다.
   darlybot --port 8972 --window-title "DJMAX RESPECT V"
   ```

   실행하면 기본적으로 `http://127.0.0.1:8972` 에서 REST API가 동작하며, 드라이런 모드(`--dry-run`)를 사용하면 실제 키 입력 없이 API를 테스트할 수 있습니다.

### 제공 API

| 메서드 | 경로        | 설명 |
| ------ | ----------- | ---- |
| GET    | `/ping`     | 서버 상태 확인 |
| GET    | `/songs`    | 로드된 곡 목록(JSON) |
| POST   | `/navigate` | `{ "title_number": "0001" }` 또는 `{ "title": "TITLE" }` 를 전달하면 해당 곡까지 이동 |

`/navigate` 호출 시 응답으로 전송된 키 시퀀스와 처리 결과가 반환됩니다.

### 로페봇과 연동하기

`scripts/darlybot-userscript.js` 파일은 로페봇 페이지에서 타일을 우클릭하면 자동으로 `/navigate` 엔드포인트를 호출하는 예시 Tampermonkey 스크립트입니다. 페이지 구조에 맞게 선택자를 수정한 후 사용하세요.

1. 크롬에서 Tampermonkey 확장 프로그램을 설치합니다.
2. 새 스크립트를 만들고 `scripts/darlybot-userscript.js` 내용을 붙여넣습니다.
3. 필요한 경우 `TILE_SELECTOR` 및 데이터 추출 로직을 수정하여 타일 요소에서 제목과 타이틀 번호를 읽어오도록 맞춥니다.
4. 스크립트를 저장한 후 [b300.vercel.app](https://b300.vercel.app) 페이지를 새로고침합니다.
5. 타일을 우클릭하면 로컬 서버에 곡 정보가 전송되고, 실행 중인 DJMAX에 키 입력이 전달됩니다.

## 실행 파일 만들기 (PyInstaller)

Windows 환경에서 손쉽게 실행할 수 있도록 PyInstaller를 사용한 단일 EXE 패키징을 지원합니다.

```bash
pip install pyinstaller
pyinstaller --name darlybot --onefile --add-data "곡순서.csv;." --add-data "scripts/darlybot-userscript.js;scripts" -m darlybot
```

빌드가 완료되면 `dist/darlybot.exe` 가 생성됩니다. `곡순서.csv` 파일을 실행 파일과 같은 폴더에 배치하면 애플리케이션이 자동으로 인식합니다. 다른 위치에 둘 경우 `--csv` 옵션으로 경로를 지정하세요.

## 테스트

```bash
pytest
```

테스트는 곡 순서 CSV 처리와 키 시퀀스 계산 로직을 검증합니다. Windows 입력 자동화 라이브러리는 모킹되어 테스트 환경에서도 안전하게 실행됩니다.

## 라이선스

MIT License
