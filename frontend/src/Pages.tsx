import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { j, fmtMs, fmtTok } from './api'
import { Prose, TierPill, WarningList } from './components'

type Briefing = { id: string; title: string; audience: string; author: string; status: string; items: BItem[] }
type BItem = { item_id: string; run_id: string; question: string; headline: string; markdown: string; tier: number; tier_label: string; rows: unknown[]; signoff: { reviewer: string; decision: string; comment: string; at: string } | null; readiness: { senate_ready: boolean; missing: string[] }; pins: Record<string, string> }

export function BriefingPage() {
  const [list, setList] = useState<{ id: string; title: string; status: string; n_items: number }[]>([])
  const [b, setB] = useState<Briefing | null>(null)
  const [reviewer, setReviewer] = useState('Staff pharmacist')
  const load = async (id?: string) => {
    const l = await j<typeof list>('/api/briefings'); setList(l)
    const target = id ?? b?.id ?? l[0]?.id
    if (target) setB(await j<Briefing>(`/api/briefings/${target}`))
  }
  useEffect(() => { load() }, [])
  const create = async () => { const t = prompt('Briefing title', 'Pediatric Antibiotic Shortages — Senate HELP briefing'); if (!t) return; const nb = await j<Briefing>('/api/briefings', { method: 'POST', body: JSON.stringify({ title: t, author: reviewer }) }); await load(nb.id) }
  const sign = async (item: BItem, decision: string) => { const comment = decision === 'approved' ? '' : (prompt('Comment') ?? ''); await j(`/api/briefings/${b!.id}/items/${item.item_id}/signoff`, { method: 'POST', body: JSON.stringify({ reviewer, decision, comment }) }); await load() }
  const remove = async (item: BItem) => { await j(`/api/briefings/${b!.id}/items/${item.item_id}`, { method: 'DELETE' }); await load() }
  const ready = b?.items.filter((i) => i.readiness.senate_ready).length ?? 0
  return (
    <div className="page">
      <h1 className="page-title">Briefing builder</h1>
      <p className="page-sub">Answers you add here become numbered items in a footnoted memo. An item is read-aloud ready only when it is Tier 1 Certified and a reviewer has approved it — the system drafts, a person signs.</p>
      <div className="inline-form" style={{ marginBottom: 18 }}>
        <select value={b?.id ?? ''} onChange={(e) => load(e.target.value)} aria-label="Briefing">{list.map((x) => <option key={x.id} value={x.id}>{x.title} ({x.n_items})</option>)}</select>
        <button className="btn" onClick={create}>New briefing</button>
        <label className="small muted">Reviewer <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
        {b && <><a className="btn" href={`/api/briefings/${b.id}/export.docx`}>Download .docx</a><a className="btn" href={`/api/briefings/${b.id}/export.md`}>Download .md</a></>}
      </div>
      {b && (
        <>
          <div className="stat-row">
            <div className="stat"><b>{b.items.length}</b><span>items</span></div>
            <div className="stat"><b>{ready}</b><span>Senate-ready (Tier 1 + approved)</span></div>
            <div className="stat"><b>{b.items.reduce((a, i) => a + i.rows.length, 0)}</b><span>source rows footnoted</span></div>
            <div className="stat"><b style={{ textTransform: 'capitalize' }}>{b.status}</b><span>briefing status</span></div>
          </div>
          {b.items.length === 0 && <div className="empty">No items yet. Ask a question, then use “Add to briefing” on the answer.</div>}
          {b.items.map((it, n) => (
            <article key={it.item_id} className={`answer tier-${it.tier}`} style={{ marginTop: 16 }}>
              <div className="tier-line">
                <span className="tier-name">{n + 1}. Tier {it.tier} — {it.tier_label}</span>
                <span className={it.readiness.senate_ready ? 'ready' : 'notready'}>{it.readiness.senate_ready ? 'Senate-ready' : 'Not yet: ' + it.readiness.missing.join('; ')}</span>
              </div>
              <div className="muted small">{it.question}</div>
              <p className="headline" style={{ fontSize: 18 }}>{it.headline}</p>
              <details><summary className="small">Full answer</summary><Prose md={it.markdown} onCite={() => {}} /></details>
              <div className="actions">
                {it.signoff ? <span className="small">Reviewed by {it.signoff.reviewer}: <b>{it.signoff.decision}</b> {it.signoff.comment && `— ${it.signoff.comment}`}</span> : <span className="small muted">Awaiting review</span>}
                <span style={{ marginLeft: 'auto' }} />
                <button className="btn small" onClick={() => sign(it, 'approved')} disabled={it.tier !== 1} title={it.tier !== 1 ? 'Only Tier 1 answers can be approved for testimony' : ''}>Approve</button>
                <button className="btn small" onClick={() => sign(it, 'needs_changes')}>Needs changes</button>
                <Link className="btn small" to={`/?run=${it.run_id}`}>Open run</Link>
                <button className="btn small" onClick={() => remove(it)}>Remove</button>
              </div>
            </article>))}
        </>)}
    </div>
  )
}

