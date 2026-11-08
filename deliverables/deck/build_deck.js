const pptxgen = require('pptxgenjs');
const { applyTheme } = require('/root/.claude/skills/synced/e25d3650-69d3-46cc-b7eb-51a04d4c1cf2_db56b546-6761-4c68-aa7a-89f173c5b046/pptx/scripts/apply_theme.js');

const THEME = { name: 'CDER Briefing', headFontFace: 'Cambria', bodyFontFace: 'Calibri',
  colors: { dk1: '16211D', lt1: 'FFFFFF', dk2: '4A5550', lt2: 'F6F7F5', accent1: '1F6F43', accent2: 'B4700E', accent3: '3B4FA8', accent4: 'A32D2D', accent5: '97BC62', accent6: 'DDE1DC', hlink: '1F6F43', folHlink: '4A5550' } };
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = 'Neil Sahai'; pres.title = 'CDER Drug Shortage Briefing Agent';
const C = pres.SchemeColor;
const W = 13.33, H = 7.5, M = 0.6;

pres.defineSlideMaster({ title: 'DARK', background: { color: THEME.colors.dk1 }, objects: [
  { placeholder: { options: { name: 'title', type: 'title', x: M, y: 2.2, w: W - 2 * M, h: 1.6, fontSize: 40, bold: true, color: C.background1, margin: 0, valign: 'bottom' } } },
  { placeholder: { options: { name: 'body', type: 'body', x: M, y: 4.0, w: W - 2 * M, h: 1.6, fontSize: 20, color: THEME.colors.accent6, margin: 0, valign: 'top' } } },
]});
pres.defineSlideMaster({ title: 'LIGHT', background: { color: THEME.colors.lt1 }, objects: [
  { placeholder: { options: { name: 'title', type: 'title', x: M, y: 0.45, w: W - 2 * M, h: 0.9, fontSize: 32, bold: true, color: C.text1, margin: 0, valign: 'middle' } } },
  { text: { text: 'CDER Drug Shortage Briefing Agent · N. Sahai', options: { x: M, y: H - 0.5, w: 8, h: 0.3, fontSize: 10, color: THEME.colors.dk2, margin: 0 } } },
  { slideNumber: { x: W - M - 0.6, y: H - 0.5, w: 0.6, h: 0.3, fontSize: 10, color: THEME.colors.dk2, align: 'right' } },
]});
const tb = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: 'top' }, o));
const card = (s, x, y, w, h, fill) => s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: THEME.colors.accent6, width: 0.75 }, rectRadius: 0.08 });

// 1 — title
pres.addSection({ title: 'Opening' });
let s = pres.addSlide({ masterName: 'DARK', sectionTitle: 'Opening' });
s.addText('Can Dr. Whitmore read it aloud?', { placeholder: 'title' });
s.addText([{ text: 'An agentic briefing tool for FDA CDER drug-shortage testimony\n', options: { breakLine: true } },
  { text: 'Deloitte Federal FDE take-home #3 · Neil Sahai · November 2026', options: { fontSize: 15, color: THEME.colors.accent6 } }], { placeholder: 'body' });
s.addNotes('Open on the Ask page with the amoxicillin question already running. Title slide stays up for ten seconds at most.');

