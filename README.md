# SmartFolders

**Der intelligente, vollständig lokale AI-Dateiassistent für Windows & macOS (und Linux).**

SmartFolders überwacht deine Ordner, erkennt und kategorisiert neue Dateien mit KI,
benennt sie sinnvoll um, liest Text aus Bildern/PDFs (OCR), findet Duplikate und
lässt dich deine Dateien **semantisch wie mit ChatGPT** durchsuchen – komplett
offline, ohne Cloud und ohne Telemetrie.

```
IMG_4832.png        ->  Rechnung_Amazon_2026.png
Screenshot_949.png  ->  Python_OpenCV_Error.png
document.pdf        ->  Mietvertrag_Wohnung.pdf
```

> 📖 **Neu hier? Die komplette Schritt-für-Schritt-Anleitung von „Python
> installieren" bis „App bauen" findest du in [docs/ANLEITUNG.md](docs/ANLEITUNG.md).**

---

## Highlights

| | Funktion | Beschreibung |
|---|---|---|
| 📂 | **Echtzeit-Überwachung** | Downloads, Desktop, Dokumente, Bilder & eigene Ordner – multithreaded im Hintergrund. |
| 🧠 | **AI-Dateierkennung** | Rechnungen, Verträge, Bewerbungen, Steuer, Uni, Code, Screenshots, Memes, Fotos … |
| 🏷️ | **Smart Rename** | Inhaltsbasierte, saubere Dateinamen mit Datum/Absender/Fehlertyp. |
| 🔍 | **AI-Suche** | „Zeig Rechnungen von Amazon", „Wo ist mein Lebenslauf?", „PDFs vom März". |
| 🧾 | **OCR** | Text aus Bildern, Screenshots und gescannten PDFs (Tesseract). |
| ♻️ | **Duplicate Finder** | Exakte Duplikate (SHA-256) **und** ähnliche Bilder (perceptual hash). |
| ⚙️ | **Regeln & Automatisierung** | GUI-Regeln mit Prioritäten, Bedingungen & Aktionen. |
| ⚡ | **AI Optimized Settings** | Erkennt deine Hardware und stellt Threads/Cache/Intensität optimal ein. |
| 📊 | **Dashboard** | Live-Statistiken, Aktivitäts-Feed, Kategorien, Performance. |
| 🎨 | **Modernes UI** | Dark/Light Theme, Sidebar, globale Suche, flüssige Optik. |
| 🔐 | **Datenschutz** | 100 % lokal, keine Cloud-Pflicht, keine Datenübertragung. |

---

## Schnellstart (ein Befehl installiert alles)

Der Installer richtet **alle** Abhängigkeiten ein – Python-Pakete, die native
**Tesseract-OCR-Engine** (per `winget`/`brew`/`apt`) und das lokale KI-Modell –
auf Windows, macOS und Linux:

```bash
python install.py            # interaktiv, volle Ausstattung
python install.py --yes      # ohne Rückfragen
python install.py --minimal  # nur Kern (ohne KI/OCR)
python install.py --venv     # in lokales .venv installieren
```

Danach starten:

```bash
python -m smartfolders              # Desktop-App
python -m smartfolders --minimized  # versteckt in den Tray
```

> Details und manuelle Installation: **[docs/INSTALL.md](docs/INSTALL.md)**

---

## Fertige App herunterladen (ohne Python)

Du musst nichts selbst bauen: Bei jedem Versions-Tag erstellt GitHub Actions
automatisch fertige, doppelklickbare Apps für **Windows, macOS und Linux** und
hängt sie an ein **Release** an.

1. Im Repo auf **Releases** gehen
   (`https://github.com/leopoldhartung7-debug/Ai-datei-scan-/releases`).
