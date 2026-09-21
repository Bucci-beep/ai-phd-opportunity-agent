from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from phd_agent.ingestion.hashing import compute_content_hash
from phd_agent.ingestion.models import CanonicalOpportunity
from phd_agent.ingestion.normalization import (
    normalize_opportunity,
    normalize_url,
    normalize_whitespace,
)


class MatchReason(StrEnum):
    SOURCE_EXTERNAL_ID = "source_external_id"
    SOURCE_URL = "source_url"
    CONTENT_HASH = "content_hash"
    NO_MATCH = "no_match"


@dataclass(frozen=True)
class DeduplicationResult:
    is_duplicate: bool
    reason: MatchReason


def _normalized_source_name(
    opportunity: CanonicalOpportunity,
) -> str:
    return normalize_whitespace(
        opportunity.provenance.source_name
    ).casefold()


def _same_source(
    first: CanonicalOpportunity,
    second: CanonicalOpportunity,
) -> bool:
    return (
        _normalized_source_name(first)
        == _normalized_source_name(second)
    )


def _same_external_id(
    first: CanonicalOpportunity,
    second: CanonicalOpportunity,
) -> bool:
    first_id = first.provenance.external_id
    second_id = second.provenance.external_id

    if first_id is None or second_id is None:
        return False

    return first_id.strip() == second_id.strip()


def _same_source_url(
    first: CanonicalOpportunity,
    second: CanonicalOpportunity,
) -> bool:
    first_url = normalize_url(
        str(first.provenance.source_url)
    )
    second_url = normalize_url(
        str(second.provenance.source_url)
    )

    return first_url == second_url


def compare_opportunities(
    first: CanonicalOpportunity,
    second: CanonicalOpportunity,
) -> DeduplicationResult:
    """
    Compare two canonical opportunities using conservative identity rules.

    Priority is important.

    Source identity is checked before content equality because an existing
    listing may have changed since the previous crawl while still referring
    to the same real opportunity.
    """

    first = normalize_opportunity(first)
    second = normalize_opportunity(second)

    if _same_source(first, second):
        if _same_external_id(first, second):
            return DeduplicationResult(
                is_duplicate=True,
                reason=MatchReason.SOURCE_EXTERNAL_ID,
            )

        if _same_source_url(first, second):
            return DeduplicationResult(
                is_duplicate=True,
                reason=MatchReason.SOURCE_URL,
            )

    if compute_content_hash(first) == compute_content_hash(second):
        return DeduplicationResult(
            is_duplicate=True,
            reason=MatchReason.CONTENT_HASH,
        )

    return DeduplicationResult(
        is_duplicate=False,
        reason=MatchReason.NO_MATCH,
    )
