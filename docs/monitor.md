# Bridge Monitor

A real-time monitoring tool and adaptive logger for the Raspberry Pi cellular failover bridge.

---

## Features

- **Live TUI Dashboard** — CPU temp, CPU/RAM usage, network I/O per interface, bridge activity detection
- **Adaptive Logging** — Polls every 30s for responsive detection; writes every 30 min when idle, every 1 min when active
- **Daily Rotation** — One JSON file per day, auto-cleans files older than 30 days
- **Configurable** — All intervals and thresholds adjustable via config file

---

## Install

```bash title="Install bridge-monitor"
cd bridge-monitor
pip3 install .
```

---

## Usage

### Live Dashboard

```bash title="Launch the dashboard"
bridge-monitor
# or explicitly:
bridge-monitor dashboard
```

The dashboard displays:

| Metric          | Description                  |
| --------------- | ---------------------------- |
| CPU Temperature | With color warning at 70°C+  |
| CPU Usage       | With visual progress bar     |
| RAM Usage       | Used/Total with progress bar |
| eth0 (LAN) I/O  | RX/TX totals and live rates  |
| eth1 (WAN) I/O  | RX/TX totals and live rates  |
| Bridge Status   | Active (forwarding) or idle  |
| Uptime          | System uptime                |

Press `q` to quit.

### View Configuration

```bash title="Show current config"
bridge-monitor config
```

### Manual Logging

```bash title="Start logging manually"
bridge-monitor log
```

---

## Logging Service (Systemd)

For continuous background logging, install the systemd service:

```bash title="Install the service"
cd bridge-monitor
sudo bash install-service.sh
```

This installs and starts `bridge-monitor-logger.service`, which runs in the background and writes logs to `/var/log/bridge-monitor/`.

### Service Commands

```bash title="Manage the service"
sudo systemctl status bridge-monitor-logger    # Check status
sudo systemctl restart bridge-monitor-logger   # Restart
sudo systemctl stop bridge-monitor-logger      # Stop
sudo journalctl -u bridge-monitor-logger -f    # View live output
```

### Updating

To update `bridge-monitor` after pulling new changes from the repository:

```bash title="Update bridge-monitor"
# Pull the latest code
cd ~/raspi-cellular-failover-bridge
git pull origin main

# Reinstall into the existing virtual environment
cd bridge-monitor
sudo /opt/bridge-monitor/venv/bin/pip install .

# Restart the logging service to pick up changes
sudo systemctl restart bridge-monitor-logger
```

!!! note "No need to re-run install-service.sh"
The symlink at `/usr/local/bin/bridge-monitor` already points to the venv binary, so the updated code is available immediately after reinstalling.

---

## Configuration

Edit `/etc/bridge-monitor/config.json`:

```json title="/etc/bridge-monitor/config.json"
{
	"poll_interval_seconds": 30,
	"idle_write_interval_minutes": 30,
	"active_write_interval_minutes": 1,
	"retention_days": 30,
	"bridge_threshold_packets": 10,
	"bridge_window_size": 10,
	"log_directory": "/var/log/bridge-monitor"
}
```

| Setting                         | Default                   | Description                                                            |
| ------------------------------- | ------------------------- | ---------------------------------------------------------------------- |
| `poll_interval_seconds`         | `30`                      | How often to poll bridge status (keeps detection responsive)           |
| `idle_write_interval_minutes`   | `30`                      | How often to write a log entry when bridge is idle                     |
| `active_write_interval_minutes` | `1`                       | How often to write a log entry when bridge is active                   |
| `retention_days`                | `30`                      | Days to keep log files before cleanup                                  |
| `bridge_threshold_packets`      | `10`                      | Minimum average packets/min to consider bridge active                  |
| `bridge_window_size`            | `10`                      | Number of rate samples to average (higher = smoother, slower to react) |
| `log_directory`                 | `/var/log/bridge-monitor` | Where log files are written                                            |

!!! tip "After editing"
Restart the service: `sudo systemctl restart bridge-monitor-logger`

---

## Log Format

Logs are stored as JSON Lines (`.jsonl`) with one file per day:

```
/var/log/bridge-monitor/
├── bridge_2026-03-01.jsonl
├── bridge_2026-03-02.jsonl
└── bridge_2026-03-03.jsonl
```

Each line is a JSON object:

```json title="Example log entry"
{
	"timestamp": "2026-03-03T14:30:00.123456",
	"cpu_temp_c": 48.3,
	"cpu_percent": 12.5,
	"ram_total_mb": 1906.2,
	"ram_used_mb": 342.1,
	"ram_percent": 17.9,
	"uptime_seconds": 86400,
	"bridge_active": true,
	"network": {
		"eth0": {
			"bytes_sent": 123456789,
			"bytes_recv": 987654321,
			"packets_sent": 12345,
			"packets_recv": 98765,
			"send_rate_bps": 1024.5,
			"recv_rate_bps": 4096.2
		},
		"eth1": {
			"bytes_sent": 987654321,
			"bytes_recv": 123456789,
			"packets_sent": 98765,
			"packets_recv": 12345,
			"send_rate_bps": 4096.2,
			"recv_rate_bps": 1024.5
		}
	}
}
```

---

## Bridge Detection

The monitor detects bridge activity by polling the iptables MASQUERADE packet counter:

```bash
sudo iptables -t nat -nvL POSTROUTING
```

### Sliding Window Algorithm

Instead of a simple on/off check, the detector uses a **sliding window average** for smooth, self-tuning detection:

1. Each poll computes the instantaneous packet rate (packets/minute)
2. The rate is added to a sliding window of the last `bridge_window_size` samples
3. The **average** across the window is compared against `bridge_threshold_packets`

This naturally handles bursty internet traffic:

- **Heavy traffic** fills the window with high values → average stays high → bridge stays active longer
- **Light traffic that stops** → zeros push the average down quickly → goes idle sooner
- **Momentary gaps** between bursts → some high values remain in the window → no oscillation

A 30-second minimum hold time prevents single-sample flicker at startup.
