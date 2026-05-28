"""SQLite persistence layer.

A single :class:`Database` instance is shared across threads. SQLite is opened
in WAL mode with ``check_same_thread=False`` and every write is guarded by a
re-entrant lock, which is more than sufficient for the modest write rate of a
file-organizer. Reads are lock-free.

Schema (see :data:`SCHEMA`):

* ``files``        - one row per tracked file with AI metadata.
* ``files_fts``    - FTS5 virtual table mirroring searchable text.
* ``embeddings``   - serialized semantic vectors for files.
* ``rules``        - user automation rules (JSON columns for conditions/actions).
* ``history``      - append-only audit log of engine actions.
* ``preferences``  - free-form key/value store for misc settings.
"""

from __future__ import annotations

import sqlite3
import struct
import threading
import time
from collections.abc import Iterable, Sequence
from pathlib import Path

from ..constants import Category
from ..utils.logging import get_logger
from .models import FileRecord, HistoryEntry, Rule

log = get_logger(__name__)

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    path          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    extension     TEXT,
    size          INTEGER DEFAULT 0,
    category      TEXT,
    confidence    REAL DEFAULT 0,
    tags          TEXT,
    ocr_text      TEXT,
    content_preview TEXT,
    sha256        TEXT,
    phash         TEXT,
    original_name TEXT,
    created_at    REAL,
    modified_at   REAL,
    indexed_at    REAL,
    is_duplicate  INTEGER DEFAULT 0,
    duplicate_of  TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
CREATE INDEX IF NOT EXISTS idx_files_sha256   ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_phash    ON files(phash);
CREATE INDEX IF NOT EXISTS idx_files_ext      ON files(extension);

CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    name, tags, ocr_text, content_preview,
    content='files', content_rowid='id', tokenize='unicode61'
);

-- Keep the FTS index in sync with the files table via triggers.
CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
    INSERT INTO files_fts(rowid, name, tags, ocr_text, content_preview)
    VALUES (new.id, new.name, new.tags, new.ocr_text, new.content_preview);
END;
CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
    INSERT INTO files_fts(files_fts, rowid, name, tags, ocr_text, content_preview)
    VALUES ('delete', old.id, old.name, old.tags, old.ocr_text, old.content_preview);
END;
CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
    INSERT INTO files_fts(files_fts, rowid, name, tags, ocr_text, content_preview)
    VALUES ('delete', old.id, old.name, old.tags, old.ocr_text, old.content_preview);
    INSERT INTO files_fts(rowid, name, tags, ocr_text, content_preview)
    VALUES (new.id, new.name, new.tags, new.ocr_text, new.content_preview);
END;

