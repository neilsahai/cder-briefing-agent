"""FastAPI surface. /api/ask streams trace steps over SSE and ends with the full Answer."""
from __future__ import annotations

import asyncio
import json
import queue
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")

from . import briefings  # noqa: E402
from .agent.runner import run  # noqa: E402
from .data.audit import get_audit  # noqa: E402
from .data.store import get_store  # noqa: E402
from .llm.routing import ROLE_MODELS  # noqa: E402
from .registry.certified import get_registry  # noqa: E402
from .registry.runs import analytics, list_runs, load_run  # noqa: E402
from .tools import REGISTRY  # noqa: E402

app = FastAPI(title="CDER Drug Shortage Briefing Agent", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AskIn(BaseModel):
    question: str
    as_of: str | None = None
    pins: dict[str, str] | None = None
    use_registry: bool = True


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@app.post("/api/ask")
async def ask(body: AskIn):
    q: queue.Queue = queue.Queue()

    def worker() -> None:
        try:
            ans = run(body.question, as_of=body.as_of, pins=body.pins, use_registry=body.use_registry,
                      sink=lambda st: q.put(("step", json.loads(st.model_dump_json()))))
            q.put(("answer", json.loads(ans.model_dump_json())))
        except Exception as ex:  # noqa: BLE001
            q.put(("error", {"error": f"{type(ex).__name__}: {ex}"}))
        finally:
            q.put(("done", {}))

    threading.Thread(target=worker, daemon=True).start()

    async def gen():
        yield _sse("start", {"question": body.question})
        while True:
            try:
                kind, data = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.15)
                yield ": keepalive\n\n"
                continue
            yield _sse(kind, data)
            if kind == "done":
                break

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/ask_sync")
def ask_sync(body: AskIn):
    ans = run(body.question, as_of=body.as_of, pins=body.pins, use_registry=body.use_registry)
    return json.loads(ans.model_dump_json())


# ----------------------------------------------------------------------------- runs
@app.get("/api/runs")
def runs(limit: int = 100):
    return list_runs(limit)


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    r = load_run(run_id)
    if not r:
        raise HTTPException(404, "run not found")
    return r


@app.get("/api/analytics")
def get_analytics():
    return analytics()


# ----------------------------------------------------------------------------- data
@app.get("/api/data/health")
def data_health(as_of: str | None = None):
    a = get_audit(as_of)
    return {"summary": a.summary(), "findings": [{"rule_id": f.rule_id, "severity": f.severity, "message": f.message,
                                                 "rows": [r.id for r in f.rows][:50], "n_rows": len(f.rows)} for f in a.findings]}


@app.get("/api/data/rows")
def data_rows(ids: str = Query(description="comma-separated row ids like drug_shortages#L2")):
    store = get_store()
    out = []
    for rid in ids.split(","):
        rid = rid.strip()
        if "#L" not in rid:
            continue
        table, line = rid.split("#L")
        if table not in store.frames:
            continue
        df = store.frames[table]
        row = df[df["line_no"] == int(line)]
        if len(row):
            d = {k: (str(v) if not isinstance(v, (int, float)) else v) for k, v in row.iloc[0].to_dict().items()}
            out.append({"row_id": rid, "table": table, "line": int(line), "data": d})
    return out


@app.get("/api/data/schema")
def data_schema():
    store = get_store()
    return {"schema": store.schema_text(), "data_max_date": store.data_max_date.isoformat(),
            "tables": {t: len(store.frames[t]) for t in store.frames}}


@app.get("/api/ontology")
def ontology_file():
    return Response((REPO_ROOT / "ontology.yaml").read_text(), media_type="text/yaml")


@app.get("/api/decisions")
def decisions_file():
    return Response((REPO_ROOT / "DECISIONS.md").read_text(), media_type="text/markdown")


@app.get("/api/tools")
def tools():
    return [{"name": n, "certified": t.certified, "decision_refs": t.decision_refs, "description": t.description} for n, t in REGISTRY.items()]


@app.get("/api/config")
def config():
    import os
    return {"provider": os.environ.get("PROVIDER", "anthropic"), "models": ROLE_MODELS}


# ----------------------------------------------------------------------------- certified registry
class PromoteIn(BaseModel):
    run_id: str
    name: str
    verified_by: str
    notes: str = ""


@app.get("/api/certified")
def certified(include_revoked: bool = False):
    return get_registry().list(include_revoked)


@app.get("/api/certified/audit")
def certified_audit():
    return get_registry().audit()


