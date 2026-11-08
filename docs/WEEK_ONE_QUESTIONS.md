# Week one with the client — what I would ask ODSS before building for real

Every default in `DECISIONS.md` is a guess that FDA's public definitions are the office's definitions. Week one
is for replacing guesses with the client's answers. Each question maps to a decision the system already makes
explicitly, so the answer changes one line in the ontology, not the architecture.

| # | Question for Dr. Whitmore's staff | Decision it settles |
|---|---|---|
| 1 | When you say a shortage is "resolved," is that the Drug Shortage Staff determination (market covered by all manufacturers) or something narrower your office uses internally? Do you ever quote a status that is not the latest revision? | D4 — latest-revision rule, status semantics |
| 2 | For a hearing on pediatric antibiotics, which products count as "pediatric"? Is oral suspension/solution the right proxy, or is there an internal list? | pediatric proxy in the ontology |
| 3 | When a shortage reason is "Manufacturing Delay," does your office treat it as a quality issue in briefings, or only `Quality: cGMP Issue`? | D5 |
| 4 | When Congress asks "how many drugs," do you answer at the molecule level, the product/NDC level, or the record level? Has that ever been challenged? | D6 |
| 5 | Which system is the authority for the application ↔ facility link — Drugs@FDA, the establishment registration, or an internal mapping? (The snapshot links only 21 of 150 records.) | D7, join coverage |
| 6 | For "manufacturer," do you mean the application holder or the facility operator? Do briefings name contract manufacturers? | D7 |
| 7 | Where does country of establishment come from when a site has never been inspected? Is there a registry we should join to? | D10 |
| 8 | For fiscal-year attribution of an inspection, do you follow the Data Dashboard convention (inspection end date) or the classification date? Does OAI scope to Drug Quality Assurance only, or any project area? | D2, D8 |
| 9 | Do you count tentative approvals when you say "approved applications" in a supply picture? | D9 |
| 10 | What is the as-of date you want printed on a briefing: the data pull date, the hearing date, or a fixed snapshot date per hearing? | D1 |
| 11 | Who is allowed to certify an answer for testimony, and who signs the memo? Is there an existing review chain we should mirror? | sign-off roles, certified registry |
| 12 | What did the staff pharmacist actually catch in the amoxicillin incident, and in what form did the error reach the draft? (The system should be tested against the real incident, not my reconstruction of it.) | regression suite |
| 13 | Which questions did the Senate committee staff actually ask last time? (Those become the first certified queries.) | certified registry seed |
| 14 | What are the FEI format rules your chemists apply by eye — length, prefixes, check digits? | D7 FEI validation |
| 15 | How often is each source refreshed, and is there a changelog? (Determines the staleness threshold and whether "Current" can be trusted without a re-pull.) | D4 staleness flag |
| 16 | What may leave the agency boundary? Is Claude on Bedrock in GovCloud the acceptable path, or is there an existing enclave? | deployment |

Discovery deliverable at the end of week one: a revised `ontology.yaml` and `DECISIONS.md` signed by the
office, and a certified-query seed list drawn from real committee questions.