// 2 — the incident
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Opening' });
s.addText('The incident, replayed on the data you sent', { placeholder: 'title' });
tb(s, '"Is the amoxicillin shortage resolved?"', { x: M, y: 1.5, w: 6, h: 0.5, fontSize: 20, italic: true, color: THEME.colors.dk2 });
// two rows
const rowCard = (y, label, status, rev, fill, col) => { card(s, M, y, 6.0, 1.05, fill); tb(s, label, { x: M + 0.25, y: y + 0.12, w: 5.5, h: 0.3, fontSize: 12, color: THEME.colors.dk2 }); tb(s, status, { x: M + 0.25, y: y + 0.42, w: 2.5, h: 0.5, fontSize: 26, bold: true, color: col }); tb(s, rev, { x: M + 3.0, y: y + 0.5, w: 2.8, h: 0.4, fontSize: 13, color: THEME.colors.dk2 }); };
rowCard(2.2, 'drug_shortages.csv · line 3 · DS-2023-0142', 'Resolved', 'revised 2023-11-15', THEME.colors.lt2, THEME.colors.accent3);
rowCard(3.45, 'drug_shortages.csv · line 2 · DS-2023-0142', 'Current', 'revised 2024-01-10', 'E7F2EB', THEME.colors.accent1);
tb(s, 'Same record. Two statuses. 56 days apart.', { x: M, y: 4.75, w: 6, h: 0.4, fontSize: 14, color: THEME.colors.dk2, italic: true });
// right: naive vs system
card(s, 7.2, 1.5, 5.5, 2.1, 'FBE9E9'); tb(s, 'A row scan that finds a Resolved row', { x: 7.45, y: 1.65, w: 5.1, h: 0.35, fontSize: 13, color: THEME.colors.dk2 }); tb(s, '"Yes."', { x: 7.45, y: 2.05, w: 5, h: 0.7, fontSize: 32, bold: true, color: THEME.colors.accent4 }); tb(s, 'Reached a draft of Senate testimony. Correction letter followed.', { x: 7.45, y: 2.8, w: 5.1, h: 0.6, fontSize: 13 });
card(s, 7.2, 3.85, 5.5, 2.6, 'E7F2EB'); tb(s, 'This system', { x: 7.45, y: 4.0, w: 5.1, h: 0.35, fontSize: 13, color: THEME.colors.dk2 }); tb(s, '"No."', { x: 7.45, y: 4.4, w: 5, h: 0.7, fontSize: 32, bold: true, color: THEME.colors.accent1 });
tb(s, 'Latest revision is Current. The earlier Resolved record is disclosed, not ignored. The trust tier is on the card (1 Certified, or 3 Qualified when a reading like Resolved-vs-Discontinued is shown side by side). Every value cites its row. The conflict warning attached itself — nobody asked for it.', { x: 7.45, y: 5.12, w: 5.1, h: 1.28, fontSize: 12 });
tb(s, 'That conflict is in the file you sent. So are fourteen other traps — docs/RED_TEAM_REPORT.md.', { x: M, y: 6.2, w: 12, h: 0.4, fontSize: 13, color: THEME.colors.dk2 });
s.addNotes('Run it live. Click [E2], then the row chips: line 3 then line 2. Two rows, same record, different status. Then: that conflict is in the file you sent, so are fourteen others.');

// 3 — thesis
pres.addSection({ title: 'Design' });
s = pres.addSlide({ masterName: 'DARK', sectionTitle: 'Design' });
s.addText('Semantic decisions moved from runtime to modeling time', { placeholder: 'title' });
s.addText('Last year\'s tool failed because meaning was decided inside a model, invisibly, at runtime. This one defines it once in an ontology you can read, makes numbers unable to pass through the model, labels every claim with a trust tier, and ships with the evals that prove it.', { placeholder: 'body' });
s.addNotes('The one sentence. Say it, pause, move on.');

// 4 — architecture pipeline
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Design' });
s.addText('A workflow where it can be, an agent only where it must', { placeholder: 'title' });
const steps = [['Gate', 'Haiku', 'Answerable? Ambiguous terms? Before any data.', THEME.colors.lt2],
  ['Planner', 'Sonnet → Opus on a rule', 'Declares interpretations first. Resolves literals. Certified tools; SQL last.', 'E9ECF7'],
  ['Narrator', 'Sonnet', 'Placeholders and citations only. Cannot write a number.', THEME.colors.lt2],
  ['Verifier', 'Opus, always', 'Atomic claims × evidence × source table. One revision.', 'E7F2EB'],
  ['Tier', 'Code', '1 Certified · 2 Derived · 3 Qualified · 4 Not answerable', THEME.colors.lt2]];
