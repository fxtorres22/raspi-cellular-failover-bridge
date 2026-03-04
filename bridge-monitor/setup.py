from setuptools import setup, find_packages

setup(
    name="bridge-monitor",
    version="1.0.0",
    description="Raspberry Pi cellular failover bridge monitor and logger",
    author="fxtorres22",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "bridge-monitor=bridge_monitor.cli:main",
        ],
    },
)
