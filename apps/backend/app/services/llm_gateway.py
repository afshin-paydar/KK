"""Qwen policy gateway.

Builds a constrained prompt from (event + policy), calls Qwen via the DashScope
OpenAI-compatible API, and asks for a single structured action. The Qwen API key
lives only here. The returned action is still validated by policy_engine before
it is ever published to a device.
"""

import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

SYSTEM_PROMPT = """You are the reasoning core for an edge device under a strict policy.
You receive event metadata (no images) and must choose at most ONE action from the
allowed_actions list. Respond ONLY with JSON: {"type": "<action.type>", "params": {...}}.
If no action is appropriate, respond with {"type": "noop", "params": {}}."""


@dataclass
class LLMResult:
    proposed_action: dict[str, Any]
    response_raw: dict[str, Any]
    prompt: dict[str, Any]
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int


def _build_messages(event: dict[str, Any], policy_spec: dict[str, Any]) -> list[dict]:
    context = {
        "allowed_actions": policy_spec.get("allowed_actions", []),
        "guardrails": policy_spec.get("guardrails", {}),
        "event": event,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context)},
    ]


async def reason(event: dict[str, Any], policy_spec: dict[str, Any]) -> LLMResult:
    settings = get_settings()
    model = policy_spec.get("llm", {}).get("model", settings.qwen_default_model)
    max_tokens = policy_spec.get("llm", {}).get("max_tokens", 256)
    messages = _build_messages(event, policy_spec)

    import time

    started = time.monotonic()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.qwen_api_base}/chat/completions",
            headers={"Authorization": f"Bearer {settings.qwen_api_key}"},
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    latency_ms = int((time.monotonic() - started) * 1000)

    content = data["choices"][0]["message"]["content"]
    try:
        proposed = json.loads(content)
    except json.JSONDecodeError:
        proposed = {"type": "noop", "params": {}}

    usage = data.get("usage", {})
    return LLMResult(
        proposed_action=proposed,
        response_raw=data,
        prompt={"messages": messages},
        model=model,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        latency_ms=latency_ms,
    )
