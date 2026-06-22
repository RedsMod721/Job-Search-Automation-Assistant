from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from src import company_search

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resp(status: int = 200, data: Any = None, text: str = "") -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.raise_for_status = MagicMock(side_effect=None if status < 400 else requests.HTTPError(f"HTTP {status}"))
    r.json = MagicMock(return_value=data if data is not None else {})
    r.text = text if text else (json.dumps(data) if data else "")
    return r


def _mock_session(get_side_effect=None, head_side_effect=None) -> MagicMock:
    """Return a mock session whose .get() and .head() delegate to the given callables."""
    session = MagicMock()
    if get_side_effect is not None:
        session.get.side_effect = get_side_effect
    if head_side_effect is not None:
        session.head.side_effect = head_side_effect
    return session


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_DDG_DELOITTE = {
    "Heading": "Deloitte",
    "AbstractURL": "https://en.wikipedia.org/wiki/Deloitte",
    "AbstractTitle": "Deloitte",
    "Results": [],
    "RelatedTopics": [],
}

_WIKI_DELOITTE = {
    "type": "standard",
    "title": "Deloitte",
    "titles": {"canonical": "Deloitte"},
    "wikibase_item": "Q491756",
}

_WIKIDATA_CLAIMS = {
    "entities": {
        "Q491756": {
            "claims": {
                "P856": [{"mainsnak": {"datavalue": {"value": "https://www2.deloitte.com"}}}],
                "P1128": [{"mainsnak": {"datavalue": {"value": {"amount": "+415000"}}}}],
                "P452": [{"mainsnak": {"datavalue": {"value": {"id": "Q1048204"}}}}],
            }
        }
    }
}

_WIKIDATA_INDUSTRY_LABEL = {"entities": {"Q1048204": {"labels": {"en": {"value": "professional services"}}}}}

_DDG_HTML_WITH_LINKEDIN = '<a href="https://www.linkedin.com/company/deloitte">Deloitte LinkedIn</a>'


# ---------------------------------------------------------------------------
# Happy path: all four sources return data
# ---------------------------------------------------------------------------


def test_search_companies_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        params = kwargs.get("params", {})
        if "html.duckduckgo.com" in url:
            return _resp(200, text=_DDG_HTML_WITH_LINKEDIN)
        if "duckduckgo.com" in url:
            return _resp(200, _DDG_DELOITTE)
        if "wikipedia.org/api/rest_v1/page/summary" in url:
            return _resp(200, _WIKI_DELOITTE)
        if "wikidata.org" in url:
            ids = params.get("ids", "")
            if ids == "Q491756":
                return _resp(200, _WIKIDATA_CLAIMS)
            if ids == "Q1048204":
                return _resp(200, _WIKIDATA_INDUSTRY_LABEL)
        return _resp(404)

    monkeypatch.setattr(company_search, "_make_session", lambda network_settings=None: _mock_session(fake_get))

    results = company_search.search_companies("Professional Services", "New York", ["Deloitte"])

    assert len(results) == 1
    r = results[0]
    assert r["company_name"] == "Deloitte"
    assert r["company_website"] == "https://www2.deloitte.com"
    assert r["company_size"] == "10,000+"
    assert r["company_industry"] == "professional services"
    assert "linkedin.com/company/deloitte" in r["company_linkedin"]


# ---------------------------------------------------------------------------
# Source independence: DDG returns no Wikipedia link → LinkedIn still tried
# ---------------------------------------------------------------------------


def test_search_companies_ddg_fails_linkedin_still_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        if "html.duckduckgo.com" in url:
            return _resp(200, text=_DDG_HTML_WITH_LINKEDIN)
        if "duckduckgo.com" in url:
            return _resp(200, {"Heading": "", "AbstractURL": "", "Results": [], "RelatedTopics": []})
        return _resp(404)

    monkeypatch.setattr(company_search, "_make_session", lambda network_settings=None: _mock_session(fake_get))

    results = company_search.search_companies("", "", ["Deloitte"])

    assert len(results) == 1
    assert "linkedin.com/company/deloitte" in results[0]["company_linkedin"]


# ---------------------------------------------------------------------------
# Source independence: Wikidata fails → name + LinkedIn still returned
# ---------------------------------------------------------------------------


def test_search_companies_wikidata_fails_partial_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        if "html.duckduckgo.com" in url:
            return _resp(200, text=_DDG_HTML_WITH_LINKEDIN)
        if "duckduckgo.com" in url:
            return _resp(200, _DDG_DELOITTE)
        if "wikipedia.org/api/rest_v1" in url:
            return _resp(200, _WIKI_DELOITTE)
        if "wikidata.org" in url:
            return _resp(500)
        return _resp(404)

    monkeypatch.setattr(company_search, "_make_session", lambda network_settings=None: _mock_session(fake_get))

    results = company_search.search_companies("", "", ["Deloitte"])

    assert len(results) == 1
    r = results[0]
    assert r.get("company_name") == "Deloitte"
    assert "company_website" not in r
    assert "linkedin.com/company" in r.get("company_linkedin", "")


# ---------------------------------------------------------------------------
# Source independence: LinkedIn scrape 429 → no company_linkedin field
# ---------------------------------------------------------------------------


