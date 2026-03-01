# Raspberry Pi Cellular Failover Bridge

Turn a **Raspberry Pi 4** and a **USB LTE modem** into a transparent network bridge so your router can fail over to a cellular connection when your primary ISP goes down.

---

## The Problem

Some routers (like the ASUS BQ16 Pro) support Dual-WAN failover but cannot detect a LTE modem connected via USB. Without a recognized WAN interface, the router has no way to use the cellular connection as a backup.

## The Solution

Place a Raspberry Pi between the USB modem and the router. The Pi:

1. Receives an IP from the LTE modem via DHCP.
2. Performs NAT (IP masquerading) on outbound traffic.
3. Presents a static IP to the router over Ethernet.

The router sees a normal Ethernet gateway on its secondary WAN port and can handle failover/failback automatically.

---

## Prerequisites

| Item               | Details                                                                |
| ------------------ | ---------------------------------------------------------------------- |
| **Raspberry Pi**   | Model 4 (or later) with Ethernet port. I used 2Gb model.               |
| **OS**             | Raspberry Pi OS (Bookworm or later recommended)                        |
| **USB LTE Modem**  | TCL LinkPort or any modem that presents as a USB Ethernet device       |
| **Ethernet Cable** | To connect the Pi's built-in Ethernet to the router                    |
| **Router**         | Any router with Dual-WAN / failover support (guide uses ASUS BQ16 Pro) |
| **Access**         | SSH or direct terminal access to the Pi                                |

!!! tip "Fresh Image Recommended"

    - Starting from a clean Raspberry Pi OS image avoids conflicts with existing network configurations.
    - I used Raspberry Pi OS Lite (64-bit) for Raspberry Pi 4.

---

## Guide Overview

This documentation is split into two sections:

1. **[Raspberry Pi Configuration](config.md)** — Set up the Pi as a NAT bridge: interface pinning, IP forwarding, iptables rules, and validation.
2. **[Router Configuration](router.md)** — Configure your router's Dual-WAN failover to use the Pi as the secondary WAN gateway.

Follow both sections in order to get a fully working cellular failover setup.
