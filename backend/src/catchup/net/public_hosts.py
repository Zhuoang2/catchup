"""Public address rules for fetches and image URLs, without DNS lookups."""

import ipaddress
import re

from catchup.net.urls import split_url

NAT64_PREFIX = ipaddress.IPv6Network("64:ff9b::/96")


def is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address in NAT64_PREFIX:
        address = ipaddress.IPv4Address(address.packed[-4:])
    return not (
        not address.is_global or address.is_private or address.is_loopback
        or address.is_link_local or address.is_reserved or address.is_multicast
        or address.is_unspecified
    )


def is_public_url(url: str) -> bool:
    if "\\" in url:
        return False
    parts = split_url(url)
    if parts is None or parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    host = parts.hostname
    if "[" in parts.netloc:
        try:
            return is_public_address(ipaddress.IPv6Address(host))
        except ValueError:
            return False
    name = host.removesuffix(".")
    if not re.fullmatch(r"[a-z0-9_-]+(\.[a-z0-9_-]+)*", name):
        return False
    if re.fullmatch(r"[0-9]+|0x[0-9a-f]*", name.rsplit(".", 1)[-1]):
        try:
            return is_public_address(ipaddress.IPv4Address(name))
        except ValueError:
            return False
    local_suffixes = ("localhost", "localdomain", "local", "internal", "intranet",
                      "private", "corp", "home", "home.arpa", "lan")
    return "." in name and not any(
        name == suffix or name.endswith("." + suffix) for suffix in local_suffixes
    )
