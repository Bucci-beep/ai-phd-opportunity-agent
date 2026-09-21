from collections.abc import Iterable

import pytest

from phd_agent.ingestion.adapters import RawOpportunity, SourceAdapter
from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    FundingStatus,
    OpportunityStatus,
    SourceProvenance,
)


class FakeSourceAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "fake_source"

    def fetch(self) -> Iterable[RawOpportunity]:
        return [
            {
                "id": "phd-001",
                "title": "AI for Cardiovascular Health",
                "institution": "University of Bristol",
                "url": "https://example.ac.uk/phd-001",
                "funded": True,
            },
            {
                "id": "phd-002",
                "title": "Machine Learning for Medical Imaging",
                "institution": "University of Example",
                "url": "https://example.ac.uk/phd-002",
                "funded": False,
            },
        ]

    def parse(self, raw: RawOpportunity) -> CanonicalOpportunity:
        funding_status = (
            FundingStatus.FULLY_FUNDED
            if raw["funded"]
            else FundingStatus.UNKNOWN
        )

        return CanonicalOpportunity(
            title=str(raw["title"]),
            institution=str(raw["institution"]),
            funding_status=funding_status,
            status=OpportunityStatus.OPEN,
            project_url=str(raw["url"]),
            provenance=SourceProvenance(
                source_name=self.source_name,
                external_id=str(raw["id"]),
                source_url=str(raw["url"]),
                raw_metadata=dict(raw),
            ),
        )


def test_adapter_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        SourceAdapter()


def test_fake_adapter_has_stable_source_name() -> None:
    adapter = FakeSourceAdapter()

    assert adapter.source_name == "fake_source"


def test_fetch_returns_raw_records() -> None:
    adapter = FakeSourceAdapter()

    records = list(adapter.fetch())

    assert len(records) == 2
    assert records[0]["id"] == "phd-001"
    assert records[1]["id"] == "phd-002"


def test_parse_converts_raw_record_to_canonical_model() -> None:
    adapter = FakeSourceAdapter()

    raw = next(iter(adapter.fetch()))
    opportunity = adapter.parse(raw)

    assert isinstance(opportunity, CanonicalOpportunity)
    assert opportunity.title == "AI for Cardiovascular Health"
    assert opportunity.institution == "University of Bristol"
    assert opportunity.funding_status is FundingStatus.FULLY_FUNDED
    assert opportunity.provenance.source_name == "fake_source"
    assert opportunity.provenance.external_id == "phd-001"


def test_collect_returns_canonical_opportunities() -> None:
    adapter = FakeSourceAdapter()

    opportunities = adapter.collect()

    assert len(opportunities) == 2
    assert all(
        isinstance(opportunity, CanonicalOpportunity)
        for opportunity in opportunities
    )

    assert opportunities[0].title == "AI for Cardiovascular Health"
    assert opportunities[1].title == "Machine Learning for Medical Imaging"


def test_collect_preserves_source_metadata() -> None:
    adapter = FakeSourceAdapter()

    opportunity = adapter.collect()[0]

    assert opportunity.provenance.raw_metadata["id"] == "phd-001"
    assert opportunity.provenance.raw_metadata["funded"] is True
