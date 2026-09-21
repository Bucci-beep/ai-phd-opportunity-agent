from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    SourceProvenance,
)
from phd_agent.ingestion.normalization import (
    normalize_country,
    normalize_opportunity,
    normalize_optional_text,
    normalize_url,
    normalize_whitespace,
)


def make_opportunity() -> CanonicalOpportunity:
    return CanonicalOpportunity(
        title="  AI   for\nHealthcare  ",
        institution="  University   of Bristol ",
        department="  School of   Engineering  ",
        location_text=" Bristol  ",
        country=" uk ",
        description=(
            " Machine learning\n\nfor cardiovascular\t disease. "
        ),
        research_area=" AI   in Health ",
        funding_text=" Fully   funded ",
        stipend_text=" £21,000   per year ",
        visa_notes=" International   students eligible ",
        deadline_text=" 31   October 2026 ",
        application_url=(
            "https://EXAMPLE.ac.uk/apply/"
            "?utm_source=newsletter&project=123"
            "#application"
        ),
        project_url=(
            "https://EXAMPLE.ac.uk/projects/ai-health/"
            "?utm_campaign=phd"
        ),
        provenance=SourceProvenance(
            source_name="  jobs.ac.uk  ",
            external_id="  PHD-123  ",
            source_url=(
                "https://WWW.JOBS.AC.UK/job/PHD-123/"
                "?utm_source=email#details"
            ),
        ),
    )


def test_normalize_whitespace() -> None:
    assert (
        normalize_whitespace("  AI   for\n health\t research ")
        == "AI for health research"
    )


def test_optional_blank_text_becomes_none() -> None:
    assert normalize_optional_text("   ") is None
    assert normalize_optional_text("\n\t") is None
    assert normalize_optional_text(None) is None


def test_optional_text_is_cleaned() -> None:
    assert (
        normalize_optional_text("  fully   funded ")
        == "fully funded"
    )


def test_known_country_alias_is_normalized() -> None:
    assert normalize_country("UK") == "United Kingdom"
    assert normalize_country(" uk ") == "United Kingdom"
    assert normalize_country("Great Britain") == "United Kingdom"


def test_unknown_country_is_preserved() -> None:
    assert normalize_country("Switzerland") == "Switzerland"


def test_url_tracking_parameters_and_fragment_are_removed() -> None:
    url = (
        "https://EXAMPLE.COM/phd/project/"
        "?utm_source=email&id=123&fbclid=abc#details"
    )

    assert normalize_url(url) == (
        "https://example.com/phd/project?id=123"
    )


def test_meaningful_query_parameters_are_sorted() -> None:
    url = "https://example.com/search?z=2&a=1"

    assert normalize_url(url) == (
        "https://example.com/search?a=1&z=2"
    )


def test_root_url_keeps_root_slash() -> None:
    assert normalize_url("https://EXAMPLE.COM/") == (
        "https://example.com/"
    )


def test_non_root_trailing_slash_is_removed() -> None:
    assert normalize_url(
        "https://example.com/phd/project/"
    ) == "https://example.com/phd/project"


def test_opportunity_is_normalized() -> None:
    original = make_opportunity()

    normalized = normalize_opportunity(original)

    assert normalized.title == "AI for Healthcare"
    assert normalized.institution == "University of Bristol"
    assert normalized.department == "School of Engineering"
    assert normalized.location_text == "Bristol"
    assert normalized.country == "United Kingdom"

    assert normalized.description == (
        "Machine learning for cardiovascular disease."
    )

    assert normalized.research_area == "AI in Health"
    assert normalized.funding_text == "Fully funded"
    assert normalized.stipend_text == "£21,000 per year"

    assert normalized.application_url is not None
    assert str(normalized.application_url) == (
        "https://example.ac.uk/apply?project=123"
    )

    assert normalized.project_url is not None
    assert str(normalized.project_url) == (
        "https://example.ac.uk/projects/ai-health"
    )

    assert normalized.provenance.source_name == "jobs.ac.uk"
    assert normalized.provenance.external_id == "PHD-123"

    assert str(normalized.provenance.source_url) == (
        "https://www.jobs.ac.uk/job/PHD-123"
    )


def test_normalization_does_not_mutate_original() -> None:
    original = make_opportunity()

    normalized = normalize_opportunity(original)

    assert original.title == "AI   for\nHealthcare"
    assert normalized.title == "AI for Healthcare"

    assert str(original.application_url) != str(
        normalized.application_url
    )


def test_normalization_is_idempotent() -> None:
    opportunity = make_opportunity()

    once = normalize_opportunity(opportunity)
    twice = normalize_opportunity(once)

    assert once == twice


def test_equivalent_records_normalize_identically() -> None:
    first = CanonicalOpportunity(
        title="AI for Healthcare",
        institution="University of Bristol",
        country="United Kingdom",
        project_url="https://example.ac.uk/phd/123",
        provenance=SourceProvenance(
            source_name="jobs.ac.uk",
            source_url="https://jobs.ac.uk/job/123",
        ),
    )

    second = CanonicalOpportunity(
        title="  AI   for Healthcare ",
        institution=" University  of Bristol ",
        country="UK",
        project_url=(
            "https://EXAMPLE.ac.uk/phd/123/"
            "?utm_source=email"
        ),
        provenance=SourceProvenance(
            source_name=" jobs.ac.uk ",
            source_url=(
                "https://JOBS.ac.uk/job/123/"
                "?utm_campaign=test"
            ),
        ),
    )

    assert normalize_opportunity(first) == (
        normalize_opportunity(second)
    )


def test_normalization_preserves_validated_url_types() -> None:
    from pydantic import HttpUrl

    normalized = normalize_opportunity(make_opportunity())

    assert isinstance(normalized.application_url, HttpUrl)
    assert isinstance(normalized.project_url, HttpUrl)
    assert isinstance(normalized.provenance.source_url, HttpUrl)
