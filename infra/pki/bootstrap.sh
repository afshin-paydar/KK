#!/usr/bin/env bash
# Dev-only PKI bootstrap: root CA -> intermediate CA -> broker + backend certs.
# The intermediate CA key is what the backend uses to sign per-device certs.
# DO NOT use these for production; use a managed CA / HSM there.
set -euo pipefail
cd "$(dirname "$0")"

mk_key() { openssl genrsa -out "$1" 4096; }

# Root CA
mk_key root-ca.key
openssl req -x509 -new -key root-ca.key -days 3650 -out root-ca.pem \
  -subj "/O=KnockKnock/CN=KK Root CA"

# Intermediate CA (signs device + service certs)
mk_key intermediate-ca.key
openssl req -new -key intermediate-ca.key -out intermediate-ca.csr \
  -subj "/O=KnockKnock/CN=KK Intermediate CA"
openssl x509 -req -in intermediate-ca.csr -CA root-ca.pem -CAkey root-ca.key \
  -CAcreateserial -days 1825 -out intermediate-ca.pem \
  -extfile <(printf "basicConstraints=critical,CA:true,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign")

cat intermediate-ca.pem root-ca.pem > ca-chain.pem

# Leaf cert helper: $1 = CN
leaf() {
  mk_key "$1.key"
  openssl req -new -key "$1.key" -out "$1.csr" -subj "/O=KnockKnock/CN=$1"
  openssl x509 -req -in "$1.csr" -CA intermediate-ca.pem -CAkey intermediate-ca.key \
    -CAcreateserial -days 825 -out "$1.pem"
  rm -f "$1.csr"
}

leaf broker     # MQTT broker server cert
leaf backend    # backend's MQTT client cert (CN=backend, see acl)

rm -f intermediate-ca.csr *.srl
echo "PKI bootstrapped. Device certs are issued at runtime by the backend PKI."
