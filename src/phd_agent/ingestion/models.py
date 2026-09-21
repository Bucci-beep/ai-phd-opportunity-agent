from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class FundingStatus(StrEnum):
    FULLY_FUNDED = "fully_funded"
    PARTIALLY_FUNDED = "partially_funded"
    UNFUNDED = "unfunded"
    UNKNOWN = "unknown"


class OpportunityStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ROLLING = "rolling"
    UNKNOWN = "unknown"


class SourceProvenance(BaseModel):
    """Identifies where an opportunity was discovered."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    external_id: str | None = None
    source_url: HttpUrl
    source_posted_at: datetime | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_name")
    @classmethod
    def validate_source_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("source_name cannot be blank")

        return value


class CanonicalOpportunity(BaseModel):
    """
    Source independent representation of a PhD opportunity.

    Source adapters must convert their source specific records into this
    model before normalization, hashing, deduplication or persistence.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    institution: str = Field(min_length=1)
    department: str | None = None

    location_text: str | None = None
    country: str = "United Kingdom"

    description: str | None = None
    research_area: str | None = None

    funding_status: FundingStatus = FundingStatus.UNKNOWN
    funding_amount_gbp: float | None = Field(default=None, ge=0)
    funding_text: str | None = None
    tuition_covered: bool | None = None
    stipend_text: str | None = None

    international_students_eligible: bool | None = None
    visa_notes: str | None = None

    start_date: date | None = None
    deadline: date | None = None
    deadline_text: str | None = None

    status: OpportunityStatus = OpportunityStatus.UNKNOWN

    application_url: HttpUrl | None = None
    project_url: HttpUrl | None = None

    provenance: SourceProvenance

    @field_validator("title", "institution", "country")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("required text fields cannot be blank")

        return value
