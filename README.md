# 로페봇 ↔ DJMAX 연동 프로그램

로페봇(b300.vercel.app)에서 곡 타일을 우클릭하면 현재 실행 중인 **DJMAX RESPECT V** 로비로 이동하여 해당 곡을 빠르게 찾아주는 자동화 도구입니다. 프로그램을 실행하면 내장된 브라우저 창에서 로페봇이 열리고, 타일 우클릭 → "DJMAX으로 보내기"를 선택하면 게임 창을 활성화한 뒤 필요한 알파벳 키와 방향키 입력을 자동으로 전송합니다.

## 주요 기능

- 곡 순서를 나타내는 `곡순서.csv`를 기반으로 곡 탐색 경로 계산
- 알파벳 단축키 + 방향키 조합을 자동 입력하여 해당 곡 위치로 이동
- 로페봇 타일에 사용자 정의 컨텍스트 메뉴(우클릭 메뉴) 추가
- 선택 결과를 화면 우측 하단 토스트 메시지로 피드백
- Python 스크립트 그대로 사용하거나 PyInstaller로 손쉽게 `exe` 패키징 가능

## 폴더 구성

```
.
├── config.example.json   # 기본 설정 템플릿, 필요 시 config.json으로 복사
├── 곡순서.csv             # 곡 순서 데이터 (샘플)
├── loppebot_bridge/      # 연동 로직 모듈
├── main.py               # 실행 엔트리 포인트
└── requirements.txt      # 필요한 Python 패키지 목록
```

## 준비 사항

1. **Python 3.10+** (Windows 권장)
2. `곡순서.csv` 파일: 첫 행에 헤더(`title_number,title`)를 포함한 CSV 포맷이어야 하며, DJMAX 인게임 정렬과 동일한 순서로 곡을 나열합니다.
3. 로컬 PC에 DJMAX RESPECT V가 실행 중이어야 하며, 로비 화면에서 곡 리스트가 포커스 가능한 상태여야 합니다.

## 설치 방법

```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows PowerShell
pip install -r requirements.txt
```

> macOS, Linux에서도 스크립트 실행은 가능하지만 실제 키 입력 및 창 제어는 Windows에서만 보장됩니다.

## 설정(customize)

1. `config.example.json`을 복사하여 같은 위치에 `config.json`을 만듭니다.
2. 주요 항목 설명:
   - `web_url`: 로드할 로페봇 주소 (필요 시 테스트 서버 주소로 교체)
   - `window_title_candidates`: 게임 창 제목 후보. 한글/영문 버전 등 여러 값을 배열로 나열 가능
   - `press_enter`: 곡 위치에 도달한 뒤 Enter를 자동으로 누를지 여부
   - `tile_selector`, `title_attribute`, `title_fallback_selector`: 우클릭을 적용할 타일과 곡명을 추출하기 위한 선택자/속성 지정
   - `context_menu_text`: 우클릭 메뉴에 표시할 문구
   - `csv_path`: 곡 순서 CSV 파일 위치. 상대 경로는 `config.json` 기준으로 계산됩니다.

## 실행 방법

```bash
python main.py
```

프로그램 실행 시 pywebview 창이 열리고 로페봇이 표시됩니다. 곡 타일을 우클릭하면 "DJMAX으로 보내기" 메뉴가 표시되며 클릭 시 자동으로 게임 창이 활성화되고 키 입력이 전송됩니다.

## Windows용 exe 패키징

PyInstaller를 사용하면 독립 실행형 `exe`를 만들 수 있습니다. `config.json`과 `곡순서.csv`를 exe와 같은 폴더에 두면 됩니다.

```bash
pyinstaller --noconfirm --onefile --name "LoppeBridge" main.py
```

> 기본 설정에서는 실행 파일이 위치한 폴더의 `config.json`을 우선 사용합니다. 없을 경우 `config.example.json`이 자동으로 로드됩니다.

## 사용 시 주의 사항

- 게임 창이 최소화되어 있거나 다른 모니터에 있을 경우 자동으로 활성화되도록 시도합니다. 실패하면 화면 우측 하단 토스트로 오류가 출력됩니다.
- `곡순서.csv`는 반드시 인게임 정렬과 동일하게 유지해야 정확한 방향키 계산이 가능합니다.
- 곡명이 영문/숫자 혼용일 경우 공백·기호를 제거한 문자열로 비교하므로, CSV의 곡명 표기와 로페봇 타일의 표기가 가능한 한 일치하도록 구성하세요.
- 프로그램을 종료하려면 pywebview 창을 닫거나 `Alt+F4`를 누르면 됩니다.

## 트러블슈팅

| 증상 | 원인/해결 |
| --- | --- |
| "곡 정보를 찾을 수 없습니다" | CSV에 곡명이 없거나 표기가 일치하지 않습니다. 곡명을 다시 확인하고 CSV를 수정하세요. |
| "DJMAX RESPECT V 실행 중인지 확인해주세요" | 게임 창을 찾지 못했습니다. 게임이 실행 중인지, 제목이 설정 파일과 일치하는지 확인하세요. |
| 키 입력은 되었지만 다른 곡이 선택됨 | CSV 순서가 실제 게임 순서와 다르거나 중복 곡명이 존재합니다. `곡순서.csv`를 최신화하세요. |

## 라이선스

본 저장소는 사용자의 편의를 위해 제공되는 예제 코드이며 별도 라이선스는 명시하지 않았습니다. 필요한 경우 자유롭게 수정하여 사용하되, 게임 이용 약관 및 관련 법규를 준수하세요.
