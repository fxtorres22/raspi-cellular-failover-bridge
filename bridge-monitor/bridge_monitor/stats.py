"""System statistics collection for the Raspberry Pi bridge.

Gathers CPU temperature, CPU usage, RAM usage, and per-interface
network I/O counters.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore


@dataclass
class NetworkStats:
    """Network I/O counters for a single interface."""

    interface: str
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    # Rates (bytes/sec) — computed between snapshots
    send_rate: float = 0.0
    recv_rate: float = 0.0


@dataclass
class SystemSnapshot:
    """A point-in-time snapshot of all system metrics."""

    timestamp: str = ""
    cpu_temp_c: float = 0.0
    cpu_percent: float = 0.0
    ram_total_mb: float = 0.0
    ram_used_mb: float = 0.0
    ram_percent: float = 0.0
    uptime_seconds: float = 0.0
    network: dict = field(default_factory=dict)  # iface_name -> NetworkStats
    bridge_active: bool = False

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        return {
            "timestamp": self.timestamp,
            "cpu_temp_c": round(self.cpu_temp_c, 1),
            "cpu_percent": round(self.cpu_percent, 1),
            "ram_total_mb": round(self.ram_total_mb, 1),
            "ram_used_mb": round(self.ram_used_mb, 1),
            "ram_percent": round(self.ram_percent, 1),
            "uptime_seconds": round(self.uptime_seconds, 0),
            "bridge_active": self.bridge_active,
            "network": {
                name: {
                    "bytes_sent": ns.bytes_sent,
                    "bytes_recv": ns.bytes_recv,
                    "packets_sent": ns.packets_sent,
                    "packets_recv": ns.packets_recv,
                    "send_rate_bps": round(ns.send_rate, 1),
                    "recv_rate_bps": round(ns.recv_rate, 1),
                }
                for name, ns in self.network.items()
            },
        }


def get_cpu_temperature() -> float:
    """Read CPU temperature from thermal zone (Raspberry Pi)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except (FileNotFoundError, ValueError, PermissionError):
        # Fallback: try psutil sensors
        if psutil:
            try:
                temps = psutil.sensors_temperatures()
                if "cpu_thermal" in temps:
                    return temps["cpu_thermal"][0].current
            except Exception:
                pass
        return 0.0


class StatsCollector:
    """Collects system statistics with rate calculation between snapshots."""

    def __init__(self, interfaces: list[str] | None = None):
        """Initialize the collector.

        Args:
            interfaces: List of interface names to monitor.
                        Defaults to ["eth0", "eth1"].
        """
        self.interfaces = interfaces or ["eth0", "eth1"]
        self._prev_net: dict[str, NetworkStats] = {}
        self._prev_time: float = 0.0

    def collect(self, bridge_active: bool = False) -> SystemSnapshot:
        """Collect a full system snapshot.

        Args:
            bridge_active: Whether the bridge is currently active.

        Returns:
            A SystemSnapshot with all current metrics.
        """
        now = time.time()
        snapshot = SystemSnapshot(
            timestamp=datetime.now().isoformat(),
            bridge_active=bridge_active,
        )

        # CPU temperature
        snapshot.cpu_temp_c = get_cpu_temperature()

        # CPU & RAM
        if psutil:
            snapshot.cpu_percent = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            snapshot.ram_total_mb = mem.total / (1024 * 1024)
            snapshot.ram_used_mb = mem.used / (1024 * 1024)
            snapshot.ram_percent = mem.percent

            # Uptime
            snapshot.uptime_seconds = now - psutil.boot_time()

            # Network I/O
            net_io = psutil.net_io_counters(pernic=True)
            for iface in self.interfaces:
                if iface in net_io:
                    counters = net_io[iface]
                    ns = NetworkStats(
                        interface=iface,
                        bytes_sent=counters.bytes_sent,
                        bytes_recv=counters.bytes_recv,
                        packets_sent=counters.packets_sent,
                        packets_recv=counters.packets_recv,
                    )

                    # Calculate rates if we have a previous snapshot
                    if iface in self._prev_net and self._prev_time > 0:
                        elapsed = now - self._prev_time
                        if elapsed > 0:
                            prev = self._prev_net[iface]
                            ns.send_rate = (ns.bytes_sent - prev.bytes_sent) / elapsed
                            ns.recv_rate = (ns.bytes_recv - prev.bytes_recv) / elapsed

                    snapshot.network[iface] = ns

        # Store for next rate calculation
        self._prev_net = dict(snapshot.network)
        self._prev_time = now

        return snapshot
