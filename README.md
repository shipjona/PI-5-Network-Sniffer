# Grizzl-E Charger Monitor

Headless Raspberry Pi monitor for the approved Grizzl-E charger fleet.

## Current Status

This repository already contains a Flask fleet dashboard, SQLite storage,
NetworkManager-based Wi-Fi helpers, and a background polling entry point.

Current implementation state:

- Python virtual environment exists at `.venv`.
- Core imports and SQLite writes are verified by `verify_setup.py`.
- Git is initialized and configured for `shipjona <jonathan25551@outlook.com>`.
- Charger inventory is configured without committing Wi-Fi passwords.
- `wlan0` scanning uses NetworkManager machine-readable output.
- Scanner filters only configured charger SSIDs by default.
- Production Wi-Fi profiles are configured with `ipv4.never-default=yes` and
  `ipv6.never-default=yes` before connection.
- Test charger can be accessed directly at `http://192.168.68.166` without
  switching `wlan0`.

Known remaining work:

- Parse Grizzl-E rendered charging-history rows into normalized session fields.
- Migrate from raw payload session storage to `charger_id + session_start_utc`
  duplicate prevention.
- Add charger visibility/collection-run tables.
- Expand dashboard pages, CSV export, health checks, systemd deployment, and
  weekly email reporting.

## Approved Charger SSIDs

Production:

`CHARGER_2`, `CHARGER_3`, `CHARGER_10`, `CHARGER_11`, `CHARGER_12`,
`CHARGER_13`, `CHARGER_14`, `CHARGER_15`, `CHARGER_16`, `CHARGER_17`,
`CHARGER_18`, `CHARGER_19`, `CHARGER_20`, `CHARGER_21`

Development/test:

`Shipman-GRU` at `http://192.168.68.166`

## Secrets

Do not commit real Wi-Fi or SMTP credentials.

Create the protected environment file:

```bash
sudo install -d -o root -g grizzl-monitor -m 0750 /etc/grizzl-monitor
sudo cp config/grizzl-monitor.env.example /etc/grizzl-monitor/grizzl-monitor.env
sudo chown root:grizzl-monitor /etc/grizzl-monitor/grizzl-monitor.env
sudo chmod 0640 /etc/grizzl-monitor/grizzl-monitor.env
sudo nano /etc/grizzl-monitor/grizzl-monitor.env
```

Required Wi-Fi variables:

```bash
GRIZZL_PRODUCTION_WIFI_PASSWORD=...
GRIZZL_TEST_WIFI_PASSWORD=...
```

The application reads `/etc/grizzl-monitor/grizzl-monitor.env` at runtime.
Secrets are resolved only when a Wi-Fi connection is attempted.

## Development Commands

Activate the environment:

```bash
cd /home/grizzlepi/grizzl-monitor
source .venv/bin/activate
```

Verify baseline setup:

```bash
python verify_setup.py
```

Run unit tests:

```bash
python -m pytest
```

Scan for approved charger SSIDs on `wlan0`:

```bash
python scripts/test_scan.py
```

Show all visible SSIDs for diagnostics:

```bash
python scripts/test_scan.py --all
```

Start the current dashboard locally:

```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

## Network Rules

- `eth0` is the management interface for SSH, dashboard, Internet, time sync,
  and reporting.
- `wlan0` is reserved for charger AP scanning and production charger
  connections.
- Production charger Wi-Fi profiles must never install a default route.
- The test charger at `192.168.68.166` should be scraped directly while it is
  reachable on the management LAN.

Before production connection testing, verify:

```bash
nmcli -t -f DEVICE,TYPE,STATE device status
ip route show default
```

Do not run a live production Wi-Fi connection test unless Ethernet management
connectivity has been confirmed.
