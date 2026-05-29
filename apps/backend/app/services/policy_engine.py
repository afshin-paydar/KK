"""Policy enforcement for LLM-proposed actions.

The gateway never trusts the model's output directly. Every proposed action is
validated here against the device's active policy: it must be in the allowlist,
not in deny_actions, and its params must satisfy the action type's JSON schema.
"""

from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate


@dataclass
class PolicyCheck:
    allowed: bool
    reason: str | None = None


def validate_action(
    proposed: dict[str, Any],
    policy_spec: dict[str, Any],
    action_schemas: dict[str, dict],
) -> PolicyCheck:
    action_type = proposed.get("type")
    if not action_type:
        return PolicyCheck(False, "missing action type")

    guardrails = policy_spec.get("guardrails", {})
    if action_type in guardrails.get("deny_actions", []):
        return PolicyCheck(False, f"{action_type} is denied by guardrails")

    allowed = {a["type"]: a for a in policy_spec.get("allowed_actions", [])}
    if action_type not in allowed:
        return PolicyCheck(False, f"{action_type} not in policy allowlist")

    schema = action_schemas.get(action_type)
    if schema:
        try:
            validate(instance=proposed.get("params", {}), schema=schema)
        except ValidationError as exc:
            return PolicyCheck(False, f"params failed schema: {exc.message}")

    return PolicyCheck(True)


def resolve_locally(event_payload: dict[str, Any], policy_spec: dict[str, Any]) -> dict | None:
    """Mirror of the on-device fast path: match local_rules without the LLM.

    Used by the gateway as a fallback / for parity testing; the Pi runs the same
    logic from its cached snapshot so common cases never reach the cloud.
    """
    for rule in policy_spec.get("local_rules", []):
        when = rule.get("when", {})
        if all(event_payload.get(k) == v for k, v in when.items()):
            return rule.get("do")
    return None
