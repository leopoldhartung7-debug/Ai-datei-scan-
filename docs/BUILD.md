# Build- & EXE-Anleitung

SmartFolders wird mit **PyInstaller** zu einem eigenständigen Programm gebündelt.
Das Bundle enthält die komplette Python-Laufzeit und alle Abhängigkeiten – der
Endnutzer braucht **kein** installiertes Python.

> Wichtig: PyInstaller kann **nicht** cross-kompilieren. Baue Windows-Builds auf
> Windows, macOS-Builds auf macOS usw.

## 1. Voraussetzungen

```bash
pip install -r requirements-dev.txt   # enthält pyinstaller
# (oder gezielt:)  pip install pyinstaller
```

Für ein vollwertiges Build vorher alle Laufzeit-Abhängigkeiten installieren
(`python install.py` oder `pip install -r requirements.txt`), damit PyInstaller
die KI-/OCR-Module mitnimmt.

## 2. Build starten

```bash
python build/build_exe.py            # Ein-Ordner-Build (schneller Start, empfohlen)
python build/build_exe.py --onefile  # einzelne Datei (langsamerer Start)
python build/build_exe.py --clean    # vorherige Artefakte entfernen
```

Ergebnis:

| Plattform | Artefakt |
|-----------|----------|
| Windows | `dist/SmartFolders/SmartFolders.exe` (bzw. `dist/SmartFolders.exe` bei `--onefile`) |
| macOS | `dist/SmartFolders.app` |
| Linux | `dist/SmartFolders/SmartFolders` |

Das Build-Skript setzt sinnvolle Defaults (`--noconsole`, versteckte Importe für
lazy geladene Module, `--collect-all` für `sentence-transformers`/`transformers`,
sofern installiert) und auf macOS `--windowed` + Bundle-Identifier.

## 3. Tesseract mitliefern (optional)

OCR benötigt die native Tesseract-Engine. Optionen:

1. **Nutzer installiert Tesseract selbst** (Standard). Ohne Tesseract läuft die
   App weiter, nur OCR ist deaktiviert.
2. **Tesseract mitbündeln:** Tesseract-Binaries und `tessdata` ins Bundle kopieren
   und beim Start `pytesseract.pytesseract.tesseract_cmd` auf den gebündelten Pfad
   setzen. PyInstaller-Aufruf um `--add-binary` / `--add-data` ergänzen, z. B.:

   ```bash
   # Windows-Beispiel
   pyinstaller ... --add-binary "C:\\Program Files\\Tesseract-OCR\\tesseract.exe;tesseract" \
                   --add-data   "C:\\Program Files\\Tesseract-OCR\\tessdata;tessdata"
   ```

## 4. Installer / Distribution

* **Windows:** Aus dem Ein-Ordner-Build mit **Inno Setup** oder **NSIS** einen
  klassischen Setup-Assistenten erstellen (Startmenü-Eintrag, Autostart-Option,
  Deinstaller). Code-Signing-Zertifikat empfohlen, um SmartScreen-Warnungen zu
  vermeiden.
* **macOS:** `dist/SmartFolders.app` in ein **DMG** packen (`create-dmg`),
  anschließend signieren & notarisieren (`codesign`, `notarytool`).
* **Linux:** Ordner als `.tar.gz` ausliefern oder ein **AppImage** erstellen.

## 5. Build-Größe reduzieren (optional)

Die KI-Bibliotheken machen den Großteil der Bundle-Größe aus. Für eine schlanke
Variante ohne semantische KI:

```bash
pip uninstall sentence-transformers transformers torch
python build/build_exe.py
```

Die Suche nutzt dann automatisch den Hashing-Fallback – kleineres Bundle, weiter
voll funktionsfähig.

## 6. Reproduzierbarkeit

* Build in einem frischen `.venv` ausführen.
* Versionen über `requirements.txt` pinnen.
* `python build/build_exe.py --clean` vor jedem Release-Build.
