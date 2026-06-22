from __future__ import annotations

from src import company_search
from src.network import describe_network_settings, make_session, proxy_values, tls_verify_value


def test_tls_verification_enabled_by_default() -> None:
    session = company_search._make_session()

    assert session.verify is True


def test_tls_verification_uses_custom_ca_bundle() -> None:
    value = tls_verify_value({"verify_tls": True, "custom_ca_bundle": "config/corporate-ca.pem"})

    assert str(value).endswith("config\\corporate-ca.pem") or str(value).endswith("config/corporate-ca.pem")


def test_tls_verification_can_be_explicitly_disabled() -> None:
    session = make_session({"verify_tls": False})

    assert session.verify is False


def test_proxy_values_are_explicit() -> None:
    proxies = proxy_values(
        {
            "http_proxy": "http://proxy.local:8080",
            "https_proxy": "https://proxy.local:8443",
            "no_proxy": "localhost,127.0.0.1",
        }
    )

    assert proxies == {
        "http": "http://proxy.local:8080",
        "https": "https://proxy.local:8443",
        "no_proxy": "localhost,127.0.0.1",
    }


def test_make_session_ignores_ambient_proxy_env(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")

    session = make_session()

    assert session.trust_env is False
    assert session.proxies == {}


def test_network_description_redacts_presence_not_values() -> None:
    description = describe_network_settings(
        {
            "verify_tls": True,
            "custom_ca_bundle": "config/corporate-ca.pem",
            "http_proxy": "http://proxy.local:8080",
            "request_timeout_seconds": 12,
        }
    )

    assert description["verify_tls"] is True
    assert description["http_proxy_configured"] is True
    assert description["request_timeout_seconds"] == 12