def test_search_companies_linkedin_scrape_429_no_field(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        params = kwargs.get("params", {})
        if "html.duckduckgo.com" in url:
            return _resp(429)
        if "duckduckgo.com" in url:
            return _resp(200, _DDG_DELOITTE)
        if "wikipedia.org" in url:
            return _resp(200, _WIKI_DELOITTE)
        if "wikidata.org" in url:
            ids = params.get("ids", "")
            if ids == "Q491756":
                return _resp(200, _WIKIDATA_CLAIMS)
            return _resp(200, _WIKIDATA_INDUSTRY_LABEL)
        return _resp(404)

    monkeypatch.setattr(company_search, "_make_session", lambda network_settings=None: _mock_session(fake_get))

    results = company_search.search_companies("", "", ["Deloitte"])

    assert len(results) == 1
    assert "company_linkedin" not in results[0]
    assert results[0].get("company_website") == "https://www2.deloitte.com"


# ---------------------------------------------------------------------------
# Guard: empty / None keywords
# ---------------------------------------------------------------------------


def test_search_companies_empty_keywords_returns_empty() -> None:
    assert company_search.search_companies("", "", []) == []


def test_search_companies_none_keywords_returns_empty() -> None:
    assert company_search.search_companies("", "", None) == []


def test_search_companies_all_empty_returns_empty() -> None:
    assert company_search.search_companies("", "", None) == []


# ---------------------------------------------------------------------------
# URL-like first keyword is skipped in favour of next non-URL keyword
# ---------------------------------------------------------------------------


def test_search_companies_skips_url_first_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    searched: list[str] = []

    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        params = kwargs.get("params", {})
        q = params.get("q", "")
        searched.append(q)
        return _resp(200, {"Heading": "", "AbstractURL": "", "Results": [], "RelatedTopics": []})

    monkeypatch.setattr(company_search, "_make_session", lambda network_settings=None: _mock_session(fake_get))

    company_search.search_companies("", "", ["https://deloitte.com", "Deloitte"])

    # The first query should use "Deloitte", not the URL
    assert any("Deloitte" in q and not q.startswith("http") for q in searched)


# ---------------------------------------------------------------------------
# _employees_to_size_range boundary values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "count, expected",
    [
        (0, "1-9"),
        (9, "1-9"),
        (10, "10-49"),
        (49, "10-49"),
        (50, "50-199"),
        (199, "50-199"),
        (200, "200-499"),
        (499, "200-499"),
        (500, "500-999"),
        (999, "500-999"),
        (1_000, "1,000-4,999"),
        (4_999, "1,000-4,999"),
        (5_000, "5,000-9,999"),
        (9_999, "5,000-9,999"),
        (10_000, "10,000+"),
        (415_000, "10,000+"),
    ],
)
def test_employees_to_size_range(count: int, expected: str) -> None:
    assert company_search._employees_to_size_range(count) == expected


# ---------------------------------------------------------------------------
# find_career_page: suffix probe returns on first 200
# ---------------------------------------------------------------------------


def test_find_career_page_suffix_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_head(url: str, **kwargs: Any) -> MagicMock:
        return _resp(200 if url.endswith("/careers") else 404)

    monkeypatch.setattr(
        company_search, "_make_session", lambda network_settings=None: _mock_session(head_side_effect=fake_head)
    )

    result = company_search.find_career_page("Deloitte", "https://www2.deloitte.com")
    assert result == "https://www2.deloitte.com/careers"


# ---------------------------------------------------------------------------
# find_career_page: all probes fail → DDG fallback
# ---------------------------------------------------------------------------


def test_find_career_page_fallback_to_ddg(monkeypatch: pytest.MonkeyPatch) -> None:
    _DDG_CAREERS = {
        "Results": [{"FirstURL": "https://www2.deloitte.com/global/en/careers.html"}],
        "RelatedTopics": [],
    }

    def fake_head(url: str, **kwargs: Any) -> MagicMock:
        return _resp(404)

    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        return _resp(200, _DDG_CAREERS)

    monkeypatch.setattr(
        company_search,
        "_make_session",
        lambda network_settings=None: _mock_session(fake_get, fake_head),
    )

    result = company_search.find_career_page("Deloitte", "https://www2.deloitte.com")
    assert result is not None
    assert "career" in result.lower()


# ---------------------------------------------------------------------------
# find_career_page: no website → goes straight to DDG
# ---------------------------------------------------------------------------


def test_find_career_page_no_website_uses_ddg(monkeypatch: pytest.MonkeyPatch) -> None:
    _DDG_CAREERS = {
        "Results": [{"FirstURL": "https://www2.deloitte.com/global/en/careers.html"}],
        "RelatedTopics": [],
    }

    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        return _resp(200, _DDG_CAREERS)

    monkeypatch.setattr(company_search, "_make_session", lambda network_settings=None: _mock_session(fake_get))

    result = company_search.find_career_page("Deloitte", None)
    assert result is not None
    assert "career" in result.lower()


# ---------------------------------------------------------------------------
# Wikipedia disambiguation page is rejected: Wikidata never queried
# ---------------------------------------------------------------------------


def test_search_companies_wikipedia_disambiguation_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    wikidata_called = []

    def fake_get(url: str, **kwargs: Any) -> MagicMock:
        if "html.duckduckgo.com" in url:
            return _resp(200, text="")
        if "duckduckgo.com" in url:
            return _resp(200, _DDG_DELOITTE)
        if "wikipedia.org" in url:
            return _resp(200, {"type": "disambiguation", "wikibase_item": "Q999"})
        if "wikidata.org" in url:
            wikidata_called.append(url)
            return _resp(200, {})
        return _resp(404)

    monkeypatch.setattr(company_search, "_make_session", lambda network_settings=None: _mock_session(fake_get))

    results = company_search.search_companies("", "", ["Deloitte"])

    assert not wikidata_called, "Wikidata should not be queried for disambiguation pages"
    r = results[0] if results else {}
    assert "company_website" not in r
    assert "company_size" not in r
