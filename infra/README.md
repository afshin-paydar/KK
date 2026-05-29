# KK Infra (dev)

> **Run `pki/bootstrap.sh` BEFORE `docker compose up`.** The broker mounts
> `pki/` for its CA + server cert; if those files don't exist yet it fails with
> `Error: Unable to load CA certificates`.

```bash
# 1. Bootstrap a dev PKI (root + intermediate CA, broker + backend certs)
bash pki/bootstrap.sh

# 2. Bring up Postgres + MQTT broker (mTLS).  --build picks up mqtt/Dockerfile
docker compose up -d --build
```

The broker config + ACL are baked into a small image (`mqtt/Dockerfile`) with
`mosquitto` ownership, so editing `mqtt/mosquitto.conf` or `mqtt/acl` requires a
`docker compose up -d --build` to take effect.

- `pki/` — dev CA chain. The backend uses `intermediate-ca.{pem,key}` to sign
  per-device client certs at enrollment time. Device private keys are generated
  on the Pi and never seen here.
- `mqtt/mosquitto.conf` — requires client certs; CN (device_id) becomes the MQTT
  username, matched by `mqtt/acl` so each device is confined to `devices/<id>/#`.

Production: replace the dev CA with a managed CA / HSM, run a CRL or OCSP, and use
a clustered broker (e.g. EMQX) with the same mTLS + per-device ACL model.
