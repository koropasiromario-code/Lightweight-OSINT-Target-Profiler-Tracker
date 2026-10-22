"""Safe, bounded metadata collection for explicitly allowlisted public websites."""
import hashlib
import ipaddress
import os
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

DEFAULT_ALLOWED_HOSTS = {"example.com", "www.example.com"}
ALLOWED_HOSTS = {
    host.strip().lower().rstrip(".")
    for host in os.getenv("OSINT_ALLOWED_HOSTS", ",".join(sorted(DEFAULT_ALLOWED_HOSTS))).split(",")
    if host.strip()
}
MAX_RESPONSE_BYTES = max(1024, int(os.getenv("OSINT_MAX_RESPONSE_BYTES", "1000000")))
TIMEOUT_SECONDS = max(1, int(os.getenv("OSINT_TIMEOUT_SECONDS", "8")))
USER_AGENT = "LightweightOSINT-Research/1.1"


class TargetValidationError(ValueError):
    """Target does not satisfy the application's safety policy."""


class CollectionError(RuntimeError):
    """A network or response processing error safe to show to the user."""


def validate_target(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise TargetValidationError("Masukkan URL HTTPS yang valid.")
    raw = url.strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise TargetValidationError("Hanya URL HTTPS yang diperbolehkan.")
    if parsed.username or parsed.password:
        raise TargetValidationError("URL yang berisi kredensial tidak diperbolehkan.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise TargetValidationError("Port URL tidak valid.") from exc
    if port not in (None, 443):
        raise TargetValidationError("Hanya port HTTPS standar (443) yang diperbolehkan.")

    host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise TargetValidationError(
            "Host tidak ada dalam OSINT_ALLOWED_HOSTS. Tambahkan hanya domain yang Anda miliki "
            "atau yang secara eksplisit diizinkan."
        )
    if parsed.fragment:
        # Fragments are not sent to the server and are excluded from the canonical target.
        pass

    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise TargetValidationError("Domain tidak dapat di-resolve.") from exc
    if not answers:
        raise TargetValidationError("Domain tidak memiliki alamat IP yang dapat digunakan.")
    for answer in answers:
        try:
            ip = ipaddress.ip_address(answer[4][0])
        except ValueError as exc:
            raise TargetValidationError("DNS mengembalikan alamat IP yang tidak valid.") from exc
        if not ip.is_global:
            raise TargetValidationError("Domain resolve ke alamat IP nonpublik; permintaan diblokir.")

    # Do not persist fragments. Query parameters are retained for the request but omitted from
    # the display/storage target to avoid accidentally recording tokens in reports.
    return urlunparse(("https", host, parsed.path or "/", "", parsed.query, ""))


def collect_metadata(url: str) -> dict:
    request_url = validate_target(url)
    parsed = urlparse(request_url)
    display_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    started = time.monotonic()

    try:
        with requests.get(
            request_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1"},
            timeout=(TIMEOUT_SECONDS, TIMEOUT_SECONDS),
            allow_redirects=False,
            stream=True,
        ) as response:
            content_type = response.headers.get("Content-Type", "")
            declared_length = response.headers.get("Content-Length")
            if declared_length:
                try:
                    if int(declared_length) > MAX_RESPONSE_BYTES:
                        raise CollectionError(f"Respons melebihi batas {MAX_RESPONSE_BYTES} byte.")
                except ValueError:
                    pass

            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=16384):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise CollectionError(f"Respons melebihi batas {MAX_RESPONSE_BYTES} byte.")
                chunks.append(chunk)
            body = b"".join(chunks)
            is_html = "html" in content_type.lower()
            html = body.decode(response.encoding or "utf-8", errors="replace") if is_html else ""
            soup = BeautifulSoup(html, "html.parser") if html else None

            def meta(name: str, attr: str = "name"):
                if soup is None:
                    return None
                tag = soup.find("meta", attrs={attr: name})
                value = tag.get("content", "").strip() if tag else ""
                return value or None

            title_tag = soup.find("title") if soup else None
            canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value) if soup else None
            canonical = canonical_tag.get("href", "").strip() if canonical_tag else None
            return {
                "target": display_url,
                "source_url": display_url,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "status_code": response.status_code,
                "title": title_tag.get_text(" ", strip=True) if title_tag else None,
                "description": meta("description"),
                "canonical_url": canonical,
                "og_title": meta("og:title", "property"),
                "robots_meta": meta("robots"),
                "html_language": (soup.html.get("lang") if soup and soup.html else None),
                "content_type": content_type or None,
                "server_header": response.headers.get("Server"),
                "response_bytes": len(body),
                "response_time_ms": round((time.monotonic() - started) * 1000, 2),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "is_html": is_html,
                "redirect_location": response.headers.get("Location") if response.is_redirect else None,
                "collector_version": "1.1",
            }
    except (TargetValidationError, CollectionError):
        raise
    except requests.Timeout as exc:
        raise CollectionError("Permintaan ke target melewati batas waktu.") from exc
    except requests.RequestException as exc:
        raise CollectionError("Koneksi ke target gagal. Periksa jaringan atau target.") from exc
