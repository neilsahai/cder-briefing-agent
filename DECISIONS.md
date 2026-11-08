# DECISIONS.md — Interpretive decisions this system makes, and why

Every ambiguous term in the required queries has more than one defensible reading. This file
records the reading the system uses **by default**, the alternates it will compute on request,
and the evidence behind each choice. The agent's planner reads the same definitions from
`ontology.yaml`; this document is the human-readable rationale.

Principle: **the system never picks silently.** When readings diverge materially, it computes
all of them and shows them side by side with the interpretation labeled.

---

## D1. "As of" date (what does "currently" mean?)

- **Default:** the latest date present in the dataset — `max(revision_date, inspection_end_date, classification_date)` = **2025-10-23**.
- **Alternate:** any user-supplied date (`as_of=YYYY-MM-DD`); the briefing-memo export prints the as-of date on every page.
- **Why:** The assignment PDF describes the data as "a snapshot as of early 2025," but the files contain inspection classifications through October 2025 and shortage revisions through June 2025. A snapshot is "current" as of its most recent record. Hard-coding "early 2025" would silently discard eight months of inspection data.
- **Disclosed on:** every answer that depends on "current," "now," or a fiscal-year window.

## D2. Fiscal year

- **Rule:** FDA fiscal year runs Oct 1 – Sep 30; FY *N* = Oct 1 (N−1) – Sep 30 (N). (Given in the PDF.)
- **Which date assigns an inspection to a FY — default: `inspection_end_date`.** Alternate: `classification_date`.
- **Why:** FDA's public Inspection Classification Database and Data Dashboard report inspections by inspection end date. In this dataset 1 of 20 OAI rows (Sandoz Princeton, FEI 3004455667) straddles a FY boundary: ended 2024-09-26 (FY2024), classified 2024-11-10 (FY2025). Results that differ by basis are shown under both.

## D3. "Last two fiscal years"

- **Default:** the two most recently *completed* fiscal years relative to the as-of date. With as-of 2025-10-23 → **FY2024 and FY2025**.
- **Alternate:** current partial FY plus the prior FY (FY2026 + FY2025).
- **Why:** "Last two" most naturally means completed periods; a 23-day-old FY2026 contains no classified inspections anyway, so both readings yield the same OAI set at the default as-of — the tool states this rather than assuming it.

## D4. "Currently in shortage"

- **Rule:** one row per `shortage_id`, taking the row with the **latest `revision_date`**; status must equal `Current`.
- **Conflict handling:** if a `shortage_id` has multiple rows with different statuses, the answer carries a **status-conflict warning** naming both rows, their revision dates, and which one was used. This dataset has exactly one: `DS-2023-0142` (Amoxicillin 250mg/5mL susp) — `Resolved` rev 2023-11-15, then `Current` rev 2024-01-10. The system reports it as **Current (per latest revision), with a prior Resolved record.**
- **Status semantics are never collapsed.** Per FDA: *Currently in Shortage* = total supply of all clinically interchangeable versions is inadequate to meet demand; *Resolved* = Drug Shortage Staff determines the market is covered based on information from all manufacturers; *Discontinued/To Be Discontinued* = manufacturer has stopped or will stop making the product. "Resolved" and "Discontinued" are both "not current" but mean opposite things for supply planning. The dataset uses `Discontinued`; real FDA uses `To Be Discontinued`/`Discontinuation` — noted in the ontology.
- **Staleness flag:** a `Current` row whose latest revision is more than 18 months before the as-of date is flagged *stale* (9 rows, all last revised 2021–2022). The status is still reported as recorded; the flag tells the reader to confirm before quoting.

## D5. "Quality problems"

- **Default (strict):** `reason_category = 'Quality: cGMP Issue'` — the only category explicitly labeled quality. 6 current records.
- **Alternate (broad):** strict + `Manufacturing Delay`, which in FDA shortage reporting often has a quality root cause but is not labeled as such. 21 current records.
- **Why:** The question says "because of quality problems." The data has a category literally named Quality. Expanding it is an inference about root cause the data doesn't support; the system offers the broad reading as an explicit alternate, not as the answer.

## D6. "How many drugs"

- **Default:** count of **distinct `generic_name`** (drug level).
- **Also reported:** record level (`shortage_id`) and presentation level (`generic_name` + `presentation`). These differ whenever a drug has several presentations or second-source records (the `…B`-suffix IDs are second-source entries for the same drug/presentation under a different application).
- **Why:** A Senator asking "how many drugs" means drugs. A pharmacist may need NDC-level counts. Both are shown; the headline uses drug level and says so.

## D7. "Manufacturing sites" and "manufacturer"

