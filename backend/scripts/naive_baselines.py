"""What naive approaches produce for each trap in docs/RED_TEAM_REPORT.md. Deterministic; no LLM."""
import sys
from pathlib import Path

import pandas as pd

d = Path(__file__).resolve().parents[2] / "data" / "raw"
s = pd.read_csv(d / "drug_shortages.csv", dtype=str); a = pd.read_csv(d / "applications.csv", dtype=str); i = pd.read_csv(d / "inspections.csv", dtype=str)
fy = lambda x: (lambda t: t.year + (t.month >= 10))(pd.to_datetime(x))

print("T1  any Amoxicillin row says Resolved:", bool(((s.generic_name == "Amoxicillin") & (s.shortage_status == "Resolved")).any()),
      "| latest revision of DS-2023-0142:", s[s.shortage_id == "DS-2023-0142"].sort_values("revision_date").iloc[-1].shortage_status)
print("T2  'not Current' rows:", (s.shortage_status != "Current").sum(), "| of which Discontinued:", (s.shortage_status == "Discontinued").sum())
j = s[s.shortage_status == "Current"].merge(a, left_on="related_application", right_on="application_number")
print("T3  inner join Current→applications keeps", len(j), "of", (s.shortage_status == "Current").sum())
print("T4  FEIs beginning with '4': applications", a.manufacturing_fei.str.startswith("4").sum(), "inspections", i.fei_number.str.startswith("4").sum(),
      "| 3009999999 exists:", "3009999999" in set(i.fei_number) | set(a.manufacturing_fei))
print("T5  quality strict:", ((s.shortage_status == "Current") & (s.reason_category == "Quality: cGMP Issue")).sum(),
      "| broad:", ((s.shortage_status == "Current") & s.reason_category.isin(["Quality: cGMP Issue", "Manufacturing Delay"])).sum())
print("T6  Current rows:", (s.shortage_status == "Current").sum(), "| distinct drugs:", s[s.shortage_status == "Current"].generic_name.nunique(), "| B-suffix:", s.shortage_id.str.endswith("B").sum())
jj = a.merge(i[["fei_number", "firm_name"]].drop_duplicates(), left_on="manufacturing_fei", right_on="fei_number")
print("T7  sponsor != operator:", (jj.sponsor_name.str.lower() != jj.firm_name.str.lower()).sum(), "of", len(jj))
print("T8  FEIs with no inspection record:", sorted(set(a.manufacturing_fei) - set(i.fei_number)))
oai = i[i.classification == "OAI"]
print("T9  OAI in FY2025 by end date:", (oai.inspection_end_date.map(fy) == 2025).sum(), "| by classification date:", (oai.classification_date.map(fy) == 2025).sum())
amx = a[a.active_ingredient == "Amoxicillin"]
print("T11 'dosage_form' column in applications:", "dosage_form" in a.columns)
print("T12 amoxicillin applications:", len(amx), "| excluding Tentative Approval:", (amx.marketing_status != "Tentative Approval").sum())
mm = s.merge(a, left_on="related_application", right_on="application_number")
print("T13 shortage rows whose linked application ingredient differs:", (mm.generic_name != mm.active_ingredient).sum(), sorted(mm[mm.generic_name != mm.active_ingredient].related_application.unique()))
cur = s.sort_values("revision_date").groupby("shortage_id").tail(1); cur = cur[cur.shortage_status == "Current"]
print("T14 Current rows revised >18 months before 2025-10-23:", (pd.to_datetime(cur.revision_date) < pd.Timestamp("2024-04-23")).sum(), "of", len(cur))
