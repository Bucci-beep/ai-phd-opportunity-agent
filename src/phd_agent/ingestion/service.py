from __future__ import annotations

from dataclasses import dataclass

from phd_agent.ingestion.adapters import SourceAdapter
from phd_agent.ingestion.models import CanonicalOpportunity
from phd_agent.ingestion.normalization import normalize_opportunity
from phd_agent.ingestion.persistence import (
    OpportunityRepository,
    PersistenceResult,
)
from phd_agent.ingestion.snapshots import decide_snapshot_action


@dataclass(frozen=True)
class IngestionItemResult:
    opportunity: CanonicalOpportunity
    persistence: PersistenceResult


@dataclass(frozen=True)
class IngestionRunResult:
    source_name: str
    processed: int
    created: int
    updated: int
    unchanged: int
    snapshots_created: int
    results: tuple[IngestionItemResult, ...]


class IngestionService:
    """
    Coordinates opportunity ingestion.

    The service owns workflow order while adapters own source retrieval
    and repositories own persistence.
    """

    def __init__(
        self,
        repository: OpportunityRepository,
    ) -> None:
        self.repository = repository

    def ingest_opportunity(
        self,
        opportunity: CanonicalOpportunity,
    ) -> IngestionItemResult:
        """
        Normalize, match, classify and persist one opportunity.
        """

        normalized = normalize_opportunity(opportunity)

        existing = self.repository.find_match(normalized)

        decision = decide_snapshot_action(
            incoming=normalized,
            existing=existing,
        )

        persistence = self.repository.persist(
            opportunity=normalized,
            decision=decision,
        )

        return IngestionItemResult(
            opportunity=normalized,
            persistence=persistence,
        )

    def ingest_adapter(
        self,
        adapter: SourceAdapter,
    ) -> IngestionRunResult:
        """
        Ingest every opportunity returned by one source adapter.
        """

        item_results: list[IngestionItemResult] = []

        created = 0
        updated = 0
        unchanged = 0
        snapshots_created = 0

        for opportunity in adapter.collect():
            result = self.ingest_opportunity(opportunity)

            item_results.append(result)

            if result.persistence.created:
                created += 1

            if result.persistence.updated:
                updated += 1

            if (
                not result.persistence.created
                and not result.persistence.updated
            ):
                unchanged += 1

            if result.persistence.snapshot_created:
                snapshots_created += 1

        return IngestionRunResult(
            source_name=adapter.source_name,
            processed=len(item_results),
            created=created,
            updated=updated,
            unchanged=unchanged,
            snapshots_created=snapshots_created,
            results=tuple(item_results),
        )
