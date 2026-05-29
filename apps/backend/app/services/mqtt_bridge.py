"""MQTT bridge: consume device events, run the policy gateway, publish actions.

Connects to the broker over mTLS using the backend's own client cert. Subscribes
to events/acks for the whole fleet and publishes validated actions back to the
owning device's topic. The full decision loop lives in `handle_event`.
"""

import json
import ssl
import uuid
from datetime import datetime, timezone

from asyncio_mqtt import Client, MqttError

from app.config import get_settings
from app.schemas import ActionMsg, EventMsg

ACTIONS_TTL_SECONDS = 30


def _tls_context() -> ssl.SSLContext:
    settings = get_settings()
    ctx = ssl.create_default_context(cafile=settings.mqtt_ca_cert)
    ctx.load_cert_chain(settings.mqtt_client_cert, settings.mqtt_client_key)
    return ctx


async def handle_event(client: Client, msg_payload: bytes) -> None:
    """Decision loop for a single inbound event. Wire up DB + services here."""
    event = EventMsg.model_validate_json(msg_payload)

    # 1. load device policy  (TODO: query active PolicyAssignment + Policy)
    # 2. result = await llm_gateway.reason(event.payload, policy_spec)
    # 3. check = policy_engine.validate_action(result.proposed_action, spec, schemas)
    # 4. persist Event + LLMDecision + Action (audit)
    # 5. if check.allowed: publish action below

    action = ActionMsg(
        action_id=uuid.uuid4(),
        correlation_id=event.correlation_id,
        type="noop",
        params={},
    )
    topic = f"devices/{event.device_id}/actions"
    await client.publish(topic, action.model_dump_json(by_alias=True), qos=1)


async def run_bridge() -> None:
    settings = get_settings()
    while True:
        try:
            async with Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                tls_context=_tls_context(),
            ) as client:
                async with client.messages() as messages:
                    await client.subscribe("devices/+/events", qos=1)
                    await client.subscribe("devices/+/acks", qos=1)
                    async for message in messages:
                        if message.topic.value.endswith("/events"):
                            await handle_event(client, message.payload)
                        # acks: update Action.status -> acked/executed (TODO)
        except (MqttError, OSError) as exc:
            # backoff + reconnect (covers broker downtime and missing cert files)
            import asyncio

            print(f"[mqtt_bridge] {type(exc).__name__}: {exc} — retrying in 2s")
            await asyncio.sleep(2)
