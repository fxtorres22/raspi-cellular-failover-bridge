"""Configuration loader for bridge-monitor.

Reads /etc/bridge-monitor/config.json with sensible defaults.
"""

import json
import os

DEFAULT_CONFIG = {
    "poll_interval_seconds": 30,
    "idle_write_interval_minutes": 30,
    "active_write_interval_minutes": 1,
    "retention_days": 30,
    "bridge_threshold_packets": 10,
    "bridge_window_size": 10,
    "log_directory": "/var/log/bridge-monitor",
}

CONFIG_PATH = "/etc/bridge-monitor/config.json"


def load_config(path: str | None = None) -> dict:
    """Load configuration from JSON file, falling back to defaults.

    Args:
        path: Override path to config file (for testing).

    Returns:
        Merged configuration dictionary.
    """
    config = DEFAULT_CONFIG.copy()
    config_path = path or CONFIG_PATH

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
            # Only merge known keys
            for key in DEFAULT_CONFIG:
                if key in user_config:
                    config[key] = user_config[key]
        except (json.JSONDecodeError, PermissionError) as e:
            print(f"WARNING: Could not read config at {config_path}: {e}")
            print("         Using default configuration.")

    return config
