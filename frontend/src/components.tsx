import { useEffect, useMemo, useState } from 'react'
import { marked } from 'marked'
import { j, fmtMs, fmtTok } from './api'
import type { Answer, Evidence, TraceStep, Warning, Interpretation } from './api'

// ---------------------------------------------------------------- markdown with clickable citations
export function Prose({ md, onCite, active }: { md: string; onCite: (id: string) => void; active?: string | null }) {
  const html = useMemo(() => {
    const raw = marked.parse(md, { async: false }) as string
    return raw.replace(/\[((?:E\d+|SYS)(?:\s*,\s*(?:E\d+|SYS))*)\]/g, (_m, ids: string) =>
      ids.split(',').map((x) => x.trim()).map((id) => `<button class="cite${active === id ? ' active' : ''}" data-cite="${id}" type="button">${id}</button>`).join(''))
  }, [md, active])
  return (
    <div className="prose" onClick={(e) => { const t = (e.target as HTMLElement).closest('[data-cite]'); if (t) onCite(t.getAttribute('data-cite')!) }}
      dangerouslySetInnerHTML={{ __html: html }} />
  )
}

// ---------------------------------------------------------------- source row viewer
export function RowView({ rowId }: { rowId: string }) {
  const [row, setRow] = useState<{ table: string; line: number; data: Record<string, unknown> } | null>(null)
  useEffect(() => { j<{ table: string; line: number; data: Record<string, unknown> }[]>(`/api/data/rows?ids=${encodeURIComponent(rowId)}`).then((r) => setRow(r[0] ?? null)) }, [rowId])
  if (!row) return <div className="muted small">Loading row {rowId}…</div>
  return (
    <div className="rowview">
      <table><tbody>
        <tr><th>source</th><td><code>{row.table}.csv</code>, line {row.line}</td></tr>
        {Object.entries(row.data).filter(([k]) => k !== 'line_no').map(([k, v]) => <tr key={k}><th>{k}</th><td>{String(v)}</td></tr>)}
      </tbody></table>
    </div>
  )
}

export function RowChips({ rows }: { rows: string[] }) {
  const [open, setOpen] = useState<string | null>(null)
  const shown = rows.slice(0, 40)
  return (
    <>
      <div className="rows">
        {shown.map((r) => <button key={r} className="rowid" onClick={() => setOpen(open === r ? null : r)} aria-pressed={open === r}>{r}</button>)}
        {rows.length > shown.length && <span className="muted small">+{rows.length - shown.length} more</span>}
      </div>
      {open && <RowView rowId={open} />}
    </>
  )
}

// ---------------------------------------------------------------- warnings & interpretations
export function WarningList({ warnings }: { warnings: Warning[] }) {
  if (!warnings.length) return <div className="muted small">No data warnings attached to this evidence.</div>
  return <>{warnings.map((w, i) => <div key={i} className={`warn ${w.severity}`}><code>{w.code}</code> &nbsp;{w.message}</div>)}</>
}

export function InterpretationList({ items, pins }: { items: Interpretation[]; pins?: Record<string, string> }) {
  if (!items.length) return <div className="muted small">No ambiguous terms recorded.</div>
  const pinned = (t: string) => Object.keys(pins ?? {}).some((k) => t.toLowerCase().includes(k.toLowerCase()) || k.toLowerCase().includes(t.toLowerCase()))
  return <>{items.map((i, n) => (
    <div className="interp" key={n}>
      <div className="t">{i.term} <span className="muted small">[{i.decision_ref}]</span></div>
      <div>
        <div>{i.chosen}{pinned(i.term) && <span className="pin" style={{ marginLeft: 8 }}>pinned</span>}</div>
        {i.alternatives.length > 0 && <div className="alt small">alternate: {i.alternatives.join(' · ')}{i.differs === true && <span className="d"> — gives a different answer</span>}{i.differs === false && <span className="small"> — same result</span>}</div>}
        {i.note && <div className="small muted">{i.note}</div>}
      </div>
    </div>))}</>
}

