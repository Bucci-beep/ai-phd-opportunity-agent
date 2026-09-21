from uuid import uuid4

import pytest

from phd_agent.ingestion.hashing import compute_content_hash
from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    FundingStatus,
    OpportunityStatus,
    SourceProvenance,
)
from phd_agent.ingestion.persistence import (
    OpportunityRepository,
    PersistenceResult,
    opportunity_to_database_record,
    provenance_to_database_record,
)


def make_opportunity() -> CanonicalOpportunity:
    return CanonicalOpportunity(
        title="AI for Cardiovascular Health",
        institution="University of Bristol",
        department="School of Engineering",
        location_text="Bristol",
        description="Machine learning for cardiovascular disease.",
        research_area="Artificial Intelligence in Healthcare",
        funding_status=FundingStatus.FULLY_FUNDED,
        funding_amount_gbp=21000,
        funding_text="Fully funded",
        tuition_covered=True,
        stipend_text="£21,000 per year",
        international_students_eligible=True,
        visa_notes="International applicants eligible.",
        deadline_text="31 October 2026",
        status=OpportunityStatus.OPEN,
        application_url="https://example.ac.uk/apply",
        project_url="https://example.ac.uk/phd/ai-health",
        provenance=SourceProvenance(
            source_name="jobs.ac.uk",
            external_id="PHD-123",
            source_url="https://jobs.ac.uk/job/PHD-123",
            raw_metadata={
                "category": "studentship",
            },
        ),
    )


def test_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        OpportunityRepository()


def test_opportunity_record_excludes_provenance() -> None:
    opportunity = make_opportunity()
    content_hash = compute_content_hash(opportunity)

    record = opportunity_to_database_record(
        opportunity,
        content_hash,
    )

    assert "provenance" not in record
    assert "source_name" not in record
    assert "source_url" not in record
    assert "external_id" not in record


def test_opportunity_record_contains_content_hash() -> None:
    opportunity = make_opportunity()
    content_hash = compute_content_hash(opportunity)

    record = opportunity_to_database_record(
        opportunity,
        content_hash,
    )

    assert record["content_hash"] == content_hash
    assert len(record["content_hash"]) == 64


def test_opportunity_record_matches_database_fields() -> None:
    opportunity = make_opportunity()
    content_hash = compute_content_hash(opportunity)

    record = opportunity_to_database_record(
        opportunity,
        content_hash,
    )

    assert record["title"] == "AI for Cardiovascular Health"
    assert record["institution"] == "University of Bristol"
    assert record["funding_status"] == "fully_funded"
    assert record["status"] == "open"
    assert record["funding_amount_gbp"] == 21000.0


def test_provenance_record_contains_source_fields() -> None:
    opportunity = make_opportunity()

    record = provenance_to_database_record(opportunity)

    assert record == {
        "external_id": "PHD-123",
        "source_url": "https://jobs.ac.uk/job/PHD-123",
        "raw_metadata": {
            "category": "studentship",
        },
    }


def test_persistence_result_records_actions() -> None:
    opportunity_id = uuid4()

    result = PersistenceResult(
        opportunity_id=opportunity_id,
        created=True,
        updated=False,
        snapshot_created=True,
    )

    assert result.opportunity_id == opportunity_id
    assert result.created is True
    assert result.updated is False
    assert result.snapshot_created is True
