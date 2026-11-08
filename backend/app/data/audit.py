"""Data-quality audit. Runs on load; produces AuditFindings and a lineage index.

The lineage index maps every flagged RowRef id -> [findings]. Tools call `warnings_for(rows)`
so any answer whose evidence touches a flagged row inherits the relevant warning automatically.
That is how the amoxicillin status-conflict warning reaches an answer without anyone asking.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from functools import lru_cache

import pandas as pd

from ..models import AuditFinding, RowRef, Severity, Warning
from .store import DataStore, fiscal_year, get_store

FEI_VALID = re.compile(r"^\d{7}$|^\d{10}$")


class Audit:
    def __init__(self, store: DataStore, as_of: date | None = None, stale_months: int = 18) -> None:
        self.store = store
        self.as_of = store.resolve_as_of(as_of)
        self.stale_months = stale_months
        self.findings: list[AuditFinding] = []
        self.lineage: dict[str, list[AuditFinding]] = defaultdict(list)
        self._run()
        for f in self.findings:
            for r in f.rows:
                self.lineage[r.id].append(f)

    # ------------------------------------------------------------------ public
    def warnings_for(self, rows: list[RowRef], min_severity: Severity = Severity.info) -> list[Warning]:
        order = [Severity.info, Severity.low, Severity.medium, Severity.high]
        seen: set[tuple[str, str]] = set()
        out: list[Warning] = []
        for r in rows:
            for f in self.lineage.get(r.id, []):
                if order.index(f.severity) < order.index(min_severity):
                    continue
                k = (f.rule_id, f.message)
                if k in seen:
                    continue
                seen.add(k)
                out.append(Warning(code=f.rule_id, severity=f.severity, message=f.message, rows=f.rows))
        return out

    def summary(self) -> dict:
        by_rule: dict[str, dict] = {}
        for f in self.findings:
            d = by_rule.setdefault(f.rule_id, {"rule_id": f.rule_id, "severity": f.severity, "count": 0, "rows": 0})
            d["count"] += 1
            d["rows"] += len(f.rows)
        return {
            "as_of": self.as_of.isoformat(),
            "total_findings": len(self.findings),
            "rules": sorted(by_rule.values(), key=lambda x: x["rule_id"]),
        }

    # ------------------------------------------------------------------ rules
    def _add(self, rule_id: str, sev: Severity, msg: str, rows: list[RowRef], **details) -> None:
        self.findings.append(AuditFinding(rule_id=rule_id, severity=sev, message=msg, rows=rows, details=details))

    def _run(self) -> None:
        s = self.store.frames["drug_shortages"]
        a = self.store.frames["applications"]
        i = self.store.frames["inspections"]
        rr = self.store.rowref

        # DQ01 status conflict within a shortage_id
        for sid, g in s.groupby("shortage_id"):
            if g["shortage_status"].nunique() > 1:
                g = g.sort_values("revision_date")
                hist = "; ".join(f"{r.shortage_status} (rev {r.revision_date})" for r in g.itertuples())
                latest = g.iloc[-1]
                self._add(
                    "DQ01_status_conflict", Severity.high,
                    f"Shortage {sid} has conflicting status records: {hist}. Latest revision is "
                    f"'{latest.shortage_status}' and is used; the earlier '{g.iloc[0].shortage_status}' record is NOT ignored — it is disclosed.",
                    self.store.rowrefs("drug_shortages", g), shortage_id=sid, used=latest.shortage_status,
                )

        # DQ02 orphan application
        app_nums = set(a["application_number"])
        orphans = s[~s["related_application"].isin(app_nums)]
        if len(orphans):
            self._add(
                "DQ02_orphan_application", Severity.medium,
                f"{len(orphans)} of {len(s)} shortage rows reference an application number not present in applications.csv; "
                f"manufacturing site cannot be determined for these.",
                self.store.rowrefs("drug_shortages", orphans), count=len(orphans), total=len(s),
            )

        # DQ03 ingredient mismatch
        m = s.merge(a[["application_number", "active_ingredient", "line_no"]].rename(columns={"line_no": "_aline"}),
                    left_on="related_application", right_on="application_number")
        mm = m[m["generic_name"].str.lower() != m["active_ingredient"].str.lower()]
        for appn, g in mm.groupby("related_application"):
            rows = self.store.rowrefs("drug_shortages", g)
            arow = a[a["application_number"] == appn].iloc[0]
            rows.append(rr("applications", arow))
            self._add(
                "DQ03_ingredient_mismatch", Severity.high,
                f"{len(g)} shortage record(s) for '{g.iloc[0].generic_name}' link to {appn}, whose active ingredient is "
                f"'{arow.active_ingredient}'. Possible mislink; application-level facts for these shortages are unreliable.",
                rows, application=appn,
            )

        # DQ04/05 FEI format
        for tbl, col in (("applications", "manufacturing_fei"), ("inspections", "fei_number")):
            df = self.store.frames[tbl]
            bad = df[~df[col].str.fullmatch(FEI_VALID)]
            if len(bad):
                self._add("DQ04_fei_invalid_format", Severity.high,
                          f"{len(bad)} {tbl} rows have an FEI that is not 7 or 10 digits.",
                          self.store.rowrefs(tbl, bad))
            prefix_counts = df[col].str[0].value_counts()
            majority = prefix_counts.idxmax()
            anom = df[(df[col].str[0] != majority) & df[col].str.fullmatch(FEI_VALID)]
            if len(anom):
                self._add("DQ05_fei_prefix_anomaly", Severity.medium,
                          f"{len(anom)} {tbl} rows have an FEI beginning with '{'/'.join(sorted(anom[col].str[0].unique()))}' while "
                          f"{prefix_counts[majority]} begin with '{majority}'. Verify these FEIs against FDA's FEI portal before citing.",
                          self.store.rowrefs(tbl, anom), feis=sorted(anom[col].unique().tolist()))

        # DQ06 FEI with no inspection record
        insp_feis = set(i["fei_number"])
        noinsp = a[~a["manufacturing_fei"].isin(insp_feis)]
        for fei, g in noinsp.groupby("manufacturing_fei"):
            self._add("DQ06_fei_no_inspection", Severity.medium,
                      f"FEI {fei} ({', '.join(sorted(g.sponsor_name.unique()))}) has no inspection record; "
                      f"country and inspection history are UNKNOWN for this site.",
                      self.store.rowrefs("applications", g), fei=fei)

        # DQ07 FY boundary straddle
        fy_e = i["inspection_end_date"].map(fiscal_year)
        fy_c = i["classification_date"].map(fiscal_year)
        strad = i[fy_e != fy_c]
        for _, r in strad.iterrows():
            self._add("DQ07_fy_boundary_straddle", Severity.low,
                      f"Inspection of FEI {r.fei_number} ({r.firm_name}) ended {r.inspection_end_date} (FY{fiscal_year(r.inspection_end_date)}) "
                      f"but was classified {r.classification_date} (FY{fiscal_year(r.classification_date)}); fiscal-year attribution depends on basis.",
                      [rr("inspections", r)])

        # DQ08 stale Current
        latest = self.store.df("SELECT * FROM shortages_latest WHERE shortage_status='Current'")
        cutoff = pd.Timestamp(self.as_of) - pd.DateOffset(months=self.stale_months)
        stale = latest[pd.to_datetime(latest["revision_date"]) < cutoff]
        for _, r in stale.iterrows():
            self._add("DQ08_stale_current", Severity.medium,
                      f"Shortage {r.shortage_id} ({r.generic_name}) is recorded as Current but was last revised {str(r.revision_date)[:10]}, "
                      f"more than {self.stale_months} months before the as-of date {self.as_of}. Confirm status before quoting.",
                      [rr("drug_shortages", r)])

        # DQ09 sponsor != operator
        fac = self.store.df("SELECT fei_number, firm_name FROM facilities")
        j = a.merge(fac, left_on="manufacturing_fei", right_on="fei_number")
        mism = j[j["sponsor_name"].str.lower() != j["firm_name"].str.lower()]
        if len(mism):
            self._add("DQ09_sponsor_operator_mismatch", Severity.info,
                      f"{len(mism)} of {len(j)} applications list a sponsor different from the inspected facility operator "
                      f"(contract manufacturing). 'Manufacturer' is ambiguous: sponsor vs site operator.",
                      self.store.rowrefs("applications", mism))

        # DQ10 second-source records
        b = s[s["shortage_id"].str.endswith("B")]
        if len(b):
            self._add("DQ10_second_source_record", Severity.info,
                      f"{len(b)} shortage records carry a 'B' suffix — second-source entries for the same drug/presentation under a different application. "
                      f"Drug-level and record-level counts will differ.",
                      self.store.rowrefs("drug_shortages", b))

        # DQ11 shared FEI across sponsors
        for fei, g in a.groupby("manufacturing_fei"):
            if g["sponsor_name"].nunique() > 1:
                self._add("DQ11_shared_fei_multiple_sponsors", Severity.info,
                          f"FEI {fei} manufactures for {g.sponsor_name.nunique()} sponsors: {', '.join(sorted(g.sponsor_name.unique()))}.",
                          self.store.rowrefs("applications", g), fei=fei)

        # DQ12 missing dosage form (table-level)
        self._add("DQ12_missing_dosage_form", Severity.medium,
                  "applications.csv has no dosage-form column. Application counts cannot be restricted to a presentation "
                  "(e.g. 'oral suspension'); only active-ingredient-level counts are possible.",
                  [], table="applications")

        # DQ13 status label differs from FDA
        self._add("DQ13_status_label_differs_from_fda", Severity.info,
                  "Dataset status 'Discontinued' corresponds to FDA's 'To Be Discontinued' / 'Discontinuation'. "
                  "It means the manufacturer exited; it is NOT a synonym for Resolved.",
                  [], table="drug_shortages")


@lru_cache(maxsize=4)
def get_audit(as_of: str | None = None) -> Audit:
    return Audit(get_store(), as_of=as_of)
