# Architektur

SmartFolders trennt strikt zwischen einer **UI-agnostischen Engine** und der
**PyQt6-Oberfläche**. Beide kommunizieren ausschließlich über einen Event-Bus.
Dadurch ist die Engine vollständig headless betreibbar (CLI, Server, Tests) und
die UI bleibt austauschbar.

## Schichten

```
smartfolders/
├── utils/      reine Helfer ohne Abhängigkeiten (Logging, Pfade, Hashing)
├── constants/  Kategorien, Extension-Maps, Defaults (seiteneffektfrei)
├── config.py   typisierte Settings + atomare JSON-Persistenz
├── core/       Engine-Bausteine:
│   ├── models.py     Dataclasses (FileRecord, Rule, HistoryEntry …)
│   ├── database.py   SQLite-Persistenz (WAL, FTS5, Embeddings)
│   ├── events.py     thread-sicherer Pub/Sub-Event-Bus
│   ├── scanner.py    lazy Verzeichnis-Walk
│   ├── watcher.py    watchdog (+ Polling-Fallback), Debouncing
│   ├── rules.py      reine Regel-Auswertung (seiteneffektfrei)
│   └── organizer.py  einziger Ort für Datei-Mutationen (move/rename/trash)
├── ai/         Klassifikation, OCR, Embeddings, Suche, Rename, Duplikate
├── system/     Hardware-Erkennung, Optimizer, Autostart (Win/Mac/Linux)
├── engine.py   Orchestrator: Pipeline + Worker-Pool + Stats
└── ui/         PyQt6: Fenster, Views, Theme, Tray, Event-Bridge, Onboarding
```

## Verarbeitungs-Pipeline

Jede erkannte Datei durchläuft in einem Worker-Thread:

1. **Detect** – Watcher meldet eine „settled" Datei (Größe stabil → fertig kopiert).
2. **Extract** – Textvorschau aus Text-/Code-/PDF-Dateien.
3. **OCR** – bei Bildern/gescannten PDFs (falls Tesseract vorhanden).
4. **Classify** – Kategorie + Konfidenz + Tags (Heuristik, optional ML-Refinement).
5. **Index** – Upsert in `files`, FTS5-Trigger aktualisiert den Suchindex.
6. **Embed** – Vektor für semantische Suche in `embeddings`.
7. **Rules** – Regel-Auswertung; invasive Aktionen nur bei `auto_move`/`auto_rename`.
8. **History** – jede Aktion wird revisionssicher protokolliert.

Der **Dispatcher-Thread** zieht Pfade aus einer `queue.Queue` und übergibt sie an
einen `ThreadPoolExecutor` (Größe = `max_worker_threads`). Ein **Soft-CPU-Throttle**
pausiert kurz, wenn die CPU-Last über dem konfigurierten Limit liegt.

## Nebenläufigkeit & Thread-Sicherheit

* **SQLite** im WAL-Modus, `check_same_thread=False`, Schreibzugriffe über ein
  `RLock`. Reads sind lock-frei. Ausreichend für die geringe Schreibrate eines
  Datei-Organizers.
* **Event-Bus** ist intern gelockt; die UI marshallt Events über
  `QtEventBridge` (Qt-Signal mit Queued Connection) sicher auf den GUI-Thread.
* **Watcher** entkoppelt rohe FS-Events von der Pipeline durch Debouncing.

## SQLite-Schema

