# Performance-Optimierungen

SmartFolders ist für **Dauerbetrieb im Hintergrund** ausgelegt: spürbar leise im
Normalfall, schnell bei großen Ordnern.

## 1. Nebenläufigkeit ohne Blockaden

* **Dispatcher + Worker-Pool:** Ein Dispatcher-Thread füllt einen
  `ThreadPoolExecutor`; die Poolgröße ist konfigurierbar (`max_worker_threads`).
* **Entkoppelte UI:** Schwere Arbeit läuft nie auf dem Qt-Thread. Ergebnisse
  kommen via Event-Bus → `QtEventBridge` (Queued Signal) auf den GUI-Thread.
* **Lazy Scanner:** `os.walk`-basierter Generator streamt Pfade – auch bei
  Hunderttausenden Dateien bleibt der Speicher konstant.

## 2. Ressourcen-Throttling

* **Soft-CPU-Limit:** Übersteigt die CPU-Last `cpu_limit_percent`, legen Worker
  kurze, proportionale Pausen ein (via `psutil`).
* **Scan-Intensität:** `eco` / `balanced` / `performance` / `turbo` skalieren
  Threadzahl und Aggressivität.
* **Akku-Schonung:** Auf Akku schaltet die App auf `eco` (optional).
* **Debouncing:** Datei gilt erst als „fertig", wenn ihre Größe stabil ist –
  verhindert das mehrfache Verarbeiten halb kopierter Downloads.

## 3. I/O- & Hash-Effizienz

* **Streaming-Hashing:** SHA-256 in 256-KiB-Blöcken → konstanter Speicher.
* **Zweistufige Duplikatsuche:** Erst eine billige Signatur
  `(Größe + Kopf-/Endbytes)`, nur bei Kollision der volle SHA-256.
* **I/O-Chunk-Größe** passt sich an SSD vs. HDD an.

## 4. Datenbank

* **WAL-Modus** für gleichzeitige Reads während Writes.
* `synchronous=NORMAL`, `temp_store=MEMORY`, ~16 MB Page-Cache.
* **FTS5** liefert sublineare Volltextsuche; Trigger halten den Index automatisch
  synchron (kein separater Reindex nötig).
* **Embeddings** als kompakte `float32`-BLOBs (4 Byte/Dimension).
* **Atomare Settings-Writes** (`tmp` → `replace`) verhindern korrupte Dateien.

## 5. KI-Kosten gering halten

* **Heuristik zuerst:** Die meisten Dateien werden allein über Extension +
  Keywords klassifiziert – ML läuft nur bei mehrdeutigen Dokumenten.
* **Hashing-Fallback:** Ohne `sentence-transformers` liefert ein reiner-Python-
  Vektorizer brauchbare Ähnlichkeit ohne Modell-Ladezeit/RAM.
* **OCR begrenzt:** Maximale Seitenzahl pro PDF gedeckelt; nur Bilder und
  text-arme PDFs werden überhaupt durch OCR geschickt.

## 6. AI Optimized Settings

`system/optimizer.py` leitet aus der erkannten Hardware konkrete Werte ab:

| Erkanntes Merkmal | Auswirkung |
|-------------------|------------|
| Logische Kerne | Worker-Threads (mit Reserve für UI/OS) |
| RAM | RAM-Budget & Cache-Größe |
| SSD vs. HDD | Cache-Größe & I/O-Chunk (HDD: kleiner, gegen Seek-Thrashing) |
| Akku | Drosselung auf `eco` |
| Apple Silicon | Hinweis: lokale Modelle laufen effizient |

Die Empfehlungen sind transparent begründet (kein Black-Box-Tuning) und per
„Auto-Optimize"-Button mit einem Klick übernehmbar.

## 7. Richtwerte (Größenordnung)

| Szenario | Verhalten |
|----------|-----------|
| Leerlauf-Überwachung | nahe 0 % CPU, nur Event-Wartezeit |
| Erstscan (SSD, 8 Kerne) | mehrere Tausend Dateien/Min (ohne OCR) |
| Mit OCR | I/O-/Tesseract-gebunden – Hintergrundpriorität empfohlen |
| Speicher | Kern wenige MB; mit ML-Modell je nach Modellgröße |

> Werte sind hardwareabhängig. Über `--log-level DEBUG` und das Dashboard lässt
> sich der Durchsatz live beobachten.
