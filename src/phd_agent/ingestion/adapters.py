from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import Any

from phd_agent.ingestion.models import CanonicalOpportunity


RawOpportunity = Mapping[str, Any]


class SourceAdapter(ABC):
    """
    Contract implemented by every opportunity source.

    Adapters are responsible only for retrieving source records and converting
    them into CanonicalOpportunity objects.

    Normalization, hashing, deduplication and database persistence happen
    downstream.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Stable human readable source identifier."""

    @abstractmethod
    def fetch(self) -> Iterable[RawOpportunity]:
        """Retrieve raw opportunity records from the source."""

    @abstractmethod
    def parse(self, raw: RawOpportunity) -> CanonicalOpportunity:
        """Convert one raw source record into the canonical model."""

    def collect(self) -> list[CanonicalOpportunity]:
        """
        Fetch and parse all currently available source records.

        Keeping this orchestration here gives every adapter identical basic
        behaviour while allowing fetch and parse to be tested independently.
        """

        return [self.parse(raw) for raw in self.fetch()]
