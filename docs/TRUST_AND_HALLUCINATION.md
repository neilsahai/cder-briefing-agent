# Trust and hallucination — how the risk is reduced, and where it can still fail

The bar in the brief is "can Dr. Whitmore read this aloud in a Senate hearing and stand behind it?" That is a
different bar from "is the chatbot usually right," and it changes the architecture: the question is not how to
make the model more accurate, it is how to make a wrong answer **impossible in some places, detectable in
others, and labeled everywhere**.

## Six layers, from structural guarantee to human judgment

| Layer | What it guarantees | What it cannot |
|---|---|---|
| **1. Numbers cannot come from the model.** The narrator writes placeholders (`{{E2.counts.distinct_drugs}}`); code substitutes them from tool outputs. A literal digit-bearing token is allowed only if it appears verbatim in the evidence. Any failure withholds the whole answer. | No count, date, identifier, FEI, or fiscal year that is not in a tool result can reach the reader. Measured hallucinated-number rate across 33 eval runs: **0.0%**. | A *correct* number placed in a *wrong sentence* ("4 sites received an OAI" when 4 was a different count). That is layer 3's job. |
| **2. Semantics live in the ontology, not the prompt.** "Currently in shortage," "quality problems," "foreign," "approved," "last two fiscal years" are defined once in `ontology.yaml` with their default and alternates, cross-referenced to `DECISIONS.md`. Tools implement those definitions; the planner reads them. | The same question gets the same reading every time; changing a definition changes every answer, eval, and certified query together; the reading is disclosed on every answer. | A definition that is itself wrong for the client. That is what week one is for (`WEEK_ONE_QUESTIONS.md`). |
| **3. An independent verifier.** A second model (Opus, different from the narrator) decomposes the rendered text into atomic claims and checks each against the evidence **and the correct source table** — a status word sourced from `applications` is a failure even if it happens to be right. Flagged claims trigger one revision pass; anything still flagged demotes the answer. | Overstatements ("never inspected" vs "no inspection record"), scope creep ("the mislink doesn't affect these counts" when it does), cross-row generalizations, missing caveats. In the build log, the verifier caught three such claims on the first live runs. | A claim that is subtly wrong in a way the evidence cannot adjudicate — for example, a true number described with a misleading frame. The verifier is strict about framing too, which is why some correct answers land Tier 3. |
| **4. Data-quality lineage.** Thirteen detectors run at load. Their findings attach to any answer whose evidence touches a flagged row. | The amoxicillin status conflict reaches the amoxicillin answer without anyone asking; coverage gaps are stated in the same sentence as the count. | Defects the detectors do not know about. The list grew from 9 to 13 during the build; a real deployment would keep growing it from pharmacist feedback. |
| **5. Trust tiers on every answer.** Tier 1 Certified (certified tools or certified query, verifier passed, ambiguity resolved) · 2 Derived (LLM-authored SQL, validated and executed) · 3 Qualified (material ambiguity or verifier concern, shown side by side) · 4 Not answerable. | The reader always knows how much weight an answer bears. A Tier 3 answer with the right numbers is still not testimony until a person pins the reading. | A Tier 1 answer is only as good as the certified definition behind it. Certification is a claim about process, not truth. |
| **6. Human sign-off.** Briefing items are read-aloud-ready only when Tier 1 **and** approved by a named reviewer. The certified-query registry grows only through review. | The system drafts; a person signs. The audit log records who certified what and when. | People. A reviewer who approves without reading defeats every layer above. The 30/60/90 plan starts in shadow mode for this reason. |

## Why not just prompt harder

The previous tool's failure was not a prompting failure — it was a system that let semantic decisions happen at
runtime, invisibly, with no way to tell after the fact which reading had been applied. "Use only the numbers
provided" in a prompt is a request; a renderer that rejects any other number is a constraint. The difference
matters most on the day the model misbehaves.

## Where it can still fail — stated plainly

1. **Correct number, wrong frame.** Layer 1 cannot catch a true count attached to the wrong noun. Layer 3 usually
   does; when it does not, the answer is labeled Certified and is wrong. Mitigation: pass^k evals surface this
   as variance; certification requires a reviewer to read the answer, not just the tier.
2. **Ontology drift.** If ODSS's own definition of "resolved" or "foreign" differs from FDA's public one, every
   answer is consistently wrong in the same way. Mitigation: definitions are one file, reviewed in week one,
   versioned.
3. **Join coverage is disclosed, not fixed.** 77% of current shortages cannot be linked to a site. The system
   says so every time; it cannot invent the link. A real deployment needs the application registry.
4. **The verifier is a model.** It is strict, independent, and on the strongest model tier, but it is not a
   proof. Its judgments are logged claim by claim so a reviewer can audit it.
5. **Latency.** 60–120 seconds per question. Acceptable for briefing prep, not for live Q&A in a hearing. Most
   of the time is Opus verification and two narration passes; both are deliberate.
6. **Certified queries can go stale.** A plan verified against this snapshot may be wrong against next month's
   data. Mitigation: certified entries are versioned, revocable, and re-run by the regression suite.
7. **Prompt injection via data.** Cell values are treated as data, never instructions, and the SQL guard
   rejects anything but a single SELECT over known tables — but the narrator still reads tool output that
   originated in CSV cells. A hostile data file could try to steer phrasing. Mitigation today: the renderer
   and verifier; in production: provenance-controlled data ingestion.

## What the evals measure (`evals/results/SCORECARD.md`)

- *Hallucinated-number rate*: digit-bearing tokens in the answer not present in evidence — an independent
  re-derivation, not the renderer's own check.
- *Citation precision*: claims supported ÷ claims total after revision (395 / 1 on the capability suite).
- *Verifier catch rate*: runs where the first narration had a flagged claim (17–33%). This is a feature:
  it is how often layer 3 earned its cost.
- *pass^k*: every trial of a case passing — the reliability number that matters when the reader is a Senator.
