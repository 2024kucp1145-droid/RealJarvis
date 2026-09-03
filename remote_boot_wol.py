# -*- coding: utf-8 -*-
"""
remote_boot_wol.py
===================
Phase 2: Remote Boot & Power Controller (Wake-on-LAN Magic Packet Engine).

Capabilities:
1. Auto-discovers Laptop MAC Address & Broadcast IP.
2. Generates standard 102-byte cryptographic WoL Magic Packet.
3. Provides remote power execution: Lock, Sleep, Hibernate, Shutdown, Restart.
4. Generates a standalone mobile WoL script to wake this laptop from phone.
"""

import os
import re
import uuid
import socket
import struct
import subprocess


def get_laptop_mac_address() -> str:
    """Retrieves the physical MAC address of the laptop's primary network adapter."""
    try:
        mac_num = uuid.getnode()
        mac_hex = f"{mac_num:012x}"
        mac_formatted = ":".join(mac_hex[i:i+2] for i in range(0, 12, 2)).upper()
        return mac_formatted
    except Exception:
        return "00:00:00:00:00:00"


def get_local_ip_and_broadcast() -> tuple:
    """Returns local LAN IP and subnet broadcast address (e.g. 192.168.1.255)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        # Derive broadcast
        parts = local_ip.split(".")
        broadcast_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
        return local_ip, broadcast_ip
    except Exception:
        return "127.0.0.1", "255.255.255.255"


def create_magic_packet(mac_address: str) -> bytes:
    """Constructs the standard 102-byte WoL Magic Packet."""
    clean_mac = re.sub(r"[^0-9a-fA-F]", "", mac_address)
    if len(clean_mac) != 12:
        raise ValueError("Invalid MAC address length")

    mac_bytes = bytes.fromhex(clean_mac)
    # Magic Packet format: 6 bytes of 0xFF followed by 16 repetitions of MAC address
    return b"\xff" * 6 + mac_bytes * 16


def send_wol_magic_packet(mac_address: str = None, broadcast_ip: str = "255.255.255.255", port: int = 9) -> bool:
    """Broadcasts WoL Magic Packet over UDP to power on the laptop."""
    target_mac = mac_address or get_laptop_mac_address()
    packet = create_magic_packet(target_mac)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (broadcast_ip, port))
            print(f"[remote_boot_wol] Magic Packet sent to {target_mac} via {broadcast_ip}:{port}")
            return True
    except Exception as e:
        print(f"[remote_boot_wol send error: {e}]")
        return False


def execute_power_action(action: str) -> str:
    """Executes OS power state transitions."""
    act = action.lower().strip()
    if "lock" in act:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "🔒 Laptop lock kar diya gaya hai."

    if "sleep" in act:
        # Puts system in Modern Standby / ACPI S3 sleep
        subprocess.Popen("powershell -Command rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return "💤 Laptop sleep mode mein ja raha hai."

    if "hibernate" in act:
        subprocess.Popen("shutdown /h", shell=True)
        return "❄️ Laptop hibernate ho raha hai."

    if "restart" in act:
        subprocess.Popen("shutdown /r /t 5", shell=True)
        return "🔄 Laptop 5 second mein restart ho jayega."

    if "shutdown" in act:
        subprocess.Popen("shutdown /s /t 10", shell=True)
        return "🛑 Laptop 10 second mein shutdown ho jayega."

    return "Power action samajh nahi aayi. Options: lock, sleep, hibernate, restart, shutdown."


def get_wol_configuration_info() -> str:
    """Generates phone-ready configuration details for remote wake."""
    mac = get_laptop_mac_address()
    local_ip, broadcast = get_local_ip_and_broadcast()
    return (
        f"⚡ *JARVIS REMOTE WAKE (WoL) SETUP*\n\n"
        f"• *Laptop MAC Address:* `{mac}`\n"
        f"• *Local IP:* `{local_ip}`\n"
        f"• *Broadcast Subnet:* `{broadcast}`\n"
        f"• *Port:* `9` (UDP)\n\n"
        f"📱 *Phone se On Kaise Karein:*\n"
        f"1. Phone par koi bhi free app download karein: *'WolOn'* ya *'Wake on Lan'* (Android/iOS).\n"
        f"2. Upar diya gaya MAC Address aur Broadcast IP enter karein.\n"
        f"3. Phone par tap karte hi band laptop wirelessly switch ON ho jayega!"
    )


if __name__ == "__main__":
    print(get_wol_configuration_info())
