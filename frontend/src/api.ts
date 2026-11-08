export type RowRef = { table: string; line: number; key: string }
export type Warning = { code: string; severity: 'info' | 'low' | 'medium' | 'high'; message: string; rows: RowRef[] }
export type Interpretation = { term: string; chosen: string; alternatives: string[]; decision_ref: string; note?: string | null; alternate_result?: unknown; differs?: boolean | null }
export type Claim = { text: string; verdict: 'supported' | 'misattributed' | 'unsupported' | 'interpretation'; evidence_ids: string[]; note?: string | null }
export type Evidence = { id: string; tool: string; args: Record<string, unknown>; certified: boolean; rows: string[]; source_tables: string[]; value: unknown; warnings: Warning[]; interpretations: Interpretation[] }
export type LLMUsage = { role: string; model: string; provider: string; input_tokens: number; output_tokens: number; cache_read_tokens: number; latency_ms: number; cost_usd: number | null }
export type TraceStep = { seq: number; kind: string; title: string; started_at: string; duration_ms: number; llm: LLMUsage | null; input?: unknown; output?: unknown; status: 'ok' | 'warn' | 'fail' }
export type Answer = {
  run_id: string; question: string; tier: 1 | 2 | 3 | 4; tier_label: string; tier_reasons: string[]; headline: string; markdown: string
  gate: Record<string, unknown>; interpretations_declared: Record<string, unknown>[]; interpretations_applied: Interpretation[]
  divergent_interpretations: Record<string, unknown>[]; cannot_answer: string[]; warnings: Warning[]; claims: Claim[]
  verification: Record<string, unknown>; evidence: Evidence[]; rows: RowRef[]; substitutions: unknown[]
  certified_query_match: Record<string, unknown> | null; pins: Record<string, string>; escalation: { escalate: boolean; reasons: string[] }
  trace: { run_id: string; started_at: string; steps: TraceStep[] }; manual_lookups_replaced: number
}

export async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { headers: { 'content-type': 'application/json' }, ...init })
  if (!r.ok) throw new Error((await r.text()) || r.statusText)
  return r.json()
}

export function ask(body: { question: string; as_of?: string | null; pins?: Record<string, string> }, onStep: (s: TraceStep) => void): Promise<Answer> {
  return new Promise((resolve, reject) => {
    fetch('/api/ask', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(async (res) => {
      if (!res.ok || !res.body) return reject(new Error(await res.text()))
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      let answer: Answer | null = null
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, idx); buf = buf.slice(idx + 2)
          const ev = /^event: (\w+)/m.exec(chunk)?.[1]
          const dataLine = chunk.split('\n').find((l) => l.startsWith('data: '))
          if (!ev || !dataLine) continue
          const data = JSON.parse(dataLine.slice(6))
          if (ev === 'step') onStep(data)
          else if (ev === 'answer') answer = data
          else if (ev === 'error') return reject(new Error(data.error))
        }
      }
      if (answer) resolve(answer); else reject(new Error('stream ended without an answer'))
    }).catch(reject)
  })
}

export const TIER_NAME: Record<number, string> = { 1: 'Certified', 2: 'Derived', 3: 'Qualified', 4: 'Not answerable from this data' }
export const fmtMs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`)
export const fmtTok = (n: number) => n.toLocaleString()
