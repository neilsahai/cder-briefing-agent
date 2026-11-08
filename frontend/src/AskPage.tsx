import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ask, j } from './api'
import type { Answer, TraceStep } from './api'
import { EvidencePanel, InterpretationList, Prose, TracePanel, WarningList } from './components'

const SUGGESTED = [
  'How many drugs are currently in shortage because of quality problems, and which of their manufacturing sites received an OAI classification in the last two fiscal years?',
  'For amoxicillin oral suspension, what is the real supply picture — how many approved applications, how many are actively marketed, and what is currently in shortage?',
  'Which foreign manufacturing establishments supplying drugs currently in shortage have not been inspected since FY2021?',
  'Is the amoxicillin shortage resolved?',
  'Which pediatric antibiotics are currently in shortage?',
  'Which sponsors hold the most tentative approvals, and for which ingredients?',
]

type Tab = 'answer' | 'evidence' | 'claims' | 'interp' | 'caveats'

export default function AskPage() {
  const [params] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const [asOf, setAsOf] = useState('')
  const [pins, setPins] = useState<Record<string, string>>({})
  const [steps, setSteps] = useState<TraceStep[]>([])
  const [running, setRunning] = useState(false)
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('answer')
  const [focus, setFocus] = useState<string | null>(null)
  const [briefings, setBriefings] = useState<{ id: string; title: string }[]>([])
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => { j<{ id: string; title: string }[]>('/api/briefings').then(setBriefings).catch(() => {}) }, [answer])
  useEffect(() => { const rid = params.get('run'); if (rid) j<Answer>(`/api/runs/${rid}`).then((a) => { setAnswer(a); setQ(a.question); setSteps(a.trace.steps); setPins(a.pins ?? {}) }) }, [params])

  async function submit(question = q, usePins = pins) {
    if (!question.trim() || running) return
    setRunning(true); setError(null); setAnswer(null); setSteps([]); setTab('answer'); setFocus(null)
    try {
      const a = await ask({ question, as_of: asOf || null, pins: Object.keys(usePins).length ? usePins : undefined }, (s) => setSteps((prev) => [...prev, s]))
      setAnswer(a); setSteps(a.trace.steps)
    } catch (e) { setError((e as Error).message) } finally { setRunning(false) }
  }

  function pinAndRerun(term: string, reading: string) {
    const next = { ...pins, [term]: reading }
    setPins(next); submit(q, next)
  }

  async function pinToBriefing() {
    if (!answer) return
    let b = briefings[0]
    if (!b) b = await j<{ id: string; title: string }>('/api/briefings', { method: 'POST', body: JSON.stringify({ title: 'Pediatric Antibiotic Shortages — Senate HELP briefing' }) })
    await j(`/api/briefings/${b.id}/pin`, { method: 'POST', body: JSON.stringify({ run_id: answer.run_id }) })
    setToast(`Added to briefing “${b.title}”.`); setTimeout(() => setToast(null), 3500)
  }

  async function promote() {
    if (!answer) return
    const name = prompt('Name for this certified query (slug):', answer.question.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 50))
    if (!name) return
    const who = prompt('Verified by (name, role):', 'Staff pharmacist')
    if (!who) return
    try { await j('/api/certified/promote', { method: 'POST', body: JSON.stringify({ run_id: answer.run_id, name, verified_by: who }) }); setToast(`Certified as “${name}”. The next matching question runs this plan as Tier 1.`) }
    catch (e) { setToast(`Could not certify: ${(e as Error).message}`) }
    setTimeout(() => setToast(null), 5000)
  }

  const flagged = answer?.claims.filter((c) => c.verdict === 'unsupported' || c.verdict === 'misattributed') ?? []
  const divergentAll = answer?.interpretations_applied.filter((i) => i.differs && !Object.keys(answer.pins ?? {}).some((k) => i.term.toLowerCase().includes(k.toLowerCase()))) ?? []
  const divergent = divergentAll.filter((d, idx) => divergentAll.findIndex((x) => x.term.toLowerCase() === d.term.toLowerCase()) === idx)
  const highWarnings = answer?.warnings.filter((w) => w.severity === 'high' || w.severity === 'medium') ?? []

  return (
    <div className="page two-col">
      <div>
        <h1 className="page-title">Ask the shortage data</h1>
        <p className="page-sub">Every number in an answer is traced to a row in the three source files, every ambiguous term is named with the reading applied, and an independent verifier checks each claim before you see it.</p>
        <div className="ask-box">
          <textarea value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Which foreign sites supplying drugs in shortage haven't been inspected since FY2021?"
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit() }} aria-label="Question" />
          <div className="ask-row">
            <button className="btn primary" onClick={() => submit()} disabled={running || !q.trim()}>{running ? 'Working…' : 'Ask'}</button>
            <label>As of <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} aria-label="As-of date" /> <span className="muted small">(default: latest date in the data)</span></label>
            <span className="muted small" style={{ marginLeft: 'auto' }}>⌘/Ctrl + Enter</span>
          </div>
          {Object.keys(pins).length > 0 && (
            <div className="pins">
              <span className="muted small">Pinned readings:</span>
              {Object.entries(pins).map(([k, v]) => <span className="pin" key={k}>{k} = {v}<button aria-label={`unpin ${k}`} onClick={() => { const n = { ...pins }; delete n[k]; setPins(n) }}>×</button></span>)}
            </div>)}
        </div>
        {!answer && !running && (
          <div className="suggest">{SUGGESTED.map((s) => <button key={s} onClick={() => { setQ(s); submit(s, pins) }}>{s}</button>)}</div>)}

        {error && <div className="err" style={{ marginTop: 18 }}>The run failed: {error}</div>}

        {running && (
          <div className="answer tier-4" aria-busy="true" style={{ borderLeftColor: 'var(--rule-strong)' }}>
            <div className="tier-line"><span className="tier-name" style={{ color: 'var(--ink-2)' }}>Working</span><span className="tier-why">{steps.length ? steps[steps.length - 1].title : 'Starting…'}</span></div>
            <p className="muted" style={{ margin: 0, maxWidth: '70ch' }}>The gate classifies the question, the planner declares every ambiguous term before touching data, certified tools return values with row citations, the narrator writes with placeholders only, and an independent verifier checks each claim. The trace on the right is live.</p>
          </div>)}

        {answer && (
          <article className={`answer tier-${answer.tier}`}>
            <div className="tier-line">
              <span className="tier-name">Tier {answer.tier} — {answer.tier_label}</span>
              <span className="tier-why">{answer.tier_reasons.join(' · ')}</span>
            </div>
            <p className="headline">{answer.headline}</p>

            {divergent.length > 0 && answer.tier !== 4 && (
              <div className="warn" style={{ marginBottom: 12 }}>
                This question has {divergent.length === 1 ? 'a reading' : 'readings'} that change the answer. Pin one to resolve it:
                <div className="suggest" style={{ marginTop: 8 }}>
                  {divergent.map((d) => Array.from(new Set([d.chosen, ...d.alternatives])).map((reading) => (
                    <button key={d.term + reading} onClick={() => pinAndRerun(d.term, reading)}>{d.term}: {reading}</button>)))}
                </div>
              </div>)}

            <div className="tabs" role="tablist">
              {([['answer', 'Answer', null], ['evidence', 'Evidence', answer.evidence.length], ['claims', 'Verifier', answer.claims.length], ['interp', 'Interpretations', answer.interpretations_applied.length], ['caveats', 'Caveats', highWarnings.length]] as [Tab, string, number | null][])
                .map(([k, label, n]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{label}{n != null && <span className="n">{n}</span>}</button>)}
            </div>

            {tab === 'answer' && <Prose md={answer.markdown} active={focus} onCite={(id) => { setFocus(id); setTab('evidence'); setTimeout(() => document.getElementById(`ev-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50) }} />}
            {tab === 'evidence' && <EvidencePanel evidence={answer.evidence} focus={focus} />}
            {tab === 'claims' && (
              <div>
                <p className="small muted">An independent model (Opus) decomposed the answer into atomic claims and checked each against the evidence and its source table. Overall: <b>{String(answer.verification?.overall ?? '—')}</b>. {flagged.length ? `${flagged.length} flagged.` : 'Nothing flagged.'}</p>
                {answer.claims.map((c, i) => (
                  <div key={i} className={`warn ${c.verdict === 'supported' ? 'info' : c.verdict === 'interpretation' ? 'low' : 'high'}`}>
                    <code>{c.verdict}</code> {c.text} <span className="muted small">[{c.evidence_ids.join(', ')}]</span>{c.note && <div className="small muted">{c.note}</div>}
                  </div>))}
              </div>)}
            {tab === 'interp' && <InterpretationList items={answer.interpretations_applied} pins={answer.pins} />}
            {tab === 'caveats' && (
              <div>
                <WarningList warnings={highWarnings} />
                {answer.cannot_answer.length > 0 && <><h2 style={{ fontSize: 15, margin: '16px 0 6px', color: 'var(--ink-2)' }}>Cannot be answered from this data</h2><ul>{answer.cannot_answer.map((c, i) => <li key={i}>{c}</li>)}</ul></>}
              </div>)}

            <div className="actions">
              <button className="btn" onClick={pinToBriefing} disabled={answer.tier === 4}>Add to briefing</button>
              <button className="btn" onClick={promote} disabled={answer.tier === 4 || flagged.length > 0} title={flagged.length ? 'Fix flagged claims before certifying' : ''}>Certify this answer</button>
              <span className="hint">{answer.rows.length} source rows cited · replaced ≈{answer.manual_lookups_replaced} manual lookups across {new Set(answer.rows.map((r) => r.table)).size} files</span>
              {toast && <span className="hint" style={{ color: 'var(--tier1)' }}>{toast}</span>}
            </div>
          </article>)}
      </div>
      <TracePanel steps={steps} live={running} />
    </div>
  )
}