export function CertifiedPage() {
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [audit, setAudit] = useState<Record<string, unknown>[]>([])
  const load = async () => { setRows(await j('/api/certified?include_revoked=true')); setAudit(await j('/api/certified/audit')) }
  useEffect(() => { load() }, [])
  const revoke = async (name: string) => { const reason = prompt('Reason for revoking'); if (!reason) return; await j(`/api/certified/${name}/revoke`, { method: 'POST', body: JSON.stringify({ actor: 'analyst', reason }) }); load() }
  return (
    <div className="page">
      <h1 className="page-title">Certified queries</h1>
      <p className="page-sub">Question patterns whose exact plan a reviewer has verified. When a new question matches one, the runner executes the verified plan first and the answer is eligible for Tier 1. Certify from any clean Tier 2/3 answer; revoke here.</p>
      <table className="tbl"><thead><tr><th>Name</th><th>Question</th><th>Plan</th><th>Pinned readings</th><th>Verified</th><th>v</th><th>Status</th><th></th></tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={String(r.name)}>
            <td><code>{String(r.name)}</code></td><td>{String(r.question)}</td>
            <td><code>{String(r.tool)}</code><div className="small muted">{JSON.stringify(r.args)}</div></td>
            <td className="small">{Object.entries(r.pins as Record<string, string>).map(([k, v]) => <div key={k}>{k} = {v}</div>)}</td>
            <td className="small">{String(r.verified_by)}<div className="muted">{String(r.verified_at).slice(0, 10)}</div></td>
            <td>{String(r.version)}</td><td>{String(r.status)}</td>
            <td>{r.status === 'active' && <button className="btn small" onClick={() => revoke(String(r.name))}>Revoke</button>}</td>
          </tr>))}</tbody></table>
      <h2 style={{ fontSize: 16, margin: '26px 0 10px' }}>Audit log</h2>
      <table className="tbl"><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Target</th><th>Details</th></tr></thead>
        <tbody>{audit.map((a, i) => <tr key={i}><td className="small">{String(a.at).replace('T', ' ').slice(0, 19)}</td><td>{String(a.actor)}</td><td>{String(a.action)}</td><td><code>{String(a.target)}</code></td><td className="small muted">{String(a.details).slice(0, 140)}</td></tr>)}</tbody></table>
    </div>
  )
}

export function DataHealthPage() {
  const [d, setD] = useState<{ summary: { as_of: string; total_findings: number; rules: { rule_id: string; severity: string; count: number; rows: number }[] }; findings: { rule_id: string; severity: string; message: string; rows: string[]; n_rows: number }[] } | null>(null)
  const [schema, setSchema] = useState<{ data_max_date: string; tables: Record<string, number> } | null>(null)
  useEffect(() => { j<typeof d>('/api/data/health').then(setD); j<typeof schema>('/api/data/schema').then(setSchema) }, [])
  if (!d) return <div className="page muted">Loading…</div>
  const sev = (s: string) => ({ high: 0, medium: 1, low: 2, info: 3 }[s] ?? 9)
  return (
    <div className="page">
      <h1 className="page-title">Data health</h1>
      <p className="page-sub">Thirteen checks run every time the data loads. Findings attach themselves to any answer whose evidence touches a flagged row — that is how the amoxicillin status conflict reaches an answer without anyone asking.</p>
      <div className="stat-row">
        <div className="stat"><b>{schema ? Object.values(schema.tables).reduce((a, b) => a + b, 0) : '—'}</b><span>rows across 3 files</span></div>
        <div className="stat"><b>{d.summary.as_of}</b><span>latest record date (default as-of)</span></div>
        <div className="stat"><b>{d.summary.rules.length}</b><span>rules fired</span></div>
        <div className="stat"><b>{d.findings.filter((f) => f.severity === 'high').length}</b><span>high-severity findings</span></div>
      </div>
      {[...d.summary.rules].sort((a, b) => sev(a.severity) - sev(b.severity)).map((r) => (
        <details key={r.rule_id} style={{ marginBottom: 8 }}>
          <summary><code>{r.rule_id}</code> <span className={`tier-pill ${r.severity === 'high' ? 't3' : r.severity === 'medium' ? 't2' : 't4'}`} style={{ marginLeft: 8 }}>{r.severity}</span> <span className="muted small">{r.count} finding{r.count === 1 ? '' : 's'}, {r.rows} rows</span></summary>
          <div style={{ marginTop: 8 }}><WarningList warnings={d.findings.filter((f) => f.rule_id === r.rule_id).slice(0, 12).map((f) => ({ code: f.rule_id, severity: f.severity as 'high', message: f.message + (f.rows.length ? ` [${f.rows.slice(0, 6).join(', ')}${f.n_rows > 6 ? ', …' : ''}]` : ''), rows: [] }))} /></div>
        </details>))}
    </div>
  )
}

