from functools import cache

import anthropic
from pydantic import BaseModel

from app import trace
from app.secrets import read_secret

MODEL = "claude-opus-5-5"


class ClaudeUnavailable(Exception):
    """Claude couldn't answer: a refusal, or an API or network error. The message is safe to show."""


@cache
def client() -> anthropic.Anthropic:
    # Deployed: the key comes from Secrets Manager. Locally, set CLAUDE_API_KEY_SECRET to the staging secret's
    # name (see the README), or leave it unset and the SDK uses ANTHROPIC_API_KEY or an `ant auth login` profile.
    api_key = read_secret("CLAUDE_API_KEY_SECRET")
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


def _call(method, **kwargs):
    """One request with the lab's defaults, traced, turning failures into ClaudeUnavailable."""
    with trace.llm_step("Ask Claude") as span:
        response = _send(method, **kwargs)
        trace.record_llm(span, MODEL, response)
        if response.stop_reason == "refusal":
            raise ClaudeUnavailable("Claude declined to answer that.")
        return response


def _send(method, **kwargs):
    try:
        return method(
            model=MODEL,
            max_tokens=16000,
            # If Claude declines, Anthropic re-runs the request on its recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **kwargs,
        )
    except anthropic.AuthenticationError as e:
        # Forget the key, so one stored since (scripts/claude-key.sh) is picked up on the next request.
        client.cache_clear()
        read_secret.cache_clear()
        raise ClaudeUnavailable("The Claude API key is missing or wrong.") from e
    except anthropic.RateLimitError as e:
        raise ClaudeUnavailable("Claude is busy right now. Try again in a minute.") from e
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        raise ClaudeUnavailable("Claude couldn't be reached. Try again shortly.") from e


def ask(system: str, prompt: str) -> str:
    """One question, one short answer."""
    response = _call(
        client().beta.messages.create,
        output_config={"effort": "low"},  # short, playful replies don't need deep thinking
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def ask_for[T: BaseModel](system: str, prompt: str, output: type[T], effort: str = "medium") -> T:
    """One question, answered in the shape of `output` (checked against its schema)."""
    response = _call(
        client().beta.messages.parse,
        output_config={"effort": effort},
        output_format=output,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.parsed_output is None:
        raise ClaudeUnavailable("Claude's answer wasn't in the expected shape.")
    return response.parsed_output
