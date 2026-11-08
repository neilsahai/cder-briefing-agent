import asyncio
import json

from fastapi.testclient import TestClient

from app.api import app
from app.mcp_server import mcp


def test_api_health_rows_registry():
    c = TestClient(app)
    assert c.get("/api/data/schema").json()["data_max_date"] == "2025-10-23"
    rows = c.get("/api/data/rows", params={"ids": "drug_shortages#L2,inspections#L5"}).json()
    assert rows[0]["data"]["shortage_id"] == "DS-2023-0142" and rows[1]["data"]["classification"] == "OAI"
    names = [x["name"] for x in c.get("/api/certified").json()]
    assert names[0].startswith("q1_")
    h = c.get("/api/data/health").json()
    assert any(f["rule_id"] == "DQ01_status_conflict" for f in h["findings"])
    assert len(c.get("/api/tools").json()) >= 14


def test_briefing_lifecycle_and_export():
    c = TestClient(app)
    b = c.post("/api/briefings", json={"title": "T", "author": "tester"}).json()
    assert b["items"] == [] and b["status"] == "draft"
    md = c.get(f"/api/briefings/{b['id']}/export.md").text
    assert "# T" in md and "Footnotes" in md
    assert c.get(f"/api/briefings/{b['id']}/export.docx").status_code == 200


def test_mcp_exposes_certified_tools():
    async def go():
        tools = await mcp.list_tools()
        assert {"cq_quality_shortages_oai_sites", "current_shortages", "glossary"} <= {t.name for t in tools}
        res = await mcp.call_tool("current_shortages", {"params": {"reason_scope": "strict"}})
        txt = res[0].text if isinstance(res, (list, tuple)) else res.content[0].text
        d = json.loads(txt)
        assert d["value"]["counts"]["distinct_drugs"] == 6 and d["rows"]
    asyncio.run(go())
