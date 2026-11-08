# Pediatric Antibiotic Shortages — Briefing for Senate HELP Committee testimony

**Audience:** Senate HELP Committee — pediatric antibiotic shortages  
**Prepared by:** N. Sahai (analyst) · reviewer: staff pharmacist (demo)  
**Generated:** 2026-11-08 02:42 UTC  
**Status:** approved

> Every figure below is traced to a row in the source files (drug_shortages.csv, applications.csv, inspections.csv). Footnotes list the row citations. Items not marked **Senate-ready** carry a trust tier below Certified or lack sign-off and should not be read aloud as fact.

## 1. How many drugs are currently in shortage because of quality problems, and which of their manufacturing sites received an OAI classification in the last two fiscal years?

**Trust:** Tier 1 — Certified · ✅ Senate-ready

**Pinned interpretations:** quality problems = strict; last two fiscal years = completed; fiscal year = inspection_end_date  
**Certified query:** q1_quality_shortages_oai_sites (verified by N. Sahai (seed; validated against DECISIONS.md D1-D8 and tests/test_certified_queries.py))  

**Headline.** As of 2025-10-23, 6 distinct drugs are in Current shortage for cGMP quality reasons, and 4 of their linked manufacturing sites had an OAI classification in the last two completed fiscal years.

## Answer
As of 2025-10-23, 6 distinct drugs are in Current shortage with reason category Quality: cGMP Issue, across 6 shortage records. [E1] Of the sites linked to those drugs, 4 had an OAI classification with inspection end date in FY2024 to FY2025. [E1]

## Detail
- Drugs: Ampicillin-Sulbactam, Cefepime HCl, Meropenem, Methotrexate Sodium, Piperacillin-Tazobactam and Vancomycin HCl. All six records have status Current. [E1]
- All 6 records link to an application, so 6 are linked and 0 are unlinked. [E1]
- Baxter Healthcare Corporation, FEI 3001234567, Deerfield, United States. Drug: Ampicillin-Sulbactam. Inspection ended 2025-07-06, classified 2025-08-29 (FY2025). Row inspections#L5. [E1]
- Pfizer Manufacturing LLC, FEI 3002891456, McPherson, United States. Drug: Vancomycin HCl. Inspection ended 2024-03-25, classified 2024-05-15 (FY2024). Row inspections#L3. [E1]
- ICU Medical Inc, FEI 3007445123, Lake Forest, United States. Drug: Piperacillin-Tazobactam. Inspection ended 2024-07-02, classified 2024-08-31 (FY2024). Row inspections#L2. [E1]
- Fresenius Kabi USA LLC, FEI 3009123789, Wilson, United States. Drug: Cefepime HCl. Inspection ended 2025-07-10, classified 2025-09-26 (FY2025). Row inspections#L4. [E1]
- Each OAI is in project area Drug Quality Assurance, and the operator and sponsor are the same firm at each site. [E1]
- Linked sites with no OAI in the window: Hospira Inc, FEI 3005678901, for Methotrexate Sodium, last inspection ended 2024-05-21. FEI 3007891234, for Meropenem, has no inspection record. [E1]

## Interpretation applied
- Quality problems: pinned, strict, meaning Quality: cGMP Issue only. [SYS] Alternate, broad: 15 distinct drugs and 21 records, versus 6 drugs and 6 records under strict. [E1, SYS]
- Last two fiscal years: pinned, completed, FY2024 to FY2025. [SYS] Alternate, include current: FY2025 to FY2026, giving OAI sites 3001234567 and 3009123789, which is fewer than 4. [E1, SYS]
- Fiscal year basis: pinned, inspection end date. [SYS] Alternate, classification date: the same sites, 3001234567, 3002891456, 3007445123 and 3009123789. [E1, SYS]
- How many drugs: distinct generic name, the default. [SYS, E1]
- Currently: status Current as of the default as-of date, 2025-10-23. [SYS]
- Manufacturing site: facility operator, with sponsor shown alongside. [E1]

## Caveats
- Three Current records were last revised more than the stale threshold before the as-of date: DS-2023-0202 (Cefepime HCl, revised 2024-03-12), DS-2023-0205 (Methotrexate Sodium, revised 2024-01-17) and DS-2023-0200 (Piperacillin-Tazobactam, revised 2024-01-13). Status is reported as recorded. The warning is rated medium. [E1]
- FEI 3007891234 has no inspection record, so its country is UNKNOWN. The warning is rated medium. [E1]
- Only a minority of shortage rows overall link to an application in the data. [SYS]
- The as-of date is 2025-10-23, while the brief describes the snapshot as early the year. [SYS]

