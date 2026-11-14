"""Process-level guard that refuses any non-loopback network connection.

Installed at CLI start, before the model libraries are imported. It covers
everything that goes through Python's ``socket`` module (HTTP clients, DNS
lookups via ``getaddrinfo``). Unix-domain sockets and loopback stay allowed.
"""

from __future__ import annotations

import ipaddress
import socket

_LOCAL_NAMES = {None, "", "localhost", "127.0.0.1", "::1"}
_installed = False


class NetworkBlockedError(OSError):
    pass


def _is_loopback(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode(errors="replace")
    if host in _LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


def _check(sock: socket.socket, address) -> None:
    if sock.family == getattr(socket, "AF_UNIX", None):
        return
    host = address[0] if isinstance(address, tuple) else address
    if not _is_loopback(host):
        raise NetworkBlockedError(f"hand2md: outbound network access blocked (attempted {host!r})")


def install() -> None:
    global _installed
    if _installed:
        return

    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex
    orig_sendto = socket.socket.sendto
    orig_getaddrinfo = socket.getaddrinfo

    def connect(self, address):
        _check(self, address)
        return orig_connect(self, address)

    def connect_ex(self, address):
        _check(self, address)
        return orig_connect_ex(self, address)

    def sendto(self, data, *args):
        _check(self, args[-1])
        return orig_sendto(self, data, *args)

    def getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host):
            raise NetworkBlockedError(f"hand2md: DNS lookup blocked (attempted {host!r})")
        return orig_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.socket.sendto = sendto
    socket.getaddrinfo = getaddrinfo
    _installed = True
