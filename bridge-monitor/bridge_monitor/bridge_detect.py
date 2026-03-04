"""Bridge activity detection.

Determines if the Raspberry Pi bridge is actively forwarding traffic
by monitoring the iptables MASQUERADE packet counter with a sliding
window average for smooth, self-tuning detection.
"""

import os
import subprocess
import time
from collections import deque


class BridgeDetector:
    """Detects bridge activity using a sliding window of packet rates.

    Keeps the last N rate samples (packets/min) and compares their
    average against a threshold. This naturally handles bursty traffic:
    - Heavy traffic fills the window → takes longer to decay → stays active
    - Light traffic that stops → window clears quickly → goes idle sooner
    - No arbitrary cooldown needed

    A minimum hold time (default 30s) prevents single-sample flicker.
    """

    def __init__(
        self,
        threshold: int = 10,
        cooldown_seconds: int = 30,
        window_size: int = 10,
    ):
        """Initialize the detector.

        Args:
            threshold: Minimum average packets/minute across the window
                       to consider the bridge active. Default 10.
            cooldown_seconds: Minimum seconds to stay active after first
                              detection, as a safety floor. Default 30.
            window_size: Number of rate samples to average. Default 10.
                         At dashboard's ~2.5s poll rate → ~25s smoothing.
                         At logger's 1-min active rate → ~10 min smoothing.
        """
        self.threshold_per_min = threshold
        self.cooldown_seconds = cooldown_seconds
        self.window_size = window_size

        self._prev_packets: int | None = None
        self._prev_time: float = 0.0
        self._rate_window: deque[float] = deque(maxlen=window_size)
        self._active_since: float = 0.0
        self._is_active: bool = False

    def get_masquerade_packets(self) -> int:
        """Read the current MASQUERADE packet count from iptables.

        Tries without sudo first (works when running as root or via
        systemd service), then falls back to sudo (for interactive use).

        Returns:
            Current packet count, or 0 if unavailable.
        """
        commands = [
            ["iptables", "-t", "nat", "-nvL", "POSTROUTING"],
            ["sudo", "-n", "iptables", "-t", "nat", "-nvL", "POSTROUTING"],
        ]

        if os.geteuid() == 0:
            commands = [commands[0]]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    continue
                for line in result.stdout.splitlines():
                    if "MASQUERADE" in line:
                        parts = line.split()
                        if len(parts) >= 1:
                            count_str = parts[0].strip()
                            return self._parse_count(count_str)
            except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
                continue
        return 0

    @staticmethod
    def _parse_count(count_str: str) -> int:
        """Parse iptables counter values that may have K/M/G suffixes."""
        count_str = count_str.strip()
        multipliers = {"K": 1_000, "M": 1_000_000, "G": 1_000_000_000}

        for suffix, mult in multipliers.items():
            if count_str.upper().endswith(suffix):
                try:
                    return int(float(count_str[:-1]) * mult)
                except ValueError:
                    return 0

        try:
            return int(count_str)
        except ValueError:
            return 0

    def _get_window_average(self) -> float:
        """Get the average rate across the sliding window."""
        if not self._rate_window:
            return 0.0
        return sum(self._rate_window) / len(self._rate_window)

    def is_bridge_active(self) -> bool:
        """Check if the bridge is actively forwarding traffic.

        Computes instantaneous rate, adds it to the sliding window,
        then checks if the window average exceeds the threshold.

        The sliding window naturally smooths out bursty traffic:
        - A burst of traffic adds high values → average stays high
        - When traffic stops, zeros push the average down gradually
        - Heavy sustained traffic has more inertia than light traffic

        Returns:
            True if the bridge is actively forwarding significant traffic.
        """
        current = self.get_masquerade_packets()
        now = time.time()

        if self._prev_packets is None:
            self._prev_packets = current
            self._prev_time = now
            return False

        elapsed = now - self._prev_time
        delta = current - self._prev_packets

        self._prev_packets = current
        self._prev_time = now

        if elapsed <= 0:
            return self._is_active

        # Compute instantaneous rate and add to window
        rate_per_min = (delta / elapsed) * 60
        self._rate_window.append(rate_per_min)

        # Check window average against threshold
        avg_rate = self._get_window_average()
        traffic_detected = avg_rate > self.threshold_per_min

        if traffic_detected:
            if not self._is_active:
                self._active_since = now
            self._is_active = True
        elif self._is_active:
            # Only go idle if minimum hold time has passed
            if (now - self._active_since) >= self.cooldown_seconds:
                self._is_active = False

        return self._is_active

    def get_window_info(self) -> dict:
        """Get current window state for debugging/display.

        Returns:
            Dict with current rate, average, window contents, and status.
        """
        return {
            "window_size": len(self._rate_window),
            "window_max": self.window_size,
            "average_rate_per_min": round(self._get_window_average(), 1),
            "threshold_per_min": self.threshold_per_min,
            "is_active": self._is_active,
            "samples": [round(r, 1) for r in self._rate_window],
        }

    def get_packet_delta(self) -> int:
        """Get the raw packet delta without updating internal state."""
        current = self.get_masquerade_packets()
        if self._prev_packets is None:
            return 0
        return current - self._prev_packets
