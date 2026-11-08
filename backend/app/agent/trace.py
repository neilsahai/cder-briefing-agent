"""Execution trace: every step the agent takes, with model/tokens/latency/cost. Streamed to the UI
and persisted for replay. The trace IS the audit log."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

StepKind = Literal["gate", "escalation", "plan", "tool_call", "sql", "narrate", "render", "verify", "tier", "final", "error", "info"]


class LLMUsage(BaseModel):
    role: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: int
    cost_usd: float | None


class TraceStep(BaseModel):
    seq: int
    kind: StepKind
    title: str
    started_at: str
    duration_ms: int = 0
    llm: LLMUsage | None = None
    input: Any = None
    output: Any = None
    status: Literal["ok", "warn", "fail"] = "ok"


class Trace(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    question: str
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    steps: list[TraceStep] = Field(default_factory=list)

    def totals(self) -> dict[str, Any]:
        calls = [s.llm for s in self.steps if s.llm]
        cost = [c.cost_usd for c in calls if c.cost_usd is not None]
        return {
            "llm_calls": len(calls),
            "input_tokens": sum(c.input_tokens for c in calls),
            "output_tokens": sum(c.output_tokens for c in calls),
            "cache_read_tokens": sum(c.cache_read_tokens for c in calls),
            "latency_ms_total": sum(s.duration_ms for s in self.steps),
            "cost_usd": round(sum(cost), 6) if cost and len(cost) == len(calls) else None,
            "models_used": sorted({c.model for c in calls}),
            "tool_calls": len([s for s in self.steps if s.kind == "tool_call"]),
        }


class Tracer:
    """Collects steps and emits them to an optional sink (SSE queue, stdout, ...)."""

    def __init__(self, question: str, sink: Callable[[TraceStep], None] | None = None) -> None:
        self.trace = Trace(question=question)
        self.sink = sink
        self._seq = 0

    def step(self, kind: StepKind, title: str, *, input: Any = None, output: Any = None, llm=None,
             duration_ms: int = 0, status: str = "ok") -> TraceStep:
        self._seq += 1
        usage = None
        if llm is not None:
            usage = LLMUsage(role=llm.role, model=llm.model, provider=llm.provider, input_tokens=llm.input_tokens,
                             output_tokens=llm.output_tokens, cache_read_tokens=llm.cache_read_tokens,
                             cache_write_tokens=llm.cache_write_tokens, latency_ms=llm.latency_ms, cost_usd=llm.cost_usd)
            duration_ms = duration_ms or llm.latency_ms
        st = TraceStep(seq=self._seq, kind=kind, title=title, started_at=datetime.now(timezone.utc).isoformat(),
                       duration_ms=duration_ms, llm=usage, input=input, output=output, status=status)  # type: ignore[arg-type]
        self.trace.steps.append(st)
        if self.sink:
            self.sink(st)
        return st

    class _Timer:
        def __init__(self) -> None:
            self.t0 = time.perf_counter()

        def ms(self) -> int:
            return int((time.perf_counter() - self.t0) * 1000)

    def timer(self) -> "Tracer._Timer":
        return Tracer._Timer()