type EvalRecord = { id: string; trial?: number; error?: string | null; passed: boolean; tier: number | null; latency_ms: number; claims_total: number; claims_flagged_final: number; claims_flagged_first_pass: number | null; unverified_numbers: string[]; used_sql: boolean; escalated: boolean; checks?: { check: string; pass: boolean; detail: string }[]; judges?: { dimension: string; pass: boolean; rationale: string }[]; headline: string | null; run_id: string | null }
type EvalSuite = { summary: Record<string, unknown> & { tier_distribution: Record<string, number> }; records: EvalRecord[] }

export function EvalsPage() {
  const [d, setD] = useState<{ regression?: EvalSuite; capability?: EvalSuite; rehearsal?: EvalSuite } | null>(null)
  useEffect(() => { j<typeof d>('/api/evals/latest').then(setD) }, [])
  if (!d) return <div className="page muted">Loading…</div>
  const pct = (v: unknown) => (typeof v === 'number' ? `${Math.round(v * 100)}%` : '—')
  return (
    <div className="page">
      <h1 className="page-title">Evaluation results</h1>
      <p className="page-sub">Three suites. Regression holds the three required queries under default and alternate readings and must stay near 100%. Capability holds off-script and adversarial questions and is meant to start low and climb. Rehearsal holds twenty panel-style questions written after the build. Code graders check numbers and citations; one model judge per dimension scores what code cannot see.</p>
      {(['regression', 'capability', 'rehearsal'] as const).map((suite) => { const s = d[suite]; if (!s) return null; const sm = s.summary; const k = Number(sm.n_trials ?? 0) / Math.max(1, Number(sm.n_cases ?? 1)); return (
        <section key={suite} style={{ marginBottom: 34 }}>
          <h2 style={{ fontSize: 17 }}>{suite} — {String(sm.n_cases)} cases{k > 1 ? ` × ${k} trials` : ''}</h2>
          <div className="stat-row">
            <div className="stat"><b>{pct(sm.case_pass_pow_k)}</b><span>{k > 1 ? `cases passing every trial (pass^${k})` : 'cases passing'}</span></div>
            {k > 1 && <div className="stat"><b>{pct(sm.case_pass_at_k)}</b><span>cases passing any trial (pass@{k})</span></div>}
            <div className="stat"><b>{pct(sm.hallucinated_number_rate)}</b><span>answers with a number not in evidence</span></div>
            <div className="stat"><b>{String(sm.claims_total)} / {String(sm.claims_flagged_final)}</b><span>claims verified / flagged after revision</span></div>
            <div className="stat"><b>{pct(sm.verifier_caught_first_pass_rate)}</b><span>runs where the verifier caught something</span></div>
            <div className="stat"><b>{sm.tier_distribution[1]} / {sm.tier_distribution[2]} / {sm.tier_distribution[3]} / {sm.tier_distribution[4]}</b><span>tier 1 / 2 / 3 / 4</span></div>
            <div className="stat"><b>{fmtMs(Number(sm.avg_latency_ms))}</b><span>avg latency · {fmtTok(Math.round(Number(sm.avg_input_tokens)))} tok in</span></div>
          </div>
          <table className="tbl"><thead><tr><th>Case</th><th>Result</th><th>Tier</th><th>Claims</th><th>Verifier caught</th><th>Judges</th><th>Latency</th><th></th></tr></thead>
            <tbody>{[...s.records].sort((a, b) => a.id.localeCompare(b.id) || (a.trial ?? 0) - (b.trial ?? 0)).map((r) => (
              <tr key={`${r.id}-${r.trial ?? 0}`}><td><code>{r.id}</code>{k > 1 && <span className="small muted"> t{r.trial}</span>}
                {r.error && <div className="small notready">crashed: {r.error.slice(0, 80)}</div>}
                {!r.passed && !r.error && <div className="small muted">{(r.checks ?? []).filter((c) => !c.pass).map((c) => c.check).join(', ')}</div>}</td>
                <td>{r.passed ? <span className="ready">pass</span> : <span className="notready">fail</span>}</td><td><TierPill tier={r.tier} /></td>
                <td className="small">{r.claims_total} / {r.claims_flagged_final} flagged</td>
                <td className="small">{r.claims_flagged_first_pass ? `${r.claims_flagged_first_pass} fixed in revision` : '—'}</td>
                <td className="small">{(r.judges ?? []).map((jd) => <span key={jd.dimension} className={jd.pass ? 'ready' : 'notready'} style={{ marginRight: 8 }}>{jd.dimension}</span>)}</td>
                <td className="small">{fmtMs(r.latency_ms)}</td><td>{r.run_id && <Link className="small" to={`/?run=${r.run_id}`}>open</Link>}</td></tr>))}</tbody></table>
        </section>) })}
    </div>
  )
}

