# SmartFolders – Vollständige Anleitung

Diese Anleitung führt dich **von null** bis zur laufenden App – egal ob du
Windows, einen Mac oder Linux nutzt und egal, wie viel Vorerfahrung du hast.

> **Kurzfassung für Eilige**
> ```bash
> python install.py        # installiert alles
> python -m smartfolders   # startet die App
> ```

**Inhalt**

1. [Was ist SmartFolders?](#1-was-ist-smartfolders)
2. [Voraussetzung: Python installieren](#2-voraussetzung-python-installieren)
3. [SmartFolders herunterladen](#3-smartfolders-herunterladen)
4. [Installation (ein Befehl installiert alles)](#4-installation-ein-befehl-installiert-alles)
5. [Erster Start & Einrichtungs-Assistent](#5-erster-start--einrichtungs-assistent)
6. [Die Oberfläche bedienen](#6-die-oberfläche-bedienen)
7. [Eigene Regeln erstellen (Schritt für Schritt)](#7-eigene-regeln-erstellen-schritt-für-schritt)
8. [Typische Arbeitsabläufe / Rezepte](#8-typische-arbeitsabläufe--rezepte)
9. [Ohne Fenster: die Kommandozeile](#9-ohne-fenster-die-kommandozeile)
10. [Eigene App / .exe bauen](#10-eigene-app--exe-bauen)
11. [Datenschutz & Speicherorte](#11-datenschutz--speicherorte)
12. [Updates & Deinstallation](#12-updates--deinstallation)
13. [Problembehebung (FAQ)](#13-problembehebung-faq)

---

## 1. Was ist SmartFolders?

SmartFolders ist ein **AI-Dateiassistent**, der im Hintergrund läuft und deine
Ordner automatisch ordnet:

- **erkennt** neue Dateien (Downloads, Desktop, Dokumente, Bilder …),
- **kategorisiert** sie (Rechnung, Vertrag, Bewerbung, Code, Screenshot …),
- **benennt** sie sinnvoll um (`IMG_4832.png → Rechnung_Amazon_2026.png`),
- **liest Text** aus Bildern/PDFs (OCR),
- **findet Duplikate**,
- und lässt dich alles **wie mit ChatGPT durchsuchen**
  („Zeig Rechnungen von Amazon").

Alles läuft **lokal auf deinem Gerät** – keine Cloud, keine Datenübertragung.

---

## 2. Voraussetzung: Python installieren

SmartFolders braucht **Python 3.11 oder 3.12**. Prüfe zuerst, ob es schon da ist.

Öffne ein Terminal:
- **Windows:** Startmenü → „PowerShell" eingeben → öffnen.
- **macOS:** `Cmd`+`Leertaste` → „Terminal" → Enter.
- **Linux:** dein Terminal.

Tippe:

```bash
python --version
```

Erscheint `Python 3.11.x` oder `3.12.x` → weiter zu Schritt 3.
Erscheint ein Fehler oder eine ältere Version, installiere Python:

### Windows
1. Gehe zu <https://www.python.org/downloads/> und lade Python 3.12 herunter.
2. Starte den Installer und **setze unbedingt das Häkchen bei „Add python.exe to PATH"**.
3. „Install Now" klicken, danach PowerShell schließen und neu öffnen.

> Alternativ im Terminal: `winget install Python.Python.3.12`

### macOS
Empfohlen über [Homebrew](https://brew.sh):

```bash
brew install python@3.12
```

Ohne Homebrew: Installer von <https://www.python.org/downloads/macos/>.

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

Prüfe danach erneut mit `python --version` (ggf. `python3 --version`).

---

## 3. SmartFolders herunterladen

**Variante A – mit Git (empfohlen):**

```bash
git clone <REPO-URL> SmartFolders
cd SmartFolders
```

**Variante B – ohne Git:** Auf GitHub oben rechts auf **Code → Download ZIP**,
die ZIP entpacken, dann im Terminal in den entpackten Ordner wechseln:

```bash
cd Pfad/zu/SmartFolders
```

> Du musst dich für alle weiteren Befehle **in diesem Ordner** befinden (dort, wo
> die Datei `install.py` liegt). Mit `ls` (macOS/Linux) bzw. `dir` (Windows)
> kannst du prüfen, ob `install.py` angezeigt wird.

---

## 4. Installation (ein Befehl installiert alles)

Ein einziger Befehl installiert **alle** Bestandteile – Python-Pakete, die
**Tesseract-OCR-Engine** und das **KI-Modell** – passend für dein Betriebssystem:

```bash
python install.py
```

Während der Installation wirst du gefragt, ob die Tesseract-OCR-Engine und das
KI-Modell installiert werden sollen → mit Enter bestätigen.

**Was der Installer tut:**
1. prüft deine Python-Version,
2. installiert alle Python-Abhängigkeiten,
3. installiert Tesseract automatisch
   (Windows: `winget`/`choco`, macOS: `brew`, Linux: `apt`/`dnf`/`pacman`),
4. lädt das lokale KI-Modell **einmalig** herunter (danach offline nutzbar).

**Nützliche Optionen:**

| Befehl | Bedeutung |
|--------|-----------|
| `python install.py --yes` | Ohne Rückfragen (alles „ja"). |
| `python install.py --venv` | In eine isolierte Umgebung `.venv` installieren (sauberste Variante). |
| `python install.py --minimal` | Nur Grundfunktionen (ohne KI/OCR). |
| `python install.py --skip-tesseract` | OCR-Engine nicht installieren. |
| `python install.py --skip-model` | KI-Modell nicht vorab laden. |

> **Empfehlung für saubere Installation:** `python install.py --venv`
> Danach die App immer mit dem Python aus `.venv` starten:
> - macOS/Linux: `.venv/bin/python -m smartfolders`
> - Windows: `.venv\Scripts\python -m smartfolders`

> **Hinweis macOS/Windows:** Wenn `brew`/`winget` fehlt, zeigt der Installer dir
> den Link zur manuellen Tesseract-Installation. OCR ist optional – ohne
> Tesseract läuft alles andere normal.

---

## 5. Erster Start & Einrichtungs-Assistent

Starte die App:

```bash
python -m smartfolders
```

Beim **ersten Start** öffnet sich ein Assistent in vier Schritten:

1. **Willkommen** – kurze Erklärung.
2. **Ordner auswählen** – welche Ordner überwacht werden sollen
   (Downloads/Desktop/Dokumente/Bilder sind vorausgewählt). Mit **Add folder**
   ergänzen, mit **Remove** entfernen.
3. **Hardware optimieren** – klicke **„Analyze my machine"**. SmartFolders
   erkennt CPU/RAM/SSD und stellt Threads, Cache & Intensität optimal ein.
4. **Fertig** – die App startet.

Danach beginnt die Engine automatisch zu überwachen und einen ersten Scan zu
fahren.

> Tipp: `python -m smartfolders --minimized` startet die App direkt versteckt im
> System-Tray (Hintergrundbetrieb).

---

## 6. Die Oberfläche bedienen

Links die **Sidebar** mit sieben Bereichen, oben die **globale Suchleiste**.

### Dashboard
Dein Überblick:
- **Statistik-Karten:** indexierte Dateien, klassifiziert, OCR, Gesamtgröße,
  Duplikate, Warteschlange.
- **Kategorien** (links) und **Aktivitäts-Feed** (rechts, live).
- Oben: Status-Badge (grün = läuft), **Start/Stop engine**, **Scan now**.

Mit **Scan now** durchsuchst du jederzeit alle überwachten Ordner neu.

### Search (AI-Suche)
Frag in normaler Sprache, z. B.:
- „Zeig Rechnungen von Amazon"
- „Wo ist mein Lebenslauf?"
- „Coding Screenshots"
- „PDFs vom März"

Die Suche kombiniert Stichworte **und** Bedeutung. **Doppelklick** auf ein
Ergebnis öffnet die Datei im Explorer/Finder.

### Files
Tabelle aller erfassten Dateien mit Name, Kategorie, Größe, Tags und Datum.
Oben filtern per Textfeld oder Kategorie-Auswahl. Doppelklick öffnet die Datei.

### Rules
Deine Automatisierungsregeln (siehe [Schritt 7](#7-eigene-regeln-erstellen-schritt-für-schritt)).

### Duplicates
**„Scan for duplicates"** klicken. Es erscheinen Gruppen:
- **exact** = bytegleiche Dateien,
- **similar** = optisch ähnliche Bilder.

Die erste Datei jeder Gruppe ist als „behalten" **nicht** angehakt, die übrigen
schon. Mit **„Move ticked to trash"** wandern die markierten Kopien in den
Papierkorb (kein endgültiges Löschen).

### Optimize (AI Optimized Settings)
**„Analyze this machine"** → SmartFolders schlägt optimale Performance-Werte vor
und begründet sie. **„Auto-optimize"** übernimmt alles mit einem Klick.

### Settings
Fünf Reiter:
- **Folders:** überwachte Ordner & Zielordner für sortierte Dateien.
- **AI:** Hauptschalter und Toggles – **Auto-Classify**, **Auto-Rename**,
  **Auto-Move**, **OCR**, **Semantische Suche**, **Duplikate** + OCR-Sprachen.
- **Performance:** Intensität, Threads, CPU-Limit, RAM-Budget, Cache,
  Akku-Drosselung, **Run at login** (Autostart).
- **Appearance:** Theme (Dark/Light), Akzentfarbe, Tray-Verhalten,
  Benachrichtigungen.
- **Index & Data:** Suchindex neu aufbauen, Datenbank komprimieren, Verlauf
  löschen.

> Änderungen erst mit **„Save changes"** speichern.

> **Wichtig zu Auto-Rename / Auto-Move:** Diese sind aus Sicherheitsgründen
> **standardmäßig aus**. Erst wenn du sie aktivierst, verschiebt/benennt
> SmartFolders Dateien automatisch. Vorher ordnet es nur (erkennt, taggt,
> indexiert), ohne deine Dateien zu bewegen.

### System-Tray
Klein neben der Uhr. Rechtsklick öffnet das Menü: **Open**, **Start/Stop
engine**, **Scan now**, **Quit**. Das Fenster zu schließen beendet die App nicht
– sie läuft im Tray weiter (abschaltbar in den Einstellungen).

---

## 7. Eigene Regeln erstellen (Schritt für Schritt)

Regeln sagen SmartFolders: *„Wenn eine Datei Bedingung X erfüllt, tue Y."*

Beispiel: **Alle PDF-Rechnungen nach `Dokumente/Rechnungen` verschieben.**

1. Sidebar → **Rules** → **New rule**.
2. **Name:** `Rechnungen einsortieren`.
3. **Priority:** `10` (kleinere Zahl = wird früher ausgeführt).
4. **Condition:** Feld `category`, Operator `equals`, Wert `invoice`.
5. **Action:** Typ `move`, Ziel `Dokumente/Rechnungen`.
6. **OK** klicken. Mit der **Checkbox** in der Liste aktivierst du die Regel.

Damit Regeln tatsächlich verschieben, in **Settings → AI** den Schalter
**Auto-Move** aktivieren.

**Platzhalter im Ziel** (für dynamische Ordner):

| Platzhalter | Beispiel |
|-------------|----------|
| `{category}` | `invoice` |
| `{ext}` | `pdf` |
| `{year}` `{month}` `{day}` | `2026` `03` `15` |

Beispiel-Ziel: `Dokumente/{category}/{year}` → `Dokumente/invoice/2026`.

**Weitere Beispiel-Regeln:**

| Ziel | Bedingung | Aktion |
|------|-----------|--------|
| Screenshots sortieren | `category equals screenshot` | `move → Bilder/Screenshots` |
| Code gruppieren | `category equals code` | `move → Code` |
| Alte ZIPs archivieren | `extension equals zip` **und** `age_days greater_than 30` | `archive → Archives` |
| Große Videos taggen | `extension equals mp4` | `tag → groß,video` |

> Operatoren: `equals`, `contains`, `starts_with`, `ends_with`, `matches` (Regex),
> `greater_than`, `less_than`, `in`. Felder: `extension`, `name`, `category`,
> `size`, `age_days`, `content`, `tag`.

---

## 8. Typische Arbeitsabläufe / Rezepte

**A) Downloads-Ordner automatisch aufräumen**
1. Settings → Folders: Downloads ist überwacht (sonst hinzufügen).
2. Settings → AI: **Auto-Move** an, optional **Auto-Rename** an.
3. Passende Regeln anlegen (siehe Schritt 7).
4. Dashboard → **Scan now**. Fertig – neue Downloads werden künftig automatisch
   einsortiert.

**B) Eine bestimmte Rechnung finden**
- Globale Suchleiste oben: `Rechnung Amazon 2026` → Enter. Doppelklick öffnet sie.

**C) Speicherplatz freigeben**
- Sidebar → **Duplicates** → **Scan for duplicates** → unnötige Kopien anhaken →
  **Move ticked to trash**.

**D) Leiser Laptop-Betrieb**
- Settings → Performance: Intensität auf **Eco**, **Throttle on battery** an.

---

## 9. Ohne Fenster: die Kommandozeile

SmartFolders läuft auch komplett ohne GUI – praktisch für Automatisierung:

```bash
python -m smartfolders --headless                 # Engine im Hintergrund
python -m smartfolders scan ~/Downloads           # einmal scannen & sortieren
python -m smartfolders scan ~/Downloads --watch   # scannen + weiter überwachen
python -m smartfolders search "rechnungen amazon" # im Index suchen
python -m smartfolders dupes                       # Duplikate auflisten
python -m smartfolders --version                   # Version anzeigen
```

---

## 10. Eigene App / .exe bauen

So machst du aus dem Projekt ein doppelklickbares Programm (ohne dass Nutzer
Python brauchen):

```bash
python build/build_exe.py            # Ein-Ordner-Build (empfohlen)
python build/build_exe.py --onefile  # eine einzige Datei
```

Ergebnis:
- **Windows:** `dist/SmartFolders/SmartFolders.exe`
- **macOS:** `dist/SmartFolders.app`
- **Linux:** `dist/SmartFolders/SmartFolders`

> Der Build muss auf dem **Ziel-Betriebssystem** erstellt werden (Windows-Build
> auf Windows, Mac-Build auf Mac). Details und Installer-Erstellung (Inno
> Setup / DMG): siehe [BUILD.md](BUILD.md).

---

## 11. Datenschutz & Speicherorte

- **100 % lokal.** Keine Cloud-Pflicht, keine Telemetrie, keine Datenübertragung.
- Das KI-Modell wird **einmalig** geladen, danach funktioniert alles **offline**.

| Inhalt | Ort |
|--------|-----|
| Einstellungen | `settings.json` im Benutzer-Konfig-Ordner |
| Datenbank/Index | `smartfolders.db` im Benutzer-Daten-Ordner |
| Logs | `smartfolders.log` im Benutzer-Log-Ordner |

Die genauen Pfade richten sich nach dem Betriebssystem (siehe [INSTALL.md](INSTALL.md#4-speicherorte)).
SmartFolders liest **nur** die von dir gewählten Ordner.

---

## 12. Updates & Deinstallation

**Update (per Git):**
```bash
cd SmartFolders
git pull
python install.py --yes   # neue Abhängigkeiten nachziehen
```

**Deinstallation:**
```bash
pip uninstall smartfolders
```
Optional anschließend die Daten-/Konfig-Ordner aus [Schritt 11](#11-datenschutz--speicherorte)
löschen. Hast du **Run at login** genutzt, vorher in Settings → Performance
wieder ausschalten.

---

## 13. Problembehebung (FAQ)

**„No module named smartfolders"**
→ Du bist nicht im Projektordner. Mit `cd` in den Ordner mit `install.py`
wechseln. Oder einmalig `pip install -e .` ausführen.

**App startet nicht / Fehler `libEGL`/`xcb` (Linux)**
→ Qt-Systembibliotheken nachinstallieren:
```bash
sudo apt install libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libxcb-cursor0
```

**OCR liefert keinen Text**
→ Tesseract fehlt. Prüfen mit `tesseract --version`. Falls leer:
`python install.py` erneut ausführen oder Tesseract manuell installieren
(siehe [INSTALL.md](INSTALL.md)).

**Suche findet wenig / ist ungenau**
→ KI-Extras installieren und Modell laden:
```bash
pip install ".[ai]"
```
Ohne diese läuft ein einfacherer Fallback (funktioniert, aber weniger präzise).

**Dateien werden nicht verschoben/umbenannt**
→ In **Settings → AI** sind **Auto-Move**/**Auto-Rename** standardmäßig aus.
Aktivieren und **Save changes** klicken.

**Hohe CPU-Last beim ersten Scan**
→ Normal beim Erstdurchlauf. In **Settings → Performance** Intensität auf
**Eco**/**Balanced** stellen oder das CPU-Limit senken.

**`winget`/`brew` nicht gefunden (Tesseract-Installation)**
→ Tesseract manuell installieren:
- Windows: <https://github.com/UB-Mannheim/tesseract/wiki>
- macOS: zuerst [Homebrew](https://brew.sh), dann `brew install tesseract tesseract-lang`

**Wie sehe ich, was im Hintergrund passiert?**
→ Mit mehr Log-Details starten: `python -m smartfolders --log-level DEBUG`.
Der Dashboard-Aktivitäts-Feed zeigt Aktionen live.

---

Viel Spaß mit SmartFolders! Weiterführende Doku:
[INSTALL.md](INSTALL.md) · [BUILD.md](BUILD.md) · [ARCHITECTURE.md](ARCHITECTURE.md) ·
[PERFORMANCE.md](PERFORMANCE.md) · [SCREENSHOTS.md](SCREENSHOTS.md)
