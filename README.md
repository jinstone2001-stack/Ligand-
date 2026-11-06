# Ligand-

**Tin Oxo Studio 4.0** — Sn 옥소 클러스터를 설계하는 Python/Tkinter 기반 편집기입니다. HPC에서 MobaXterm의 X11 전달을 통해 실행할 수 있으며, 브라우저나 OpenGL이 필요하지 않습니다.

## 설치 및 실행

```bash
conda env create -f environment.yml
conda activate tinoxo
python TinOxoStudio.py
```

예제 구조 열기:

```bash
python TinOxoStudio.py examples/Sn12_Methyl.tinoxo.json
```

MobaXterm의 X server와 SSH X11 forwarding을 켠 상태에서 실행하세요. 설치·화학 처리·저장 형식·Gaussian 설정의 자세한 설명은 [한국어 사용 설명서](README_KO.md)를 참고하세요.

## 4.0 업데이트

- 리간드를 선택하면 고해상도 2D 구조 팝업에서 결합 원자를 클릭하거나 목록으로 고릅니다. 선택한 원자 번호를 실제 부착과 프로젝트 저장에 반영합니다.
- 같은 결합 원자를 선택된 여러 부모 원자에 일괄 적용합니다. L/P 가교는 선택한 donor O와 같은 연결부의 다른 O를 함께 사용합니다.
- 한글 글꼴의 X11 윤곽선 렌더링·안티앨리어싱·힌팅을 설정하고 작은 설명 글꼴을 보완했습니다. Windows는 Tk 생성 전에 DPI 처리를 설정합니다.
- Gaussian의 **간편 설정 / 커스텀 설정**에서 방법과 기저함수를 함께 조절합니다. 원소별 기저/ECP, 외부 GenECP, SCF/물성도 지원합니다.
- 선택 칸의 기본 문자 폭을 32→16, 고급 항목은 52→26으로 줄이고 창 확대 시 늘어나지 않게 했습니다.

## 기존 글꼴 / 뷰어 기능

- 한글 글꼴은 맑은고딕/굴림, 영문은 Arial/Calibri 중 선택합니다. 실제 설치 상태와 대체 글꼴을 표시합니다.
- Windows 글꼴이 없는 서버에서도 동봉한 나눔고딕/Carlito를 오프라인으로 사용합니다. 정확한 Windows 글꼴이 필요하면 HPC에 TTF/TTC를 추가하세요.
- 회전 시 도형 재생성을 없애고, 이벤트 병합과 경량 표시로 프레임 처리를 줄였습니다.
- 회전·이동·창 크기·H 표시 변경이 배율을 바꾸지 않습니다. 휠로 확대하고 맞춤 버튼으로 전체 구조를 다시 맞춥니다.
- [변경 기록](CHANGELOG.md) / [글꼴 설치 안내](fonts/README.md)

## 주요 기능

- Sn12·Sn6·Sn3 코어, 리간드 부착 및 원자·결합 편집
- RDKit ETKDG 및 MMFF94/UFF 초기 구조 정리
- 범용 리간드 목록과 사용자 SMILES 보관함
- 공명식·방향족·공액 결합 확인, 제한된 등가 말단 O 거리 보정
- 결합 정보 검사, 거리·결합각·이면각 측정, 접촉 검사
- 다크모드, 글꼴·원자 색상 설정, VESTA 기본 색상
- Gaussian 16 입력 생성과 서버 디렉토리 저장
- 프로젝트 저장·복구, 실행 취소·복원, 여러 구조 보관, 구조·이미지 내보내기

## 파일 및 검증

전체 다운로드: [TinOxoStudio 4.0 브랜치 ZIP](https://github.com/jinstone2001-stack/Ligand-/archive/refs/heads/ver-4.0.zip) — 최신 Python 코드, 글꼴, 예제, 설명서를 함께 포함합니다. 압축을 푼 폴더에서 위 설치·실행 명령을 사용하세요.

```bash
python TinOxoStudio.py --check
python -m unittest discover -s tests -v
```

리간드 결합 원자·글꼴·UTF-8/CP949·고정 배율·화학/파일·Gaussian UI를 포함한 72개 검사를 로컬 X11/Tk 8.6에서 통과했습니다. X11 DISPLAY가 없으면 GUI 검사는 생략합니다. 실제 HPC 연결과 Gaussian 16 계산은 시험하지 않았습니다. [검증 기록](VALIDATION.md)과 [출처·의존성 고지](THIRD_PARTY_NOTICES.md)를 확인하세요.

## 라이선스

[EDUCATIONAL USE ONLY LICENSE](LICENSE)를 적용합니다. 비상업적 교육 목적의 원본 사용만 허용하며 코드 수정·재배포·상업적 사용은 허용하지 않습니다. 구체적인 범위와 예외는 LICENSE 원문을 따릅니다. 제3자 구성요소는 각각의 라이선스를 따릅니다.
