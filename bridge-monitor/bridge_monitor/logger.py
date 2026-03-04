"""Adaptive JSON logger with daily file rotation.

Writes system snapshots to daily JSON Lines files and automatically
cleans up files older than the configured retention period.
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from bridge_monitor.bridge_detect import BridgeDetector
from bridge_monitor.config import load_config
from bridge_monitor.stats import StatsCollector


class BridgeLogger:
    """Adaptive logger that adjusts frequency based on bridge activity.

    - Idle mode: logs every `idle_interval_minutes`
    - Active mode: logs every `active_interval_minutes`
    - Daily rotation: one file per day (bridge_YYYY-MM-DD.jsonl)
    - Auto-cleanup: removes files older than `retention_days`
    """

    def __init__(self, config: dict | None = None):
        """Initialize the logger.

        Args:
            config: Configuration dict. Loaded from file if None.
        """
        self.config = config or load_config()
        self.log_dir = Path(self.config["log_directory"])
        self.idle_interval = self.config["idle_interval_minutes"] * 60  # seconds
        self.active_interval = self.config["active_interval_minutes"] * 60  # seconds
        self.retention_days = self.config["retention_days"]

        self.collector = StatsCollector()
        self.detector = BridgeDetector(
            threshold=self.config["bridge_threshold_packets"]
        )

        self._running = False

    def _ensure_log_dir(self) -> None:
        """Create log directory if it doesn't exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self) -> Path:
        """Get today's log file path."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"bridge_{today}.jsonl"

    def _write_snapshot(self, snapshot_dict: dict) -> None:
        """Append a snapshot to today's log file."""
        self._ensure_log_dir()
        log_path = self._get_log_path()
        with open(log_path, "a") as f:
            f.write(json.dumps(snapshot_dict) + "\n")

    def _cleanup_old_logs(self) -> None:
        """Remove log files older than retention_days."""
        if not self.log_dir.exists():
            return

        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob("bridge_*.jsonl"):
            try:
                # Extract date from filename: bridge_YYYY-MM-DD.jsonl
                date_str = log_file.stem.replace("bridge_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    log_file.unlink()
                    print(f"  Cleaned up old log: {log_file.name}")
            except (ValueError, OSError):
                pass

    def run(self) -> None:
        """Start the logging loop (blocking).

        Runs until interrupted (Ctrl+C or SIGTERM).
        """
        self._running = True
        print(f"Bridge logger started. Writing to {self.log_dir}/")
        print(f"  Idle interval:   {self.config['idle_interval_minutes']} min")
        print(f"  Active interval: {self.config['active_interval_minutes']} min")
        print(f"  Threshold:       {self.config['bridge_threshold_packets']} packets")
        print(f"  Retention:       {self.retention_days} days")
        print("")

        # Initial cleanup
        self._cleanup_old_logs()

        last_cleanup = time.time()

        try:
            while self._running:
                # Check bridge status
                bridge_active = self.detector.is_bridge_active()

                # Collect stats
                snapshot = self.collector.collect(bridge_active=bridge_active)
                snapshot_dict = snapshot.to_dict()

                # Write to log
                self._write_snapshot(snapshot_dict)

                status = "ACTIVE" if bridge_active else "idle"
                interval = self.active_interval if bridge_active else self.idle_interval
                print(
                    f"  [{snapshot.timestamp}] Bridge: {status} | "
                    f"CPU: {snapshot.cpu_percent}% | "
                    f"Temp: {snapshot.cpu_temp_c}°C | "
                    f"Next in {interval}s"
                )

                # Periodic cleanup (once per hour)
                if time.time() - last_cleanup > 3600:
                    self._cleanup_old_logs()
                    last_cleanup = time.time()

                # Wait for next interval
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nLogger stopped.")
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal the logger to stop."""
        self._running = False
