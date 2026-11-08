"""Briefing builder: analysts pin answers into a briefing, sign off claim by claim, export a footnoted memo.
Stored as JSON files under state/briefings. Export: Markdown always; DOCX via python-docx when available."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import STATE_DIR
from .registry.runs import load_run

BRIEF_DIR = STATE_DIR / "briefings"
BRIEF_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(title: str, audience: str = "Senate HELP Committee — pediatric antibiotic shortages", author: str = "") -> dict[str, Any]:
    b = {"id": uuid.uuid4().hex[:10], "title": title, "audience": author and audience or audience, "author": author,
         "created_at": _now(), "updated_at": _now(), "items": [], "status": "draft"}
    _save(b)
    return b


def _path(bid: str) -> Path:
    return BRIEF_DIR / f"{bid}.json"


def _save(b: dict[str, Any]) -> None:
    b["updated_at"] = _now()
    _path(b["id"]).write_text(json.dumps(b, indent=1, default=str))


def get(bid: str) -> dict[str, Any] | None:
    p = _path(bid)
    return json.loads(p.read_text()) if p.exists() else None


def list_all() -> list[dict[str, Any]]:
    out = []
    for p in sorted(BRIEF_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        b = json.loads(p.read_text())
        out.append({k: b[k] for k in ("id", "title", "audience", "author", "created_at", "updated_at", "status")} | {"n_items": len(b["items"])})
    return out


def pin_run(bid: str, run_id: str, note: str = "") -> dict[str, Any]:
    b = get(bid)
    run = load_run(run_id)
    if not b or not run:
        raise KeyError("briefing or run not found")
    item = {"item_id": uuid.uuid4().hex[:8], "run_id": run_id, "question": run["question"], "headline": run["headline"],
            "markdown": run["markdown"], "tier": run["tier"], "tier_label": run["tier_label"], "tier_reasons": run["tier_reasons"],
            "rows": run["rows"], "warnings": [w for w in run["warnings"] if w["severity"] in ("high", "medium")],
            "interpretations": [i for i in run.get("interpretations_applied", [])], "pins": run.get("pins", {}),
            "certified_query_match": run.get("certified_query_match"), "pinned_at": _now(), "note": note,
            "signoff": None}
    b["items"].append(item)
    _save(b)
    return b


def remove_item(bid: str, item_id: str) -> dict[str, Any]:
    b = get(bid)
    if not b:
        raise KeyError("briefing not found")
    b["items"] = [i for i in b["items"] if i["item_id"] != item_id]
    _save(b)
    return b


def sign_off(bid: str, item_id: str, reviewer: str, decision: str, comment: str = "") -> dict[str, Any]:
    b = get(bid)
    if not b:
        raise KeyError("briefing not found")
    for i in b["items"]:
        if i["item_id"] == item_id:
            i["signoff"] = {"reviewer": reviewer, "decision": decision, "comment": comment, "at": _now()}
    all_signed = b["items"] and all(i["signoff"] and i["signoff"]["decision"] == "approved" for i in b["items"])
    b["status"] = "approved" if all_signed else "draft"
    _save(b)
    return b


def readiness(item: dict[str, Any]) -> dict[str, Any]:
    """Senate-ready = Tier 1 AND approved sign-off. Everything else is labeled with what is missing."""
    missing = []
    if item["tier"] != 1:
        missing.append(f"trust tier is {item['tier']} ({item['tier_label']}); Tier 1 Certified required")
    if not item.get("signoff") or item["signoff"]["decision"] != "approved":
        missing.append("no approved analyst sign-off")
    return {"senate_ready": not missing, "missing": missing}


# ----------------------------------------------------------------------------- export
def to_markdown(b: dict[str, Any]) -> str:
    lines = [f"# {b['title']}", "", f"**Audience:** {b['audience']}  ", f"**Prepared by:** {b.get('author') or '—'}  ",
             f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
             f"**Status:** {b['status']}", "",
             "> Every figure below is traced to a row in the source files (drug_shortages.csv, applications.csv, inspections.csv). "
             "Footnotes list the row citations. Items not marked **Senate-ready** carry a trust tier below Certified or lack sign-off and should not be read aloud as fact.", ""]
    footnotes: list[str] = []
    for n, item in enumerate(b["items"], 1):
        rd = readiness(item)
        badge = "✅ Senate-ready" if rd["senate_ready"] else "⚠️ " + "; ".join(rd["missing"])
        lines += [f"## {n}. {item['question']}", "", f"**Trust:** Tier {item['tier']} — {item['tier_label']} · {badge}", ""]
        if item.get("pins"):
            lines.append("**Pinned interpretations:** " + "; ".join(f"{k} = {v}" for k, v in item["pins"].items()) + "  ")
        if item.get("certified_query_match") and item["certified_query_match"].get("applied", True):
            cq = item["certified_query_match"]
            lines.append(f"**Certified query:** {cq.get('name')} (verified by {cq.get('verified_by')})  ")
        lines += ["", f"**Headline.** {item['headline']}", "", item["markdown"].strip(), ""]
        if item["signoff"]:
            s = item["signoff"]
            lines += [f"_Reviewed by {s['reviewer']} — {s['decision']} ({s['at'][:10]}){': ' + s['comment'] if s.get('comment') else ''}_", ""]
        rows = item.get("rows", [])
        fn = len(footnotes) + 1
        footnotes.append(f"[^{fn}]: Item {n} evidence rows ({len(rows)}): " + ", ".join(f"{r['table']}#L{r['line']}" for r in rows[:60]) + (" …" if len(rows) > 60 else ""))
        lines.append(f"Source rows: see footnote [^{fn}].")
        lines.append("")
    lines += ["---", "", "## Footnotes — row-level citations", ""] + footnotes
    return "\n".join(lines)


def to_docx(b: dict[str, Any]) -> bytes | None:
    try:
        from docx import Document
        from docx.shared import Pt
    except Exception:  # noqa: BLE001
        return None
    import io
    doc = Document()
    doc.add_heading(b["title"], 0)
    p = doc.add_paragraph()
    p.add_run("Audience: ").bold = True; p.add_run(b["audience"] + "\n")
    p.add_run("Prepared by: ").bold = True; p.add_run((b.get("author") or "—") + "\n")
    p.add_run("Generated: ").bold = True; p.add_run(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "\n")
    p.add_run("Status: ").bold = True; p.add_run(b["status"])
    doc.add_paragraph("Every figure is traced to a row in the source files. Footnotes list row citations. Items not marked Senate-ready "
                      "carry a trust tier below Certified or lack sign-off and should not be read aloud as fact.").italic = True
    foot = []
    for n, item in enumerate(b["items"], 1):
        rd = readiness(item)
        doc.add_heading(f"{n}. {item['question']}", 1)
        t = doc.add_paragraph()
        t.add_run(f"Trust: Tier {item['tier']} — {item['tier_label']}. ").bold = True
        t.add_run("Senate-ready." if rd["senate_ready"] else "Not Senate-ready: " + "; ".join(rd["missing"]))
        if item.get("pins"):
            doc.add_paragraph("Pinned interpretations: " + "; ".join(f"{k} = {v}" for k, v in item["pins"].items()))
        h = doc.add_paragraph(); h.add_run("Headline. ").bold = True; h.add_run(item["headline"])
        for line in item["markdown"].splitlines():
            line = line.rstrip()
            if not line:
                continue
            if line.startswith("## ") or line.startswith("**") and line.endswith("**") and len(line) < 60:
                doc.add_heading(line.strip("#* "), 2)
            elif line.startswith("- "):
                doc.add_paragraph(re.sub(r"\*\*(.*?)\*\*", r"\1", line[2:]), style="List Bullet")
            else:
                doc.add_paragraph(re.sub(r"\*\*(.*?)\*\*", r"\1", line))
        if item["signoff"]:
            s = item["signoff"]
            doc.add_paragraph(f"Reviewed by {s['reviewer']} — {s['decision']} ({s['at'][:10]}). {s.get('comment','')}").italic = True
        rows = item.get("rows", [])
        foot.append(f"[{n}] {len(rows)} evidence rows: " + ", ".join(f"{r['table']}#L{r['line']}" for r in rows[:80]) + (" …" if len(rows) > 80 else ""))
        doc.add_paragraph(f"Source rows: footnote [{n}].")
    doc.add_heading("Footnotes — row-level citations", 1)
    for f in foot:
        para = doc.add_paragraph(f)
        for r in para.runs:
            r.font.size = Pt(8)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
