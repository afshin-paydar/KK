"""KK edge agent entrypoint.

Flow:
  1. Enroll (once): generate key + CSR, exchange token for a client cert.
  2. Connect to the MQTT broker over mTLS using the device cert.
  3. Run the local vision loop. Resolve common cases from the cached policy
     snapshot WITHOUT contacting the cloud; only escalate ambiguous events.
  4. Receive validated actions on devices/{id}/actions and execute locally.
"""

import asyncio
import json
import ssl
import uuid
from datetime import datetime, timezone

from asyncio_mqtt import Client

from kk_agent.actions import ActionExecutor
from kk_agent.config import AgentConfig, load_config
from kk_agent.enrollment import enroll
from kk_agent.tts import TTS


def _load_policy(cfg: AgentConfig) -> dict:
    if cfg.policy_path.exists():
        return json.loads(cfg.policy_path.read_text())
    return {}


def _resolve_locally(payload: dict, policy: dict) -> dict | None:
    """Fast path: match local_rules on-device — no cloud round trip."""
    for rule in policy.get("local_rules", []):
        if all(payload.get(k) == v for k, v in rule.get("when", {}).items()):
            return rule.get("do")
    return None


def _tls_context(cfg: AgentConfig) -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=str(cfg.ca_path))
    ctx.load_cert_chain(str(cfg.cert_path), str(cfg.key_path))
    return ctx


async def run(cfg: AgentConfig, device_id: uuid.UUID) -> None:
    policy = _load_policy(cfg)
    executor = ActionExecutor(TTS())
    prefix = f"devices/{device_id}"

    async with Client(
        hostname=cfg.backend_url.split("://")[-1].split(":")[0],  # broker host; see agent.toml
        port=8883,
        tls_context=_tls_context(cfg),
    ) as client:
        await client.subscribe(f"{prefix}/actions", qos=1)
        await client.subscribe(f"{prefix}/config", qos=1)

        async def consume() -> None:
            async with client.messages() as messages:
                async for m in messages:
                    topic = m.topic.value
                    data = json.loads(m.payload)
                    if topic.endswith("/config"):
                        cfg.policy_path.write_text(json.dumps(data["spec"]))
                        policy.update(data["spec"])
                    elif topic.endswith("/actions"):
                        result = executor.execute(data["type"], data.get("params", {}))
                        ack = {
                            "schema": "kk.ack.v1",
                            "action_id": data["action_id"],
                            "status": "executed" if result.get("ok") else "failed",
                            "executed_at": datetime.now(timezone.utc).isoformat(),
                            "result": result,
                        }
                        await client.publish(f"{prefix}/acks", json.dumps(ack), qos=1)

        async def produce() -> None:
            # Replace this stub with VisionPipeline.stream(); here we just heartbeat.
            while True:
                hb = {
                    "schema": "kk.telemetry.v1",
                    "device_id": str(device_id),
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "metrics": {"agent_version": "0.1.0"},
                }
                await client.publish(f"{prefix}/telemetry", json.dumps(hb), qos=0)
                await asyncio.sleep(cfg.heartbeat_interval_s)

        # On a real detection:
        #   action = _resolve_locally(payload, policy)
        #   if action:  executor.execute(...)            # handled on-device
        #   else:        publish to {prefix}/events       # escalate to gateway
        await asyncio.gather(consume(), produce())


def main() -> None:
    cfg = load_config()
    device_id = enroll(cfg) if not cfg.cert_path.exists() else _device_id_from_cert(cfg)
    asyncio.run(run(cfg, device_id))


def _device_id_from_cert(cfg: AgentConfig) -> uuid.UUID:
    from cryptography import x509

    cert = x509.load_pem_x509_certificate(cfg.cert_path.read_bytes())
    cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    return uuid.UUID(cn)


if __name__ == "__main__":
    main()
