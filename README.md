# Tin Oxo Studio 4.3.0

**Sn 옥소 클러스터 편집기를 localhost 웹 브라우저에서 실행합니다.** 기존 RDKit/ASE 계산 기능과 Gaussian 16 입력 생성기를 Python 서버에서 사용하고, 글씨와 구조 화면은 접속한 브라우저에서 표시합니다. 웹 모드에는 Tk, X11, Node.js, 외부 CDN이 필요하지 않습니다.

## 4.3 브라우저 자동 열기 수정

4.2는 SSH 환경 변수가 있으면 주소를 출력한 뒤 브라우저 자동 열기를 생략했습니다. 4.3은 **4.1처럼 기본 브라우저에 접속 주소를 전달**하도록 복원했습니다. `--no-browser`를 명시한 경우에만 자동 열기를 생략하며, 기존 `--open-browser` 명령도 계속 지원합니다. OS가 브라우저를 열지 못하면 서버를 유지하면서 전체 접속 주소와 안내를 출력합니다.

`main`은 항상 최신 검증 버전을 가리킵니다. 버전별 코드는 `ver-4.3` 같은 브랜치에도 보존합니다.

## 4.2 성능 개선

회전 중 원자·결합 그래픽을 다시 만들지 않고 카메라 값만 GPU에 전달합니다. 리간드 부착과 겹침 정리는 접촉 검사 자료를 재사용하고, 같은 리간드를 여러 자리에 붙일 때는 생성한 조각을 재사용합니다. 탐색 후보 수와 접촉 기준은 유지합니다.

편집은 바뀐 데이터만 복사·전송하며, 구조 보관함에는 현재 필요한 요약만 전송합니다. 자동 저장은 화면 응답과 분리하고 연속 편집을 묶어 처리합니다. 큰 검사 표는 페이지로 나누고, 숨겨진 표와 바뀌지 않은 화면은 다시 만들지 않습니다. 화면 설정에서 3D 품질(자동/속도 우선/고화질)과 목표 프레임을 선택할 수 있습니다. 이 설정은 버튼·메뉴의 글씨 해상도와 별개입니다.

업데이트하려면 기존 서버를 **Ctrl+C로 종료**한 다음 아래 ZIP 전체를 새 폴더에 풀어 실행하세요. 실행 화면의 버전이 **4.3.0**인지 확인하고, 열려 있던 탭은 새로 고침하세요. 기존 작업은 동일한 설정 폴더에서 복구합니다.

