from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    SourceProvenance,
)


TRACKING_QUERY_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
}

COUNTRY_ALIASES = {
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united kingdom": "United Kingdom",
    "great britain": "United Kingdom",
    "gb": "United Kingdom",
}


def normalize_whitespace(value: str) -> str:
    """Collapse repeated whitespace and trim the result."""

    return re.sub(r"\s+", " ", value).strip()


def normalize_optional_text(value: str | None) -> str | None:
    """Normalize optional text and convert blank values to None."""

    if value is None:
        return None

    normalized = normalize_whitespace(value)

    return normalized or None


def normalize_country(value: str) -> str:
    """Normalize known country aliases."""

    normalized = normalize_whitespace(value)

    alias = COUNTRY_ALIASES.get(normalized.casefold())

    return alias if alias is not None else normalized


def normalize_url(value: str | None) -> str | None:
    """
    Produce a stable URL representation.

    Tracking parameters and fragments are removed. Meaningful query
    parameters are retained and sorted.
    """

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    parts = urlsplit(value)

    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()

    if parts.port is not None:
        netloc = f"{hostname}:{parts.port}"
    else:
        netloc = hostname

    filtered_query = [
        (key, query_value)
        for key, query_value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if key.casefold() not in TRACKING_QUERY_PARAMETERS
    ]

    filtered_query.sort()

    query = urlencode(filtered_query, doseq=True)

    path = parts.path

    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            query,
            "",
        )
    )


def normalize_provenance(
    provenance: SourceProvenance,
) -> SourceProvenance:
    """Return validated normalized source provenance."""

    data = provenance.model_dump()

    data.update(
        {
            "source_name": normalize_whitespace(
                provenance.source_name
            ),
            "external_id": normalize_optional_text(
                provenance.external_id
            ),
            "source_url": normalize_url(
                str(provenance.source_url)
            ),
        }
    )

    return SourceProvenance.model_validate(data)


def normalize_opportunity(
    opportunity: CanonicalOpportunity,
) -> CanonicalOpportunity:
    """
    Return a validated normalized copy of an opportunity.

    The original object is never mutated.
    """

    data = opportunity.model_dump()

    data.update(
        {
            "title": normalize_whitespace(
                opportunity.title
            ),
            "institution": normalize_whitespace(
                opportunity.institution
            ),
            "department": normalize_optional_text(
                opportunity.department
            ),
            "location_text": normalize_optional_text(
                opportunity.location_text
            ),
            "country": normalize_country(
                opportunity.country
            ),
            "description": normalize_optional_text(
                opportunity.description
            ),
            "research_area": normalize_optional_text(
                opportunity.research_area
            ),
            "funding_text": normalize_optional_text(
                opportunity.funding_text
            ),
            "stipend_text": normalize_optional_text(
                opportunity.stipend_text
            ),
            "visa_notes": normalize_optional_text(
                opportunity.visa_notes
            ),
            "deadline_text": normalize_optional_text(
                opportunity.deadline_text
            ),
            "application_url": normalize_url(
                str(opportunity.application_url)
                if opportunity.application_url is not None
                else None
            ),
            "project_url": normalize_url(
                str(opportunity.project_url)
                if opportunity.project_url is not None
                else None
            ),
            "provenance": normalize_provenance(
                opportunity.provenance
            ),
        }
    )

    return CanonicalOpportunity.model_validate(data)
