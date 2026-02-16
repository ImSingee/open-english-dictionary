#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


DEFAULT_BATCH_SIZE = 1000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild a SQLite database from NDJSON shards in data/. "
            "Creates one table: words(word, definition)."
        )
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing NDJSON shard files (default: data)",
    )
    parser.add_argument(
        "--out-db",
        default="db.sqlite",
        help="Output SQLite file path (default: db.sqlite)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows per executemany batch (default: {DEFAULT_BATCH_SIZE})",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def iter_ndjson_files(data_dir: Path) -> list[Path]:
    return sorted(path for path in data_dir.glob("*.ndjson") if path.is_file())


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS words")
    conn.execute(
        """
        CREATE TABLE words (
            word TEXT NOT NULL COLLATE BINARY,
            definition TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX idx_words_word ON words(word)")


def flush_batch(conn: sqlite3.Connection, batch: list[tuple[str, str]]) -> None:
    if not batch:
        return
    conn.executemany(
        """
        INSERT INTO words(word, definition)
        VALUES (?, ?)
        ON CONFLICT(word) DO UPDATE SET definition=excluded.definition
        """,
        batch,
    )
    batch.clear()


def import_rows(
    conn: sqlite3.Connection,
    ndjson_files: list[Path],
    batch_size: int,
) -> tuple[int, int]:
    batch: list[tuple[str, str]] = []
    read_rows = 0

    for file_path in ndjson_files:
        with file_path.open("r", encoding="utf-8") as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SystemExit(
                        f"ERROR: invalid JSON at {file_path}:{line_no}: {exc.msg}"
                    ) from exc

                if not isinstance(payload, dict):
                    raise SystemExit(
                        f"ERROR: expected JSON object at {file_path}:{line_no}"
                    )

                word = payload.get("word")
                if not isinstance(word, str) or not word:
                    raise SystemExit(
                        f"ERROR: missing/invalid 'word' at {file_path}:{line_no}"
                    )

                batch.append((word, line))
                read_rows += 1
                if len(batch) >= batch_size:
                    flush_batch(conn, batch)

    flush_batch(conn, batch)
    stored_rows = int(conn.execute("SELECT COUNT(*) FROM words").fetchone()[0])
    return read_rows, stored_rows


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("ERROR: --batch-size must be >= 1")

    repo_root = Path(__file__).resolve().parents[1]
    data_dir = resolve_path(repo_root, args.data_dir)
    out_db = resolve_path(repo_root, args.out_db)

    if not data_dir.exists() or not data_dir.is_dir():
        raise SystemExit(f"ERROR: data directory not found: {data_dir}")

    ndjson_files = iter_ndjson_files(data_dir)
    if not ndjson_files:
        raise SystemExit(f"ERROR: no .ndjson files found in: {data_dir}")

    out_db.parent.mkdir(parents=True, exist_ok=True)
    if out_db.exists():
        out_db.unlink()

    with sqlite3.connect(out_db) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        create_schema(conn)
        read_rows, stored_rows = import_rows(conn, ndjson_files, args.batch_size)
        conn.commit()

    print(f"data_dir={data_dir}")
    print(f"out_db={out_db}")
    print(f"ndjson_files={len(ndjson_files)}")
    print(f"rows_read={read_rows}")
    print(f"rows_in_words={stored_rows}")
    print("table=words(word, definition)")
    print("index=idx_words_word(unique)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
