from __future__ import annotations

import hashlib
import json
from typing import Any

from phd_agent.ingestion.models import CanonicalOpportunity
from phd_agent.ingestion.normalization import normalize_opportunity


HASH_VERSION = "v1"

HASH_FIELDS = (
    "title",
    "institution",
    "department",
    "location_text",
    "country",
    "description",
    "research_area",
    "funding_status",
    "funding_amount_gbp",
    "funding_text",
    "tuition_covered",
    "stipend_text",
    "international_students_eligible",
    "visa_notes",
    "start_date",
    "deadline",
    "deadline_text",
    "status",
    "application_url",
    "project_url",
)


def build_hash_payload(
    opportunity: CanonicalOpportunity,
) -> dict[str, Any]:
    """
    Build the stable representation used for content hashing.

    Source provenance is deliberately excluded because it describes where
    an opportunity was discovered rather than the opportunity itself.
    """

    normalized = normalize_opportunity(opportunity)

    dumped = normalized.model_dump(
        mode="json",
        exclude={"provenance"},
    )

    content = {
        field: dumped[field]
        for field in HASH_FIELDS
    }

    return {
        "hash_version": HASH_VERSION,
        "content": content,
    }


def serialize_hash_payload(
    opportunity: CanonicalOpportunity,
) -> str:
    """
    Serialize the hash payload deterministically.

    Sorting keys and removing insignificant JSON whitespace ensures that
    equivalent payloads always produce identical bytes.
    """

    payload = build_hash_payload(opportunity)

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_content_hash(
    opportunity: CanonicalOpportunity,
) -> str:
    """Return the SHA256 hash for meaningful normalized opportunity content."""

    serialized = serialize_hash_payload(opportunity)

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()
