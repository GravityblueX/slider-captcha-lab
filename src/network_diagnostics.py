from __future__ import annotations

import json
import socket
import ssl
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class TLSDiagnostics:
    host: str
    port: int
    tls_version: str | None
    cipher: tuple[Any, ...] | None
    selected_alpn: str | None
    cert_subject: tuple[Any, ...] | None
    cert_issuer: tuple[Any, ...] | None
    not_before: str | None
    not_after: str | None
    error: str | None = None


def diagnose_tls(host: str = "example.com", port: int = 443, timeout: float = 8.0) -> TLSDiagnostics:
    """Report local TLS/ALPN observations for a host.

    This is a defensive/local diagnostics helper. It does not spoof TLS fingerprints
    or bypass access controls. Python's stdlib does not expose a full JA3/JA4
    fingerprint, but it can show negotiated TLS version, cipher, ALPN and cert data.
    """
    ctx = ssl.create_default_context()
    try:
        ctx.set_alpn_protocols(["h2", "http/1.1"])
    except NotImplementedError:
        pass
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as s:
                cert = s.getpeercert()
                return TLSDiagnostics(
                    host=host,
                    port=port,
                    tls_version=s.version(),
                    cipher=s.cipher(),
                    selected_alpn=s.selected_alpn_protocol(),
                    cert_subject=cert.get("subject"),
                    cert_issuer=cert.get("issuer"),
                    not_before=cert.get("notBefore"),
                    not_after=cert.get("notAfter"),
                )
    except Exception as e:
        return TLSDiagnostics(host, port, None, None, None, None, None, None, None, error=str(e))


def public_ip(timeout: float = 8.0) -> dict[str, Any]:
    """Get public IP context from public endpoints.

    This intentionally avoids reputation bypass logic. Reputation depends on the
    network/provider and should be evaluated by legitimate security tooling or
    authorized threat-intel services.
    """
    out: dict[str, Any] = {}
    endpoints = [
        ("ipify", "https://api.ipify.org?format=json"),
        ("ipapi", "https://ipapi.co/json/"),
    ]
    for name, url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SliderTrajectoryLab/diagnostics"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read().decode("utf-8", "replace")
                try:
                    out[name] = json.loads(data)
                except Exception:
                    out[name] = data[:500]
        except Exception as e:
            out[name] = {"error": str(e)}
    return out


def run(host: str = "example.com") -> dict[str, Any]:
    return {
        "tls_http2": asdict(diagnose_tls(host)),
        "public_ip_context": public_ip(),
        "notes": [
            "TLS/HTTP2 fingerprinting is mostly observable server-side; browsers do not expose raw JA3/JA4 to JavaScript.",
            "This tool reports local negotiated TLS/ALPN/certificate information only.",
            "IP reputation is not bypassed or modified; use authorized security services for reputation evaluation.",
        ],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Local TLS/HTTP2/IP diagnostics")
    parser.add_argument("--host", default="example.com", help="Host to test, default: example.com")
    args = parser.parse_args()
    print(json.dumps(run(args.host), ensure_ascii=False, indent=2, default=str))
