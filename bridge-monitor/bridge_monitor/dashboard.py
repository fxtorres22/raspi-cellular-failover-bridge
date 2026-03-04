"""Curses-based TUI dashboard for live bridge monitoring.

Displays CPU temp, CPU/RAM usage, network I/O per interface,
bridge status, and uptime in a continuously-updating terminal view.
"""

import curses
import signal
import sys
import time

from bridge_monitor.bridge_detect import BridgeDetector
from bridge_monitor.config import load_config
from bridge_monitor.stats import StatsCollector


def format_bytes(b: float) -> str:
    """Format byte count to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(b) < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"


def format_rate(bps: float) -> str:
    """Format bytes/sec to human-readable rate."""
    if bps < 0:
        bps = 0
    return f"{format_bytes(bps)}/s"


def format_uptime(seconds: float) -> str:
    """Format seconds to days/hours/minutes/seconds."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def draw_bar(width: int, percentage: float) -> str:
    """Draw a text-based progress bar."""
    filled = int(width * percentage / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def run_dashboard(config: dict | None = None) -> None:
    """Launch the curses-based live monitoring dashboard.

    Args:
        config: Configuration dict. Loaded from file if None.
    """
    cfg = config or load_config()
    collector = StatsCollector()
    detector = BridgeDetector(threshold=cfg["bridge_threshold_packets"])

    def _dashboard(stdscr: curses.window) -> None:
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input
        stdscr.timeout(2000)  # Refresh every 2 seconds

        # Define color pairs
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)   # OK / active
            curses.init_pair(2, curses.COLOR_RED, -1)      # Warning / hot
            curses.init_pair(3, curses.COLOR_CYAN, -1)     # Headers
            curses.init_pair(4, curses.COLOR_YELLOW, -1)   # Labels
            curses.init_pair(5, curses.COLOR_WHITE, -1)    # Normal
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # Bridge active

        # Clear entire screen and scroll buffer on first draw
        stdscr.clear()
        stdscr.refresh()

        while True:
            try:
                # Check for quit key
                key = stdscr.getch()
                if key in (ord("q"), ord("Q"), 27):  # q, Q, or ESC
                    break

                # Collect data
                bridge_active = detector.is_bridge_active()
                snapshot = collector.collect(bridge_active=bridge_active)

                # Clear and redraw
                stdscr.erase()
                height, width = stdscr.getmaxyx()

                # Minimum terminal size check
                if height < 20 or width < 60:
                    stdscr.addstr(0, 0, "Terminal too small! Need 60x20 minimum.")
                    stdscr.refresh()
                    continue

                row = 0

                # ── Title bar ────────────────────────────────────────────
                title = " RASPI BRIDGE MONITOR "
                stdscr.addstr(row, 0, "=" * width, curses.color_pair(3))
                center = max(0, (width - len(title)) // 2)
                stdscr.addstr(row, center, title, curses.color_pair(3) | curses.A_BOLD)
                row += 1
                stdscr.addstr(row, 0, "=" * width, curses.color_pair(3))
                row += 2

                # ── Bridge status ────────────────────────────────────────
                if bridge_active:
                    status_text = "  ● BRIDGE ACTIVE — Forwarding traffic"
                    status_color = curses.color_pair(6) | curses.A_BOLD | curses.A_BLINK
                else:
                    status_text = "  ○ Bridge idle — Standing by"
                    status_color = curses.color_pair(5)
                stdscr.addstr(row, 0, status_text, status_color)
                row += 2

                # ── System metrics ───────────────────────────────────────
                stdscr.addstr(row, 0, "  SYSTEM", curses.color_pair(3) | curses.A_BOLD)
                row += 1
                stdscr.addstr(row, 0, "  " + "─" * (width - 4), curses.color_pair(3))
                row += 1

                # CPU Temperature
                temp = snapshot.cpu_temp_c
                temp_color = curses.color_pair(2) if temp > 70 else curses.color_pair(1)
                stdscr.addstr(row, 2, "  CPU Temp:   ", curses.color_pair(4))
                stdscr.addstr(f"{temp:.1f}°C", temp_color)
                if temp > 80:
                    stdscr.addstr(" ⚠ HOT!", curses.color_pair(2) | curses.A_BOLD)
                row += 1

                # CPU Usage
                cpu_pct = snapshot.cpu_percent
                bar_width = min(30, width - 40)
                stdscr.addstr(row, 2, "  CPU Usage:  ", curses.color_pair(4))
                stdscr.addstr(f"{cpu_pct:5.1f}%  ", curses.color_pair(5))
                stdscr.addstr(draw_bar(bar_width, cpu_pct), curses.color_pair(1))
                row += 1

                # RAM Usage
                ram_pct = snapshot.ram_percent
                stdscr.addstr(row, 2, "  RAM Usage:  ", curses.color_pair(4))
                stdscr.addstr(
                    f"{snapshot.ram_used_mb:.0f}/{snapshot.ram_total_mb:.0f} MB "
                    f"({ram_pct:.1f}%)  ",
                    curses.color_pair(5),
                )
                stdscr.addstr(draw_bar(bar_width, ram_pct), curses.color_pair(1))
                row += 1

                # Uptime
                stdscr.addstr(row, 2, "  Uptime:     ", curses.color_pair(4))
                stdscr.addstr(
                    format_uptime(snapshot.uptime_seconds), curses.color_pair(5)
                )
                row += 2

                # ── Network I/O ──────────────────────────────────────────
                stdscr.addstr(
                    row, 0, "  NETWORK I/O", curses.color_pair(3) | curses.A_BOLD
                )
                row += 1
                stdscr.addstr(row, 0, "  " + "─" * (width - 4), curses.color_pair(3))
                row += 1

                # Header
                stdscr.addstr(
                    row,
                    2,
                    f"  {'Interface':<12} {'RX Total':>12} {'TX Total':>12}"
                    f" {'RX Rate':>12} {'TX Rate':>12}",
                    curses.color_pair(4) | curses.A_BOLD,
                )
                row += 1

                for iface_name, ns in snapshot.network.items():
                    label = iface_name
                    if iface_name == "eth0":
                        label += " (LAN)"
                    elif iface_name == "eth1":
                        label += " (WAN)"

                    stdscr.addstr(
                        row,
                        2,
                        f"  {label:<12} "
                        f"{format_bytes(ns.bytes_recv):>12} "
                        f"{format_bytes(ns.bytes_sent):>12} "
                        f"{format_rate(ns.recv_rate):>12} "
                        f"{format_rate(ns.send_rate):>12}",
                        curses.color_pair(5),
                    )
                    row += 1

                row += 1

                # ── Footer ──────────────────────────────────────────────
                stdscr.addstr(row, 0, "  " + "─" * (width - 4), curses.color_pair(3))
                row += 1
                stdscr.addstr(
                    row,
                    2,
                    "  Press 'q' to quit  |  Refreshes every 2s",
                    curses.color_pair(5),
                )

                stdscr.refresh()

            except curses.error:
                pass  # Ignore drawing errors on terminal resize

    try:
        curses.wrapper(_dashboard)
    except KeyboardInterrupt:
        pass