```sql
-- Eine Zeile pro getrackter Datei inkl. KI-Metadaten
CREATE TABLE files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    path          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    extension     TEXT,
    size          INTEGER DEFAULT 0,
    category      TEXT,
    confidence    REAL DEFAULT 0,
    tags          TEXT,                 -- komma-separiert
    ocr_text      TEXT,
    content_preview TEXT,
    sha256        TEXT,
    phash         TEXT,                 -- perceptual hash (Bilder)
    original_name TEXT,
    created_at    REAL,
    modified_at   REAL,
    indexed_at    REAL,
    is_duplicate  INTEGER DEFAULT 0,
    duplicate_of  TEXT
);
CREATE INDEX idx_files_category ON files(category);
CREATE INDEX idx_files_sha256   ON files(sha256);
CREATE INDEX idx_files_phash    ON files(phash);
CREATE INDEX idx_files_ext      ON files(extension);

-- Volltextindex (FTS5), per Trigger synchron mit `files` gehalten
CREATE VIRTUAL TABLE files_fts USING fts5(
    name, tags, ocr_text, content_preview,
    content='files', content_rowid='id', tokenize='unicode61'
);
-- + Trigger files_ai / files_ad / files_au (INSERT/DELETE/UPDATE)

-- Semantische Vektoren (als kompaktes float32-BLOB)
CREATE TABLE embeddings (
    file_id   INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    dim       INTEGER NOT NULL,
    vector    BLOB NOT NULL,
    model     TEXT,
    updated_at REAL
);

-- Benutzer-Automatisierungsregeln (Bedingungen/Aktionen als JSON)
CREATE TABLE rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    enabled         INTEGER DEFAULT 1,
    priority        INTEGER DEFAULT 100,
    match_all       INTEGER DEFAULT 1,
    stop_processing INTEGER DEFAULT 0,
    conditions      TEXT NOT NULL,      -- JSON-Array
    actions         TEXT NOT NULL       -- JSON-Array
);

-- Revisionssicheres Aktionsprotokoll
CREATE TABLE history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    path      TEXT NOT NULL,
    action    TEXT NOT NULL,            -- detected/classified/moved/…
    detail    TEXT,
    old_path  TEXT,
    timestamp REAL NOT NULL
);
CREATE INDEX idx_history_ts ON history(timestamp DESC);

-- Freie Schlüssel/Wert-Speicher
CREATE TABLE preferences (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE meta        (key TEXT PRIMARY KEY, value TEXT);  -- u. a. schema_version
```

### Suche: Lexikalisch + Semantisch (Hybrid)

`SemanticSearch` parst die Anfrage zunächst auf natürliche Filter (Kategorie,
Endung, Monat, Jahr), holt dann **FTS5-Treffer** (Stichwort) **und**
**Embedding-Treffer** (Bedeutung) und fusioniert beide per Reciprocal-Rank-Fusion.
So funktionieren Anfragen wie „Zeig Rechnungen von Amazon vom März".

## Klassifikation (zweistufig)

1. **Heuristik (immer offline):** Extension-Prior + Keyword-Scoring über
   Dateiname und extrahierten Text/OCR. Kurze Keywords matchen wortgenau
   (verhindert „cv" in „opencv"), lange Keywords als Teilstring (deutsche
   Komposita wie „mietvertrag" → „vertrag").
2. **Optionales ML-Refinement:** Bei mehrdeutigen Dokumenten Zero-Shot-Ähnlichkeit
   gegen Kategoriebeschreibungen via Embeddings.

## Datei-Mutationen

Alle Schreib-/Verschiebe-/Lösch-Operationen laufen ausschließlich über
`Organizer`. Eigenschaften:

* **Nie überschreiben:** `unique_destination()` vergibt `name (1).ext` usw.
* **Trash statt Löschen:** `send_to_trash()` nutzt `send2trash` bzw. plattform-
  native Wege (macOS `~/.Trash`), erst als letzter Ausweg permanentes Löschen.
* **Dry-Run:** Vorschaumodus ohne FS-Änderung.
* **DB-Konsistenz:** Pfadänderungen werden in der Datenbank nachgezogen.

## Plattform-Abstraktionen (Windows + macOS + Linux)

| Belang | Umsetzung |
|--------|-----------|
| Pfade/Verzeichnisse | `platformdirs` mit `~/.smartfolders`-Fallback |
| Hardware-Erkennung | `psutil` + OS-spezifische Probes (`sysctl`, `/proc`, PowerShell/WMIC) |
| Autostart | Registry (Win) · LaunchAgent-Plist (mac) · XDG-`.desktop` (Linux) |
| Datei-Manager öffnen | Explorer · Finder (`open -R`) · `xdg-open` |
| Tesseract finden | `PATH` + bekannte Windows-Installationspfade |

## Erweiterbarkeit (Premium-Vorbereitung)

Die Architektur ist bewusst auf zukünftige Features ausgelegt:

* **Cloud Sync / Multi-Device:** Die SQLite-DB + `meta.schema_version` erlauben
  Migrationen; `history` ist ein natürlicher Change-Feed für Synchronisation.
* **AI-Chat mit Dateien / PDF-Zusammenfassungen:** `embeddings` + `content_preview`
  liefern bereits Retrieval-Kontext für ein RAG-Setup.
* **Plugin-System:** Der Event-Bus ist der vorgesehene Erweiterungspunkt –
  Plugins abonnieren Events und können eigene Pipeline-Schritte ergänzen.
* **Team-Workspaces:** `preferences`/`meta` trennen User- von Workspace-State.
