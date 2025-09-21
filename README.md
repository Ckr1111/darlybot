# Darlybot Helper

로페봇([b300.vercel.app](https://b300.vercel.app))과 PC에서 실행 중인 **DJMAX RESPECT V** 사이를 연결해 주는 로컬 도우미입니다. 프로그램을 켜면 로컬 HTTP API가 열리며, 로페봇에서 곡을 선택했을 때 게임 안에서 해당 곡까지 빠르게 이동하기 위한 입력(`A~Z`, 마우스 휠, `PageUp`, `PageDown`)을 자동으로 전송합니다.

> ⚠️  실제 DJMAX 클라이언트로 키 입력을 보내려면 Windows 환경에서 실행해야 하며 `DJMAX RESPECT V.exe`가 이미 실행 중이어야 합니다.

## 구성 요소

- `곡순서.csv` : 게임 내 곡 순서를 정의하는 데이터. 첫 번째 열은 `title_number`, 두 번째 열은 `title`입니다. 저장소에는 예시 데이터가 포함되어 있으며 실제 사용 시에는 최신 곡 순서로 교체하세요.
- Python 애플리케이션 : CSV를 읽어 곡 위치를 계산하고, HTTP API를 통해 외부 명령을 받아 DJMAX 창으로 키 입력을 전송합니다.
- 로페봇(b300.vercel.app) : 사이트에 기본으로 포함된 사용자 스크립트가 우클릭한 타일의 곡 정보를 로컬 API로 전달합니다. 별도 설치 없이 로컬 서버만 켜면 됩니다.

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
| GET    | `/`         | 실행 중인 서버 정보를 제공하는 HTML 페이지 |
| GET    | `/ping`     | 서버 상태 확인 |
| GET    | `/songs`    | 로드된 곡 목록(JSON) |
| POST   | `/navigate` | `{ "title_number": "0001" }` 또는 `{ "title": "TITLE" }` 를 전달하면 해당 곡까지 이동 |

`/navigate` 호출 시 응답으로 전송된 키 시퀀스와 처리 결과가 반환됩니다.

> ℹ️  곡 제목이 한글 또는 특수문자로 시작하면 게임에서 바로 이동할 수 있는 알파벳 단축키가 없기 때문에 먼저 `a` 키를 눌러 알파벳
> 모드로 진입한 뒤, `PageUp`(한글) 또는 `PageDown`(특수문자) 키를 보내 해당 구간으로 이동합니다. 이후에는 마우스 휠을 위/아래로
> 움직여 원하는 곡까지 이동합니다.

### 로페봇과 연동하기

로페봇 페이지에는 이미 우클릭 이벤트로 `/navigate` 엔드포인트를 호출하는 스크립트가 내장되어 있습니다. Darlybot Helper를 실행한 뒤 [b300.vercel.app](https://b300.vercel.app)에서 타일을 우클릭하면 자동으로 곡 정보가 전송되고, 실행 중인 DJMAX에 키 입력이 전달됩니다.

다른 애플리케이션과 연동하고 싶다면 `/navigate` 엔드포인트로 `title_number` 또는 `title` 값을 포함한 JSON 페이로드를 POST하면 동일한 동작을 구현할 수 있습니다.

## 실행 파일 만들기 (PyInstaller)

Windows 환경에서 손쉽게 실행할 수 있도록 PyInstaller를 사용한 단일 EXE 패키징을 지원합니다.

```bash
pip install pyinstaller
pyinstaller --name darlybot --onefile -m darlybot
```

위 명령은 `-m darlybot` 으로 `src/darlybot/__main__.py` 엔트리 포인트를 실행하도록 패키징합니다. 애플리케이션은 기본적으로 프로그램 내부에 내장된 곡 순서 데이터를 사용하므로, 완성된 `dist/darlybot.exe` 만으로 실행할 수 있습니다.

최신 데이터로 교체하려면 원하는 `곡순서.csv` 파일을 실행 파일과 같은 폴더에 두거나 `--csv` 옵션으로 경로를 지정하세요. 내장 데이터는 `data/곡순서.csv` 파일과 동일하므로 저장소에서 직접 편집해도 됩니다.

## 테스트

```bash
pytest
```

테스트는 곡 순서 CSV 처리와 키 시퀀스 계산 로직을 검증합니다. Windows 입력 자동화 라이브러리는 모킹되어 테스트 환경에서도 안전하게 실행됩니다.

## 라이선스

MIT License
