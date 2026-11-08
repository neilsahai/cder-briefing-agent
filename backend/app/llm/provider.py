"""Provider interface: Anthropic API by default; Bedrock with PROVIDER=bedrock. Same code path.

Every call returns a LLMCall record (model, tokens, latency, cost) that the trace stores — the
trace is how the panel sees which model ran which step and what it cost.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from .routing import ROLE_MODELS, estimate_cost_usd

PROVIDER = os.environ.get("PROVIDER", "anthropic").lower()

# Bedrock model IDs differ from API IDs. Override via env if your region/version differs.
BEDROCK_MODEL_MAP = {
    "claude-haiku-5-5": os.environ.get("BEDROCK_HAIKU", "us.anthropic.claude-haiku-5-5-v1:0"),
    "claude-sonnet-5-5": os.environ.get("BEDROCK_SONNET", "us.anthropic.claude-sonnet-5-5-v1:0"),
    "claude-opus-5-5": os.environ.get("BEDROCK_OPUS", "us.anthropic.claude-opus-5-5-v1:0"),
}


@dataclass
class LLMCall:
    role: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    latency_ms: int
    cost_usd: float | None
    stop_reason: str | None
    response: Any = field(repr=False, default=None)


class Provider:
    def __init__(self) -> None:
        self.name = PROVIDER
        if PROVIDER == "bedrock":
            from anthropic import AnthropicBedrock  # type: ignore
            self.client = AnthropicBedrock(aws_region=os.environ.get("AWS_REGION", "us-east-1"))
        else:
            from anthropic import Anthropic
            self.client = Anthropic()  # ANTHROPIC_API_KEY from env

    def model_id(self, role: str) -> str:
        m = ROLE_MODELS[role]
        return BEDROCK_MODEL_MAP.get(m, m) if PROVIDER == "bedrock" else m

    def messages(self, role: str, *, system: str, messages: list[dict], tools: list[dict] | None = None,
                 max_tokens: int = 2048, temperature: float = 0.0, tool_choice: dict | None = None) -> LLMCall:
        model = self.model_id(role)
        # Note: this SDK generation has no `temperature`; determinism comes from tool-forced structured outputs.
        kwargs: dict[str, Any] = dict(model=model, max_tokens=max_tokens, messages=messages,
                                      system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}])
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        t0 = time.perf_counter()
        resp = self.client.messages.create(**kwargs)
        ms = int((time.perf_counter() - t0) * 1000)
        u = resp.usage
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        cw = getattr(u, "cache_creation_input_tokens", 0) or 0
        return LLMCall(role=role, model=model, provider=self.name, input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                       cache_read_tokens=cr, cache_write_tokens=cw, latency_ms=ms,
                       cost_usd=estimate_cost_usd(ROLE_MODELS[role], u.input_tokens, u.output_tokens, cr, cw),
                       stop_reason=resp.stop_reason, response=resp)


_provider: Provider | None = None


def get_provider() -> Provider:
    global _provider
    if _provider is None:
        _provider = Provider()
    return _provider


def text_of(resp: Any) -> str:
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def tool_uses(resp: Any) -> list[Any]:
    return [b for b in resp.content if getattr(b, "type", "") == "tool_use"]


class StructuredOutputError(Exception):
    pass


def structured(prov: "Provider", role: str, *, system: str, messages: list[dict], tool: dict, max_tokens: int = 2000,
               extra_tools: list[dict] | None = None) -> tuple[dict, LLMCall, Any]:
    """Get a single tool_use for `tool`. Tries forced tool_choice; if the model rejects forced choice,
    falls back to auto + instruction, validating the result and retrying once. Returns (input, call, tool_use_block)."""
    tools = (extra_tools or []) + [tool]
    try:
        call = prov.messages(role, system=system, messages=messages, tools=tools, tool_choice={"type": "tool", "name": tool["name"]}, max_tokens=max_tokens)
    except Exception as ex:  # noqa: BLE001
        if "tool_choice" not in str(ex):
            raise
        call = prov.messages(role, system=system, messages=messages, tools=tools, max_tokens=max_tokens)
    for attempt in range(2):
        uses = [u for u in tool_uses(call.response) if u.name == tool["name"]]
        if uses:
            return uses[0].input, call, uses[0]
        nudge = messages + [{"role": "assistant", "content": call.response.content},
                            {"role": "user", "content": f"You must respond by calling the `{tool['name']}` tool now. Do not answer in prose."}]
        call = prov.messages(role, system=system, messages=nudge, tools=tools, max_tokens=max_tokens)
    raise StructuredOutputError(f"model did not call {tool['name']} after retry (role={role})")
