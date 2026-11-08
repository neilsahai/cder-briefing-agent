import json, sys
from app.tools import call_tool, REGISTRY
def show(name, args):
    r = call_tool(name, args)
    print(f"\n===== {name} {args}")
    v = dict(r.value)
    for k in ("records","application_records","rows"):
        if k in v and isinstance(v[k], list): v[k] = f"<{len(v[k])} rows>"
    print(json.dumps(v, indent=1, default=str)[:5000])
    print("rows cited:", len(r.rows), "| tables:", r.source_tables)
    for i in r.interpretations: print(" INTERP", i.term, "->", i.chosen, "| alt", i.alternatives, f"[{i.decision_ref}]")
    for w in r.warnings: print(" WARN", w.severity.value, w.code, "|", w.message[:220])
print("tools:", list(REGISTRY))
show(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv)>2 else {})
