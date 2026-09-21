from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from phd_agent.ingestion.models import CanonicalOpportunity
from phd_agent.ingestion.snapshots import SnapshotDecision


@dataclass(frozen=True)
class PersistedOpportunity:
    id: UUID
    content_hash: str


@dataclass(frozen=True)
class PersistenceResult:
    opportunity_id: UUID
    created: bool
    updated: bool
    snapshot_created: bool


class OpportunityRepository(ABC):
    """
    Persistence boundary for the ingestion layer.

    Implementations may use Supabase, PostgreSQL or an in memory store.
    Ingestion logic must not depend on database specific behaviour.
    """

    @abstractmethod
    def find_match(
        self,
        opportunity: CanonicalOpportunity,
    ) -> CanonicalOpportunity | None:
        """Find an existing canonical opportunity matching the incoming one."""

    @abstractmethod
    def persist(
        self,
        opportunity: CanonicalOpportunity,
        decision: SnapshotDecision,
    ) -> PersistenceResult:
        """
        Atomically persist an ingestion decision.

        Database implementations must ensure canonical opportunity,
        source provenance and snapshot writes succeed or fail together.
        """


def opportunity_to_database_record(
    opportunity: CanonicalOpportunity,
    content_hash: str,
) -> dict[str, Any]:
    """Convert canonical opportunity content to an opportunities row."""

    data = opportunity.model_dump(
        mode="json",
        exclude={"provenance"},
    )

    data["content_hash"] = content_hash

    return data


def provenance_to_database_record(
    opportunity: CanonicalOpportunity,
) -> dict[str, Any]:
    """Convert provenance into opportunity_sources data."""

    provenance = opportunity.provenance

    return {
        "external_id": provenance.external_id,
        "source_url": str(provenance.source_url),
        "raw_metadata": provenance.raw_metadata,
    }
