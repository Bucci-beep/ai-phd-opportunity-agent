from phd_agent.ingestion.deduplication import MatchReason
from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    FundingStatus,
    OpportunityStatus,
    SourceProvenance,
)
from phd_agent.ingestion.snapshots import (
    SnapshotAction,
    build_change_summary,
    decide_snapshot_action,
)


def make_opportunity(
    *,
    title: str = "AI for Cardiovascular Health",
    description: str = "Machine learning for cardiovascular disease.",
    funding_status: FundingStatus = FundingStatus.FULLY_FUNDED,
    funding_amount_gbp: float | None = 21000,
    deadline_text: str | None = "31 October 2026",
    status: OpportunityStatus = OpportunityStatus.OPEN,
    source_name: str = "jobs.ac.uk",
    external_id: str | None = "PHD-123",
    source_url: str = "https://jobs.ac.uk/job/PHD-123",
) -> CanonicalOpportunity:
    return CanonicalOpportunity(
        title=title,
        institution="University of Bristol",
        description=description,
        funding_status=funding_status,
        funding_amount_gbp=funding_amount_gbp,
        deadline_text=deadline_text,
        status=status,
        project_url="https://example.ac.uk/projects/ai-health",
        provenance=SourceProvenance(
            source_name=source_name,
            external_id=external_id,
            source_url=source_url,
        ),
    )


def test_missing_existing_opportunity_results_in_create() -> None:
    incoming = make_opportunity()

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=None,
    )

    assert decision.action is SnapshotAction.CREATE
    assert decision.match_reason is MatchReason.NO_MATCH
    assert decision.old_hash is None
    assert len(decision.new_hash) == 64
    assert decision.changes == {}
    assert decision.has_changes is False


def test_identical_listing_is_unchanged() -> None:
    existing = make_opportunity()
    incoming = make_opportunity()

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UNCHANGED
    assert decision.match_reason is MatchReason.SOURCE_EXTERNAL_ID
    assert decision.old_hash == decision.new_hash
    assert decision.changes == {}


def test_whitespace_only_difference_is_unchanged() -> None:
    existing = make_opportunity()

    incoming_data = make_opportunity().model_dump()
    incoming_data["title"] = "  AI   for Cardiovascular Health "
    incoming_data["description"] = (
        " Machine learning for cardiovascular   disease. "
    )

    incoming = CanonicalOpportunity.model_validate(
        incoming_data
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UNCHANGED
    assert decision.old_hash == decision.new_hash


def test_changed_description_requires_snapshot() -> None:
    existing = make_opportunity()

    incoming = make_opportunity(
        description=(
            "Updated machine learning research for cardiovascular disease."
        )
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UPDATE_WITH_SNAPSHOT
    assert decision.old_hash != decision.new_hash
    assert decision.has_changes is True

    assert decision.changes["description"].old == (
        "Machine learning for cardiovascular disease."
    )
    assert decision.changes["description"].new == (
        "Updated machine learning research for cardiovascular disease."
    )


def test_changed_status_requires_snapshot() -> None:
    existing = make_opportunity(
        status=OpportunityStatus.OPEN
    )

    incoming = make_opportunity(
        status=OpportunityStatus.CLOSED
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UPDATE_WITH_SNAPSHOT

    change = decision.changes["status"]

    assert change.old == "open"
    assert change.new == "closed"


def test_changed_funding_requires_snapshot() -> None:
    existing = make_opportunity(
        funding_amount_gbp=21000,
    )

    incoming = make_opportunity(
        funding_amount_gbp=25000,
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UPDATE_WITH_SNAPSHOT

    change = decision.changes["funding_amount_gbp"]

    assert change.old == 21000.0
    assert change.new == 25000.0


def test_multiple_changes_are_reported() -> None:
    existing = make_opportunity()

    incoming = make_opportunity(
        description="Updated description.",
        funding_amount_gbp=25000,
        deadline_text="15 November 2026",
        status=OpportunityStatus.CLOSED,
    )

    changes = build_change_summary(
        existing,
        incoming,
    )

    assert set(changes) == {
        "description",
        "funding_amount_gbp",
        "deadline_text",
        "status",
    }


def test_source_metadata_change_does_not_create_snapshot() -> None:
    existing = make_opportunity()

    incoming_data = make_opportunity().model_dump()

    incoming_data["provenance"]["raw_metadata"] = {
        "crawl_number": 27,
        "retrieved_by": "crawler-v2",
    }

    incoming = CanonicalOpportunity.model_validate(
        incoming_data
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UNCHANGED
    assert decision.changes == {}


def test_same_listing_changed_content_matches_before_snapshot() -> None:
    existing = make_opportunity()

    incoming = make_opportunity(
        description="New description.",
        deadline_text="15 November 2026",
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UPDATE_WITH_SNAPSHOT
    assert decision.match_reason is MatchReason.SOURCE_EXTERNAL_ID


def test_different_opportunity_results_in_create() -> None:
    existing = make_opportunity()

    incoming = CanonicalOpportunity(
        title="Robotics for Surgical Assistance",
        institution="University of Bristol",
        description="Research into robotic surgery.",
        provenance=SourceProvenance(
            source_name="FindAPhD",
            external_id="DIFFERENT-999",
            source_url="https://findaphd.com/project/999",
        ),
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.CREATE
    assert decision.match_reason is MatchReason.NO_MATCH
    assert decision.old_hash is None


def test_same_content_from_different_source_is_unchanged() -> None:
    existing = make_opportunity(
        source_name="jobs.ac.uk",
        external_id="123",
        source_url="https://jobs.ac.uk/job/123",
    )

    incoming = make_opportunity(
        source_name="FindAPhD",
        external_id="ABC",
        source_url="https://findaphd.com/project/ABC",
    )

    decision = decide_snapshot_action(
        incoming=incoming,
        existing=existing,
    )

    assert decision.action is SnapshotAction.UNCHANGED
    assert decision.match_reason is MatchReason.CONTENT_HASH


def test_change_summary_ignores_source_provenance() -> None:
    existing = make_opportunity(
        source_name="jobs.ac.uk",
        source_url="https://jobs.ac.uk/job/123",
    )

    incoming = make_opportunity(
        source_name="FindAPhD",
        source_url="https://findaphd.com/project/ABC",
    )

    changes = build_change_summary(
        existing,
        incoming,
    )

    assert changes == {}
