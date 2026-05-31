#!/bin/sh
set -e

PASSWORD="${TOR_CONTROL_PASSWORD:-changeme}"
HASH=$(tor --hash-password "$PASSWORD" 2>/dev/null | tail -1)

if [ -z "$HASH" ]; then
    echo "ERROR: Failed to generate TOR control password hash" >&2
    exit 1
fi

cat > /etc/tor/torrc <<EOF
SocksPort 0.0.0.0:9050
ControlPort 0.0.0.0:9051
HashedControlPassword ${HASH}
SocksPolicy accept 172.0.0.0/8
SocksPolicy accept 192.168.0.0/16
SocksPolicy accept 10.0.0.0/8
SocksPolicy reject *
Log notice stdout
EOF

exec tor -f /etc/tor/torrc