const sw = 2.3, gap = 0.16, sx = M, sy = 1.7;
steps.forEach(([t, m, d, f], i) => { const x = sx + i * (sw + gap); card(s, x, sy, sw, 2.5, f); tb(s, t, { x: x + 0.18, y: sy + 0.15, w: sw - 0.3, h: 0.4, fontSize: 18, bold: true }); tb(s, m, { x: x + 0.18, y: sy + 0.55, w: sw - 0.3, h: 0.35, fontSize: 11, color: THEME.colors.accent3, bold: true }); tb(s, d, { x: x + 0.18, y: sy + 0.95, w: sw - 0.36, h: 1.5, fontSize: 12.5 });
  if (i < steps.length - 1) s.addShape(pres.ShapeType.rightArrow, { x: x + sw - 0.02, y: sy + 1.05, w: gap + 0.04, h: 0.35, fill: { color: THEME.colors.accent6 }, line: { color: THEME.colors.accent6, width: 0 } }); });
card(s, M, 4.55, W - 2 * M, 1.0, 'F6F7F5'); tb(s, 'Underneath: DuckDB with a line number on every row · 13-rule data audit whose findings attach to any answer touching a flagged row · ontology.yaml + DECISIONS.md read by the gate, the planner, the narrator and the verifier as citable [SYS] evidence.', { x: M + 0.25, y: 4.68, w: W - 2 * M - 0.5, h: 0.8, fontSize: 13 });
tb(s, 'Where the model is not used: arithmetic, joins, dedup, fiscal years, FEI checks, coverage, the tier decision. Python, 50 tests, the same code the evals run.', { x: M, y: 5.8, w: W - 2 * M, h: 0.6, fontSize: 13, color: THEME.colors.dk2, italic: true });
s.addNotes('Point at the live trace while walking left to right. Escalation is a rule in the trace, not a model opinion.');

// 5 — trust tiers
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Design' });
s.addText('Every answer says how much weight it can bear', { placeholder: 'title' });
const tiers = [['1', 'Certified', THEME.colors.accent1, 'E7F2EB', 'Certified tools or a certified query. Verifier passed. Ambiguity resolved or pinned.', 'Eligible for testimony with sign-off'],
  ['2', 'Derived', THEME.colors.accent3, 'E9ECF7', 'LLM-authored SQL: guarded, executed, three candidates compared.', 'Internal use; certify after review'],
  ['3', 'Qualified', THEME.colors.accent2, 'FBF0DD', 'A reading changes the answer, shown side by side — or a verifier concern.', 'Pin a reading → re-run → Tier 1'],
  ['4', 'Not answerable', '5A6168', 'ECEEEF', 'Out of scope, or the data lacks the field.', 'Says what can be answered instead']];
tiers.forEach(([n, name, col, fill, d, use], i) => { const x = M + i * 3.05, y = 1.6; card(s, x, y, 2.9, 4.3, fill); tb(s, n, { x: x + 0.2, y: y + 0.15, w: 1, h: 0.9, fontSize: 56, bold: true, color: col }); tb(s, name, { x: x + 0.2, y: y + 1.1, w: 2.5, h: 0.45, fontSize: 20, bold: true, color: col }); tb(s, d, { x: x + 0.2, y: y + 1.65, w: 2.5, h: 1.6, fontSize: 13.5 }); tb(s, use, { x: x + 0.2, y: y + 3.4, w: 2.5, h: 0.7, fontSize: 12.5, italic: true, color: THEME.colors.dk2 }); });
tb(s, 'A Tier 3 answer with the right numbers is still not testimony until a person decides the reading. The ambiguity is not hidden; it is a one-click decision with a paper trail.', { x: M, y: 6.1, w: W - 2 * M, h: 0.6, fontSize: 13, color: THEME.colors.dk2 });
s.addNotes('Q1 asked in different words lands Tier 3 with pin chips. Pin, rerun, Tier 1.');

