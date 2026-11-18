# Tin Oxo Studio 5.2.0 — HTML

**Python 설치 없이 브라우저에서 실행하는 5.2 배포본입니다.**

[**웹에서 바로 실행**](https://jinstone2001-stack.github.io/Ligand-/) · [단일 HTML 다운로드](https://raw.githubusercontent.com/jinstone2001-stack/Ligand-/html/index.html) · [전체 ZIP](https://github.com/jinstone2001-stack/Ligand-/archive/refs/heads/html.zip) · [지원 / 제외 기능](HTML_SUPPORT.md) · [검증 기록](VALIDATION.md)

오프라인에서는 `index.html`을 다운로드해 최신 브라우저에서 여세요. 이 파일 하나에 화면·JavaScript·코어와 내장 리간드 좌표가 포함되어 있어 Python, 서버, CDN이나 인터넷 연결이 필요하지 않습니다. 데스크톱과 모바일 터치를 지원합니다.

- Sn3/Sn6/Sn12 코어, 내장 리간드 43종과 예제용 가교 좌표, 결합 원자 선택 및 R/L/P 자리 편집.
- 5.2 외향 배치와 다중 코어 진입 검사, 원자·결합 편집, 3D 뷰어, 거리·각도·접촉 검사.
- 실행 취소/복원, 브라우저 자동 저장, 구조 보관함, 프로젝트 JSON 및 실행용 HTML 저장.
- XYZ/MOL·SDF/PDB 입출력, PNG/SVG/CSV/검사 보고서, Gaussian `.gjf` 입력 생성.

Python 전용인 임의 SMILES 생성, MMFF/UFF·SciPy 연속 최적화, 실행 중 공명·원자가 분석, MOL2/CIF/GRO/PQR 읽기, Tk/X11·서버 경로 저장은 제외했습니다. HTML의 겹침 줄이기는 단일점 리간드의 결합축 강체 회전으로 제한됩니다. [전체 제외 목록과 한계](HTML_SUPPORT.md)를 확인하세요.

**프로젝트 JSON을 별도 다운로드해 백업하세요.** 브라우저 저장소는 기기·경로에 따라 달라지고 지워질 수 있습니다. Gaussian 입력은 생성만 하며 계산 실행이나 HPC 제출은 하지 않습니다.

`html` 브랜치에는 정적 HTML·문서·라이선스만 배포합니다. Python 원본 패키지는 기존 [main](https://github.com/jinstone2001-stack/Ligand-/tree/main)에서 제공합니다. HTML 앱 안의 **사용 안내 / 제외 기능**에서도 지원 범위와 출처를 볼 수 있습니다.

[라이선스](LICENSE) · [제3자 표시 / 좌표 출처](THIRD_PARTY_NOTICES.md) · [파일 SHA-256](SHA256SUMS.txt)
