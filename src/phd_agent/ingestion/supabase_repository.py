from __future__ import annotations

from typing import Any

from supabase import Client

from phd_agent.ingestion.hashing import compute_content_hash
from phd_agent.ingestion.models import (
    CanonicalOpportunity,
    SourceProvenance,
)
from phd_agent.ingestion.normalization import (
    normalize_opportunity,
    normalize_url,
)
from phd_agent.ingestion.persistence import (
    OpportunityRepository,
    PersistenceResult,
)
from phd_agent.ingestion.snapshots import SnapshotDecision


class SupabaseOpportunityRepository(OpportunityRepository):
    """Supabase implementation of the opportunity repository."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def _get_source_id(
        self,
        source_name: str,
    ) -> str | None:
        response = (
            self.client.table("sources")
            .select("id")
            .eq("name", source_name)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return str(response.data[0]["id"])

    def _fetch_opportunity(
        self,
        opportunity_id: str,
        provenance: SourceProvenance,
    ) -> CanonicalOpportunity | None:
        response = (
            self.client.table("opportunities")
            .select("*")
            .eq("id", opportunity_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._row_to_canonical(
            response.data[0],
            provenance,
        )

    def _row_to_canonical(
        self,
        row: dict[str, Any],
        provenance: SourceProvenance,
    ) -> CanonicalOpportunity:
        allowed_fields = set(
            CanonicalOpportunity.model_fields
        ) - {"provenance"}

        data = {
            key: value
            for key, value in row.items()
            if key in allowed_fields
        }

        data["provenance"] = provenance

        return CanonicalOpportunity.model_validate(data)

    def _find_by_source_identity(
        self,
        opportunity: CanonicalOpportunity,
    ) -> CanonicalOpportunity | None:
        provenance = opportunity.provenance

        source_id = self._get_source_id(
            provenance.source_name
        )

        if source_id is None:
            return None

        if provenance.external_id:
            response = (
                self.client.table("opportunity_sources")
                .select(
                    "opportunity_id,external_id,"
                    "source_url,raw_metadata"
                )
                .eq("source_id", source_id)
                .eq("external_id", provenance.external_id)
                .limit(1)
                .execute()
            )

            if response.data:
                source_row = response.data[0]

                stored_provenance = SourceProvenance(
                    source_name=provenance.source_name,
                    external_id=source_row.get(
                        "external_id"
                    ),
                    source_url=source_row["source_url"],
                    raw_metadata=source_row.get(
                        "raw_metadata"
                    )
                    or {},
                )

                return self._fetch_opportunity(
                    str(source_row["opportunity_id"]),
                    stored_provenance,
                )

        normalized_source_url = normalize_url(
            str(provenance.source_url)
        )

        response = (
            self.client.table("opportunity_sources")
            .select(
                "opportunity_id,external_id,"
                "source_url,raw_metadata"
            )
            .eq("source_id", source_id)
            .execute()
        )

        for source_row in response.data:
            stored_url = normalize_url(
                str(source_row["source_url"])
            )

            if stored_url != normalized_source_url:
                continue

            stored_provenance = SourceProvenance(
                source_name=provenance.source_name,
                external_id=source_row.get(
                    "external_id"
                ),
                source_url=source_row["source_url"],
                raw_metadata=source_row.get(
                    "raw_metadata"
                )
                or {},
            )

            return self._fetch_opportunity(
                str(source_row["opportunity_id"]),
                stored_provenance,
            )

        return None

    def _find_by_content_hash(
        self,
        opportunity: CanonicalOpportunity,
    ) -> CanonicalOpportunity | None:
        content_hash = compute_content_hash(opportunity)

        response = (
            self.client.table("opportunities")
            .select("*")
            .eq("content_hash", content_hash)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._row_to_canonical(
            response.data[0],
            opportunity.provenance,
        )

    def find_match(
        self,
        opportunity: CanonicalOpportunity,
    ) -> CanonicalOpportunity | None:
        normalized = normalize_opportunity(opportunity)

        source_match = self._find_by_source_identity(
            normalized
        )

        if source_match is not None:
            return source_match

        return self._find_by_content_hash(normalized)

    def _find_existing_id(
        self,
        opportunity: CanonicalOpportunity,
    ) -> str | None:
        provenance = opportunity.provenance

        source_id = self._get_source_id(
            provenance.source_name
        )

        if source_id is not None:
            if provenance.external_id:
                response = (
                    self.client
                    .table("opportunity_sources")
                    .select("opportunity_id")
                    .eq("source_id", source_id)
                    .eq(
                        "external_id",
                        provenance.external_id,
                    )
                    .limit(1)
                    .execute()
                )

                if response.data:
                    return str(
                        response.data[0]["opportunity_id"]
                    )

            normalized_source_url = normalize_url(
                str(provenance.source_url)
            )

            response = (
                self.client
                .table("opportunity_sources")
                .select("opportunity_id,source_url")
                .eq("source_id", source_id)
                .execute()
            )

            for row in response.data:
                stored_url = normalize_url(
                    str(row["source_url"])
                )

                if stored_url == normalized_source_url:
                    return str(row["opportunity_id"])

        content_hash = compute_content_hash(opportunity)

        response = (
            self.client
            .table("opportunities")
            .select("id")
            .eq("content_hash", content_hash)
            .limit(1)
            .execute()
        )

        if response.data:
            return str(response.data[0]["id"])

        return None

    def persist(
        self,
        opportunity: CanonicalOpportunity,
        decision: SnapshotDecision,
    ) -> PersistenceResult:
        normalized = normalize_opportunity(opportunity)
        provenance = normalized.provenance

        opportunity_id: str | None = None

        if decision.action.value != "create":
            opportunity_id = self._find_existing_id(
                normalized
            )

            if opportunity_id is None:
                raise RuntimeError(
                    "Persistence decision requires an "
                    "existing opportunity, but no matching "
                    "database record was found."
                )

        opportunity_data = normalized.model_dump(
            mode="json",
            exclude={"provenance"},
        )

        opportunity_data["raw_metadata"] = (
            provenance.raw_metadata
        )

        change_summary = {
            field: {
                "old": change.old,
                "new": change.new,
            }
            for field, change in decision.changes.items()
        }

        response = self.client.rpc(
            "persist_ingested_opportunity",
            {
                "p_opportunity_id": opportunity_id,
                "p_source_name": provenance.source_name,
                "p_external_id": provenance.external_id,
                "p_source_url": str(
                    provenance.source_url
                ),
                "p_raw_metadata": (
                    provenance.raw_metadata
                ),
                "p_opportunity": opportunity_data,
                "p_content_hash": decision.new_hash,
                "p_content_changed": (
                    decision.action.value
                    == "update_with_snapshot"
                ),
                "p_create_snapshot": (
                    decision.action.value
                    == "update_with_snapshot"
                ),
                "p_change_summary": change_summary,
            },
        ).execute()

        data = response.data

        if not isinstance(data, dict):
            raise RuntimeError(
                "Unexpected response from "
                "persist_ingested_opportunity."
            )

        from uuid import UUID

        return PersistenceResult(
            opportunity_id=UUID(
                str(data["opportunity_id"])
            ),
            created=bool(data["created"]),
            updated=bool(data["updated"]),
            snapshot_created=bool(
                data["snapshot_created"]
            ),
        )
