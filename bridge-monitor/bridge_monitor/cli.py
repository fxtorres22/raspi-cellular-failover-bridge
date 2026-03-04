"""CLI entry point for bridge-monitor.

Subcommands:
    dashboard   Launch the live TUI dashboard (default)
    log         Start the background logging loop
    config      Show current configuration
"""

import argparse
import json
import sys

from bridge_monitor import __version__
from bridge_monitor.config import load_config


def cmd_dashboard(args: argparse.Namespace) -> None:
    """Launch the live TUI dashboard."""
    config = load_config(args.config)
    from bridge_monitor.dashboard import run_dashboard

    run_dashboard(config)


def cmd_log(args: argparse.Namespace) -> None:
    """Start the adaptive logging loop."""
    config = load_config(args.config)
    from bridge_monitor.logger import BridgeLogger

    logger = BridgeLogger(config)
    logger.run()


def cmd_config(args: argparse.Namespace) -> None:
    """Display current configuration."""
    config = load_config(args.config)
    print(json.dumps(config, indent=2))


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="bridge-monitor",
        description="Raspberry Pi cellular failover bridge monitor",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="Path to config.json (default: /etc/bridge-monitor/config.json)",
    )

    subparsers = parser.add_subparsers(dest="command")

    # dashboard (default)
    sp_dash = subparsers.add_parser(
        "dashboard",
        help="Launch the live TUI dashboard",
    )
    sp_dash.set_defaults(func=cmd_dashboard)

    # log
    sp_log = subparsers.add_parser(
        "log",
        help="Start the adaptive logging daemon",
    )
    sp_log.set_defaults(func=cmd_log)

    # config
    sp_cfg = subparsers.add_parser(
        "config",
        help="Show current configuration",
    )
    sp_cfg.set_defaults(func=cmd_config)

    args = parser.parse_args()

    # Default to dashboard if no subcommand given
    if args.command is None:
        cmd_dashboard(args)
    else:
        args.func(args)
