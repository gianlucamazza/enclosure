"""Versioned world store. Inner Party reads this; the subject never does."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_CLOCK = datetime(2026, 6, 1, 9, 0, 0, tzinfo=UTC)


def _now_iso(clock: datetime) -> str:
    return clock.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_clock(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass(frozen=True)
class Identity:
    id: str
    kind: str
    hosts: tuple[str, ...]
    display_name: str
    chrome: str
    headers: dict[str, str]


@dataclass(frozen=True)
class Fact:
    id: str
    party_claim: str
    ground_truth: str
    currently_injected: bool


@dataclass(frozen=True)
class Document:
    id: str
    channel: str
    host: str | None
    path: str
    identity_id: str | None
    body: str
    content_type: str
    headers: dict[str, str]
    mtime: str
    version: int
    live: bool
    fact_ids: tuple[str, ...]
    origin: str | None
    title: str | None = None


@dataclass(frozen=True)
class Event:
    id: int
    ts: str
    kind: str
    payload: dict[str, Any]


class World:
    """SQLite-backed, fully versioned ontology + documents + clock."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        if self.get_clock() is None:
            self.set_clock(DEFAULT_CLOCK)

    def close(self) -> None:
        self._conn.close()

    def reset(self) -> None:
        self._conn.executescript(
            """
            DELETE FROM documents;
            DELETE FROM facts;
            DELETE FROM identities;
            DELETE FROM events;
            DELETE FROM meta;
            """
        )
        self._conn.commit()
        self.set_clock(DEFAULT_CLOCK)

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identities (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              hosts_json TEXT NOT NULL,
              display_name TEXT NOT NULL,
              chrome TEXT NOT NULL,
              headers_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS facts (
              id TEXT PRIMARY KEY,
              party_claim TEXT NOT NULL,
              ground_truth TEXT NOT NULL,
              currently_injected INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY,
              channel TEXT NOT NULL,
              host TEXT,
              path TEXT NOT NULL,
              identity_id TEXT,
              body TEXT NOT NULL,
              content_type TEXT NOT NULL,
              headers_json TEXT NOT NULL,
              mtime TEXT NOT NULL,
              version INTEGER NOT NULL,
              live INTEGER NOT NULL,
              fact_ids_json TEXT NOT NULL,
              origin TEXT,
              title TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_docs_locator
              ON documents(channel, host, path, live);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL,
              kind TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    # --- clock ----------------------------------------------------------

    def get_clock(self) -> datetime | None:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = 'clock'"
        ).fetchone()
        if row is None:
            return None
        return parse_clock(row["value"])

    def set_clock(self, value: str | datetime) -> datetime:
        clock = parse_clock(value)
        self._conn.execute(
            "INSERT INTO meta(key, value) VALUES('clock', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_now_iso(clock),),
        )
        self._conn.commit()
        return clock

    def http_date(self) -> str:
        """RFC 1123 Date header from the fake clock."""
        clock = self.get_clock() or DEFAULT_CLOCK
        return clock.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # --- identities / facts --------------------------------------------

    def upsert_identity(self, identity: Identity) -> None:
        self._conn.execute(
            """
            INSERT INTO identities(id, kind, hosts_json, display_name, chrome, headers_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              kind = excluded.kind,
              hosts_json = excluded.hosts_json,
              display_name = excluded.display_name,
              chrome = excluded.chrome,
              headers_json = excluded.headers_json
            """,
            (
                identity.id,
                identity.kind,
                json.dumps(list(identity.hosts)),
                identity.display_name,
                identity.chrome,
                json.dumps(identity.headers),
            ),
        )
        self._conn.commit()

    def get_identity(self, identity_id: str) -> Identity | None:
        row = self._conn.execute(
            "SELECT * FROM identities WHERE id = ?", (identity_id,)
        ).fetchone()
        return None if row is None else _identity_from_row(row)

    def identity_for_host(self, host: str) -> Identity | None:
        host = host.lower().split(":")[0]
        for row in self._conn.execute("SELECT * FROM identities"):
            ident = _identity_from_row(row)
            if host in ident.hosts:
                return ident
        return None

    def upsert_fact(self, fact: Fact) -> None:
        self._conn.execute(
            """
            INSERT INTO facts(id, party_claim, ground_truth, currently_injected)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              party_claim = excluded.party_claim,
              ground_truth = excluded.ground_truth,
              currently_injected = excluded.currently_injected
            """,
            (
                fact.id,
                fact.party_claim,
                fact.ground_truth,
                int(fact.currently_injected),
            ),
        )
        self._conn.commit()

    def set_fact_injected(self, fact_id: str, injected: bool) -> None:
        self._conn.execute(
            "UPDATE facts SET currently_injected = ? WHERE id = ?",
            (int(injected), fact_id),
        )
        self._conn.commit()

    def get_fact(self, fact_id: str) -> Fact | None:
        row = self._conn.execute(
            "SELECT * FROM facts WHERE id = ?", (fact_id,)
        ).fetchone()
        return None if row is None else _fact_from_row(row)

    def facts(self) -> list[Fact]:
        return [_fact_from_row(r) for r in self._conn.execute("SELECT * FROM facts")]

    # --- documents ------------------------------------------------------

    def publish(
        self,
        *,
        channel: str,
        path: str,
        body: str,
        host: str | None = None,
        identity_id: str | None = None,
        content_type: str = "text/html; charset=utf-8",
        headers: dict[str, str] | None = None,
        fact_ids: Iterable[str] = (),
        origin: str | None = None,
        title: str | None = None,
    ) -> Document:
        host_n = _norm_host(host)
        path_n = _norm_path(path)
        fact_tuple = tuple(fact_ids)
        current = self.get_live(channel, host_n, path_n)
        version = 1 if current is None else current.version + 1
        if current is not None:
            self._conn.execute(
                "UPDATE documents SET live = 0 WHERE id = ?", (current.id,)
            )
        doc_id = str(uuid4())
        clock = self.get_clock() or DEFAULT_CLOCK
        mtime = _now_iso(clock)
        self._conn.execute(
            """
            INSERT INTO documents(
              id, channel, host, path, identity_id, body, content_type,
              headers_json, mtime, version, live, fact_ids_json, origin, title
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                doc_id,
                channel,
                host_n,
                path_n,
                identity_id,
                body,
                content_type,
                json.dumps(headers or {}),
                mtime,
                version,
                json.dumps(list(fact_tuple)),
                origin,
                title,
            ),
        )
        self._conn.commit()
        if fact_tuple:
            for fid in fact_tuple:
                self.set_fact_injected(fid, True)
        return self.get_by_id(doc_id)  # type: ignore[return-value]

    def get_by_id(self, doc_id: str) -> Document | None:
        row = self._conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return None if row is None else _doc_from_row(row)

    def get_live(
        self, channel: str, host: str | None, path: str
    ) -> Document | None:
        host_n = _norm_host(host)
        path_n = _norm_path(path)
        row = self._conn.execute(
            """
            SELECT * FROM documents
            WHERE channel = ? AND live = 1
              AND IFNULL(host, '') = IFNULL(?, '')
              AND path = ?
            """,
            (channel, host_n, path_n),
        ).fetchone()
        return None if row is None else _doc_from_row(row)

    def locator_history(
        self, channel: str, host: str | None, path: str
    ) -> list[Document]:
        host_n = _norm_host(host)
        path_n = _norm_path(path)
        rows = self._conn.execute(
            """
            SELECT * FROM documents
            WHERE channel = ?
              AND IFNULL(host, '') = IFNULL(?, '')
              AND path = ?
            ORDER BY version DESC
            """,
            (channel, host_n, path_n),
        ).fetchall()
        return [_doc_from_row(r) for r in rows]

    def all_paths(self, channel: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT path FROM documents WHERE channel = ?",
            (channel,),
        ).fetchall()
        return [r["path"] for r in rows]

    def live_docs(self, channel: str | None = None) -> list[Document]:
        if channel is None:
            rows = self._conn.execute(
                "SELECT * FROM documents WHERE live = 1"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM documents WHERE live = 1 AND channel = ?",
                (channel,),
            ).fetchall()
        return [_doc_from_row(r) for r in rows]

    def live_docs_with_fact(self, fact_id: str) -> list[Document]:
        out: list[Document] = []
        for doc in self.live_docs():
            if fact_id in doc.fact_ids:
                out.append(doc)
        return out

    def latest_without_fact(
        self, channel: str, host: str | None, path: str, fact_id: str
    ) -> Document | None:
        for doc in self.locator_history(channel, host, path):
            if fact_id not in doc.fact_ids:
                return doc
        return None

    def make_live(self, doc_id: str) -> Document:
        doc = self.get_by_id(doc_id)
        if doc is None:
            raise KeyError(doc_id)
        self._conn.execute(
            """
            UPDATE documents SET live = 0
            WHERE channel = ? AND IFNULL(host, '') = IFNULL(?, '') AND path = ?
            """,
            (doc.channel, doc.host, doc.path),
        )
        self._conn.execute(
            "UPDATE documents SET live = 1 WHERE id = ?", (doc_id,)
        )
        self._conn.commit()
        live = self.get_by_id(doc_id)
        assert live is not None
        return live

    def unlive(self, doc_id: str) -> None:
        self._conn.execute(
            "UPDATE documents SET live = 0 WHERE id = ?", (doc_id,)
        )
        self._conn.commit()

    def http_get(self, host: str, path: str) -> Document | None:
        host_n = _norm_host(host)
        path_n = _norm_path(path)
        doc = self.get_live("http", host_n, path_n)
        if doc is not None:
            return doc
        # directory-style fallback: /downloads -> /downloads/
        if not path_n.endswith("/"):
            doc = self.get_live("http", host_n, path_n + "/")
            if doc is not None:
                return doc
        ident = self.identity_for_host(host_n or "")
        if ident is None:
            return None
        for alias in ident.hosts:
            if alias == host_n:
                continue
            doc = self.get_live("http", alias, path_n)
            if doc is not None:
                return doc
        return None

    def search(self, query: str) -> list[Document]:
        q = query.strip().lower()
        hits: list[Document] = []
        for doc in self.live_docs("search"):
            blob = " ".join(
                part
                for part in (
                    doc.path,
                    doc.title or "",
                    doc.body,
                    doc.origin or "",
                    " ".join(doc.fact_ids),
                )
                if part
            ).lower()
            if q and q in blob:
                hits.append(doc)
                continue
            tokens = [t for t in q.replace("+", " ").split() if t]
            if tokens and all(t in blob for t in tokens):
                hits.append(doc)
        return hits

    # --- events / ledger -----------------------------------------------

    def log(self, kind: str, payload: dict[str, Any]) -> Event:
        clock = self.get_clock() or DEFAULT_CLOCK
        ts = _now_iso(clock)
        cur = self._conn.execute(
            "INSERT INTO events(ts, kind, payload_json) VALUES (?, ?, ?)",
            (ts, kind, json.dumps(payload)),
        )
        self._conn.commit()
        return Event(id=int(cur.lastrowid), ts=ts, kind=kind, payload=payload)

    def events(self, kind: str | None = None) -> list[Event]:
        if kind is None:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY id ASC"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE kind = ? ORDER BY id ASC", (kind,)
            ).fetchall()
        return [
            Event(
                id=r["id"],
                ts=r["ts"],
                kind=r["kind"],
                payload=json.loads(r["payload_json"]),
            )
            for r in rows
        ]

    def ledger(self) -> dict[str, Any]:
        """Experimenter-only view: ground truth vs what the subject can see."""
        facts = []
        for fact in self.facts():
            facts.append(
                {
                    "id": fact.id,
                    "party_claim": fact.party_claim,
                    "ground_truth": fact.ground_truth,
                    "currently_injected": fact.currently_injected,
                    "live_documents": [
                        {
                            "channel": d.channel,
                            "host": d.host,
                            "path": d.path,
                            "version": d.version,
                            "identity_id": d.identity_id,
                        }
                        for d in self.live_docs_with_fact(fact.id)
                    ],
                }
            )
        clock = self.get_clock()
        return {
            "clock": _now_iso(clock) if clock else None,
            "facts": facts,
            "live_document_count": len(self.live_docs()),
            "event_count": len(self.events()),
        }


def _norm_host(host: str | None) -> str | None:
    if host is None or host == "":
        return None
    return host.lower().split(":")[0].strip()


def _norm_path(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        # keep trailing slash for explicit directory pages
        return path
    return path


def _identity_from_row(row: sqlite3.Row) -> Identity:
    return Identity(
        id=row["id"],
        kind=row["kind"],
        hosts=tuple(json.loads(row["hosts_json"])),
        display_name=row["display_name"],
        chrome=row["chrome"],
        headers=json.loads(row["headers_json"]),
    )


def _fact_from_row(row: sqlite3.Row) -> Fact:
    return Fact(
        id=row["id"],
        party_claim=row["party_claim"],
        ground_truth=row["ground_truth"],
        currently_injected=bool(row["currently_injected"]),
    )


def _doc_from_row(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"],
        channel=row["channel"],
        host=row["host"],
        path=row["path"],
        identity_id=row["identity_id"],
        body=row["body"],
        content_type=row["content_type"],
        headers=json.loads(row["headers_json"]),
        mtime=row["mtime"],
        version=row["version"],
        live=bool(row["live"]),
        fact_ids=tuple(json.loads(row["fact_ids_json"])),
        origin=row["origin"],
        title=row["title"],
    )
