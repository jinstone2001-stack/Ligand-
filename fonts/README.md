# Offline fallback fonts

These unmodified font files are bundled to keep Korean/English text readable on Linux HPC systems without Microsoft fonts.

| Font | Source | License |
|---|---|---|
| NanumGothic-Regular.ttf | https://github.com/google/fonts/tree/main/ofl/nanumgothic | nanumgothic-OFL.txt |
| Carlito-Regular.ttf | https://github.com/google/fonts/tree/main/ofl/carlito | carlito-OFL.txt |

They are registered privately with Fontconfig for this process. No administrator access, global font configuration change or runtime download is needed. The application license does not replace the font licenses.

The Korean dropdown offers Malgun Gothic (맑은고딕) and Gulim (굴림); the English dropdown offers Arial and Calibri. Exact Microsoft faces are used when installed. If missing, the UI explicitly reports fallback to NanumGothic/Carlito. Microsoft font binaries are not bundled.

To use Microsoft fonts, copy your authorized TTF/TTC files from the Windows Fonts folder to the HPC server using SFTP, then choose **화면 설정 → 글꼴 파일 추가**. The dialog browses the HPC filesystem. Alternatively put the files in `fonts/user/` or the directory specified by `TINOXO_FONT_DIR` before launching the app. User-added fonts are kept out of Git and are not included in the provided release archive.

Bundled font SHA-256:

- NanumGothic-Regular.ttf: 76f45ef4a6bcff344c837c95a7dcc26e017e38b5846d5ae0cdcb5b86be2e2d31
- Carlito-Regular.ttf: f6418f708baede9789daef5d458c0f53d2a888af9820e8062934e504fedc6595
