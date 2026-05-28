# UI-Design & „Screenshots" (Beschreibung)

SmartFolders nutzt ein **modernes, cleanes Dark-Theme** (Light optional) mit
abgerundeten Karten, einer festen Sidebar, einer globalen Suchleiste und einer
konfigurierbaren Akzentfarbe (Standard `#5b8cff`). Alle Icons werden zur Laufzeit
vektoriell gezeichnet – es gibt keine Binärassets.

Allgemeines Layout:

```
+----------+-------------------------------------------------------+
| Sidebar  |  Topbar:  [  globale Suchleiste (Enter)            ]  |
|          +-------------------------------------------------------+
| Logo     |                                                       |
| ──────   |   Aktive Ansicht (Dashboard / Suche / Files / …)      |
| Dashboard|                                                       |
| Search   |                                                       |
| Files    |                                                       |
| Rules    |                                                       |
| Dupes    |                                                       |
| Optimize |                                                       |
| Settings |                                                       |
| ──────   |                                                       |
| Engine:  |                                                       |
|  running |                                                       |
+----------+-------------------------------------------------------+
```

## 1. Dashboard
Sechs Statistik-Karten (Indexierte Dateien, Klassifiziert, OCR, Gesamtgröße,
Duplikate, Warteschlange). Links eine **Kategorien-Liste** mit Anzahl, rechts ein
live aktualisierter **Aktivitäts-Feed** (Zeit · Datei · Aktion). Oben rechts ein
Status-Badge (grün „Running"/grau „Stopped"), ein **Start/Stop-Engine**-Button und
**Scan now**. Beim Scan erscheint ein unbestimmter Fortschrittsbalken.

## 2. AI Search
Große Suchleiste mit Beispiel-Hinweis („Zeig Rechnungen von Amazon", „Wo ist mein
Lebenslauf?"). Ein Badge zeigt das aktive Such-Backend (neuronales Modell oder
Fallback). Ergebnisse als Liste mit Dateiname, **Kategorie-Tag**, Pfad, Größe und
Match-Art/Score. Doppelklick öffnet die Datei im System-Dateimanager.

## 3. Files
Filter- und kategorisierbare **Tabelle** aller indexierten Dateien
(Name · Kategorie · Größe · Tags · Indexiert). Textfilter + Kategorie-Dropdown,
Doppelklick zum Anzeigen im Explorer/Finder.

## 4. Rules & Automation
Liste aller Regeln mit **Checkbox zum Aktivieren**, Priorität, „IF … THEN …"-
Zusammenfassung. Buttons **New rule / Edit / Delete**. Der Regel-Dialog bietet
Name, Priorität, eine Bedingung (Feld · Operator · Wert) und eine Aktion
(Typ · Zielmuster mit Platzhaltern `{category} {ext} {year} {month}`).

## 5. Duplicate Finder
**Scan-Button**, danach eine **Baumansicht**: pro Gruppe (exact/similar) die
Dateien mit Größe und Pfad. Die erste Datei ist als „Behalten" vorausgewählt, die
übrigen angehakt. Unten Reclaim-Summe und **„Move ticked to trash"** (Papierkorb,
kein Hard-Delete).

## 6. AI Optimized Settings
**„Analyze this machine"** erkennt CPU/RAM/SSD/GPU/Threads. Vier Karten zeigen die
Empfehlung (Worker-Threads, Scan-Intensität, Cache, RAM-Budget), darunter eine
**Begründungsliste** („Warum diese Einstellungen"). Ein **Auto-Optimize**-Button
übernimmt alles mit einem Klick.

## 7. Settings
Tabs:
* **Folders** – überwachte Ordner hinzufügen/entfernen, Zielordner für sortierte
  Dateien.
* **AI** – Master-Schalter + Toggles (Auto-Classify, Auto-Rename, Auto-Move, OCR,
  Semantische Suche, Duplikate), OCR-Sprachen.
* **Performance** – Intensität, Threads, CPU-Limit-Slider, RAM-Budget, Cache,
  Akku-Drosselung, **Run at login**.
* **Appearance** – Theme (Dark/Light), Akzentfarbe, Minimize/Close-to-Tray,
  Benachrichtigungen.
* **Index & Data** – Suchindex neu aufbauen, DB komprimieren (VACUUM), Verlauf
  löschen.

## 8. System-Tray
Tray-Icon (Farbe = Engine-Status) mit Menü: **Open**, **Start/Stop engine**,
**Scan now**, **Quit**. Klick aufs Icon stellt das Fenster wieder her; Schließen
minimiert standardmäßig in den Tray (Hintergrundbetrieb).

## 9. Onboarding (erster Start)
Vierseitiger Assistent: Willkommen → überwachte Ordner bestätigen →
Hardware-Optimierung („Analyze my machine") → Fertig.

---

### Farb- & Stilreferenz (Dark-Theme)

| Element | Wert |
|---------|------|
| Hintergrund | `#0f1117` |
| Karten/Oberflächen | `#1b1f2e` / Rand `#2a3042` |
| Text / gedämpft | `#e8eaf0` / `#9aa0b4` |
| Akzent | `#5b8cff` |
| Erfolg / Warnung / Gefahr | `#3ecf8e` / `#f5a623` / `#ff5c6c` |
| Ecken-Radius | Karten 14 px, Buttons 9 px |
| Schrift | Segoe UI / SF Pro / Inter |
