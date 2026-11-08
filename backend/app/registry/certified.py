"""Certified-query registry (SQLite). The promotion loop lives here.

A certified query = a question pattern + the exact tool/args plan that answers it + who verified it and when.
When a new question matches a certified query closely enough, the planner is told to prefer that plan and the
answer is eligible for Tier 1. Analysts promote a Tier-2/3 run to certified after review; they can revoke.

Matching is lexical (token overlap + sequence ratio) with a conservative threshold, optionally confirmed by a
small model for borderline scores. No embeddings service is required.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from ..config import STATE_DIR

DB_PATH = STATE_DIR / "registry.sqlite"
STOP = {"the", "a", "an", "of", "in", "for", "and", "or", "to", "is", "are", "what", "which", "how", "many", "that", "have", "has",
        "with", "by", "on", "at", "as", "be", "been", "their", "its", "any", "all", "this", "these", "those", "do", "does", "did", "there"}

SEED = [
    {
        "name": "q1_quality_shortages_oai_sites",
        "question": "How many drugs are currently in shortage because of quality problems, and which of their manufacturing sites received an OAI classification in the last two fiscal years?",
        "tool": "cq_quality_shortages_oai_sites",
        "args": {"quality_scope": "strict", "fy_mode": "completed", "fy_basis": "inspection_end_date"},
        "pins": {"quality problems": "strict", "last two fiscal years": "completed", "fiscal year": "inspection_end_date"},
        "verified_by": "N. Sahai (seed; validated against DECISIONS.md D1-D8 and tests/test_certified_queries.py)",
        "notes": "Required query 1. Alternate readings (broad, include_current, classification_date) are computed on request and shown side by side.",
    },
    {
        "name": "q2_amoxicillin_oral_suspension_supply",
        "question": "For amoxicillin oral suspension, what is the real supply picture — how many approved applications, how many are actively marketed, and what is currently in shortage?",
        "tool": "cq_supply_picture",
        "args": {"generic_name": "Amoxicillin", "presentation_like": "Oral Suspension%", "approved_scope": "full"},
        "pins": {"approved": "full"},
        "verified_by": "N. Sahai (seed; validated against DECISIONS.md D4/D9 and tests)",
        "notes": "Required query 2. Application counts cannot be restricted to oral suspension (no dosage-form column) — always disclosed.",
    },
    {
        "name": "q3_foreign_sites_not_inspected_since_fy2021",
        "question": "Which foreign manufacturing establishments supplying drugs currently in shortage have not been inspected since FY2021?",
        "tool": "cq_foreign_sites_not_inspected",
        "args": {"since_fy": 2021, "inclusive": True, "fy_basis": "inspection_end_date"},
        "pins": {"not inspected since": "last inspection FY <= target", "foreign": "inspections.country != 'United States'; UNKNOWN if never inspected"},
        "verified_by": "N. Sahai (seed; validated against DECISIONS.md D7/D10/D11 and tests)",
        "notes": "Required query 3. Never-inspected sites are reported separately with country UNKNOWN.",
    },
]


def _tokens(q: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", q.lower()) if t not in STOP and len(t) > 1}


def numeric_tokens(q: str) -> set[str]:
    return set(re.findall(r"\d[\w\-\./]*", q))


def similarity(a: str, b: str) -> float:
    if numeric_tokens(a) != numeric_tokens(b):
        return 0.0  # a different year/strength/number is a different question, however similar the words
    ta, tb = _tokens(a), _tokens(b)
    jacc = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    seq = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return round(0.6 * jacc + 0.4 * seq, 3)


class CertifiedRegistry:
    MATCH_THRESHOLD = 0.72
    BORDERLINE = 0.50

    def __init__(self, path=DB_PATH) -> None:
        self.con = sqlite3.connect(str(path), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS certified_queries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT UNIQUE NOT NULL,
              question TEXT NOT NULL,
              tool TEXT NOT NULL,
              args TEXT NOT NULL,
              pins TEXT NOT NULL DEFAULT '{}',
              verified_by TEXT NOT NULL,
              verified_at TEXT NOT NULL,
              version INTEGER NOT NULL DEFAULT 1,
              status TEXT NOT NULL DEFAULT 'active',
              source_run_id TEXT,
              notes TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT, details TEXT
            );
            """
        )
        self._seed()

    def _seed(self) -> None:
        n = self._exec("SELECT COUNT(*) FROM certified_queries").fetchone()[0]
        if n:
            return
        now = datetime.now(timezone.utc).isoformat()
        for s in SEED:
            self._exec(
                "INSERT INTO certified_queries(name, question, tool, args, pins, verified_by, verified_at, notes) VALUES (?,?,?,?,?,?,?,?)",
                (s["name"], s["question"], s["tool"], json.dumps(s["args"]), json.dumps(s["pins"]), s["verified_by"], now, s["notes"]),
            )
            self.log("system", "seed", s["name"], {"verified_by": s["verified_by"]})
        self.con.commit()

    # ------------------------------------------------------------------ read
    def list(self, include_revoked: bool = False) -> list[dict[str, Any]]:
        q = "SELECT * FROM certified_queries" + ("" if include_revoked else " WHERE status='active'") + " ORDER BY id"
        return [self._row(r) for r in self._exec(q)]

    def get(self, name: str) -> dict[str, Any] | None:
        r = self._exec("SELECT * FROM certified_queries WHERE name=?", (name,)).fetchone()
        return self._row(r) if r else None

    def match(self, question: str) -> dict[str, Any] | None:
        """Best active certified query above threshold, or None. Returns the entry plus the score."""
        best, best_s = None, 0.0
        for e in self.list():
            sc = similarity(question, e["question"])
            if sc > best_s:
                best, best_s = e, sc
        if best and best_s >= self.MATCH_THRESHOLD:
            return {**best, "score": best_s, "match_kind": "lexical"}
        if best and best_s >= self.BORDERLINE:
            return {**best, "score": best_s, "match_kind": "borderline"}  # caller may confirm with a small model
        return None

    # ------------------------------------------------------------------ write
    def promote(self, *, name: str, question: str, tool: str, args: dict[str, Any], pins: dict[str, str], verified_by: str,
                source_run_id: str | None, notes: str = "") -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        existing = self.get(name)
        if existing:
            self._exec(
                "UPDATE certified_queries SET question=?, tool=?, args=?, pins=?, verified_by=?, verified_at=?, version=version+1, status='active', source_run_id=?, notes=? WHERE name=?",
                (question, tool, json.dumps(args), json.dumps(pins), verified_by, now, source_run_id, notes, name))
            action = "recertify"
        else:
            self._exec(
                "INSERT INTO certified_queries(name, question, tool, args, pins, verified_by, verified_at, source_run_id, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                (name, question, tool, json.dumps(args), json.dumps(pins), verified_by, now, source_run_id, notes))
            action = "promote"
        self.log(verified_by, action, name, {"tool": tool, "args": args, "source_run_id": source_run_id})
        self.con.commit()
        return self.get(name)  # type: ignore[return-value]

    def revoke(self, name: str, actor: str, reason: str) -> None:
        self._exec("UPDATE certified_queries SET status='revoked' WHERE name=?", (name,))
        self.log(actor, "revoke", name, {"reason": reason})
        self.con.commit()

    def log(self, actor: str, action: str, target: str | None, details: dict[str, Any] | None = None) -> None:
        self._exec("INSERT INTO audit_log(at, actor, action, target, details) VALUES (?,?,?,?,?)",
                         (datetime.now(timezone.utc).isoformat(), actor, action, target, json.dumps(details or {}, default=str)))
        self.con.commit()

    def audit(self, limit: int = 200) -> list[dict[str, Any]]:
        return [dict(r) for r in self._exec("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]

    def _exec(self, sql: str, params: tuple = ()):
        with self._lock:
            return self.con.execute(sql, params)

    @staticmethod
    def _row(r: sqlite3.Row) -> dict[str, Any]:
        d = dict(r)
        d["args"] = json.loads(d["args"])
        d["pins"] = json.loads(d["pins"] or "{}")
        return d


_registry: CertifiedRegistry | None = None


def get_registry() -> CertifiedRegistry:
    global _registry
    if _registry is None:
        _registry = CertifiedRegistry()
    return _registry
