"""Netzwerk-Infos: aktuelle IPv4-Adressen je Interface (Ethernet/WLAN).

Nur Linux (Dev = WSL, Prod = Raspberry Pi 5) -- liest die IPv4 direkt per
ioctl(SIOCGIFADDR) aus dem Kernel, ohne externe Abhaengigkeit oder Subprozess.
Interfaces werden anhand des Namens klassifiziert (en*/eth* = Ethernet,
wl* = WLAN). Loopback und Interfaces ohne IPv4 werden ignoriert.
"""

import fcntl
import socket
import struct

_SIOCGIFADDR = 0x8915  # Linux-ioctl: IPv4-Adresse eines Interfaces


def _iface_ipv4(ifname: str) -> str | None:
    """IPv4 eines einzelnen Interfaces oder None (kein Link/keine Adresse)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = struct.pack("256s", ifname.encode()[:15])
        addr = fcntl.ioctl(s.fileno(), _SIOCGIFADDR, packed)
        return socket.inet_ntoa(addr[20:24])
    except OSError:
        return None  # Interface down / unkonfiguriert
    finally:
        s.close()


def _kind(ifname: str) -> str | None:
    """Interface-Name -> 'wifi' | 'eth' | None (uninteressant, z. B. lo/docker)."""
    if ifname.startswith("wl"):           # wlan0, wlp2s0 ...
        return "wifi"
    if ifname.startswith(("eth", "en")):  # eth0, end0 (Pi 5), enp3s0 ...
        return "eth"
    return None


def ipv4_addresses() -> dict[str, str]:
    """Aktuelle IPv4-Adressen als {'eth': ip, 'wifi': ip}.

    Nur vorhandene Adressen sind enthalten; fehlt ein Typ, fehlt der Key. Bei
    mehreren Interfaces gleichen Typs gewinnt das erste mit IPv4.
    """
    out: dict[str, str] = {}
    try:
        ifaces = socket.if_nameindex()
    except OSError:
        return out
    for _, name in ifaces:
        kind = _kind(name)
        if kind is None or kind in out:
            continue
        ip = _iface_ipv4(name)
        if ip:
            out[kind] = ip
    return out