## Cannot be answered from this data
- Whether an OAI classification caused or contributed to any shortage. The data shows only that a site is linked to a shortage drug through its application. [E1]
- Country and inspection history for FEI 3007891234. [E1]
- Dosage-form-level site attribution, because the applications data has no dosage-form column. [SYS]

_Reviewed by Staff pharmacist (demo sign-off) — approved (2026-11-08): Row citations checked against source files._

Source rows: see footnote [^1].

## 2. For amoxicillin oral suspension, what is the real supply picture — how many approved applications, how many are actively marketed, and what is currently in shortage?

**Trust:** Tier 1 — Certified · ✅ Senate-ready

**Pinned interpretations:** approved = full  
**Certified query:** q2_amoxicillin_oral_suspension_supply (verified by N. Sahai (seed; validated against DECISIONS.md D4/D9 and tests))  

**Headline.** As of 2025-10-23, amoxicillin has 4 approved applications and 3 actively marketed, counted across all dosage forms, and 1 oral suspension shortage record with status Current.

## Answer
As of 2025-10-23, the data shows 4 approved (full) amoxicillin applications and 3 marketed as Prescription. These application counts cover amoxicillin in every dosage form, not just oral suspension, because the application table has no dosage-form field [E1, SYS]. For oral suspension, 1 shortage record has a latest status of Current [E1].

## Detail
- **Applications (all dosage forms):** 6 amoxicillin applications in total. 4 are approved under the full reading, 2 are Tentative Approval, and 1 is approved but Discontinued [E1].
- **Marketed:** 3 applications have marketing status Prescription [E1]. One of them is ANDA065355 (Sandoz Inc), which is linked to the Current shortage below [E1].
- **Discontinued application:** ANDA065491 (Teva Pharmaceuticals USA Inc) has marketing status Discontinued [E1].
- **Tentative approvals:** Hikma Pharmaceuticals LLC and Cipla USA Inc hold the Tentative Approval applications [E1].
- **Current shortage:** DS-2023-0142, Amoxicillin Oral Suspension 250mg/5mL (NDC 65162-0175-00). Its status is Current, first posted 2023-08-01 and last revised 2024-01-10. The reason category is Manufacturing Delay, and the related application is ANDA065355 [E1].
- **Status reversal:** DS-2023-0142 was Resolved in the revision dated 2023-11-15. It was then Current in the revision dated 2024-01-10 [E1].
- **Discontinued shortage:** DS-2022-0089, Oral Suspension 400mg/5mL, has latest status Discontinued, as of the revision dated 2023-01-20. Discontinued means the manufacturer has stopped or will stop producing the product, and supply will not recover from this source [E1, SYS]. It is not counted as Current and is not Resolved [E1].

## Interpretation applied
- **Approved:** pinned: full, which excludes Tentative Approval [SYS]. Under the alternate reading, include_tentative, the count is 6 instead of 4 [E1].
- **Actively marketed:** marketing status Prescription. No alternate was declared [E1, SYS].
- **Currently / in shortage:** the as-of date defaults to the latest record date in the dataset, 2025-10-23. The reading is the latest revision per shortage ID with status Current [SYS, E1].
- **Resolved vs Discontinued:** kept separate. Resolved means supply recovered, and Discontinued means supply will not recover from that source [SYS].
- **How many drugs:** counted by distinct generic name [SYS].

## Caveats
- A high-severity warning says the application counts cover all amoxicillin products in any dosage form and may overstate the number of oral suspension applications [E1].
- A high-severity warning says DS-2023-0142 has conflicting status records, Resolved and then Current. The latest revision, Current, is used, and the earlier Resolved record is disclosed rather than ignored [E1].
- A medium-severity warning says DS-2023-0142 was last revised 2024-01-10, more than 18 months before the as-of date. The warning says to confirm the status before quoting it [E1].

## Cannot be answered from this data
- Application counts cannot be limited to oral suspension, because the application table has no dosage-form column [SYS, E1].
- Posted shortage status is the only supply signal available. The data cannot establish actual supply beyond it [SYS].
- The data cannot confirm whether DS-2023-0142 is still a shortage today, given the last revision date above [E1].

_Reviewed by Staff pharmacist (demo sign-off) — approved (2026-11-08): Row citations checked against source files._

Source rows: see footnote [^2].

## 3. Which foreign manufacturing establishments supplying drugs currently in shortage have not been inspected since FY2021?

**Trust:** Tier 1 — Certified · ✅ Senate-ready

**Pinned interpretations:** not inspected since = last inspection FY <= target; foreign = inspections.country != 'United States'; UNKNOWN if never inspected  
**Certified query:** q3_foreign_sites_not_inspected_since_fy2021 (verified by N. Sahai (seed; validated against DECISIONS.md D7/D10/D11 and tests))  

