from phd_agent.ingestion.deduplication import (
    MatchReason,
    compare_opportunities,
)
from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    FundingStatus,
    OpportunityStatus,
    SourceProvenance,
)


def make_opportunity(
    *,
    title: str = "AI for Cardiovascular Health",
    institution: str = "University of Bristol",
    description: str = "Machine learning for cardiovascular disease.",
    funding_status: FundingStatus = FundingStatus.FULLY_FUNDED,
    status: OpportunityStatus = OpportunityStatus.OPEN,
    source_name: str = "jobs.ac.uk",
    external_id: str | None = "PHD-123",
    source_url: str = "https://jobs.ac.uk/job/PHD-123",
) -> CanonicalOpportunity:
    return CanonicalOpportunity(
        title=title,
        institution=institution,
        description=description,
        funding_status=funding_status,
        status=status,
        project_url="https://example.ac.uk/projects/ai-health",
        provenance=SourceProvenance(
            source_name=source_name,
            external_id=external_id,
            source_url=source_url,
        ),
    )


def test_same_source_and_external_id_matches() -> None:
    first = make_opportunity()

    second = make_opportunity(
        description="Updated project description",
        status=OpportunityStatus.CLOSED,
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is True
    assert result.reason is MatchReason.SOURCE_EXTERNAL_ID


def test_external_id_requires_same_source() -> None:
    first = make_opportunity(
        source_name="jobs.ac.uk",
        external_id="123",
    )

    second = make_opportunity(
        source_name="FindAPhD",
        external_id="123",
        description="Different description",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is False
    assert result.reason is MatchReason.NO_MATCH


def test_same_source_url_matches_when_external_id_missing() -> None:
    first = make_opportunity(
        external_id=None,
        source_url="https://jobs.ac.uk/job/123",
    )

    second = make_opportunity(
        external_id=None,
        source_url="https://jobs.ac.uk/job/123",
        description="Updated description",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is True
    assert result.reason is MatchReason.SOURCE_URL


def test_source_url_normalization_is_used() -> None:
    first = make_opportunity(
        external_id=None,
        source_url="https://JOBS.AC.UK/job/123/",
    )

    second = make_opportunity(
        external_id=None,
        source_url=(
            "https://jobs.ac.uk/job/123"
            "?utm_source=email#details"
        ),
        description="Changed description",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is True
    assert result.reason is MatchReason.SOURCE_URL


def test_same_content_across_different_sources_matches_by_hash() -> None:
    first = make_opportunity(
        source_name="jobs.ac.uk",
        external_id="123",
        source_url="https://jobs.ac.uk/job/123",
    )

    second = make_opportunity(
        source_name="FindAPhD",
        external_id="ABC",
        source_url="https://findaphd.com/phds/project/ABC",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is True
    assert result.reason is MatchReason.CONTENT_HASH


def test_source_identity_has_priority_over_content_hash() -> None:
    first = make_opportunity()

    second = make_opportunity()

    result = compare_opportunities(first, second)

    assert result.reason is MatchReason.SOURCE_EXTERNAL_ID


def test_same_title_alone_does_not_match() -> None:
    first = make_opportunity(
        description="Project about cardiovascular AI.",
    )

    second = make_opportunity(
        source_name="FindAPhD",
        external_id="999",
        source_url="https://findaphd.com/project/999",
        description="Project about medical robotics.",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is False
    assert result.reason is MatchReason.NO_MATCH


def test_same_institution_alone_does_not_match() -> None:
    first = make_opportunity(
        title="AI for Cardiovascular Health",
    )

    second = make_opportunity(
        title="Robotics for Surgical Assistance",
        source_name="FindAPhD",
        external_id="999",
        source_url="https://findaphd.com/project/999",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is False
    assert result.reason is MatchReason.NO_MATCH


def test_similar_titles_do_not_trigger_fuzzy_merge() -> None:
    first = make_opportunity(
        title="Artificial Intelligence for Healthcare",
    )

    second = make_opportunity(
        title="Artificial Intelligence in Healthcare",
        source_name="FindAPhD",
        external_id="999",
        source_url="https://findaphd.com/project/999",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is False
    assert result.reason is MatchReason.NO_MATCH


def test_changed_listing_remains_same_source_opportunity() -> None:
    first = make_opportunity(
        status=OpportunityStatus.OPEN,
    )

    second = make_opportunity(
        status=OpportunityStatus.CLOSED,
        description="Updated after applications closed.",
    )

    result = compare_opportunities(first, second)

    assert result.is_duplicate is True
    assert result.reason is MatchReason.SOURCE_EXTERNAL_ID
