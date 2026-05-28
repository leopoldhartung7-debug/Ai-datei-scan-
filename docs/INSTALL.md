# Installationsanleitung

SmartFolders läuft auf **Windows 10/11**, **macOS** (Intel & Apple Silicon) und
**Linux**. Empfohlen ist **Python 3.11 oder 3.12**.

## 1. Automatische Installation (empfohlen)

Der mitgelieferte Installer richtet alles ein – Python-Pakete, die native
Tesseract-OCR-Engine und das lokale KI-Modell:

```bash
git clone <repo-url> SmartFolders
cd SmartFolders
python install.py
```

Flags:

| Flag | Wirkung |
|------|---------|
| `--yes`, `-y` | Keine Rückfragen (CI/automatisiert). |
| `--minimal` | Nur Kern-Abhängigkeiten (ohne KI/OCR/Native). |
| `--venv` | Installiert in ein lokales `.venv`. |
| `--skip-tesseract` | Tesseract nicht installieren. |
| `--skip-model` | KI-Modell nicht vorab herunterladen. |

Der Installer nutzt automatisch den passenden Paketmanager für Tesseract:

* **Windows:** `winget` (UB-Mannheim.TesseractOCR) oder `choco`
* **macOS:** `brew install tesseract tesseract-lang`
* **Linux:** `apt` / `dnf` / `pacman`

## 2. Manuelle Installation

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### Tesseract (für OCR) manuell

* **Windows:** Installer von <https://github.com/UB-Mannheim/tesseract/wiki>.
  SmartFolders erkennt den Standardpfad automatisch.
* **macOS:** `brew install tesseract tesseract-lang`
* **Linux (Debian/Ubuntu):** `sudo apt install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng`

OCR ist optional – fehlt Tesseract, deaktiviert SmartFolders die OCR-Funktion und
läuft normal weiter.

### Optionale KI-Extras

```bash
pip install ".[ai]"     # sentence-transformers + transformers (semantische Suche)
pip install ".[ocr]"    # pytesseract + pdf2image + Pillow
pip install ".[media]"  # ImageHash + PyMuPDF (ähnliche Bilder, PDF-Text)
```

Ohne `[ai]` nutzt die Suche einen reinen-Python-Fallback (geringere Qualität,
aber voll funktionsfähig und offline).

## 3. Starten

```bash
python -m smartfolders              # Desktop-App
python -m smartfolders --minimized  # versteckt im System-Tray starten
python -m smartfolders --headless   # ohne GUI (z. B. auf Servern)
```

Beim ersten Start führt ein **Onboarding-Assistent** durch die Auswahl der
überwachten Ordner und die Hardware-Optimierung.

## 4. Speicherorte

| Inhalt | Pfad (über `platformdirs`) |
|--------|-----------------------------|
| Einstellungen | `…/SmartFolders/settings.json` (User-Config-Dir) |
| Datenbank | `…/SmartFolders/smartfolders.db` (User-Data-Dir) |
| Logs | `…/SmartFolders/smartfolders.log` (User-Log-Dir) |
| KI-Modell-Cache | `~/.cache/huggingface` (Standard von sentence-transformers) |

Auf einer minimalen Installation ohne `platformdirs` fällt SmartFolders auf
`~/.smartfolders/` zurück.

## 5. Deinstallation

```bash
pip uninstall smartfolders
```

Anschließend optional die Daten-/Config-Verzeichnisse aus Schritt 4 löschen.

## Fehlerbehebung

* **`No module named smartfolders`** – aus dem Projektordner starten oder das
  Paket mit `pip install -e .` installieren.
* **Qt startet nicht / `libEGL` fehlt (Linux)** – `sudo apt install libegl1
  libxkbcommon0 libdbus-1-3 libfontconfig1 libxcb-cursor0`.
* **OCR liefert nichts** – Tesseract installiert? `tesseract --version` prüfen.
* **Suche findet wenig** – KI-Extras installieren (`pip install ".[ai]"`) und das
  Modell einmalig herunterladen lassen.
