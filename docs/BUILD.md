# Build from source

Requires Python 3.12. Build separately on Windows and Linux.

```sh
python -m venv .venv
# Linux: . .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt pyinstaller==6.20.0
python main.py
```

`run-linux.sh` and `run-windows.bat` also run the application from source.

```sh
python -m unittest discover -s tests -v
python build.py
python scripts/smoke_desktop.py --updates
```

The interface artwork is generated from code. After changing `deadlock_fps/theme.py` or `scripts/make_assets.py`, regenerate it and the documentation images (PySide6 only, no game or network needed):

```sh
python scripts/make_assets.py       # assets/ and docs/contact-sheet.png
python scripts/make_screenshots.py --docs
```

The design rules are in [DESIGN.md](DESIGN.md).

Interface text goes through `tr()` (`deadlock_fps/i18n.py`). English lives in `deadlock_fps/lang_en.py` and Arabic for the crosshair workspace in `deadlock_fps/lang_ar.py`. After adding text:

```sh
python scripts/i18n_tool.py wrap    # wrap new strings in tr()
python scripts/i18n_tool.py check   # fail if a translation is missing
```

Tests read the code's own text (language `source`), so they do not depend on the catalogues.

Portable packages are written to `dist/`. CI tests and builds on both platforms. Application data is stored outside the portable folder. See [third-party notices](../THIRD_PARTY.md) for content and dependency licenses.
