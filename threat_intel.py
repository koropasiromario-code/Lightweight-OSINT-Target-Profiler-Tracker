
"""Passive threat-intelligence lookups for authorized investigations."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlsplit

import requests

OTX_BASE = "https://otx.alienvault.com/api/v1"
TIMEOUT = 10
MAX_RESPONSE_BYTES = 1_000_000


def normalize_indicator(value: str) -> tuple[str, str]:
    """Return (type, normalized value); reject ambiguous inputs."""
    value = value.strip()

    if not value or len(value) > 253:
        raise ValueError("Indikator kosong atau terlalu panjang.")

    # Accept a bare domain, IP, or HTTP(S) URL.
    candidate = value
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Hanya URL HTTP/HTTPS yang didukung.")
        if parsed.username or parsed.password:
            raise ValueError("URL dengan kredensial tidak diizinkan.")
        candidate = parsed.hostname

    try:
        addr = ipaddress.ip_address(candidate)
        if not addr.is_global:
            raise ValueError("IP harus merupakan alamat publik.")
        return ("IPv4" if addr.version == 4 else "IPv6", str(addr))
    except ValueError as exc:
        # Distinguish invalid IP input from a legitimate domain.
        if "IP harus" in str(exc):
            raise

    domain = candidate.rstrip(".").lower()
    if len(domain) > 253 or "." not in domain:
        raise ValueError("Masukkan domain publik yang valid.")
    if not re.fullmatch(
        r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z]{2,63}",
        domain,
    ):
        raise ValueError("Format domain tidak valid.")

    # Reject names resolving only to local/private/reserved addresses.
    try:
        answers = socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)
        ips = {item[4][0].split("%")[0] for item in answers}
        if ips and not all(ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError(
                "Domain mengarah ke alamat nonpublik; kueri ditolak."
            )
    except socket.gaierror:
        # A domain can be absent from DNS and still have a reputation record.
        pass

    return "domain", domain


def lookup_otx(indicator: str, api_key: str) -> dict:
    """Look up a domain or public IP in AlienVault OTX."""
    kind, value = normalize_indicator(indicator)

    if not api_key:
        return {
            "source": "AlienVault OTX",
            "indicator": value,
            "status": "not_configured",
            "error": "OTX API key belum dikonfigurasi.",
        }

    path = "IPv4" if kind == "IPv4" else (
        "IPv6" if kind == "IPv6" else "domain"
    )
    url = f"{OTX_BASE}/indicators/{path}/{value}/general"

    try:
        response = requests.get(
            url,
            headers={"X-OTX-API-KEY": api_key},
            timeout=TIMEOUT,
            allow_redirects=False,
            stream=True,
        )
        if response.status_code != 200:
            return {
                "source": "AlienVault OTX",
                "indicator": value,
                "status": "unavailable",
                "http_status": response.status_code,
            }

        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                return {
                    "source": "AlienVault OTX",
                    "indicator": value,
                    "status": "rejected",
                    "error": "Respons melebihi batas ukuran.",
                }
            chunks.append(chunk)

        data = response.json() if not chunks else __import__("json").loads(
            b"".join(chunks).decode("utf-8")
        )
        pulse_info = data.get("pulse_info") or {}
        pulses = pulse_info.get("pulses") or []

        return {
            "source": "AlienVault OTX",
            "indicator": value,
            "status": "ok",
            "pulse_count": pulse_info.get("count", len(pulses)),
            "pulses": [
                {
                    "name": str(p.get("name", ""))[:200],
                    "created": p.get("created"),
                    "modified": p.get("modified"),
                    "tags": p.get("tags", [])[:20],
                    "references": p.get("references", [])[:10],
                }
                for p in pulses[:20]
            ],
            "fetched_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }
    except (requests.RequestException, ValueError, KeyError) as exc:
        return {
            "source": "AlienVault OTX",
            "indicator": value,
            "status": "error",
            "error": type(exc).__name__,
        }
