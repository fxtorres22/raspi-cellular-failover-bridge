"""Bridge activity detection.

Determines if the Raspberry Pi bridge is actively forwarding traffic
by monitoring the iptables MASQUERADE packet counter.
"""

import re
import subprocess


class BridgeDetector:
    """Detects bridge activity by polling iptables MASQUERADE counters.

    The bridge is considered "active" when the packet count delta between
    two polls exceeds the configured threshold. This filters out the
    router's cold-standby health-check pings (typically a few packets).
    """

    def __init__(self, threshold: int = 50):
        """Initialize the detector.

        Args:
            threshold: Minimum packet delta to consider the bridge active.
                       Default 50 filters out cold-standby health checks.
        """
        self.threshold = threshold
        self._prev_packets: int | None = None

    def get_masquerade_packets(self) -> int:
        """Read the current MASQUERADE packet count from iptables.

        Returns:
            Current packet count, or 0 if unavailable.
        """
        try:
            result = subprocess.run(
                ["iptables", "-t", "nat", "-nvL", "POSTROUTING"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                if "MASQUERADE" in line:
                    # Format: "pkts bytes target prot ..."
                    # The first column is the packet count
                    parts = line.split()
                    if len(parts) >= 1:
                        # Remove K/M/G suffixes if present
                        count_str = parts[0].strip()
                        return self._parse_count(count_str)
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            pass
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

    def is_bridge_active(self) -> bool:
        """Check if the bridge is actively forwarding traffic.

        Compares the current MASQUERADE packet count against the previous
        reading. If the delta exceeds the threshold, the bridge is active.

        Returns:
            True if the bridge is actively forwarding significant traffic.
        """
        current = self.get_masquerade_packets()

        if self._prev_packets is None:
            self._prev_packets = current
            return False

        delta = current - self._prev_packets
        self._prev_packets = current

        return delta > self.threshold

    def get_packet_delta(self) -> int:
        """Get the raw packet delta without updating internal state.

        Useful for display purposes.
        """
        current = self.get_masquerade_packets()
        if self._prev_packets is None:
            return 0
        return current - self._prev_packets
