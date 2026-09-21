from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    FundingStatus,
    OpportunityStatus,
    SourceProvenance,
)


def make_provenance() -> SourceProvenance:
    return SourceProvenance(
        source_name="jobs.ac.uk",
        external_id="PHD-123",
        source_url="https://www.jobs.ac.uk/job/PHD-123",
        source_posted_at=datetime(
            2026,
            9,
            17,
            10,
            30,
            tzinfo=timezone.utc,
        ),
        raw_metadata={"source_category": "studentship"},
    )


def test_source_provenance_is_valid() -> None:
    provenance = make_provenance()

    assert provenance.source_name == "jobs.ac.uk"
    assert provenance.external_id == "PHD-123"
    assert str(provenance.source_url) == "https://www.jobs.ac.uk/job/PHD-123"
    assert provenance.raw_metadata["source_category"] == "studentship"


def test_canonical_opportunity_accepts_valid_record() -> None:
    opportunity = CanonicalOpportunity(
        title="AI for Cardiovascular Disease Detection",
        institution="University of Bristol",
        department="School of Engineering Mathematics and Technology",
        location_text="Bristol",
        description="Research into machine learning for cardiovascular health.",
        research_area="Artificial Intelligence in Healthcare",
        funding_status=FundingStatus.FULLY_FUNDED,
        funding_amount_gbp=21000,
        funding_text="Fully funded for four years",
        tuition_covered=True,
        stipend_text="£21,000 annual stipend",
        international_students_eligible=True,
        visa_notes="International applicants are eligible.",
        start_date=date(2027, 1, 1),
        deadline=date(2026, 10, 31),
        deadline_text="31 October 2026",
        status=OpportunityStatus.OPEN,
        application_url="https://example.ac.uk/apply",
        project_url="https://example.ac.uk/phd/ai-health",
        provenance=make_provenance(),
    )

    assert opportunity.title == "AI for Cardiovascular Disease Detection"
    assert opportunity.institution == "University of Bristol"
    assert opportunity.country == "United Kingdom"
    assert opportunity.funding_status is FundingStatus.FULLY_FUNDED
    assert opportunity.status is OpportunityStatus.OPEN
    assert opportunity.international_students_eligible is True


def test_defaults_match_database_defaults() -> None:
    opportunity = CanonicalOpportunity(
        title="Machine Learning PhD",
        institution="Example University",
        provenance=make_provenance(),
    )

    assert opportunity.country == "United Kingdom"
    assert opportunity.funding_status is FundingStatus.UNKNOWN
    assert opportunity.status is OpportunityStatus.UNKNOWN
    assert opportunity.funding_amount_gbp is None
    assert opportunity.deadline is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", ""),
        ("title", "   "),
        ("institution", ""),
        ("institution", "   "),
    ],
)
def test_required_text_rejects_blank_values(
    field: str,
    value: str,
) -> None:
    data = {
        "title": "Example PhD",
        "institution": "Example University",
        "provenance": make_provenance(),
    }

    data[field] = value

    with pytest.raises(ValidationError):
        CanonicalOpportunity(**data)


def test_required_text_is_trimmed() -> None:
    opportunity = CanonicalOpportunity(
        title="  AI Healthcare PhD  ",
        institution="  University of Bristol  ",
        provenance=make_provenance(),
    )

    assert opportunity.title == "AI Healthcare PhD"
    assert opportunity.institution == "University of Bristol"


def test_negative_funding_amount_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CanonicalOpportunity(
            title="AI PhD",
            institution="Example University",
            funding_amount_gbp=-100,
            provenance=make_provenance(),
        )


def test_invalid_source_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceProvenance(
            source_name="example",
            source_url="not-a-url",
        )


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CanonicalOpportunity(
            title="AI PhD",
            institution="Example University",
            provenance=make_provenance(),
            made_up_field="should fail",
        )