[**최신 버전 ZIP 다운로드 (main)**](https://github.com/jinstone2001-stack/Ligand-/archive/refs/heads/main.zip) · [4.3 고정 버전](https://github.com/jinstone2001-stack/Ligand-/archive/refs/heads/ver-4.3.zip) · [측정·검증 결과](VALIDATION.md) · [전체 작업 기록](04.ligand.md)

## 설치

```bash
conda env create -f environment.yml
conda activate tinoxo
```

이미 Python 환경이 있다면 `python -m pip install -r requirements.txt`로 설치합니다.

## 실행 및 포트 선택

```bash
python TinOxoStudio.py
```

터미널의 **접속 포트 [8765]:**에 원하는 번호를 입력하면 해당 주소가 기본 웹 브라우저에서 자동으로 열립니다. Enter는 8765를 사용합니다. 포트를 미리 지정할 수도 있습니다.

```bash
python TinOxoStudio.py --port 8888
```

접속 주소는 `http://127.0.0.1:8888/#token=…` 형식으로 출력됩니다. 자동 열기가 안 되면 **터미널의 전체 주소**를 복사해 브라우저에서 여세요. 토큰은 실행마다 바뀌며 처음 접속 후 주소 표시줄에서 제거됩니다. 사용 중인 포트는 덮어쓰지 않고 오류와 다른 포트 지정 예를 표시합니다. `--port 0`은 빈 포트를 자동으로 선택합니다.

- 자동 브라우저 열기 끄기: `python TinOxoStudio.py --port 8888 --no-browser`
- 저장 파일로 시작: `python TinOxoStudio.py examples/Sn12_Methyl.tinoxo.json --port 8888`
- 복구 대신 빈 코어로 시작: `python TinOxoStudio.py --port 8888 --fresh`
- 기존 Tk 편집기: `python TinOxoStudio.py --native` (Tk/X11 환경 필요)
- 서버 종료: 실행 터미널에서 **Ctrl+C**

## HPC / SSH

PC에서 포트 전달로 접속한 다음, 열린 SSH 터미널에서 서버를 실행합니다. 두 포트 번호를 같게 사용하면 출력된 주소를 그대로 열 수 있습니다.

```bash
# PC에서 실행
ssh -L 8888:127.0.0.1:8888 user@hpc-server

# 접속한 HPC 터미널에서 실행
conda activate tinoxo
python TinOxoStudio.py --port 8888 --no-browser
```

PC의 브라우저에서 HPC 터미널에 출력된 전체 주소를 엽니다. **X11 전달은 필요하지 않습니다.** 자동 열기는 Python이 실행되는 컴퓨터의 기본 브라우저를 대상으로 합니다. 따라서 포트 전달로 PC 브라우저를 사용할 때는 위처럼 서버를 `--no-browser`로 실행하세요. 4.3은 SSH 환경 변수만으로 자동 열기를 생략하지 않습니다.

## 제공 기능

- Sn12·Sn6·Sn3 코어와 예제, 모든 Sn 선택, Sn12 OH 6자리 준비
- 브라우저 내 회전·이동·휠 확대, 단일/다중/사각형 원자 선택, 고정 배율
- 리간드 라이브러리/사용자 SMILES, SVG 결합 원자 선택 팝업, 공통/개별 계획 일괄 적용
- 원자 좌표·형식전하·동위원소·고정·색상 편집, R/L/P/추가 자리 편집
- RDKit ETKDG + MMFF94/UFF, 백그라운드 계산과 취소, Sn–C 길이 변경
- 결합 후보/수동 편집, 접촉 검사, 거리·각도·이면각, 공명식 확인
- Gaussian 방법·기저함수 통합, 간편/커스텀 설정, 원소별 기저/ECP, 입력 다운로드/서버 저장
- 실행 취소/복원, 구조 보관함, 프로젝트 자동 복구, JSON/XYZ/SDF/PDB/CSV/보고서·PNG/SVG 내보내기
- 한글/영문 글꼴·크기·색상·원소 색상, 다크/라이트

원자 선택·회전은 브라우저 안에서 처리합니다. WebGL을 사용할 수 없으면 Canvas 2D로 대체합니다. SMILES 생성·힘장·검사·Gaussian 구문은 기존 Python 코드를 재사용합니다. 과학적 범위와 파일 동작은 [한국어 설명서](README_KO.md)를 참고하세요.

## 저장과 복구

편집 결과는 서버의 `~/.config/tinoxo-studio/web-workspace.json`에 백그라운드로 원자적으로 자동 저장됩니다. 하단의 **자동 저장됨** 표시로 완료를 확인하세요. 연속 편집은 약 250ms 동안 묶어 저장하며, Ctrl+C 정상 종료는 남은 저장을 마친 뒤 끝납니다. 저장 오류는 하단에 표시합니다. 다음 실행 시 복구하며, `--config-dir DIR`로 작업 공간을 나눌 수 있습니다. 여러 서버 인스턴스를 쓰려면 각각 다른 설정 폴더를 지정하세요.

**프로젝트 저장 → JSON 다운로드**는 접속한 PC에 저장합니다. **서버 경로에 저장**은 Python 서버의 경로에 저장합니다. 전체 프로젝트 JSON에는 구조·보관함·설정·즐겨찾기가 포함됩니다.

## 검증 및 다운로드

```bash
python TinOxoStudio.py --check
python -m unittest discover -s tests -v
```

[검증 기록](VALIDATION.md)에는 HTTP/계산/DOM 검사와 실제 브라우저 화면 검증의 제한을 구분해 기록했습니다. [변경 기록](CHANGELOG.md) / [출처·의존성](THIRD_PARTY_NOTICES.md)

[**최신 main 전체 소스 ZIP 다운로드**](https://github.com/jinstone2001-stack/Ligand-/archive/refs/heads/main.zip) · [**ver-4.3 고정 버전 ZIP**](https://github.com/jinstone2001-stack/Ligand-/archive/refs/heads/ver-4.3.zip) — 압축을 푼 폴더에서 실행하세요. `.py`만 복사하지 말고 `TinOxoWeb.py`, `web/`, `fonts/`도 함께 사용하세요.

## 라이선스

[EDUCATIONAL USE ONLY LICENSE](LICENSE): 비상업적 교육 목적의 원본 사용만 허용하며 코드 수정·재배포·상업적 사용은 허용하지 않습니다. 구체적인 범위와 예외는 LICENSE를 따릅니다. 제3자 구성요소는 각 라이선스를 따릅니다.
