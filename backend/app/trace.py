"""Tracing: each step of a request (reading data, working something out, a Claude call) is recorded as a span,
shaped the way OpenTelemetry shapes them, so the same spans can later also be sent to Langfuse or any other
OpenTelemetry tool. Claude calls use OpenTelemetry's GenAI attribute names (gen_ai.*); cost is worked out here.

    with trace.start("Recap") as t:
        with trace.step("Fetch the run", "data") as span:
            span.note = "..."
"""

import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal

from pydantic import BaseModel, Field, computed_field

Kind = Literal["request", "data", "code", "llm"]

# US dollars per million tokens: input, output, cache reads, cache writes. Thinking is billed as output.
PRICES = {"claude-opus-5-5": (4.00, 20.00, 0.20, 5.00)}


class Span(BaseModel):
    span_id: str = Field(default_factory=lambda: secrets.token_hex(8))
    parent_id: str | None = None
    name: str
    kind: Kind
    start: float  # Unix time in seconds
    end: float | None = None
    status: Literal["ok", "error"] = "ok"
    note: str = ""  # one short line for the "behind the scenes" page
    attributes: dict[str, str | int | float] = {}

    @computed_field
    @property
    def duration_ms(self) -> int | None:
        return None if self.end is None else round((self.end - self.start) * 1000)


class Trace(BaseModel):
    trace_id: str = Field(default_factory=lambda: secrets.token_hex(16))
    name: str
    spans: list[Span] = []  # in the order they started; the first is the whole request


_trace: ContextVar[Trace | None] = ContextVar("trace", default=None)
_span: ContextVar[Span | None] = ContextVar("span", default=None)


@contextmanager
def start(name: str) -> Iterator[Trace]:
    """A new trace for one request, its first span covering all of it."""
    trace = Trace(name=name)
    token = _trace.set(trace)
    try:
        with step(name, "request"):
            yield trace
    finally:
        _trace.reset(token)


@contextmanager
def step(name: str, kind: Kind) -> Iterator[Span]:
    """One step, inside whichever step is running. Outside a trace (in tests, say) the step runs unrecorded."""
    trace, parent = _trace.get(), _span.get()
    span = Span(name=name, kind=kind, start=time.time(), parent_id=parent.span_id if parent else None)
    if trace is not None:
        trace.spans.append(span)
    token = _span.set(span)
    try:
        yield span
    except Exception as e:
        span.status = "error"
        span.attributes["error.type"] = type(e).__name__
        raise
    finally:
        span.end = time.time()
        _span.reset(token)


@contextmanager
def llm_step(name: str) -> Iterator[Span]:
    """Where a Claude call is recorded: the running step if it's an LLM step (so it keeps its own name and
    note), otherwise a new one."""
    span = _span.get()
    if span is not None and span.kind == "llm":
        yield span
    else:
        with step(name, "llm") as span:
            yield span


def record_llm(span: Span, requested_model: str, response) -> None:
    """The model, tokens and cost of one Claude response."""
    usage = response.usage
    tokens = (
        usage.input_tokens,
        usage.output_tokens,
        usage.cache_read_input_tokens or 0,
        usage.cache_creation_input_tokens or 0,
    )
    span.attributes.update(
        {
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": "anthropic",
            "gen_ai.request.model": requested_model,
            "gen_ai.response.model": response.model,  # differs if Claude declined and a fallback model answered
            "gen_ai.response.id": response.id,
            "gen_ai.response.finish_reasons": response.stop_reason or "",
            "gen_ai.usage.input_tokens": tokens[0],
            "gen_ai.usage.output_tokens": tokens[1],
            "gen_ai.usage.cache_read.input_tokens": tokens[2],
            "gen_ai.usage.cache_creation.input_tokens": tokens[3],
        }
    )
    prices = PRICES.get(response.model)
    if prices:
        span.attributes["lab.cost_usd"] = round(sum(t * p for t, p in zip(tokens, prices)) / 1_000_000, 6)
