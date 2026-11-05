from types import SimpleNamespace

import pytest

from app import trace


def fake_response(model="claude-opus-5-5"):
    usage = SimpleNamespace(
        input_tokens=1_600, output_tokens=400, cache_read_input_tokens=None, cache_creation_input_tokens=None
    )
    return SimpleNamespace(id="msg_1", model=model, stop_reason="end_turn", usage=usage)


def test_steps_nest_inside_the_trace():
    with trace.start("Recap") as t:
        with trace.step("Fetch the run", "data") as fetch:
            fetch.note = "From the runs table"
        with trace.step("Write the recap", "llm"):
            pass

    root, fetch, write = t.spans
    assert [s.name for s in t.spans] == ["Recap", "Fetch the run", "Write the recap"]
    assert root.parent_id is None
    assert fetch.parent_id == write.parent_id == root.span_id
    assert fetch.note == "From the runs table"
    assert all(s.end is not None and s.duration_ms >= 0 for s in t.spans)
    assert len(t.trace_id) == 32 and len(root.span_id) == 16  # OpenTelemetry's sizes


def test_a_failed_step_is_marked():
    with trace.start("Recap") as t:
        with pytest.raises(ValueError), trace.step("Write the recap", "llm"):
            raise ValueError("no")

    assert t.spans[1].status == "error"
    assert t.spans[1].attributes["error.type"] == "ValueError"
    assert t.spans[0].status == "ok"  # the error was handled inside the request


def test_steps_outside_a_trace_still_run():
    with trace.step("Fetch the run", "data") as span:
        span.note = "Not recorded anywhere"


def test_a_claude_call_is_recorded_on_the_llm_step_it_runs_in():
    with trace.start("Recap") as t:
        with trace.step("Write the recap", "llm"):
            with trace.llm_step("Ask Claude") as span:
                trace.record_llm(span, "claude-opus-5-5", fake_response())

    assert [s.name for s in t.spans] == ["Recap", "Write the recap"]
    attributes = t.spans[1].attributes
    assert attributes["gen_ai.request.model"] == "claude-opus-5-5"
    assert attributes["gen_ai.usage.input_tokens"] == 1_600
    assert attributes["gen_ai.usage.output_tokens"] == 400
    # 1,600 in at $4 per million, 400 out at $20 per million.
    assert attributes["lab.cost_usd"] == pytest.approx(0.0144)


def test_a_claude_call_outside_an_llm_step_gets_its_own():
    with trace.start("Hello") as t:
        with trace.llm_step("Ask Claude") as span:
            trace.record_llm(span, "claude-opus-5-5", fake_response())

    assert [(s.name, s.kind) for s in t.spans] == [("Hello", "request"), ("Ask Claude", "llm")]


def test_a_model_without_a_price_has_no_cost():
    with trace.start("Recap") as t, trace.llm_step("Ask Claude") as span:
        trace.record_llm(span, "claude-opus-5-5", fake_response(model="some-fallback-model"))

    assert t.spans[1].attributes["gen_ai.response.model"] == "some-fallback-model"
    assert "lab.cost_usd" not in t.spans[1].attributes
