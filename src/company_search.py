from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote

import requests

from .network import make_session, request_timeout

_log = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; JobSearchBot/1.0)"
_TIMEOUT_SECONDS = 8
_HEAD_TIMEOUT_SECONDS = 5

_DDG_API_URL = "https://api.duckduckgo.com/"
_DDG_HTML_URL = "https://html.duckduckgo.com/html/"
_WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
_WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

_CAREER_SUFFIXES = (
    "/careers",
    "/jobs",
    "/en/careers",
    "/en-us/careers",
    "/global/en/careers",
    "/about/careers",
    "/work-with-us",
    "/join-us",
    "/we-are-hiring",
)

_LINKEDIN_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/company/([A-Za-z0-9\-_%]+)",
    re.IGNORECASE,
)

_CAREER_KW_RE = re.compile(
    r"\b(careers?|jobs?|join|hiring|work[\-\s]with[\-\s]us)\b",
    re.IGNORECASE,
)


def _make_session(network_settings: dict[str, Any] | None = None) -> requests.Session:
    session = make_session(network_settings, user_agent=_USER_AGENT)
    session.request_timeout_seconds = request_timeout(network_settings, default=_TIMEOUT_SECONDS)  # type: ignore[attr-defined]
    session.head_timeout_seconds = request_timeout(network_settings, default=_HEAD_TIMEOUT_SECONDS)  # type: ignore[attr-defined]
    return session


def _timeout(session: requests.Session) -> int:
    return int(getattr(session, "request_timeout_seconds", _TIMEOUT_SECONDS))


def _head_timeout(session: requests.Session) -> int:
    return int(getattr(session, "head_timeout_seconds", _HEAD_TIMEOUT_SECONDS))


# ---------------------------------------------------------------------------
# Source helpers
# ---------------------------------------------------------------------------


