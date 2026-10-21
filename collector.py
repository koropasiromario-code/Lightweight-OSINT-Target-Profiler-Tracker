import ipaddress
import socket
from urllib.parse import urlparse
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


ALLOWED_HOSTS = {"example.com", "www.example.com"}
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 8


class TargetValidationError(ValueError):
    """Input target tidak memenuhi kebijakan keamanan."""


def validate_target(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise TargetValidationError("Masukkan URL HTTPS yang valid.")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise TargetValidationError("Hanya URL HTTPS yang diperbolehkan.")
    if parsed.username or parsed.password:
        raise TargetValidationError("URL yang berisi kredensial tidak diperbolehkan.")

    host = parsed.hostname.lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise TargetValidationError(
            "Versi awal hanya mengizinkan example.com dan www.example.com. "
            "Ubah allowlist secara sadar untuk target yang Anda miliki atau diizinkan."
        )

    # Defense-in-depth: check every resolved address. Hosting production
    # should additionally enforce outbound network policy at firewall/proxy level.
    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise TargetValidationError("Domain tidak dapat di-resolve.") from exc

    for answer in answers:
        ip = ipaddress.ip_address(answer[4][0])
        if not ip.is_global:
            raise TargetValidationError("Domain resolve ke alamat IP nonpublik.")

    return f"https://{host}{parsed.path or '/'}" + (f"?{parsed.query}" if parsed.query else "")


def collect_metadata(url: str) -> dict:
    safe_url = validate_target(url)

    # Host is allowlisted and redirects are disabled to prevent redirect-based SSRF.
    response = requests.get(
        safe_url,
        headers={"User-Agent": "LightweightOSINT-Research/1.0"},
        timeout=TIMEOUT_SECONDS,
        allow_redirects=False,
        stream=True,
    )

    try:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            raise TargetValidationError("Target tidak mengembalikan konten HTML.")

        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=16384):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise TargetValidationError("Ukuran respons melebihi batas 1 MB.")
            chunks.append(chunk)
        body = b"".join(chunks)

        # Requests decodes text using response encoding where available.
        html = body.decode(response.encoding or "utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        description_tag = soup.find("meta", attrs={"name": "description"})

        return {
            "target": safe_url,
            "source_url": safe_url,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "status_code": response.status_code,
            "title": title_tag.get_text(" ", strip=True) if title_tag else None,
            "description": description_tag.get("content", "").strip() if description_tag else None,
            "content_type": content_type,
            "server_header": response.headers.get("Server"),
        }
    finally:
        response.close()