**Headline.** As of 2025-10-23, 4 foreign sites tied to Current shortages had their last inspection in FY2021 or earlier, within the linked subset only.

## Answer
As of 2025-10-23, 4 foreign manufacturing sites linked to Current shortages have a last inspection in FY2021 or earlier. This covers only the sites that could be linked to a shortage record, so it is not a complete list [E1, SYS].

## Detail
- **Aurobindo Pharma Unit IV**, Visakhapatnam, India (FEI 3025111222). Drug: Vancomycin HCl. Last inspection ended 2018-04-03 (FY2018), classification VAI. Inspections on record: 1. Row inspections#L17 [E1].
- **Zhejiang Tianyu Pharmaceutical**, Taizhou, China (FEI 3026333444). Drug: Piperacillin-Tazobactam. Last inspection ended 2020-03-20 (FY2020), classification NAI. Inspections on record: 1. Row inspections#L18 [E1].
- **Macleods Pharmaceuticals Ltd**, Mumbai, India (FEI 3027555666). Drug: Ceftriaxone Sodium. Last inspection ended 2017-04-11 (FY2017), classification NAI. Inspections on record: 1. Row inspections#L19 [E1].
- **Shanxi Zhendong Taisheng Pharma**, Changzhi, China (FEI 4005777888). Drug: Ampicillin-Sulbactam. Last inspection ended 2019-07-22 (FY2019), classification NAI. Inspections on record: 1. Row inspections#L20 [E1].
- **Never inspected, country UNKNOWN** (2 sites): FEI 3007891234 (sponsor Zhejiang Huahai Pharmaceutical; drug Meropenem) and FEI 4001567890 (sponsor Hainan Poly Pharm Co Ltd; drug Cefepime HCl). They are not classed as foreign or domestic [E1].
- **Excluded, inspected more recently:** Aurobindo Pharma Limited, Hyderabad, India, last inspection ended 2023-11-07 (FY2024); drug Amoxicillin-Clavulanate [E1].

## Interpretation applied
- **Not inspected since:** pinned: last inspection FY <= FY2021. The alternate, last inspection FY < FY2021, returns the same four FEIs, so the list does not depend on this choice [SYS, E1].
- **Foreign:** pinned: inspections country other than United States; UNKNOWN if never inspected [SYS]. An inference from sponsor name was not used [SYS].
- **Fiscal year:** inspection_end_date basis. The alternate, classification_date, was not computed [SYS].
- **Currently in shortage:** latest revision per shortage is Current as of 2025-10-23. The alternates, a user-specified date and current-or-discontinued, were not computed [SYS].
- **Manufacturer:** facility operator, with the sponsor shown alongside. The sponsor-only alternate was not computed [SYS, E1].

## Caveats
- Manufacturing site is knowable for 13 of 57 Current shortage records. The other 44 reference an application not in the data (warning severity high) [E1].
- FEIs 3007891234 and 4001567890 have no inspection record. For them, "not inspected since FY2021" is trivially true but means never inspected [E1].
- FEI 4005777888 and FEI 4001567890 have an FEI prefix anomaly. Verify them against FDA's FEI portal before citing (severity medium) [E1].
- Amoxicillin-Clavulanate records link to ANDA078201, whose active ingredient is Amoxicillin. Application-level facts for those shortages are unreliable (severity high) [E1].
- Many Current records were last revised more than 18 months before the as-of date. Status is reported as recorded and should be confirmed before quoting (severity medium) [E1].
- Shortage DS-2023-0142 has a Resolved record (revised 2023-11-15) and a later Current record (revised 2024-01-10). The latest, Current, is used (severity high) [E1].

## Cannot be answered from this data
- Foreign sites for the shortage records that do not link to an application in the data. Their manufacturing sites cannot be determined [E1, SYS].
- The country of the never-inspected sites. Country is known only through inspection records [SYS, E1].

_Reviewed by Staff pharmacist (demo sign-off) — approved (2026-11-08): Row citations checked against source files._

Source rows: see footnote [^3].

## 4. Is the amoxicillin shortage resolved?

**Trust:** Tier 1 — Certified · ✅ Senate-ready


**Headline.** No: as of 2025-10-23, the latest record for the amoxicillin oral suspension shortage DS-2023-0142 is Current, not Resolved.

## Answer
No. As of 2025-10-23, the latest revision of amoxicillin shortage DS-2023-0142 (Oral Suspension 250mg/5mL) has status Current, not Resolved [E3]. An earlier Resolved record for this shortage was superseded by the later Current revision [E2].