def _query_ddg_instant_answer(session: requests.Session, company_name: str) -> dict[str, Any] | None:
    try:
        resp = session.get(
            _DDG_API_URL,
            params={"q": company_name, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=_timeout(session),
        )
        resp.raise_for_status()
        data = resp.json()
        abstract_url: str = data.get("AbstractURL", "") or ""
        if "wikipedia.org" not in abstract_url:
            return None
        # Extract the Wikipedia article title from the URL path
        wiki_title = abstract_url.rstrip("/").split("/")[-1]
        heading: str = data.get("Heading") or data.get("AbstractTitle") or ""
        return {"wiki_title": wiki_title, "heading": heading}
    except Exception as exc:
        _log.debug("DDG Instant Answer failed for %r: %s", company_name, exc)
        return None


def _query_wikipedia_summary(session: requests.Session, wiki_title: str) -> dict[str, Any] | None:
    try:
        url = _WIKI_SUMMARY_URL.format(title=quote(wiki_title, safe=""))
        resp = session.get(url, timeout=_timeout(session))
        resp.raise_for_status()
        data = resp.json()
        if data.get("type") != "standard":
            return None
        entity_id: str = data.get("wikibase_item", "") or ""
        canonical: str = (data.get("titles") or {}).get("canonical") or data.get("title") or ""
        if not entity_id:
            return None
        return {"entity_id": entity_id, "canonical_name": canonical}
    except Exception as exc:
        _log.debug("Wikipedia summary failed for %r: %s", wiki_title, exc)
        return None


def _query_wikidata_claims(session: requests.Session, entity_id: str) -> dict[str, Any] | None:
    try:
        resp = session.get(
            _WIKIDATA_API_URL,
            params={"action": "wbgetentities", "ids": entity_id, "props": "claims", "format": "json"},
            timeout=_timeout(session),
        )
        resp.raise_for_status()
        data = resp.json()
        claims: dict = data.get("entities", {}).get(entity_id, {}).get("claims", {})

        result: dict[str, Any] = {}

        # P856 — official website
        try:
            result["website"] = claims["P856"][0]["mainsnak"]["datavalue"]["value"]
        except (KeyError, IndexError, TypeError):
            pass

        # P1128 — number of employees
        try:
            raw_amount: str = claims["P1128"][0]["mainsnak"]["datavalue"]["value"]["amount"]
            result["employee_count"] = int(float(raw_amount.lstrip("+")))
        except (KeyError, IndexError, TypeError, ValueError):
            pass

        # P452 — industry (entity reference; need label lookup)
        try:
            result["industry_entity_id"] = claims["P452"][0]["mainsnak"]["datavalue"]["value"]["id"]
        except (KeyError, IndexError, TypeError):
            pass

        # P4264 — LinkedIn organization ID (slug), e.g. "deloitte"
        try:
            result["linkedin_slug"] = claims["P4264"][0]["mainsnak"]["datavalue"]["value"]
        except (KeyError, IndexError, TypeError):
            pass

        return result if result else None
    except Exception as exc:
        _log.debug("Wikidata claims failed for %r: %s", entity_id, exc)
        return None


def _fetch_wikidata_label(session: requests.Session, entity_id: str) -> str | None:
    try:
        resp = session.get(
            _WIKIDATA_API_URL,
            params={
                "action": "wbgetentities",
                "ids": entity_id,
                "props": "labels",
                "languages": "en",
                "format": "json",
            },
            timeout=_timeout(session),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["entities"][entity_id]["labels"]["en"]["value"]
    except Exception as exc:
        _log.debug("Wikidata label failed for %r: %s", entity_id, exc)
        return None


def _scrape_ddg_linkedin(session: requests.Session, company_name: str) -> str | None:
    """Extract a LinkedIn company URL from DuckDuckGo HTML results — never visits linkedin.com."""
    try:
        resp = session.get(
            _DDG_HTML_URL,
            params={"q": f"{company_name} linkedin company"},
            timeout=_timeout(session),
        )
        if resp.status_code != 200:
            return None
        match = _LINKEDIN_RE.search(resp.text)
        if match:
            slug = match.group(1).rstrip("/")
            return f"https://www.linkedin.com/company/{slug}"
    except Exception as exc:
        _log.debug("DDG LinkedIn scrape failed for %r: %s", company_name, exc)
    return None


# ---------------------------------------------------------------------------
# Career-page helpers
# ---------------------------------------------------------------------------


def _probe_career_suffixes(session: requests.Session, base_url: str) -> str | None:
    for suffix in _CAREER_SUFFIXES:
        url = base_url + suffix
        try:
            r = session.head(url, timeout=_head_timeout(session), allow_redirects=True)
            if r.status_code < 400:
                return url
        except requests.RequestException as exc:
            _log.debug("Career suffix probe failed for %s: %s", url, exc)
            continue
    return None


def _search_career_ddg(session: requests.Session, company_name: str) -> str | None:
    try:
        resp = session.get(
            _DDG_API_URL,
            params={"q": f"{company_name} careers", "format": "json", "no_html": "1"},
            timeout=_timeout(session),
        )
        resp.raise_for_status()
        data = resp.json()
        for item in (data.get("Results") or []) + (data.get("RelatedTopics") or []):
            url: str = item.get("FirstURL", "") or ""
            if url and _CAREER_KW_RE.search(url):
                return url
    except Exception as exc:
        _log.debug("DDG career search failed for %r: %s", company_name, exc)
    return None


# ---------------------------------------------------------------------------
# Size-range helper
# ---------------------------------------------------------------------------


def _employees_to_size_range(count: int) -> str:
    if count < 10:
        return "1-9"
    if count < 50:
        return "10-49"
    if count < 200:
        return "50-199"
    if count < 500:
        return "200-499"
    if count < 1_000:
        return "500-999"
    if count < 5_000:
        return "1,000-4,999"
    if count < 10_000:
        return "5,000-9,999"
    return "10,000+"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_companies(
    sector: str,
    location: str,
    keywords: list[str] | None = None,
    network_settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    keywords = keywords or []

    # Determine best company name to search: skip URL-like first tokens
    company_name = ""
    for kw in keywords:
        if kw and not kw.startswith("http"):
            company_name = kw
            break
    if not company_name:
        company_name = sector or location
    if not company_name:
        return []

    result: dict[str, Any] = {}
    session = _make_session(network_settings)

    # Source 1 — DDG Instant Answer → Wikipedia title + heading
    wiki_title: str | None = None
    ddg = _query_ddg_instant_answer(session, company_name)
    if ddg:
        if ddg.get("heading"):
            result.setdefault("company_name", ddg["heading"])
        wiki_title = ddg.get("wiki_title")

    # Source 2 — Wikipedia REST → Wikidata entity ID
    entity_id: str | None = None
    if wiki_title:
        wiki = _query_wikipedia_summary(session, wiki_title)
        if wiki:
            entity_id = wiki.get("entity_id")
            if wiki.get("canonical_name"):
                result.setdefault("company_name", wiki["canonical_name"])

    # Source 3 — Wikidata → website, size, industry, LinkedIn slug
    wikidata_linkedin: str | None = None
    if entity_id:
        claims = _query_wikidata_claims(session, entity_id)
        if claims:
            if claims.get("website"):
                result["company_website"] = claims["website"]
            if claims.get("employee_count") is not None:
                result["company_size"] = _employees_to_size_range(claims["employee_count"])
            if claims.get("industry_entity_id"):
                label = _fetch_wikidata_label(session, claims["industry_entity_id"])
                if label:
                    result["company_industry"] = label
            if claims.get("linkedin_slug"):
                wikidata_linkedin = f"https://www.linkedin.com/company/{claims['linkedin_slug']}"

    # Source 4 — LinkedIn URL: prefer Wikidata P4264 slug; fall back to DDG HTML scrape
    if wikidata_linkedin:
        result["company_linkedin"] = wikidata_linkedin
    else:
        linkedin_url = _scrape_ddg_linkedin(session, company_name)
        if linkedin_url:
            result["company_linkedin"] = linkedin_url

    return [result] if result else []


def find_career_page(
    company_name: str,
    website: str | None = None,
    network_settings: dict[str, Any] | None = None,
) -> str | None:
    session = _make_session(network_settings)

    if website:
        base = website.rstrip("/")
        if not base.startswith("http"):
            base = "https://" + base
        found = _probe_career_suffixes(session, base)
        if found:
            return found

    return _search_career_ddg(session, company_name)


def save_company_result(company: dict[str, Any]) -> str:
    from .database import upsert_company

    return upsert_company(company)
