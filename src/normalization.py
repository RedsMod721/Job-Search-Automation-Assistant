from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}
COMPANY_SUFFIXES = {
    "ag",
    "bv",
    "co",
    "company",
    "corp",
    "corporation",
    "gmbh",
    "inc",
    "limited",
    "llc",
    "ltd",
    "plc",
    "sa",
    "sarl",
    "sas",
}


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_company_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    parts = collapse_whitespace(text).split()
    while parts and parts[-1] in COMPANY_SUFFIXES:
        parts.pop()
    return " ".join(parts)


def canonicalize_url(value: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    if not re.match(r"^[a-z][a-z0-9+.-]*://", raw_value, flags=re.IGNORECASE):
        raw_value = f"https://{raw_value}"

    parsed = urlsplit(raw_value)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/+", "/", parsed.path or "").rstrip("/")
    query_items = []
    for key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered_key = key.lower()
        if lowered_key in TRACKING_QUERY_KEYS or lowered_key.startswith(TRACKING_QUERY_PREFIXES):
            continue
        query_items.append((key, query_value))
    query = urlencode(query_items, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_for_hash(value: str) -> str:
    return collapse_whitespace(str(value or "")).lower()


def content_hash(value: str) -> str:
    normalized = normalize_for_hash(value)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()
