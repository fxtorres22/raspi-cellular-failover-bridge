#!/bin/bash
# iptables-rules.sh — NAT + security hardening for the cellular bridge
# Called by postinst and can be re-run manually anytime.

set -e

# Clear existing rules for a clean slate
iptables -F
iptables -t nat -F
iptables -t mangle -F

# NAT: rewrite LAN -> WAN source IPs
iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE

# Forwarding: allow router -> LTE, and return traffic back
iptables -A FORWARD -i eth0 -o eth1 -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# MSS clamping: adjust TCP MSS to path MTU (fixes cellular packet drops)
iptables -t mangle -A FORWARD -o eth1 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu

# Security hardening: drop unsolicited traffic hitting the Pi from LTE
iptables -A INPUT -i eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A INPUT -i eth1 -j DROP

# Save rules persistently
netfilter-persistent save
systemctl enable netfilter-persistent 2>/dev/null || true

echo "  iptables rules applied and saved."
