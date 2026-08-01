# Grizzl-E Charger Monitor

Headless Raspberry Pi 5 appliance for monitoring approved Grizzl-E charger
access points while keeping management traffic on Ethernet.

## Current Status

Implemented:

- Normalized parser for Grizzl-E `/get_logResult` JSON and rendered HTML rows.
- SQLite schema with `chargers`, `sessions`, `charger_observations`,
  `collection_runs`, `service_state`, and `report_runs`.
- Duplicate prevention using `UNIQUE(charger_id, session_start_utc)`.
- Offline work-site collection with optional direct test-charger polling at
  `http://192.168.68.166`.
- Work-charger offline logging when approved SSIDs are not visible or Wi-Fi scan
  is unavailable.
- NetworkManager/nmcli scanner using machine-readable output.
- Production Wi-Fi profiles configured with `never-default` route protection.
- Flask dashboard pages for overview, chargers, sessions, health, settings, and
  CSV export.
- CLI tools for initialize, scrape, scan, poll, health, export, and report.
- Weekly report generator with CSV attachment and SMTP send path.
- Systemd collector, web, report service, report timer, install script, and
  NetworkManager polkit rule.
- Pytest coverage for parser, database dedupe, scanner offline logging, CSV
  export, reports, routes, config, and Wi-Fi output parsing.

The current source defaults to offline work-site operation. The home test
charger is disabled unless `GRIZZL_ENABLE_TEST_CHARGER=1` is set.

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

Required for production Wi-Fi:

```bash
GRIZZL_PRODUCTION_WIFI_PASSWORD=...
GRIZZL_TEST_WIFI_PASSWORD=...
GRIZZL_FLASK_SECRET_KEY=...
GRIZZL_ENABLE_TEST_CHARGER=0
```

Required for email reports:

```bash
SMTP_HOST=...
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
REPORT_SENDER=...
REPORT_RECIPIENT=...
```

## Development Commands

Activate the Pi environment:

```bash
cd /home/grizzlepi/grizzl-monitor
source .venv/bin/activate
```

Initialize the database:

```bash
python scripts/initialize_db.py
```

Run tests:

```bash
python -m pytest
```

Poll the home test charger directly when the Pi is on the home LAN:

```bash
python scripts/test_scrape.py --charger-id 0
python scripts/test_scrape.py --charger-id 0
```

The second run should report duplicate rows instead of inserting more sessions.

Run one collector cycle:

```bash
python scripts/poll_once.py
```

On the offline work-site appliance, this scans for approved work chargers and
stores local status/failure data without attempting the home test charger.

Scan approved charger SSIDs on the Pi:

```bash
python scripts/test_scan.py
```

Show all visible SSIDs for diagnostics:

```bash
python scripts/test_scan.py --all
```

Export CSV:

```bash
python scripts/export_csv.py --output data/exports/sessions.csv
```

Run health checks:

```bash
python scripts/health_check.py
```

Generate a report dry-run:

```bash
python scripts/send_report.py --dry-run --output-dir data/reports
```

Start the production web dashboard manually:

```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

## Dashboard

Pages:

- `/` overview metrics, charger status, recent sessions, recent collection runs.
- `/chargers` charger visibility, errors, manual collect action.
- `/sessions` filters, pagination, CSV export.
- `/health` database, disk, NetworkManager, interface, time, and test-charger
  diagnostics.
- `/settings` non-secret charger display/enable/target URL settings and report
  dry-run action.

CSV export endpoint:

```text
/export.csv?charger_id=0&start=2026-07-28T00:00:00-07:00&end=2026-08-02T00:00:00-07:00
```

## Offline Data Pull Workflow

For the work-site appliance, the Pi can run without internet. It stores scan,
collection, session, and failure data locally in SQLite.

## Storage Layout

Current appliance layout:

```text
/                         /dev/mmcblk0p2   ext4   Raspberry Pi OS and app code
/home/grizzlepi/grizzl-monitor/data
                          /dev/nvme0n1p1   ext4   Grizzl database and app data
```

The NVMe data filesystem is labeled `GRIZZL_DATA` and mounted by UUID from
`/etc/fstab`. The collector and web systemd units include
`RequiresMountsFor=/home/grizzlepi/grizzl-monitor/data` so they wait for the
data mount before starting.

After migration, the original SD-card data directory is preserved as a dated
backup beside the project directory, for example:

```text
/home/grizzlepi/grizzl-monitor/data.sd-backup-YYYYMMDD-HHMMSS
```

Direct PC-to-Pi Ethernet settings:

Windows Ethernet adapter:

```text
IP address: 10.55.0.1
Subnet mask: 255.255.255.0
Gateway: blank
DNS: blank or automatic
```

Pi `eth0`:

```text
IP address: 10.55.0.2/24
Gateway: blank
```

Monthly pull commands from the PC:

```powershell
ssh grizzlepi@10.55.0.2
```

Then open the dashboard from the PC:

```text
http://10.55.0.2:5000
```

Download CSV from:

```text
http://10.55.0.2:5000/export.csv
```

Keep `GRIZZL_ENABLE_TEST_CHARGER=0` for offline work-site operation. Set it to
`1` only when the Pi has a route to the home test charger at `192.168.68.166`.

## Network Rules

- `eth0` is the management interface for SSH, dashboard, Internet, time sync,
  and reporting.
- `wlan0` is reserved for charger AP scanning and production charger
  connections.
- Production charger Wi-Fi profiles must never install a default route.
- The test charger at `192.168.68.166` is scraped directly while reachable on
  the management LAN.
- Work chargers are logged offline when their approved AP SSID is not visible.

Before production connection testing, verify:

```bash
nmcli -t -f DEVICE,TYPE,STATE device status
ip route show default
```

Do not run a live production Wi-Fi connection test unless Ethernet management
connectivity has been confirmed.

## Systemd Install On The Pi

From the project directory:

```bash
sudo bash scripts/install.sh
sudo nano /etc/grizzl-monitor/grizzl-monitor.env
sudo systemctl restart polkit NetworkManager
sudo systemctl start grizzl-monitor-collector.service
sudo systemctl start grizzl-monitor-web.service
sudo systemctl start grizzl-monitor-report.timer
```

Check status/logs:

```bash
systemctl status grizzl-monitor-collector.service
systemctl status grizzl-monitor-web.service
systemctl list-timers grizzl-monitor-report.timer
journalctl -u grizzl-monitor-collector.service -f
```
