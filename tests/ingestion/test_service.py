from collections.abc import Iterable
from uuid import UUID, uuid4

from phd_agent.ingestion.adapters import (
    RawOpportunity,
    SourceAdapter,
)
from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    SourceProvenance,
)
from phd_agent.ingestion.persistence import (
    OpportunityRepository,
    PersistenceResult,
)
from phd_agent.ingestion.service import IngestionService
from phd_agent.ingestion.snapshots import (
    SnapshotAction,
    SnapshotDecision,
)


class FakeAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "fake_source"

    def fetch(self) -> Iterable[RawOpportunity]:
        return [
            {
                "id": "1",
                "title": "  AI   for Healthcare ",
                "url": "https://example.com/phd/1",
            },
            {
                "id": "2",
                "title": "Medical Imaging AI",
                "url": "https://example.com/phd/2",
            },
        ]

    def parse(
        self,
        raw: RawOpportunity,
    ) -> CanonicalOpportunity:
        return CanonicalOpportunity(
            title=str(raw["title"]),
            institution="Example University",
            provenance=SourceProvenance(
                source_name=self.source_name,
                external_id=str(raw["id"]),
                source_url=str(raw["url"]),
            ),
        )


class FakeRepository(OpportunityRepository):
    def __init__(self) -> None:
        self.existing: CanonicalOpportunity | None = None
        self.persist_calls: list[
            tuple[
                CanonicalOpportunity,
                SnapshotDecision,
            ]
        ] = []

    def find_match(
        self,
        opportunity: CanonicalOpportunity,
    ) -> CanonicalOpportunity | None:
        return self.existing

    def persist(
        self,
        opportunity: CanonicalOpportunity,
        decision: SnapshotDecision,
    ) -> PersistenceResult:
        self.persist_calls.append(
            (
                opportunity,
                decision,
            )
        )

        return PersistenceResult(
            opportunity_id=uuid4(),
            created=(
                decision.action is SnapshotAction.CREATE
            ),
            updated=(
                decision.action
                is SnapshotAction.UPDATE_WITH_SNAPSHOT
            ),
            snapshot_created=(
                decision.action
                is SnapshotAction.UPDATE_WITH_SNAPSHOT
            ),
        )


def make_opportunity(
    *,
    title: str = "AI for Healthcare",
    description: str | None = None,
) -> CanonicalOpportunity:
    return CanonicalOpportunity(
        title=title,
        institution="Example University",
        description=description,
        provenance=SourceProvenance(
            source_name="fake_source",
            external_id="1",
            source_url="https://example.com/phd/1",
        ),
    )


def test_single_new_opportunity_is_created() -> None:
    repository = FakeRepository()
    service = IngestionService(repository)

    result = service.ingest_opportunity(
        make_opportunity()
    )

    assert result.persistence.created is True
    assert result.persistence.updated is False
    assert result.persistence.snapshot_created is False

    assert len(repository.persist_calls) == 1

    _, decision = repository.persist_calls[0]

    assert decision.action is SnapshotAction.CREATE


def test_service_normalizes_before_repository_lookup() -> None:
    repository = FakeRepository()
    service = IngestionService(repository)

    opportunity = make_opportunity(
        title="  AI   for\n Healthcare "
    )

    result = service.ingest_opportunity(opportunity)

    assert result.opportunity.title == "AI for Healthcare"

    persisted, _ = repository.persist_calls[0]

    assert persisted.title == "AI for Healthcare"


def test_existing_unchanged_opportunity_is_not_updated() -> None:
    repository = FakeRepository()

    repository.existing = make_opportunity()

    service = IngestionService(repository)

    result = service.ingest_opportunity(
        make_opportunity()
    )

    assert result.persistence.created is False
    assert result.persistence.updated is False
    assert result.persistence.snapshot_created is False

    _, decision = repository.persist_calls[0]

    assert decision.action is SnapshotAction.UNCHANGED


def test_changed_opportunity_creates_snapshot() -> None:
    repository = FakeRepository()

    repository.existing = make_opportunity(
        description="Old description"
    )

    service = IngestionService(repository)

    result = service.ingest_opportunity(
        make_opportunity(
            description="New description"
        )
    )

    assert result.persistence.created is False
    assert result.persistence.updated is True
    assert result.persistence.snapshot_created is True

    _, decision = repository.persist_calls[0]

    assert (
        decision.action
        is SnapshotAction.UPDATE_WITH_SNAPSHOT
    )

    assert "description" in decision.changes


def test_adapter_run_processes_all_records() -> None:
    repository = FakeRepository()
    service = IngestionService(repository)

    result = service.ingest_adapter(FakeAdapter())

    assert result.source_name == "fake_source"
    assert result.processed == 2
    assert len(result.results) == 2
    assert len(repository.persist_calls) == 2


def test_adapter_run_counts_created_records() -> None:
    repository = FakeRepository()
    service = IngestionService(repository)

    result = service.ingest_adapter(FakeAdapter())

    assert result.created == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.snapshots_created == 0


def test_result_contains_valid_opportunity_ids() -> None:
    repository = FakeRepository()
    service = IngestionService(repository)

    result = service.ingest_adapter(FakeAdapter())

    for item in result.results:
        assert isinstance(
            item.persistence.opportunity_id,
            UUID,
        )