export function RunsPage() {
  const [runs, setRuns] = useState<Record<string, unknown>[]>([])
  const [an, setAn] = useState<Record<string, unknown> | null>(null)
  useEffect(() => { j<typeof runs>('/api/runs?limit=200').then(setRuns); j<typeof an>('/api/analytics').then(setAn) }, [])
  const tiers = (an?.by_tier ?? {}) as Record<string, number>
  const backlog = (an?.certification_backlog ?? []) as { question: string; count: number }[]
  return (
    <div className="page">
      <h1 className="page-title">Runs and usage</h1>
      <p className="page-sub">Every run is persisted with its full trace and can be replayed. The certification backlog is the list of questions analysts keep asking that are not yet Tier 1 — the pharmacist's review queue.</p>
      {an && (
        <div className="stat-row">
          <div className="stat"><b>{String(an.total_runs)}</b><span>runs</span></div>
          <div className="stat"><b>{tiers['1'] ?? 0} / {tiers['2'] ?? 0} / {tiers['3'] ?? 0} / {tiers['4'] ?? 0}</b><span>tier 1 / 2 / 3 / 4</span></div>
          <div className="stat"><b>{typeof an.certified_rate === 'number' ? `${Math.round(an.certified_rate * 100)}%` : '—'}</b><span>answers at Tier 1</span></div>
          <div className="stat"><b>{an.avg_latency_ms ? fmtMs(Number(an.avg_latency_ms)) : '—'}</b><span>avg latency</span></div>
          <div className="stat"><b>{String(an.avg_rows_cited ?? '—')}</b><span>avg rows cited per answer</span></div>
        </div>)}
      {backlog.length > 0 && (
        <details style={{ marginBottom: 18 }}><summary>Certification backlog ({backlog.length})</summary>
          <table className="tbl" style={{ marginTop: 8 }}><tbody>{backlog.map((b) => <tr key={b.question}><td>{b.question}</td><td className="small muted">{b.count}×</td><td><Link className="small" to={`/?q=${encodeURIComponent(b.question)}`}>ask</Link></td></tr>)}</tbody></table>
        </details>)}
      <table className="tbl"><thead><tr><th>When</th><th>Question</th><th>Tier</th><th>Claims</th><th>Rows</th><th>Latency</th><th>Models</th><th></th></tr></thead>
        <tbody>{runs.map((r) => (
          <tr key={String(r.run_id)}><td className="small muted">{String(r.started_at ?? '').replace('T', ' ').slice(5, 16)}</td><td>{String(r.question)}</td><td><TierPill tier={Number(r.tier)} /></td>
            <td className="small">{String(r.n_claims)} / {String(r.n_flagged)}</td><td className="small">{String(r.rows_cited)}</td><td className="small">{fmtMs(Number(r.latency_ms))}</td>
            <td className="small muted">{(r.models as string[]).map((m) => m.replace('claude-', '')).join(', ')}</td><td><Link className="small" to={`/?run=${r.run_id}`}>replay</Link></td></tr>))}</tbody></table>
    </div>
  )
}
