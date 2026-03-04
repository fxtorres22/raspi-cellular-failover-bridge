"""Adaptive JSON logger with daily file rotation.

Writes system snapshots to daily JSON Lines files and automatically
cleans up files older than the configured retention period.

Polls bridge status frequently for responsive detection, but only
writes log entries at a cadence that depends on bridge state.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from bridge_monitor.bridge_detect import BridgeDetector
from bridge_monitor.config import load_config
from bridge_monitor.stats import StatsCollector


class BridgeLogger:
    """Adaptive logger that polls frequently but writes at different cadences.

    - Polls every ``poll_interval_seconds`` to keep the sliding-window
      bridge detector fed with fresh samples.
    - Idle mode: writes every ``idle_write_interval_minutes``
    - Active mode: writes every ``active_write_interval_minutes``
    - On idle→active transition: writes immediately
    - Daily rotation: one file per day (bridge_YYYY-MM-DD.jsonl)
    - Auto-cleanup: removes files older than ``retention_days``
    """

    def __init__(self, config: dict | None = None):
        """Initialize the logger.

        Args:
            config: Configuration dict. Loaded from file if None.
        """
        self.config = config or load_config()
        self.log_dir = Path(self.config["log_directory"])
        self.poll_interval = self.config["poll_interval_seconds"]
        self.idle_write_interval = self.config["idle_write_interval_minutes"] * 60
        self.active_write_interval = self.config["active_write_interval_minutes"] * 60
        self.retention_days = self.config["retention_days"]

        self.collector = StatsCollector()
        self.detector = BridgeDetector(
            threshold=self.config["bridge_threshold_packets"],
            window_size=self.config["bridge_window_size"],
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

        Polls bridge status every ``poll_interval_seconds`` to keep the
        sliding-window detector responsive.  Only collects full system
        stats and writes a snapshot when the write interval has elapsed
        or when a state transition occurs.

        Runs until interrupted (Ctrl+C or SIGTERM).
        """
        self._running = True
        print(f"Bridge logger started. Writing to {self.log_dir}/")
        print(f"  Poll interval:         {self.config['poll_interval_seconds']}s")
        print(
            f"  Idle write interval:   "
            f"{self.config['idle_write_interval_minutes']} min"
        )
        print(
            f"  Active write interval: "
            f"{self.config['active_write_interval_minutes']} min"
        )
        print(f"  Threshold:             {self.config['bridge_threshold_packets']} pkt/min")
        print(f"  Window size:           {self.config['bridge_window_size']} samples")
        print(f"  Retention:             {self.retention_days} days")
        print("")

        # Initial cleanup
        self._cleanup_old_logs()

        last_cleanup = time.time()
        last_write = 0.0  # force an initial write on first tick
        prev_active = False

        try:
            while self._running:
                # 1. Poll bridge status (keeps the sliding window fed)
                bridge_active = self.detector.is_bridge_active()
                now = time.time()

                # 2. Determine if we should write a snapshot
                became_active = bridge_active and not prev_active
                write_interval = (
                    self.active_write_interval
                    if bridge_active
                    else self.idle_write_interval
                )
                interval_elapsed = (now - last_write) >= write_interval

                should_write = became_active or interval_elapsed

                if should_write:
                    snapshot = self.collector.collect(bridge_active=bridge_active)
                    snapshot_dict = snapshot.to_dict()
                    self._write_snapshot(snapshot_dict)
                    last_write = now

                    status = "ACTIVE" if bridge_active else "idle"
                    reason = (
                        "(transition)"
                        if became_active
                        else f"(next in {write_interval}s)"
                    )
                    print(
                        f"  [{snapshot.timestamp}] Bridge: {status} | "
                        f"CPU: {snapshot.cpu_percent}% | "
                        f"Temp: {snapshot.cpu_temp_c}°C | "
                        f"WRITE {reason}"
                    )
                else:
                    status = "ACTIVE" if bridge_active else "idle"
                    print(
                        f"  [{datetime.now().isoformat()}] Bridge: {status} | "
                        f"poll (write in "
                        f"{max(0, int(write_interval - (now - last_write)))}s)"
                    )

                prev_active = bridge_active

                # Periodic cleanup (once per hour)
                if now - last_cleanup > 3600:
                    self._cleanup_old_logs()
                    last_cleanup = now

                # 3. Sleep until next poll
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\nLogger stopped.")
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal the logger to stop."""
        self._running = False