## Detail
- **Amoxicillin Oral Suspension 250mg/5mL, DS-2023-0142:** The timeline has two revisions. It was marked Resolved on 2023-11-15 (drug_shortages#L3). It was then revised to Current on 2024-01-10 (drug_shortages#L2) [E2]. The latest status is Current [E2]. The reason category is Manufacturing Delay [E3].
- **Amoxicillin Oral Suspension 400mg/5mL, DS-2022-0089:** The only record is Discontinued, revised 2023-01-20 (drug_shortages#L4) [E2]. The reason category is Discontinuation of Manufacture [E3]. Discontinued means the manufacturer has stopped or will stop producing the product, and supply will not recover from this source [SYS]. It is not Resolved [SYS].
- **Counts:** The query returned 1 distinct drug, 2 shortage records and 2 presentations [E3]. By latest status, 1 is Current and 1 is Discontinued [E3].

## Interpretation applied
- **"Resolved":** I used the status Resolved only. It means the Drug Shortage Staff determined the market is covered and supply recovered [SYS]. It is never equated with Discontinued, and no alternate reading is listed for it [SYS].
- **"Amoxicillin":** I used the generic name Amoxicillin, all presentations [E1]. The name Amoxicillin-Clavulanate is a separate generic name that matched by substring [E1]. It was not queried or computed, so no result is shown for it [SYS].
- **"Currently":** I used the default as-of date, which is the latest record date in the dataset, 2025-10-23 [SYS]. No user-specified date was computed [SYS].
- **Latest revision per shortage:** The dedupe rule is latest_revision_per_shortage_id [SYS]. The earlier Resolved record is disclosed in the timeline above and not ignored [E2].

## Caveats
- **Status conflict (severity high):** DS-2023-0142 has conflicting records, Resolved (revision 2023-11-15) and Current (revision 2024-01-10). The latest revision, Current, is used [E2, E3].
- **Stale Current record (severity medium):** The Current status was last revised 2024-01-10. That is more than 18 months before the as-of date 2025-10-23. The warning says to confirm status before quoting [E2, E3].
- **Scope:** This answer covers shortage records only. No application or manufacturing-site analysis was done [SYS].

## Cannot be answered from this data
- Whether the shortage is resolved in reality after the last revision. The snapshot's latest Current revision is stale, so the data cannot confirm present status [E2, SYS].
- The status of Amoxicillin-Clavulanate shortages, which were not assessed [SYS].

_Reviewed by Staff pharmacist (demo sign-off) — approved (2026-11-08): Row citations checked against source files._

Source rows: see footnote [^4].

---

## Footnotes — row-level citations

[^1]: Item 1 evidence rows (17): drug_shortages#L9, drug_shortages#L7, drug_shortages#L8, drug_shortages#L10, drug_shortages#L5, drug_shortages#L6, applications#L10, applications#L15, inspections#L5, applications#L16, inspections#L6, applications#L12, inspections#L2, applications#L13, inspections#L3, applications#L14, inspections#L4
[^2]: Item 2 evidence rows (9): applications#L2, applications#L3, applications#L4, applications#L5, applications#L6, applications#L7, drug_shortages#L2, drug_shortages#L4, drug_shortages#L3
[^3]: Item 3 evidence rows (80): drug_shortages#L90, drug_shortages#L2, drug_shortages#L127, drug_shortages#L9, drug_shortages#L13, drug_shortages#L16, drug_shortages#L60, drug_shortages#L45, drug_shortages#L111, drug_shortages#L23, drug_shortages#L27, drug_shortages#L93, drug_shortages#L7, drug_shortages#L14, drug_shortages#L88, drug_shortages#L132, drug_shortages#L15, drug_shortages#L106, drug_shortages#L18, drug_shortages#L48, drug_shortages#L70, drug_shortages#L130, drug_shortages#L64, drug_shortages#L138, drug_shortages#L28, drug_shortages#L143, drug_shortages#L30, drug_shortages#L56, drug_shortages#L78, drug_shortages#L122, drug_shortages#L144, drug_shortages#L79, drug_shortages#L101, drug_shortages#L145, drug_shortages#L75, drug_shortages#L97, drug_shortages#L119, drug_shortages#L8, drug_shortages#L10, drug_shortages#L25, drug_shortages#L69, drug_shortages#L47, drug_shortages#L91, drug_shortages#L87, drug_shortages#L65, drug_shortages#L109, drug_shortages#L5, drug_shortages#L12, drug_shortages#L80, drug_shortages#L125, drug_shortages#L147, drug_shortages#L37, drug_shortages#L63, drug_shortages#L107, drug_shortages#L6, drug_shortages#L11, drug_shortages#L117, applications#L10, applications#L15, inspections#L5 …
[^4]: Item 4 evidence rows (3): drug_shortages#L4, drug_shortages#L3, drug_shortages#L2