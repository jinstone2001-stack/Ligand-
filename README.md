# Ligand-

**Tin Oxo Studio 3.0** — Sn 옥소 클러스터를 설계하는 Python/Tkinter 기반 편집기입니다. HPC에서 MobaXterm의 X11 전달을 통해 실행할 수 있으며, 브라우저나 OpenGL이 필요하지 않습니다.

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

전체 다운로드 패키지: [TinOxoStudio_Python_3_0_Package.zip](dist/TinOxoStudio_Python_3_0_Package.zip)

```bash
python TinOxoStudio.py --check
python -m unittest discover -s tests -v
```

로컬 화학/파일 검사 30개와 X11 GUI 검사 5개를 실행했습니다. X11 DISPLAY가 없으면 GUI 검사는 생략합니다. 실제 HPC 연결과 Gaussian 16 계산은 시험하지 않았습니다. [검증 기록](VALIDATION.md)과 [출처·의존성 고지](THIRD_PARTY_NOTICES.md)를 확인하세요.

## 라이선스

[EDUCATIONAL USE ONLY LICENSE](LICENSE)를 적용합니다. 비상업적 교육 목적의 원본 사용만 허용하며 코드 수정·재배포·상업적 사용은 허용하지 않습니다. 구체적인 범위와 예외는 LICENSE 원문을 따릅니다. 제3자 구성요소는 각각의 라이선스를 따릅니다.
