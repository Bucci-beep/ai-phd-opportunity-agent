from copy import deepcopy

import pytest

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


def make_opportunity(
    *,
    source_name: str = "jobs.ac.uk",
    source_url: str = "https://jobs.ac.uk/job/123",
    external_id: str | None = "123",
) -> CanonicalOpportunity:
    return CanonicalOpportunity(
        title="AI for Cardiovascular Health",
        institution="University of Bristol",
        department="School of Engineering",
        location_text="Bristol",
        country="United Kingdom",
        description=(
            "Machine learning for cardiovascular disease detection."
        ),
        research_area="Artificial Intelligence in Healthcare",
        funding_status=FundingStatus.FULLY_FUNDED,
        funding_amount_gbp=21000,
        funding_text="Fully funded for four years",
        tuition_covered=True,
        stipend_text="£21,000 per year",
        international_students_eligible=True,
        visa_notes="International applicants are eligible.",
        deadline_text="31 October 2026",
        status=OpportunityStatus.OPEN,
        application_url="https://example.ac.uk/apply",
        project_url="https://example.ac.uk/phd/ai-health",
        provenance=SourceProvenance(
            source_name=source_name,
            external_id=external_id,
            source_url=source_url,
            raw_metadata={
                "crawler_run": "abc123",
            },
        ),
    )


def test_hash_is_sha256_hex_digest() -> None:
    content_hash = compute_content_hash(make_opportunity())

    assert len(content_hash) == 64
    assert all(
        character in "0123456789abcdef"
        for character in content_hash
    )


def test_same_opportunity_produces_same_hash() -> None:
    opportunity = make_opportunity()

    first = compute_content_hash(opportunity)
    second = compute_content_hash(opportunity)

    assert first == second


def test_equivalent_whitespace_produces_same_hash() -> None:
    first = make_opportunity()

    second = make_opportunity().model_copy(
        update={
            "title": "  AI   for Cardiovascular\nHealth ",
            "institution": " University   of Bristol ",
            "description": (
                " Machine learning for cardiovascular "
                "disease   detection. "
            ),
        }
    )

    assert compute_content_hash(first) == compute_content_hash(second)


def test_country_alias_produces_same_hash() -> None:
    first = make_opportunity()

    second = make_opportunity().model_copy(
        update={"country": "UK"}
    )

    assert compute_content_hash(first) == compute_content_hash(second)


def test_tracking_parameters_do_not_change_hash() -> None:
    first = make_opportunity()

    second_data = make_opportunity().model_dump()

    second_data.update(
        {
            "project_url": (
                "https://example.ac.uk/phd/ai-health/"
                "?utm_source=email"
            ),
            "application_url": (
                "https://example.ac.uk/apply"
                "?utm_campaign=phd"
            ),
        }
    )

    second = CanonicalOpportunity.model_validate(second_data)

    assert compute_content_hash(first) == compute_content_hash(second)


@pytest.mark.parametrize(
    ("field", "new_value"),
    [
        ("title", "Different PhD Title"),
        ("description", "Substantially different description"),
        ("funding_amount_gbp", 25000),
        ("funding_status", FundingStatus.PARTIALLY_FUNDED),
        ("deadline_text", "15 November 2026"),
        ("status", OpportunityStatus.CLOSED),
    ],
)
def test_meaningful_content_changes_hash(
    field: str,
    new_value: object,
) -> None:
    original = make_opportunity()

    changed = original.model_copy(
        update={field: new_value}
    )

    assert compute_content_hash(original) != (
        compute_content_hash(changed)
    )


def test_different_source_provenance_does_not_change_hash() -> None:
    first = make_opportunity(
        source_name="jobs.ac.uk",
        source_url="https://jobs.ac.uk/job/123",
        external_id="123",
    )

    second = make_opportunity(
        source_name="University of Bristol",
        source_url="https://bristol.ac.uk/phd/project/456",
        external_id="456",
    )

    assert compute_content_hash(first) == compute_content_hash(second)


def test_raw_metadata_does_not_change_hash() -> None:
    first = make_opportunity()

    second = deepcopy(first)

    second.provenance.raw_metadata["crawler_run"] = "different"
    second.provenance.raw_metadata["page_number"] = 7

    assert compute_content_hash(first) == compute_content_hash(second)


def test_hash_payload_excludes_provenance() -> None:
    payload = build_hash_payload(make_opportunity())

    assert "provenance" not in payload["content"]
    assert "source_name" not in payload["content"]
    assert "external_id" not in payload["content"]
    assert "raw_metadata" not in payload["content"]


def test_hash_payload_contains_version() -> None:
    payload = build_hash_payload(make_opportunity())

    assert payload["hash_version"] == HASH_VERSION
    assert HASH_VERSION == "v1"


def test_serialization_is_deterministic() -> None:
    opportunity = make_opportunity()

    first = serialize_hash_payload(opportunity)
    second = serialize_hash_payload(opportunity)

    assert first == second


def test_serialized_payload_has_no_insignificant_json_whitespace() -> None:
    serialized = serialize_hash_payload(make_opportunity())

    assert ": " not in serialized
    assert ", " not in serialized
