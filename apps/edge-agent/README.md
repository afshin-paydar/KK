# KK Edge Agent

Runs on the Raspberry Pi. Does on-device vision + TTS, talks to the cloud only
over MQTT (mTLS), and acts locally.

## Install (on the Pi)

```bash
uv sync                      # add --extra vision --extra tts for real models
cp agent.toml.example /etc/kk/agent.toml   # set backend_url + enrollment_token
uv run kk-agent
```

## What it does
1. **Enroll once** — generates a keypair + CSR locally (private key never leaves
   the Pi), exchanges the one-time token for a per-device client cert.
2. **Connect** to the MQTT broker via mutual TLS (cert CN = device_id).
3. **Run vision locally** — only structured detection metadata is published;
   raw frames stay on-device.
4. **Resolve locally first** — `local_rules` from the cached policy snapshot are
   matched on-device, so common cases need no cloud round trip. Ambiguous events
   are escalated to `devices/{id}/events` for the gateway/Qwen to reason on.
5. **Execute actions** received on `devices/{id}/actions`, then ack.

## Layout
```
kk_agent/
  config.py      TOML config
  enrollment.py  keypair + CSR -> client cert
  vision.py      on-device detection -> metadata only
  tts.py         on-device text-to-speech
  actions.py     local action execution
  main.py        enroll + MQTT loop (produce/consume)
```
