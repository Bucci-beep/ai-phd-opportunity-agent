from phd_agent.ingestion.adapters import RawOpportunity, SourceAdapter
from phd_agent.ingestion.hashing import (
    HASH_VERSION,
    build_hash_payload,
    compute_content_hash,
    serialize_hash_payload,
)
from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    FundingStatus,
    OpportunityStatus,
    SourceProvenance,
)
from phd_agent.ingestion.normalization import (
    normalize_country,
    normalize_opportunity,
    normalize_optional_text,
    normalize_provenance,
    normalize_url,
    normalize_whitespace,
)

__all__ = [
    "CanonicalOpportunity",
    "FundingStatus",
    "HASH_VERSION",
    "OpportunityStatus",
    "RawOpportunity",
    "SourceAdapter",
    "SourceProvenance",
    "build_hash_payload",
    "compute_content_hash",
    "normalize_country",
    "normalize_opportunity",
    "normalize_optional_text",
    "normalize_provenance",
    "normalize_url",
    "normalize_whitespace",
    "serialize_hash_payload",
]

from phd_agent.ingestion.deduplication import (
    DeduplicationResult,
    MatchReason,
    compare_opportunities,
)
