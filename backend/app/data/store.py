"""DuckDB-backed data store. Every table carries `line_no` (CSV line number) so any row is citable.

Derived views encode DECISIONS.md rules so SQL (certified or LLM-authored) can use them:
  - shortages_latest : one row per shortage_id (latest revision)            [D4]
  - facilities       : one row per FEI with latest inspection + country      [D7/D10]
  - inspections_fy   : inspections + fiscal_year under both bases            [D2]
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

import duckdb
import pandas as pd

from ..config import CSV_FILES
from ..models import RowRef

TABLES = ("drug_shortages", "applications", "inspections")

KEY_COLS = {
    "drug_shortages": ("shortage_id", "revision_date"),
    "applications": ("application_number",),
    "inspections": ("fei_number", "inspection_end_date", "project_area"),
}

DATE_COLS = {
    "drug_shortages": ("initial_posting_date", "revision_date"),
    "applications": ("approval_date",),
    "inspections": ("inspection_end_date", "classification_date"),
}


def fiscal_year(d: date | pd.Timestamp | None) -> int | None:
    """FDA FY: Oct 1 – Sep 30. FY N ends Sep 30 of calendar year N.  [D2]"""
    if d is None or pd.isna(d):
        return None
    d = pd.Timestamp(d)
    return d.year + 1 if d.month >= 10 else d.year


def fy_bounds(fy: int) -> tuple[date, date]:
    return date(fy - 1, 10, 1), date(fy, 9, 30)


class DataStore:
    def __init__(self) -> None:
        self.con = duckdb.connect(database=":memory:")
        self.frames: dict[str, pd.DataFrame] = {}
        for t in TABLES:
            df = pd.read_csv(CSV_FILES[t], dtype=str, keep_default_na=False)
            df.insert(0, "line_no", range(2, len(df) + 2))  # header is line 1
            for c in DATE_COLS[t]:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
            self.frames[t] = df
            self.con.register(f"_{t}_raw", df)
            self.con.execute(f"CREATE TABLE {t} AS SELECT * FROM _{t}_raw")
        self._create_views()
        self.data_max_date: date = self._compute_data_max()

    # ------------------------------------------------------------------ views
    def _create_views(self) -> None:
        self.con.execute(
            """
            CREATE VIEW shortages_latest AS
            SELECT s.*
            FROM drug_shortages s
            JOIN (
              SELECT shortage_id, MAX(revision_date) AS max_rev
              FROM drug_shortages GROUP BY shortage_id
            ) m ON s.shortage_id = m.shortage_id AND s.revision_date = m.max_rev
            """
        )
        self.con.execute(
            """
            CREATE VIEW inspections_fy AS
            SELECT i.*,
              CASE WHEN month(inspection_end_date) >= 10 THEN year(inspection_end_date)+1 ELSE year(inspection_end_date) END AS fy_end,
              CASE WHEN month(classification_date) >= 10 THEN year(classification_date)+1 ELSE year(classification_date) END AS fy_class
            FROM inspections i
            """
        )
        self.con.execute(
            """
            CREATE VIEW facilities AS
            SELECT fei_number,
                   any_value(firm_name) AS firm_name,
                   any_value(city) AS city,
                   any_value(country) AS country,
                   MAX(inspection_end_date) AS last_inspection_end_date,
                   COUNT(*) AS inspection_count,
                   SUM(CASE WHEN classification='OAI' THEN 1 ELSE 0 END) AS oai_count
            FROM inspections GROUP BY fei_number
            """
        )

    def _compute_data_max(self) -> date:
        r = self.con.execute(
            """
            SELECT GREATEST(
              (SELECT MAX(revision_date) FROM drug_shortages),
              (SELECT MAX(inspection_end_date) FROM inspections),
              (SELECT MAX(classification_date) FROM inspections)
            )
            """
        ).fetchone()
        return r[0]

    # ------------------------------------------------------------------ helpers
    def df(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        return self.con.execute(sql, params or []).df()

    def rowref(self, table: str, row: pd.Series | dict) -> RowRef:
        key = "@".join(str(row[c]) for c in KEY_COLS[table])
        return RowRef(table=table, line=int(row["line_no"]), key=key)

    def rowrefs(self, table: str, df: pd.DataFrame) -> list[RowRef]:
        return [self.rowref(table, r) for _, r in df.iterrows()]

    def resolve_as_of(self, as_of: date | str | None) -> date:
        if as_of is None or as_of == "data_max":
            return self.data_max_date
        if isinstance(as_of, str):
            return date.fromisoformat(as_of)
        return as_of

    def schema_text(self) -> str:
        """Schema description for the SQL guard / planner (tables + derived views)."""
        out = []
        for t in TABLES:
            cols = [c for c in self.frames[t].columns]
            out.append(f"{t}({', '.join(cols)})")
        out.append("shortages_latest(same columns as drug_shortages; one row per shortage_id = latest revision)")
        out.append("inspections_fy(inspections columns + fy_end, fy_class)")
        out.append("facilities(fei_number, firm_name, city, country, last_inspection_end_date, inspection_count, oai_count)")
        return "\n".join(out)


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return DataStore()