2. Beim neuesten Release herunterladen:
   * **Windows:** `SmartFolders-Windows.zip` → entpacken → `SmartFolders.exe` starten.
   * **macOS:** `SmartFolders-macOS.zip` → entpacken → `SmartFolders.app` öffnen
     (beim ersten Mal Rechtsklick → „Öffnen", da nicht signiert).
   * **Linux:** `SmartFolders-Linux.tar.gz` → entpacken → `./SmartFolders` starten.

Die Bundles enthalten die komplette Laufzeit – **kein Python nötig**.

> Noch kein Release vorhanden? Im Reiter **Actions** den Workflow
> „Build downloadable apps" per **Run workflow** starten, oder einen Tag pushen:
> `git tag v1.0.0 && git push origin v1.0.0`.

---

## Selbst bauen (.exe / .app)

```bash
python build/build_exe.py            # Ein-Ordner-Build (empfohlen)
python build/build_exe.py --onefile  # eine einzige Datei
```

* **Windows** → `dist/SmartFolders/SmartFolders.exe`
* **macOS** → `dist/SmartFolders.app`
* **Linux** → `dist/SmartFolders/SmartFolders`

> Hinweis: PyInstaller baut **nicht** plattformübergreifend – eine Windows-`.exe`
> entsteht nur auf Windows, eine `.app` nur auf macOS. Genau dafür gibt es den
> automatischen Cloud-Build oben. Details: **[docs/BUILD.md](docs/BUILD.md)**

---

## Kommandozeile (headless)

SmartFolders läuft auch komplett ohne GUI – ideal für Server/Automatisierung:

```bash
python -m smartfolders --headless                # Engine im Hintergrund
python -m smartfolders scan ~/Downloads          # einmalig scannen & sortieren
python -m smartfolders scan ~/Downloads --watch  # scannen + weiter überwachen
python -m smartfolders search "rechnungen amazon märz"
python -m smartfolders dupes                     # Duplikate auflisten
```

---

## Projektstruktur

```
SmartFolders/
├── install.py                 # Ein-Schritt-Installer (Win/Mac/Linux)
├── requirements.txt           # Laufzeit-Abhängigkeiten
├── requirements-dev.txt       # + Test/Build-Tools
├── pyproject.toml             # Paket- & Tool-Konfiguration
├── build/
│   └── build_exe.py           # PyInstaller-Build (exe/app)
├── docs/
│   ├── ANLEITUNG.md           # Vollständige Schritt-für-Schritt-Anleitung
│   ├── INSTALL.md             # Installationsanleitung
│   ├── BUILD.md               # Build- & EXE-Anleitung
│   ├── ARCHITECTURE.md        # Architektur + SQLite-Schema
│   ├── PERFORMANCE.md         # Performance-Optimierungen
│   └── SCREENSHOTS.md         # UI-Beschreibung / „Screenshots"
├── smartfolders/
│   ├── __main__.py            # CLI / Einstiegspunkt
│   ├── config.py              # Typisierte Settings + JSON-Persistenz
│   ├── constants.py           # Kategorien, Extension-Maps, Defaults
│   ├── engine.py              # Orchestrator (Pipeline, Worker-Pool, Stats)
│   ├── core/                  # Datenbank, Modelle, Watcher, Scanner,
│   │                          #   Organizer, Regeln, Event-Bus
│   ├── ai/                    # Klassifikation, OCR, Embeddings, Suche,
│   │                          #   Rename, Duplikate, Textextraktion
│   ├── system/                # Hardware-Erkennung, Optimizer, Autostart
│   ├── ui/                    # PyQt6-Oberfläche (Fenster, Views, Theme, Tray)
│   └── utils/                 # Logging, Pfade, Hashing
└── tests/                     # pytest-Suite (Core, AI, Engine, Optimizer)
```

---

## Architektur in einem Satz

Eine **UI-agnostische Engine** (`engine.py`) betreibt eine threadbasierte
Verarbeitungs-Pipeline und kommuniziert über einen **Event-Bus** mit der
**PyQt6-Oberfläche**; alle schweren KI-/OCR-Abhängigkeiten sind **optional** und
besitzen reine-Python-Fallbacks, sodass die App immer lauffähig und offline
nutzbar bleibt.

> Vollständige Erklärung inkl. **SQLite-Schema**: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

```
                +----------------------------------------------+
   Dateisystem  |            SmartFoldersEngine                |   PyQt6 UI
   ----------->  |  Watcher -> Queue -> Worker-Pool -> Pipeline |  <----------
   (watchdog)   |     |                                  |      |  Dashboard
                |     v                                  v      |  Suche
                |  Scanner   Classifier · OCR · Embeddings      |  Regeln
                |            Renamer · Rules · Organizer        |  Duplikate
                |                      |                        |  Optimize
                |                      v                        |  Settings
                |                  SQLite-DB  ---- EventBus ---->|  (Tray)
                +----------------------------------------------+
```

---

## Graceful Degradation (warum es überall läuft)

| Abhängigkeit fehlt | Fallback |
|---|---|
| `sentence-transformers` | Deterministischer Hashing-Vektorizer → Suche bleibt funktionsfähig |
| `pytesseract` / Tesseract | OCR wird deaktiviert, Rest läuft normal |
| `watchdog` | Polling-basierter Watcher |
| `PyMuPDF` | PDF-Text wird übersprungen (Dateiname/Tags weiter nutzbar) |
| `psutil` | Hardware-Erkennung via stdlib |
| `imagehash` | Average-Hash-Fallback über Pillow |

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Die Suite deckt Datenbank, Regeln, Klassifikation, Rename, Embeddings/Suche,
Duplikate, Optimizer und die End-to-End-Pipeline ab.

---

## Premium-Vorbereitung

Die Architektur ist vorbereitet für: Cloud Sync, AI-Chat mit Dateien,
PDF-Zusammenfassungen, Plugin-System, Team-Workspaces und Multi-Device-Sync –
siehe [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Lizenz

**Proprietär – Alle Rechte vorbehalten.** Kopieren, Weitergeben, Verändern oder
kommerzielle Nutzung sind ohne ausdrückliche schriftliche Genehmigung des
Rechteinhabers **nicht gestattet** – siehe [LICENSE](LICENSE).
