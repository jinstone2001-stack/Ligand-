# Sources and third-party components

The Python application depends on separately installed RDKit (BSD license), ASE (LGPL), NumPy, SciPy, Pillow, and Python/Tk. Dependency binaries are not bundled. Consult the installed packages for their current license texts.

Core coordinates and attachment-site metadata are carried over from the user's TinOxoStudio.html v2.2, preserving source identifiers and explanatory notes. Sn12 coordinates originate from DOI 10.21942/uva.24574750 (CC BY 4.0), associated with DOI 10.1021/acs.jpcc.3c07480. Sn6 coordinates originate from DOI 10.1107/S160053681204888X. Original Sn3 coordinates are from DOI 10.1021/ic001088k; the Sn3O3 ring is an explicitly documented deletion-derived design backbone. The phosphinate motif reference is DOI 10.1021/ja00237a072.

Numeric element RGB values were compared with VESTA 3.5.8, https://jp-minerals.org/vesta/ . The source software and its distributed elements.ini file are not included. The program stores only the numeric color mapping and uses VESTA's generic XX grey for elements without a defined value. VESTA: K. Momma and F. Izumi, J. Appl. Crystallogr. 44, 1272–1276 (2011).

An embedded compressed copy of the user's existing standalone HTML editor provides compatibility export. It remains a v2.2 browser application; new native Python features are not represented as browser-native implementations. Its original code notices and coordinate provenance are preserved.

Gaussian is a separate product of Gaussian, Inc. The program generates input text only and does not include Gaussian software, basis-function coefficient files, or documentation copies. Official links and the documentation access record are in README_KO.md.

Versions 3.1 and later bundle unmodified NanumGothic-Regular.ttf and Carlito-Regular.ttf from google/fonts as offline fallback fonts. They remain under their SIL Open Font License 1.1 terms, reproduced in fonts/nanumgothic-OFL.txt and fonts/carlito-OFL.txt. The application's educational-use restriction does not replace these font licenses. Microsoft Malgun Gothic, Gulim, Arial and Calibri are selectable when locally installed; no Microsoft font binaries are included. Source URLs and SHA-256 values are recorded in fonts/README.md.
