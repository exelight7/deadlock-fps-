# Third-party materials

Application source is MIT (LICENSE). That license does not relicense Valve content, supplied reference configuration, imported community VPK mods, or third-party dependencies.

- PySide6 / Qt for Python: LGPLv3 / GPLv3 / commercial licensing as applicable. Qt libraries remain separate files in the portable distribution. Corresponding source and notices: https://code.qt.io/pyside/pyside-setup.git and https://code.qt.io/qt/ ; https://www.qt.io/licensing/open-source-lgpl-obligations . LGPLv3 and GPLv3 license texts are included in assets/licenses, bundled under _internal/assets/licenses. Any license/notice files supplied by installed dependency distributions are also copied into notices. Use a compatible modified Qt library by replacing dynamic libraries in the extracted portable folder.
- psutil: BSD-3-Clause; https://github.com/giampaolo/psutil
- PyInstaller: GPL with bootloader exception; https://pyinstaller.org/en/stable/license.html
- Original supplied `video.txt`, `gameinfo.gi`, `readme.txt`: preserved as user-provided reference data. Authorship/license not established; excluded from the application's MIT grant.
- Daylock, Remove Name Tags, Old Healthbars, Sinner Fix: imported at runtime from user-supplied files. Original authors/licenses were not supplied. The repository and downloadable builds do not distribute these VPKs.
- Process Lasso and RTSS installers: audited as supplied binary attachments, not executed, verified safe, bundled, or required. Their licenses and behavior are outside this project.
- Deadlock and Steam names belong to their respective owners. This is an independent community utility.

- ServerPickerX by FN-FAL113 and contributors: https://github.com/FN-FAL113/server-picker-x (GPL-3.0). Supplied binary inspected as an integration reference. Toolbox implements the relay selection workflow independently; upstream code/assets/binaries are not bundled or relicensed. Valve's public SDR catalog snapshot is cached data, not part of the MIT source grant.

- Noto Sans Arabic: bundled for consistent Arabic typography on Windows and Linux; SIL Open Font License 1.1, included at `assets/licenses/Noto-OFL.txt`.
- User-selected artwork and eye logo: supplied via the user's Pinterest references; see `assets/artwork/SOURCES.md`. Original ownership remains with the artists/owners; these images are excluded from the source MIT license.

- Country/territory flag SVGs: flag-icons by Panayiotis Lipiridis and contributors, MIT. Upstream https://github.com/lipis/flag-icons ; pinned commit in `assets/flags/SOURCE.md`, full license in `assets/licenses/flag-icons-MIT.txt`. The unknown-region globe is original code-native SVG.
