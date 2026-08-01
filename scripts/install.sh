#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/grizzlepi/grizzl-monitor}"
APP_USER="${APP_USER:-grizzlepi}"
APP_GROUP="${APP_GROUP:-grizzl-monitor}"
ENV_DIR="${ENV_DIR:-/etc/grizzl-monitor}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
POLKIT_DIR="${POLKIT_DIR:-/etc/polkit-1/rules.d}"
INSTALL_OPTIONAL_VITALS_TOOLS="${INSTALL_OPTIONAL_VITALS_TOOLS:-0}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/install.sh" >&2
  exit 1
fi

groupadd --system --force "$APP_GROUP"
usermod -aG "$APP_GROUP" "$APP_USER"

install -d -o "$APP_USER" -g "$APP_GROUP" -m 0755 "$PROJECT_DIR/data"
install -d -o "$APP_USER" -g "$APP_GROUP" -m 0755 "$PROJECT_DIR/logs"
install -d -o root -g "$APP_GROUP" -m 0750 "$ENV_DIR"

if [[ "$INSTALL_OPTIONAL_VITALS_TOOLS" == "1" ]] && command -v apt-get >/dev/null 2>&1; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    smartmontools \
    nvme-cli
fi

if [[ ! -f "$ENV_DIR/grizzl-monitor.env" ]]; then
  install -o root -g "$APP_GROUP" -m 0640 \
    "$PROJECT_DIR/config/grizzl-monitor.env.example" \
    "$ENV_DIR/grizzl-monitor.env"
  echo "Created $ENV_DIR/grizzl-monitor.env. Edit it before live Wi-Fi/reporting."
fi

install -o root -g root -m 0644 \
  "$PROJECT_DIR/systemd/50-grizzl-monitor-networkmanager.rules" \
  "$POLKIT_DIR/50-grizzl-monitor-networkmanager.rules"

install -o root -g root -m 0644 \
  "$PROJECT_DIR/systemd/grizzl-monitor-collector.service" \
  "$SYSTEMD_DIR/grizzl-monitor-collector.service"
install -o root -g root -m 0644 \
  "$PROJECT_DIR/systemd/grizzl-monitor-web.service" \
  "$SYSTEMD_DIR/grizzl-monitor-web.service"
install -o root -g root -m 0644 \
  "$PROJECT_DIR/systemd/grizzl-monitor-report.service" \
  "$SYSTEMD_DIR/grizzl-monitor-report.service"
install -o root -g root -m 0644 \
  "$PROJECT_DIR/systemd/grizzl-monitor-report.timer" \
  "$SYSTEMD_DIR/grizzl-monitor-report.timer"

sudo -u "$APP_USER" "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/initialize_db.py"

systemctl daemon-reload
systemctl enable grizzl-monitor-collector.service
systemctl enable grizzl-monitor-web.service
systemctl enable grizzl-monitor-report.timer

cat <<EOF
Install complete.

Next:
  sudo nano $ENV_DIR/grizzl-monitor.env
  sudo systemctl restart polkit NetworkManager
  sudo systemctl start grizzl-monitor-collector.service
  sudo systemctl start grizzl-monitor-web.service
  sudo systemctl start grizzl-monitor-report.timer

Check:
  systemctl status grizzl-monitor-collector.service
  systemctl status grizzl-monitor-web.service
  journalctl -u grizzl-monitor-collector.service -f

Optional NVMe SMART vitals tools, when the Pi has internet:
  sudo INSTALL_OPTIONAL_VITALS_TOOLS=1 bash scripts/install.sh
EOF