// 6 — ambiguity, native charts
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Design' });
s.addText('Readings that change the answer are computed, not chosen', { placeholder: 'title' });
const chartOpts = (title) => ({ showTitle: true, title, titleFontSize: 13, titleColor: THEME.colors.dk1, titleFontFace: '+mn-lt', showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 12, dataLabelColor: THEME.colors.dk1, dataLabelFontFace: '+mn-lt', chartColors: [THEME.colors.accent1, THEME.colors.accent2], catAxisLabelColor: THEME.colors.dk2, valAxisLabelColor: THEME.colors.dk2, catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt', catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, valGridLine: { color: THEME.colors.accent6, size: 0.5 }, catGridLine: { style: 'none' }, showLegend: false, valAxisMaxVal: 16, barGapWidthPct: 60 });
s.addChart(pres.ChartType.bar, [{ name: 'Drugs in shortage for quality reasons', labels: ['strict (cGMP only)', 'broad (+ manufacturing delay)'], values: [6, 15] }], Object.assign({ x: M, y: 1.5, w: 6.0, h: 3.6, barDir: 'col' }, chartOpts('"Quality problems" — distinct drugs')));
s.addChart(pres.ChartType.bar, [{ name: 'Sites with an OAI', labels: ['FY24–25 (completed)', 'FY25–26 (incl. current)'], values: [4, 2] }], Object.assign({ x: 6.9, y: 1.5, w: 5.8, h: 3.6, barDir: 'col' }, chartOpts('"Last two fiscal years" — OAI sites'), { valAxisMaxVal: 6 }));
tb(s, 'Each certified query computes its alternate readings deterministically and reports whether they differ. The trust tier never depends on whether the planner felt like checking. Default readings and their rationale: DECISIONS.md D1–D14; the client confirms or overrides them in week one.', { x: M, y: 5.35, w: W - 2 * M, h: 0.9, fontSize: 13 });
s.addNotes('Open Interpretations on the Q1 answer. Both alternates are computed; FY basis gives the same four sites and says so.');

// 7 — certified loop
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Design' });
s.addText('The loop that turns a prototype into a product', { placeholder: 'title' });
const loop = [['Off-script question', 'Tier 2 Derived — guarded SQL, three candidates agree'], ['Analyst reviews', 'Evidence rows, verifier claims, interpretations'], ['Certify', 'Plan + args + pinned readings + who + when + version'], ['Next time', 'Runner executes the verified plan first → Tier 1'], ['Backlog', 'Questions asked but not yet certified = the pharmacist\'s queue']];
loop.forEach(([t, d], i) => { const x = M + i * 2.46; card(s, x, 1.7, 2.3, 2.3, i === 2 ? 'E7F2EB' : THEME.colors.lt2); s.addShape(pres.ShapeType.ellipse, { x: x + 0.2, y: 1.9, w: 0.55, h: 0.55, fill: { color: i === 2 ? THEME.colors.accent1 : THEME.colors.dk1 }, line: { width: 0 } }); tb(s, String(i + 1), { x: x + 0.2, y: 1.9, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: C.background1, align: 'center', valign: 'middle' }); tb(s, t, { x: x + 0.2, y: 2.6, w: 2.0, h: 0.45, fontSize: 16, bold: true }); tb(s, d, { x: x + 0.2, y: 3.05, w: 2.0, h: 0.9, fontSize: 12 }); });
card(s, M, 4.4, W - 2 * M, 1.75, 'F6F7F5');
tb(s, 'Same pattern as Snowflake\'s verified-query repository and Databricks\' trusted assets. The three required queries ship this way — verified plans, not hardcoded answers — so they are rigorous without being special-cased, and the panel can see them in the registry next to anything certified during the demo. Every promote and revoke lands in an audit log.', { x: M + 0.25, y: 4.55, w: W - 2 * M - 0.5, h: 1.5, fontSize: 13.5 });
s.addNotes('Demo: ask the tentative-approvals question, certify it, open Certified queries, re-ask.');

// 8 — evidence it works
pres.addSection({ title: 'Evidence' });
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Evidence' });
s.addText('Measured, not claimed', { placeholder: 'title' });
const stats = [['0.0%', 'answers containing a number not present in evidence (33 runs)'], ['395 / 1', 'claims verified / flagged after revision, capability suite'], ['10 / 10', 'adversarial cases passing: fake FEI, fake drug, blame, testimony language, injection…'], ['$0.20–0.29', 'per question at Anthropic list prices, Opus verification included']];
stats.forEach(([n, l], i) => { const x = M + i * 3.05; s.addShape(pres.ShapeType.line, { x, y: 1.55, w: 2.85, h: 0, line: { color: THEME.colors.dk1, width: 1.5 } }); tb(s, n, { x, y: 1.65, w: 2.85, h: 0.8, fontSize: 34, bold: true, color: THEME.colors.accent1 }); tb(s, l, { x, y: 2.5, w: 2.85, h: 1.0, fontSize: 12, color: THEME.colors.dk2 }); });
s.addChart(pres.ChartType.line, [{ name: 'Capability suite pass rate', labels: ['first run', 'after SYS evidence + grader fixes', 'after path index + concurrency fixes'], values: [42, 75, 96] }], Object.assign({ x: M, y: 3.7, w: 6.3, h: 3.0, lineDataSymbol: 'circle', lineDataSymbolSize: 9, lineSize: 2.5 }, chartOpts('Capability suite (24 off-script cases), % passing'), { valAxisMaxVal: 100, valAxisMinVal: 0, dataLabelPosition: 't' }));
card(s, 7.2, 3.7, 5.5, 3.0, 'F6F7F5');
tb(s, [{ text: 'Two suites, three grader types\n', options: { bold: true, fontSize: 14, breakLine: true } },
  { text: 'Regression (9 cases): the required queries under default and alternate readings, every planted trap. 8–9/9; the miss is the Opus verifier flagging a framing nit on a correct answer → Tier 3. The safe direction.\n', options: { fontSize: 12, breakLine: true } },
  { text: 'Capability (24): off-script, definitional, temporal, adversarial. Code graders for numbers and citations; one model judge per dimension. pass^k, not pass@k.\n', options: { fontSize: 12, breakLine: true } },
  { text: 'The verifier caught something on 17–33% of first drafts. That is the cost of the Opus call earning itself.', options: { fontSize: 12 } }], { x: 7.45, y: 3.85, w: 5.1, h: 2.75, isTextBox: true, margin: 0, valign: 'top', color: C.text1 });
s.addNotes('Evals page. Four numbers. Capability started at 42% — the harness found the bugs; the build log has them.');

// 9 — where it fails
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Evidence' });
s.addText('Where it still fails — said before you ask', { placeholder: 'title' });
const fails = [['Correct number, wrong frame', 'The renderer cannot catch a true count attached to the wrong noun. The verifier usually does; when it does not, a Certified answer is wrong. That is why sign-off exists and why pass^k is reported.'],
  ['The join is disclosed, not fixed', '44 of 57 current shortages cannot be linked to a site in this snapshot. The system says so in the same sentence as the count. Only the production application registry closes it.'],
  ['Sixty to ninety seconds', 'Two narration passes and an Opus verification per question. Right for briefing prep; wrong for a live hearing. Certified queries can be pre-computed before the day.'],
  ['The ontology is a guess until week one', 'Defaults follow FDA\'s public definitions. If ODSS means something narrower by "resolved" or "foreign," every answer is consistently wrong the same way — one file, versioned, sixteen questions to fix it.']];
fails.forEach(([t, d], i) => { const x = M + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.45; card(s, x, y, 5.95, 2.25, i === 0 ? 'FBF0DD' : THEME.colors.lt2); tb(s, t, { x: x + 0.25, y: y + 0.2, w: 5.5, h: 0.45, fontSize: 17, bold: true }); tb(s, d, { x: x + 0.25, y: y + 0.7, w: 5.45, h: 1.45, fontSize: 12.5 }); });
s.addNotes('Say these before they ask. The second one is the honest answer to "is this a full list?" — no, and it says so every time.');

// 10 — what's next
pres.addSection({ title: 'Next' });
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Next' });
s.addText('From prototype to a hearing: 30 / 60 / 90', { placeholder: 'title' });
const phases = [['Days 1–30 · Shadow mode', ['Two analysts run real questions alongside the Excel process; nothing goes in a binder', 'Week one: 16 discovery questions rewrite the ontology in ODSS\'s own definitions', 'Staff pharmacist certifies the first ~20 queries from real committee questions']],
  ['Days 31–60 · Internal briefings', ['Tier 1 + signed items into internal briefings for the Deputy Center Director', 'Real sources replace the snapshot: shortage DB, Drugs@FDA, FEI registry; nightly audit with diffs', 'Claude on Bedrock in AWS GovCloud; nothing leaves the agency account']],
  ['Days 61–90 · First external memo', ['One externally facing memo built entirely from certified, signed items', 'Capability suite re-seeded from the pilot backlog; pass^k gates every change', 'Decide on scale: which other CDER offices share the sources, what their ontology deltas are']]];
phases.forEach(([t, items], i) => { const x = M + i * 4.1; card(s, x, 1.6, 3.95, 4.4, i === 0 ? 'E7F2EB' : THEME.colors.lt2); tb(s, t, { x: x + 0.25, y: 1.8, w: 3.5, h: 0.5, fontSize: 16, bold: true, color: THEME.colors.accent1 }); s.addText(items.map((it, k) => ({ text: it, options: { bullet: true, breakLine: k < items.length - 1, paraSpaceAfter: 8 } })), { x: x + 0.25, y: 2.4, w: 3.5, h: 3.4, fontSize: 12.5, color: C.text1, isTextBox: true, margin: 0, valign: 'top' }); });
tb(s, 'Reusable across offices and agencies: the pipeline, trust tiers, certified registry, eval harness, briefing builder, MCP exposure. Client-specific and isolated: ontology.yaml, DECISIONS.md, the certified tools over the client\'s tables, the audit rules.', { x: M, y: 6.2, w: W - 2 * M, h: 0.6, fontSize: 12.5, color: THEME.colors.dk2 });
s.addNotes('End here. Offer the repo, the memo, the scorecard. Take questions.');

// 11 — appendix: required answers
pres.addSection({ title: 'Appendix' });
s = pres.addSlide({ masterName: 'LIGHT', sectionTitle: 'Appendix' });
s.addText('Appendix — the three required queries, as of 2025-10-23', { placeholder: 'title' });
const rows = [[{ text: 'Query', options: { bold: true, fill: { color: THEME.colors.lt2 } } }, { text: 'Default reading', options: { bold: true, fill: { color: THEME.colors.lt2 } } }, { text: 'Alternate readings computed', options: { bold: true, fill: { color: THEME.colors.lt2 } } }],
  ['1 · Quality shortages / OAI sites', '6 drugs (Quality: cGMP Issue). 4 linked sites with an OAI in FY2024–25: Baxter Deerfield, Pfizer McPherson, ICU Medical Lake Forest, Fresenius Kabi Wilson. Hospira: VAI only. Meropenem site: no inspection record, country unknown.', 'Broad quality scope: 15 drugs / 21 records. FY25–26: 2 sites. Classification-date basis: same 4. "Early 2025" per the PDF: FY23–24, only Pfizer and ICU Medical.'],
  ['2 · Amoxicillin oral suspension', '6 applications for the ingredient (no dosage-form column): 4 fully approved, 2 tentative, 3 actively marketed, 1 discontinued. One oral-suspension record Current (DS-2023-0142, earlier Resolved revision disclosed); one Discontinued.', 'Include tentative: 6 approved. As of 2023-12-01: DS-2023-0142 was Resolved; conflict still disclosed. Amox-clav records mislinked to an amoxicillin ANDA — flagged.'],
  ['3 · Foreign sites not inspected since FY2021', '4: Aurobindo Unit IV (FY2018), Zhejiang Tianyu (FY2020), Macleods (FY2017), Shanxi Zhendong (FY2019). 2 never-inspected sites reported separately with UNKNOWN country. Coverage: 13 of 57 current records link to a site.', 'Exclusive reading (< FY2021): same 4. Since FY2024: adds Aurobindo Hyderabad. Two FEIs with a prefix anomaly flagged for verification.']];
s.addTable(rows, { x: M, y: 1.5, w: W - 2 * M, colW: [2.6, 4.8, 4.73], fontSize: 11, color: C.text1, border: { type: 'solid', color: THEME.colors.accent6, pt: 0.5 }, valign: 'top', margin: 0.08 });
s.addNotes('Reference only. Golden values pinned in backend/tests/test_certified_queries.py.');

(async () => { await pres.writeFile({ fileName: 'walkthrough_deck.pptx' }); await applyTheme('walkthrough_deck.pptx', THEME); console.log('written'); })();