@app.post("/api/certified/promote")
def promote(body: PromoteIn):
    r = load_run(body.run_id)
    if not r:
        raise HTTPException(404, "run not found")
    if r["tier"] == 4:
        raise HTTPException(400, "cannot certify an unanswerable question")
    flagged = [c for c in r.get("claims", []) if c["verdict"] in ("unsupported", "misattributed")]
    if flagged:
        raise HTTPException(400, f"run has {len(flagged)} flagged claim(s); fix before certifying")
    # the plan = the non-SYS evidence tool calls; pins = divergent terms resolved by the chosen readings
    ev = [e for e in r["evidence"] if e["id"] != "SYS"]
    if not ev:
        raise HTTPException(400, "run has no evidence to certify")
    primary = ev[0]
    pins = dict(r.get("pins") or {})
    for i in r.get("interpretations_applied", []):
        if i.get("differs"):
            pins.setdefault(i["term"], i["chosen"])
    entry = get_registry().promote(name=body.name, question=r["question"], tool=primary["tool"], args=primary["args"], pins=pins,
                                   verified_by=body.verified_by, source_run_id=body.run_id, notes=body.notes)
    return entry


class RevokeIn(BaseModel):
    actor: str
    reason: str


@app.post("/api/certified/{name}/revoke")
def revoke(name: str, body: RevokeIn):
    get_registry().revoke(name, body.actor, body.reason)
    return {"ok": True}


# ----------------------------------------------------------------------------- briefings
class BriefingIn(BaseModel):
    title: str
    audience: str = "Senate HELP Committee — pediatric antibiotic shortages"
    author: str = ""


class PinIn(BaseModel):
    run_id: str
    note: str = ""


class SignIn(BaseModel):
    reviewer: str
    decision: str  # approved | rejected | needs_changes
    comment: str = ""


@app.get("/api/briefings")
def briefings_list():
    return briefings.list_all()


@app.post("/api/briefings")
def briefings_create(body: BriefingIn):
    return briefings.create(body.title, body.audience, body.author)


@app.get("/api/briefings/{bid}")
def briefing_get(bid: str):
    b = briefings.get(bid)
    if not b:
        raise HTTPException(404)
    for i in b["items"]:
        i["readiness"] = briefings.readiness(i)
    return b


@app.post("/api/briefings/{bid}/pin")
def briefing_pin(bid: str, body: PinIn):
    try:
        return briefings.pin_run(bid, body.run_id, body.note)
    except KeyError as ex:
        raise HTTPException(404, str(ex))


@app.delete("/api/briefings/{bid}/items/{item_id}")
def briefing_remove(bid: str, item_id: str):
    return briefings.remove_item(bid, item_id)


@app.post("/api/briefings/{bid}/items/{item_id}/signoff")
def briefing_sign(bid: str, item_id: str, body: SignIn):
    return briefings.sign_off(bid, item_id, body.reviewer, body.decision, body.comment)


@app.get("/api/briefings/{bid}/export.md")
def briefing_md(bid: str):
    b = briefings.get(bid)
    if not b:
        raise HTTPException(404)
    return Response(briefings.to_markdown(b), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="briefing-{bid}.md"'})


@app.get("/api/briefings/{bid}/export.docx")
def briefing_docx(bid: str):
    b = briefings.get(bid)
    if not b:
        raise HTTPException(404)
    data = briefings.to_docx(b)
    if data is None:
        raise HTTPException(501, "python-docx not installed")
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="briefing-{bid}.docx"'})


# ----------------------------------------------------------------------------- evals
@app.get("/api/evals/latest")
def evals_latest():
    out = {}
    for suite in ("regression", "capability"):
        p = REPO_ROOT / "evals" / "results" / f"latest_{suite}.json"
        if p.exists():
            d = json.loads(p.read_text())
            out[suite] = {"summary": d["summary"], "records": [{k: r.get(k) for k in ("id", "passed", "tier", "latency_ms", "claims_total", "claims_flagged_final",
                                                                                    "claims_flagged_first_pass", "unverified_numbers", "used_sql", "escalated", "checks", "judges", "headline", "run_id")} for r in d["records"]]}
    sc = REPO_ROOT / "evals" / "results" / "SCORECARD.md"
    out["scorecard_md"] = sc.read_text() if sc.exists() else ""
    return out


# ----------------------------------------------------------------------------- static frontend (built)
DIST = REPO_ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        f = DIST / full_path
        if full_path and f.exists() and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