// ---------------------------------------------------------------- evidence panel
export function EvidencePanel({ evidence, focus }: { evidence: Evidence[]; focus?: string | null }) {
  return <>{evidence.map((e) => (
    <div className="ev" key={e.id} id={`ev-${e.id}`} style={focus === e.id ? { background: 'var(--tier1-bg)', margin: '0 -12px', padding: '14px 12px', borderRadius: 6 } : undefined}>
      <div className="ev-head">
        <span className="ev-id">{e.id}</span>
        <span className="ev-tool">{e.tool}</span>
        <span className={`badge ${e.id === 'SYS' ? 'sys' : e.certified ? 'cert' : 'derived'}`}>{e.id === 'SYS' ? 'ontology / decisions' : e.certified ? 'certified tool' : 'LLM-authored SQL'}</span>
        <span className="muted small">{e.rows.length} row{e.rows.length === 1 ? '' : 's'} cited · {e.source_tables.join(', ')}</span>
      </div>
      {Object.keys(e.args).length > 0 && <div className="small muted" style={{ marginTop: 4 }}>args: <code>{JSON.stringify(e.args)}</code></div>}
      {e.interpretations.length > 0 && <div style={{ marginTop: 6 }}><InterpretationList items={e.interpretations} /></div>}
      {e.warnings.length > 0 && <div style={{ marginTop: 6 }}><WarningList warnings={e.warnings} /></div>}
      <details><summary className="small">Value returned by the tool</summary><pre>{JSON.stringify(e.value, null, 1)}</pre></details>
      {e.rows.length > 0 && <RowChips rows={e.rows} />}
    </div>))}</>
}

// ---------------------------------------------------------------- trace
export function TracePanel({ steps, live, totals }: { steps: TraceStep[]; live: boolean; totals?: Answer['trace'] | null }) {
  const llm = steps.filter((s) => s.llm)
  const tokIn = llm.reduce((a, s) => a + (s.llm?.input_tokens ?? 0), 0)
  const tokOut = llm.reduce((a, s) => a + (s.llm?.output_tokens ?? 0), 0)
  const ms = steps.reduce((a, s) => a + s.duration_ms, 0)
  const models = Array.from(new Set(llm.map((s) => s.llm!.model.replace('claude-', ''))))
  const cost = llm.every((s) => s.llm?.cost_usd != null) && llm.length ? llm.reduce((a, s) => a + (s.llm?.cost_usd ?? 0), 0) : null
  void totals
  return (
    <aside className="trace" aria-live="polite">
      <h3>Execution trace <span>{steps.length} step{steps.length === 1 ? '' : 's'}{live ? ' · running' : ''}</span></h3>
      {steps.length === 0 && <div className="muted small">Each step the agent takes appears here as it happens: gate, interpretations, tool calls, narration, verification, trust tier.</div>}
      {steps.map((s, i) => (
        <div className={`step ${s.status}${live && i === steps.length - 1 ? ' live' : ''}`} key={s.seq}>
          <div className="dot" />
          <div>
            <div className="t"><span>{s.title}</span><span className="k">{s.kind}</span></div>
            {s.llm && <div className="m">{s.llm.model.replace('claude-', '')} · {fmtTok(s.llm.input_tokens)}+{fmtTok(s.llm.output_tokens)} tok · {fmtMs(s.llm.latency_ms)}{s.llm.cost_usd != null ? ` · $${s.llm.cost_usd.toFixed(4)}` : ''}</div>}
            {!s.llm && s.duration_ms > 0 && <div className="m">{fmtMs(s.duration_ms)}</div>}
          </div>
        </div>))}
      {steps.length > 0 && (
        <div className="totals">
          <div>LLM calls <b>{llm.length}</b></div><div>Wall time <b>{fmtMs(ms)}</b></div>
          <div>Tokens in <b>{fmtTok(tokIn)}</b></div><div>Tokens out <b>{fmtTok(tokOut)}</b></div>
          <div style={{ gridColumn: '1 / -1' }}>Models <b>{models.join(', ') || '—'}</b></div>
          <div style={{ gridColumn: '1 / -1' }}>Cost <b>{cost != null ? `$${cost.toFixed(4)}` : 'n/a (pricing table not configured)'}</b></div>
        </div>)}
    </aside>
  )
}

export function TierPill({ tier }: { tier: number | null | undefined }) {
  const names: Record<number, string> = { 1: 'Certified', 2: 'Derived', 3: 'Qualified', 4: 'Not answerable' }
  if (tier == null) return <span className="tier-pill t4">—</span>
  return <span className={`tier-pill t${tier}`}>Tier {tier} · {names[tier]}</span>
}
