"""Consolidate repetitive per-row warnings into one line per code (keeps every RowRef)."""
from __future__ import annotations

from collections import defaultdict

from ..models import RowRef, Warning

PER_ROW_CODES = {
    "DQ08_stale_current": "{n} 'Current' record(s) in this evidence were last revised more than 18 months before the as-of date; status is reported as recorded — confirm before quoting: {items}.",
    "DQ06_fei_no_inspection": "{n} FEI(s) in this evidence have no inspection record, so country and inspection history are UNKNOWN: {items}.",
    "DQ07_fy_boundary_straddle": "{n} inspection(s) in this evidence ended in one fiscal year but were classified in the next; FY attribution depends on date basis: {items}.",
    "DQ11_shared_fei_multiple_sponsors": "{n} FEI(s) in this evidence manufacture for multiple sponsors (contract manufacturing): {items}.",
}

THRESHOLD = 2


def _item(code: str, msg: str) -> str:
    # pull the identifier at the start of the message: "Shortage DS-2023-0142 (…)" / "FEI 3007891234 (…)" / "Inspection of FEI …"
    toks = msg.replace("Inspection of ", "").split()
    if len(toks) >= 2 and toks[0] in ("Shortage", "FEI"):
        name = toks[1]
        paren = msg.find("(")
        close = msg.find(")", paren)
        if paren != -1 and close != -1 and close - paren < 60:
            return f"{name} {msg[paren:close+1]}"
        return name
    return msg[:40]


def consolidate(warnings: list[Warning]) -> list[Warning]:
    by_code: dict[str, list[Warning]] = defaultdict(list)
    order: list[str] = []
    for w in warnings:
        if w.code not in by_code:
            order.append(w.code)
        by_code[w.code].append(w)
    out: list[Warning] = []
    for code in order:
        ws = by_code[code]
        # de-dupe identical messages
        uniq: dict[str, Warning] = {}
        for w in ws:
            if w.message not in uniq:
                uniq[w.message] = w
            else:
                seen = {r.id for r in uniq[w.message].rows}
                uniq[w.message].rows += [r for r in w.rows if r.id not in seen]
        ws = list(uniq.values())
        if code in PER_ROW_CODES and len(ws) > THRESHOLD:
            rows: list[RowRef] = []
            seen: set[str] = set()
            items = []
            for w in ws:
                for r in w.rows:
                    if r.id not in seen:
                        seen.add(r.id); rows.append(r)
                items.append(_item(code, w.message))
            out.append(Warning(code=code, severity=ws[0].severity, rows=rows,
                               message=PER_ROW_CODES[code].format(n=len(ws), items="; ".join(items))))
        else:
            out.extend(ws)
    sev_rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    out.sort(key=lambda w: sev_rank[w.severity.value])
    return out