CREATE TABLE IF NOT EXISTS embeddings (
    file_id   INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    dim       INTEGER NOT NULL,
    vector    BLOB NOT NULL,
    model     TEXT,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    enabled         INTEGER DEFAULT 1,
    priority        INTEGER DEFAULT 100,
    match_all       INTEGER DEFAULT 1,
    stop_processing INTEGER DEFAULT 0,
    conditions      TEXT NOT NULL,
    actions         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    path      TEXT NOT NULL,
    action    TEXT NOT NULL,
    detail    TEXT,
    old_path  TEXT,
    timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_ts ON history(timestamp DESC);

CREATE TABLE IF NOT EXISTS preferences (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    """Thread-safe SQLite wrapper exposing typed helper methods."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.path, check_same_thread=False, timeout=30.0
        )
        self._conn.row_factory = sqlite3.Row
        self._configure()
        self._migrate()
        log.info("Database ready at %s", self.path)

    # ------------------------------------------------------------------ setup
    def _configure(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.execute("PRAGMA temp_store=MEMORY;")
        cur.execute("PRAGMA cache_size=-16000;")  # ~16 MB page cache
        self._conn.commit()

    def _migrate(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()
            current = self.get_meta("schema_version")
            if current is None:
                self.set_meta("schema_version", str(SCHEMA_VERSION))
            # Future migrations would branch on int(current) here.

    # ------------------------------------------------------------------- meta
    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self._conn.commit()

    # ------------------------------------------------------------ preferences
    def set_pref(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO preferences(key, value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self._conn.commit()

    def get_pref(self, key: str, default: str | None = None) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM preferences WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    # ------------------------------------------------------------------ files
    def upsert_file(self, record: FileRecord) -> int:
        """Insert or update a file row keyed on its path. Returns the row id."""
        record.indexed_at = record.indexed_at or time.time()
        row = record.to_row()
        cols = [c for c in row if c != "id"]
        placeholders = ",".join("?" for _ in cols)
        updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "path")
        sql = (
            f"INSERT INTO files ({','.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(path) DO UPDATE SET {updates}"
        )
        with self._lock:
            cur = self._conn.execute(sql, [row[c] for c in cols])
            self._conn.commit()
            if cur.lastrowid:
                record.id = cur.lastrowid
            else:
                got = self._conn.execute(
                    "SELECT id FROM files WHERE path=?", (record.path,)
                ).fetchone()
                record.id = got["id"] if got else None
        return record.id or 0

    def get_file(self, path: str) -> FileRecord | None:
        row = self._conn.execute("SELECT * FROM files WHERE path=?", (path,)).fetchone()
        return FileRecord.from_row(row) if row else None

    def get_file_by_id(self, file_id: int) -> FileRecord | None:
        row = self._conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
        return FileRecord.from_row(row) if row else None

    def update_file_path(self, old_path: str, new_path: str) -> None:
        new_name = Path(new_path).name
        with self._lock:
            self._conn.execute(
                "UPDATE files SET path=?, name=? WHERE path=?",
                (new_path, new_name, old_path),
            )
            self._conn.commit()

    def delete_file(self, path: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM files WHERE path=?", (path,))
            self._conn.commit()

    def all_files(self, limit: int | None = None, offset: int = 0) -> list[FileRecord]:
        sql = "SELECT * FROM files ORDER BY indexed_at DESC"
        params: list = []
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params = [limit, offset]
        rows = self._conn.execute(sql, params).fetchall()
        return [FileRecord.from_row(r) for r in rows]

    def files_by_category(self, category: Category) -> list[FileRecord]:
        rows = self._conn.execute(
            "SELECT * FROM files WHERE category=? ORDER BY indexed_at DESC",
            (category.value,),
        ).fetchall()
        return [FileRecord.from_row(r) for r in rows]

    def files_missing_ocr(self, extensions: Sequence[str], limit: int = 50) -> list[FileRecord]:
        if not extensions:
            return []
        marks = ",".join("?" for _ in extensions)
        rows = self._conn.execute(
            f"SELECT * FROM files WHERE (ocr_text IS NULL OR ocr_text='') "
            f"AND extension IN ({marks}) LIMIT ?",
            [*extensions, limit],
        ).fetchall()
        return [FileRecord.from_row(r) for r in rows]

    def files_missing_embedding(self, limit: int = 100) -> list[FileRecord]:
        rows = self._conn.execute(
            "SELECT f.* FROM files f LEFT JOIN embeddings e ON e.file_id=f.id "
            "WHERE e.file_id IS NULL LIMIT ?",
            (limit,),
        ).fetchall()
        return [FileRecord.from_row(r) for r in rows]

    # --------------------------------------------------------------- counting
    def count_files(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()["c"]

    def category_counts(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT category, COUNT(*) AS c FROM files GROUP BY category"
        ).fetchall()
        return {r["category"]: r["c"] for r in rows}

    def total_size(self) -> int:
        row = self._conn.execute("SELECT COALESCE(SUM(size),0) AS s FROM files").fetchone()
        return int(row["s"])

    # ----------------------------------------------------------------- search
    def search_fts(self, query: str, limit: int = 50) -> list[FileRecord]:
        """Full-text keyword search via FTS5. Returns best-ranked first."""
        if not query.strip():
            return []
        match = _fts_query(query)
        try:
            rows = self._conn.execute(
                "SELECT f.* FROM files_fts s JOIN files f ON f.id=s.rowid "
                "WHERE files_fts MATCH ? ORDER BY rank LIMIT ?",
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # Malformed match expression - fall back to a LIKE scan.
            like = f"%{query}%"
            rows = self._conn.execute(
                "SELECT * FROM files WHERE name LIKE ? OR ocr_text LIKE ? "
                "OR content_preview LIKE ? OR tags LIKE ? LIMIT ?",
                (like, like, like, like, limit),
            ).fetchall()
        return [FileRecord.from_row(r) for r in rows]

    # ------------------------------------------------------------- embeddings
    def store_embedding(self, file_id: int, vector: Sequence[float], model: str) -> None:
        blob = _pack_vector(vector)
        with self._lock:
            self._conn.execute(
                "INSERT INTO embeddings(file_id, dim, vector, model, updated_at) "
                "VALUES(?,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET "
                "dim=excluded.dim, vector=excluded.vector, model=excluded.model, "
                "updated_at=excluded.updated_at",
                (file_id, len(vector), blob, model, time.time()),
            )
            self._conn.commit()

    def iter_embeddings(self) -> Iterable[tuple[int, list[float]]]:
        """Yield ``(file_id, vector)`` for every stored embedding."""
        for row in self._conn.execute("SELECT file_id, dim, vector FROM embeddings"):
            yield row["file_id"], _unpack_vector(row["vector"], row["dim"])

    def has_embeddings(self) -> bool:
        return self._conn.execute("SELECT 1 FROM embeddings LIMIT 1").fetchone() is not None

    # ------------------------------------------------------------------ rules
    def save_rule(self, rule: Rule) -> int:
        row = rule.to_row()
        with self._lock:
            if rule.id is None:
                cols = [c for c in row if c != "id"]
                cur = self._conn.execute(
                    f"INSERT INTO rules ({','.join(cols)}) "
                    f"VALUES ({','.join('?' for _ in cols)})",
                    [row[c] for c in cols],
                )
                rule.id = cur.lastrowid
            else:
                self._conn.execute(
                    "UPDATE rules SET name=?, enabled=?, priority=?, match_all=?, "
                    "stop_processing=?, conditions=?, actions=? WHERE id=?",
                    (
                        row["name"], row["enabled"], row["priority"], row["match_all"],
                        row["stop_processing"], row["conditions"], row["actions"], rule.id,
                    ),
                )
            self._conn.commit()
        return rule.id or 0

    def get_rules(self, enabled_only: bool = False) -> list[Rule]:
        sql = "SELECT * FROM rules"
        if enabled_only:
            sql += " WHERE enabled=1"
        sql += " ORDER BY priority ASC, id ASC"
        return [Rule.from_row(r) for r in self._conn.execute(sql).fetchall()]

    def delete_rule(self, rule_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM rules WHERE id=?", (rule_id,))
            self._conn.commit()

    # ---------------------------------------------------------------- history
    def add_history(self, entry: HistoryEntry) -> int:
        row = entry.to_row()
        cols = [c for c in row if c != "id"]
        with self._lock:
            cur = self._conn.execute(
                f"INSERT INTO history ({','.join(cols)}) "
                f"VALUES ({','.join('?' for _ in cols)})",
                [row[c] for c in cols],
            )
            self._conn.commit()
        return cur.lastrowid or 0

    def recent_history(self, limit: int = 100) -> list[HistoryEntry]:
        rows = self._conn.execute(
            "SELECT * FROM history ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [HistoryEntry.from_row(r) for r in rows]

    def clear_history(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM history")
            self._conn.commit()

    # --------------------------------------------------------------- maintenance
    def vacuum(self) -> None:
        with self._lock:
            self._conn.execute("VACUUM")
            self._conn.commit()

    def rebuild_search_index(self) -> None:
        with self._lock:
            self._conn.execute("INSERT INTO files_fts(files_fts) VALUES('rebuild')")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.commit()
            finally:
                self._conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _pack_vector(vector: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack_vector(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"<{dim}f", blob))


def _fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 prefix-match expression.

    Each alphanumeric token becomes a prefix term joined with OR so partial
    words still match, while stripping characters FTS5 would treat as syntax.
    """
    tokens = []
    for raw in query.replace('"', " ").split():
        cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in "_-")
        if cleaned:
            tokens.append(f'"{cleaned}"*')
    return " OR ".join(tokens) if tokens else '""'
