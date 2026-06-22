from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from .utils import resolve_path

DEFAULT_TIMEOUT_SECONDS = 30


def tls_verify_value(network_settings: dict[str, Any] | None = None) -> bool | str:
    settings = network_settings or {}
    verify_tls = settings.get("verify_tls", True)
    if verify_tls is False:
        return False

    custom_ca_bundle = str(settings.get("custom_ca_bundle") or "").strip()
    if custom_ca_bundle:
        return str(resolve_path(custom_ca_bundle))
    return True


def proxy_values(network_settings: dict[str, Any] | None = None) -> dict[str, str]:
    settings = network_settings or {}
    proxies: dict[str, str] = {}
    http_proxy = str(settings.get("http_proxy") or "").strip()
    https_proxy = str(settings.get("https_proxy") or "").strip()
    no_proxy = str(settings.get("no_proxy") or "").strip()
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy
    if no_proxy:
        proxies["no_proxy"] = no_proxy
    return proxies


def request_timeout(network_settings: dict[str, Any] | None = None, default: int = DEFAULT_TIMEOUT_SECONDS) -> int:
    try:
        return int((network_settings or {}).get("request_timeout_seconds", default))
    except (TypeError, ValueError):
        return default


def configure_session(
    session: requests.Session,
    network_settings: dict[str, Any] | None = None,
    *,
    user_agent: str | None = None,
) -> requests.Session:
    session.trust_env = False
    if user_agent:
        session.headers["User-Agent"] = user_agent
    session.verify = tls_verify_value(network_settings)
    session.proxies.clear()
    proxies = proxy_values(network_settings)
    if proxies:
        session.proxies.update(proxies)
    return session


def make_session(
    network_settings: dict[str, Any] | None = None,
    *,
    user_agent: str | None = None,
) -> requests.Session:
    session = requests.Session()
    return configure_session(session, network_settings, user_agent=user_agent)


def describe_network_settings(network_settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = network_settings or {}
    custom_ca_bundle = str(settings.get("custom_ca_bundle") or "").strip()
    return {
        "verify_tls": settings.get("verify_tls", True) is not False,
        "custom_ca_bundle": custom_ca_bundle,
        "custom_ca_bundle_exists": bool(custom_ca_bundle and Path(resolve_path(custom_ca_bundle)).exists()),
        "http_proxy_configured": bool(str(settings.get("http_proxy") or "").strip()),
        "https_proxy_configured": bool(str(settings.get("https_proxy") or "").strip()),
        "no_proxy_configured": bool(str(settings.get("no_proxy") or "").strip()),
        "request_timeout_seconds": request_timeout(settings),
    }
