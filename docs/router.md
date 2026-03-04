# Router Configuration (ASUS BQ16 Pro)

This page covers the router-side settings needed to use the Raspberry Pi bridge as a secondary WAN. The examples below use an **ASUS BQ16 Pro** running firmware **3.0.0.6.102_36998**, but the concepts apply to any router with Dual-WAN failover support.

---

## Dual WAN Settings

- **Enable Dual WAN:** ON
- **Primary WAN:** Your normal ISP port
- **Secondary WAN:** Ethernet LAN (choose port) → cable to Pi `eth0`
- **Dual WAN Mode:** Fail Over
- **Allow failback:** OFF _(keep disabled during initial testing; enable after the setup is stable — see [Failback Guidance](#failback-guidance) below)_

---

## Auto Network Detection (WAN Health Checks)

These settings control how quickly the router detects a WAN outage and triggers failover.

- **Detect Interval:** `5 s`
- **Failover / Failback Trigger:** `3` fails / `6` passes
- **Network Monitoring:** DNS Query + Ping
- **Resolve Hostname:** `one.one.one.one`
- **Ping Target:** `8.8.4.4`

!!! note "Why use alternate monitoring IPs?"
Using `one.one.one.one` and `8.8.4.4` instead of `1.1.1.1` and `8.8.8.8` ensures the router's health-check traffic does not get confused with standard client DNS traffic heading to your primary resolvers.

---

## Secondary WAN IP Settings

These must match the static IP subnet configured on the Pi's `eth0` interface (see [Raspberry Pi Configuration](config.md#assign-ips-mtu-networkmanager)).

- **WAN Connection Type:** Static IP
- **IP / Mask:** `192.168.100.10` / `255.255.255.0`
- **Gateway:** `192.168.100.1`
- **DNS:** `1.1.1.1`, `8.8.8.8`
- **Enable NAT:** Yes

---

## LAN Port Stability

- **Jumbo Frame / EEE / Link Aggregation:** Disabled

!!! warning "Energy Efficient Ethernet (EEE)"
Disabling these settings prevents link renegotiation and energy-save flaps that cause the secondary WAN to unexpectedly drop.

---

## Failback Guidance

Once your failover setup is working reliably:

1. **Run for at least 24–48 hours** with `Allow failback` set to **OFF**, simulating a few outages to confirm the secondary WAN is stable.
2. **Enable failback** by setting `Allow failback` to **ON** in the Dual WAN settings.
3. After enabling failback, unplug the primary WAN, wait for failover, then re-plug it. The router should automatically switch back to the primary WAN within 30–60 seconds (controlled by the failback trigger count × detect interval).

!!! tip "Monitoring failback"
Watch the router's WAN status page during the test. If failback does not trigger, verify that the primary WAN link is fully up and that the health-check targets are reachable through it.