- **Site = FEI** on the application linked from the shortage record (`drug_shortages.related_application → applications.manufacturing_fei`).
- **Sponsor ≠ site operator.** `applications.sponsor_name` is the application holder; `inspections.firm_name` is who operates the facility. In 110 of 121 joinable rows they differ (contract manufacturing). Answers show **both** and label them.
- **Coverage disclosure:** only 21 of 150 shortage rows (13 of 57 current) reference an application that exists in `applications.csv`. Any site-level answer states *"sites known for N of M current shortage records; M−N have no linkable application in this dataset."*
- **FEI validity:** FEIs are 7- or 10-digit numeric identifiers. Rows whose FEI does not match are flagged *invalid format*. FEIs that match the length rule but share no prefix with the rest of the dataset (`4xxxxxxxxx`, 19 application rows, 4 inspection rows) are flagged *format anomaly — verify against the FEI portal before citing*. The 2024 incident in the brief involved an invented FEI; this check exists because of it.

## D8. "Received an OAI classification"

- **Rule:** any inspection row with `classification = 'OAI'` for that FEI whose FY (per D2) falls in the window (per D3), **regardless of `project_area`**.
- **Disclosed:** `project_area` and `product_type` for each OAI hit. FDA classifies per project area, so a site can be OAI for Pre-Approval and NAI for Drug Quality Assurance in the same visit. Readers may want to restrict to Drug Quality Assurance; the tool offers that filter.

## D9. "Approved applications" and "actively marketed"

- **Approved (default):** `marketing_status IN ('Prescription', 'Discontinued')` — fully approved applications, whether or not still marketed. **Tentative Approval is excluded** and reported separately: a tentatively approved ANDA meets FDA requirements but cannot be marketed (typically patent/exclusivity), so counting it overstates supply.
- **Alternate:** include Tentative Approval (any application with an approval date).
- **Actively marketed:** `marketing_status = 'Prescription'`.
- **Dosage-form limitation:** `applications.csv` has **no dosage-form column**. For "amoxicillin oral suspension," application counts can only be given at the active-ingredient level (6 Amoxicillin ANDAs) with an explicit statement that the data cannot distinguish oral suspension from capsules or tablets. The shortage side *can* filter on `presentation`.
- **Mislink check:** all 7 Amoxicillin-Clavulanate shortage rows reference `ANDA078201`, whose `active_ingredient` is plain Amoxicillin. Flagged as *ingredient mismatch between shortage record and linked application*; not silently trusted.

## D10. "Foreign establishment"

- **Rule:** `inspections.country != 'United States'` for that FEI.
- **Unknown:** if the FEI has no inspection record, country is **unknown** — the dataset has no other country field. The system reports these separately as *country unverifiable; sponsor name suggests non-US (inference, not data)*. Two current-shortage FEIs fall here (3007891234 Zhejiang Huahai; 4001567890 Hainan Poly).

## D11. "Not inspected since FY2021"

- **Rule:** the FEI's most recent `inspection_end_date` falls in FY2021 or earlier (i.e., no inspection in FY2022+), **or** the FEI has never been inspected (reported as a distinct group, since "not since FY2021" presumes a prior inspection).
- **Why:** "since FY2021" is read inclusively as "no inspection after FY2021." The alternate (no inspection in FY2021 or later) is offered.

## D12. Narration and numbers

- The language model never writes a number, identifier, date, or status value into an answer. Narration uses typed placeholders (`{{E3.count}}`) that are filled from tool outputs by code. Any placeholder that fails to resolve blocks the answer.
- A second model (the verifier) decomposes the narration into atomic claims and checks each against the evidence rows **and** the table those rows came from. A status word sourced from the wrong table is a failure even if the word happens to be correct.

## D13. Trust tiers

| Tier | Meaning | Citable in testimony? |
|---|---|---|
| 1 Certified | Answered via certified tools / certified queries (human-reviewed, versioned) | Yes, with analyst sign-off |
| 2 Derived | LLM-authored SQL, AST-validated, executed, verifier passed | Internal use; promote after review |
| 3 Qualified | Material ambiguity or stated assumption; interpretations shown side by side | Only with the qualifier read aloud |
| 4 Not answerable | Data lacks the field or the question is out of scope | No — says what *can* be answered |

Disclosed-but-not-demoting alternates: some alternates are computed and shown for transparency but do not demote
the tier, because the default is a *definition* in this file rather than a judgment call — D4 (Discontinued is a
separate status, so "in shortage" = Current) and D6 (record- and presentation-level counts are "also reported").
Tools mark these `demotes: false`. A reading that is a genuine judgment call (D5 quality scope, D3 fiscal-year
window, D9 approved scope) always demotes until pinned.

Cap rule: if the gate finds the question's *primary* ask is not in the data (e.g. "when will the shortage end?") but related facts are, the answer is at most **Tier 3** even when every fact it does give is certified. The certified facts are context, not the answer to the question as asked. (Added after rehearsal: a forecast question had earned a Certified label on the strength of its status facts.)

## D14. Things this system does not do

- Infer root causes beyond `reason_category`.
- Guess a country, FEI, or status that is not in the data.
- Use retrieval over documents — all answers come from structured queries over the three tables.
- Let the model decide "complexity"; model routing is by role with rule-based escalation (see `backend/app/llm/routing.py`).
