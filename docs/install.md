# Quick Install (Debian Package)

Build and install the `raspi-bridge` package to automate all Raspberry Pi configuration in one step.

---

## Build the Package

On any machine with `dpkg-deb` available (Raspberry Pi, WSL, or Docker):

```bash title="Build the .deb"
cd raspi-bridge
bash build.sh
```

This produces `raspi-bridge_1.0.0_all.deb` in the project root.

---

## Install

Copy the `.deb` to your Raspberry Pi and install:

```bash title="Install the package"
sudo dpkg -i raspi-bridge_1.0.0_all.deb
sudo apt-get install -f   # resolve any missing dependencies
```

The installer automatically:

1. Enables IPv4 forwarding (`net.ipv4.ip_forward = 1`)
2. Creates NetworkManager profiles (`eth0-static`, `eth1-lte`)
3. Applies iptables NAT + security hardening rules
4. Reloads udev rules

---

## Run the Setup Wizard

After installing, run the interactive setup wizard to pin your interfaces by MAC address:

```bash title="Configure interface pinning"
sudo raspi-bridge-setup
```

The wizard will:

- **Auto-detect** all Ethernet interfaces and their MAC addresses
- Let you **select** which is LAN (→ `eth0`) and WAN (→ `eth1`)
- Allow you to **override** any MAC manually
- Optionally **disable Wi-Fi and Bluetooth** for power saving
- Write the udev rules to `/etc/udev/rules.d/70-persistent-net.rules`

??? tip "Re-running the wizard"
You can re-run `sudo raspi-bridge-setup` at any time to change your MAC assignments (e.g., if you swap modems).

---

## Verify

After a reboot, confirm everything is working:

```bash title="Verify configuration"
# Check IP forwarding
sysctl net.ipv4.ip_forward   # should return 1

# Check iptables NAT rules
sudo iptables -t nat -nvL POSTROUTING

# Check NetworkManager profiles
nmcli connection show

# Check interface names
ip link show
```

---

## Uninstall

```bash title="Remove the package"
sudo dpkg -r raspi-bridge
```

This cleanly reverts all configuration changes (removes NM profiles, flushes iptables, disables IP forwarding).

---

## Updating

To update `raspi-bridge` after pulling new changes from the repository:

```bash title="Update raspi-bridge"
# Pull the latest code
cd ~/raspi-cellular-failover-bridge
git pull origin main

# Rebuild the package
cd raspi-bridge
bash build.sh

# Reinstall (automatically re-runs postinst)
cd ..
sudo dpkg -i raspi-bridge_1.0.0_all.deb
```

---

## Docker ARM Testing

You can validate the package on Windows/WSL2 using Docker Desktop with ARM emulation:

```bash title="Test in ARM container"
docker run -it --rm --platform linux/arm64 \
  -v "$(pwd):/mnt" debian:bookworm bash

# Inside the container:
dpkg -i /mnt/raspi-bridge_1.0.0_all.deb
apt-get install -f
```
