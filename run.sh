#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -euo pipefail

DATA_FILE=/data/odroid-m1s-ups.dev
UPS_NAME="$(bashio::config 'ups_name')"

mkdir -p /etc/nut /run/nut /var/state/ups
chown -R nut:nut /run/nut /var/state/ups /data
export NUT_STATEPATH=/run/nut
export NUT_ALTPIDPATH=/run/nut

/usr/local/bin/render-nut-config \
    --config /data/options.json \
    --data-file "${DATA_FILE}" \
    --output /etc/nut/ups.conf

cat > /etc/nut/upsd.conf <<'EOF'
LISTEN 0.0.0.0 3493
MAXAGE 15
EOF

cat > /etc/nut/upsd.users <<EOF
[${UPS_NAME}_mon]
    password = $(bashio::config 'password')
    upsmon = primary

[$(bashio::config 'username')]
    password = $(bashio::config 'password')
    actions = SET
    instcmds = ALL
EOF

cat > /etc/nut/nut.conf <<'EOF'
MODE=netserver
EOF

# Start the serial bridge first so dummy-ups always has a valid definition file.
/usr/local/bin/odroid-m1s-ups --config /data/options.json --state-file "${DATA_FILE}" &
BRIDGE_PID=$!
trap 'kill "${BRIDGE_PID}" 2>/dev/null || true; upsdrvctl stop; kill "${UPSD_PID:-}" 2>/dev/null || true' EXIT TERM INT

upsdrvctl start
upsd -F &
UPSD_PID=$!
wait "${UPSD_PID}"
