from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from phd_agent.ingestion.deduplication import (
    DeduplicationResult,
    MatchReason,
    compare_opportunities,
)
from phd_agent.ingestion.hashing import (
    HASH_FIELDS,
    compute_content_hash,
)
from phd_agent.ingestion.models import CanonicalOpportunity
from phd_agent.ingestion.normalization import normalize_opportunity


class SnapshotAction(StrEnum):
    CREATE = "create"
    UNCHANGED = "unchanged"
    UPDATE_WITH_SNAPSHOT = "update_with_snapshot"


@dataclass(frozen=True)
class FieldChange:
    old: Any
    new: Any


@dataclass(frozen=True)
class SnapshotDecision:
    action: SnapshotAction
    match_reason: MatchReason
    old_hash: str | None
    new_hash: str
    changes: dict[str, FieldChange]

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)


def build_change_summary(
    existing: CanonicalOpportunity,
    incoming: CanonicalOpportunity,
) -> dict[str, FieldChange]:
    """
    Compare meaningful normalized opportunity fields.

    Source provenance is intentionally excluded because source observations
    are persisted separately from canonical opportunity content.
    """

    existing_normalized = normalize_opportunity(existing)
    incoming_normalized = normalize_opportunity(incoming)

    existing_data = existing_normalized.model_dump(
        mode="json",
        exclude={"provenance"},
    )
    incoming_data = incoming_normalized.model_dump(
        mode="json",
        exclude={"provenance"},
    )

    changes: dict[str, FieldChange] = {}

    for field in HASH_FIELDS:
        old_value = existing_data[field]
        new_value = incoming_data[field]

        if old_value != new_value:
            changes[field] = FieldChange(
                old=old_value,
                new=new_value,
            )

    return changes


def decide_snapshot_action(
    incoming: CanonicalOpportunity,
    existing: CanonicalOpportunity | None,
) -> SnapshotDecision:
    """
    Decide how an incoming opportunity should affect persistence.

    No existing opportunity means CREATE.

    Matching identity with unchanged content means UNCHANGED.

    Matching identity with changed content means UPDATE_WITH_SNAPSHOT.

    If the supplied existing opportunity does not match the incoming
    opportunity, the incoming record is treated as a new opportunity.
    """

    incoming_hash = compute_content_hash(incoming)

    if existing is None:
        return SnapshotDecision(
            action=SnapshotAction.CREATE,
            match_reason=MatchReason.NO_MATCH,
            old_hash=None,
            new_hash=incoming_hash,
            changes={},
        )

    match: DeduplicationResult = compare_opportunities(
        existing,
        incoming,
    )

    if not match.is_duplicate:
        return SnapshotDecision(
            action=SnapshotAction.CREATE,
            match_reason=MatchReason.NO_MATCH,
            old_hash=None,
            new_hash=incoming_hash,
            changes={},
        )

    existing_hash = compute_content_hash(existing)

    if existing_hash == incoming_hash:
        return SnapshotDecision(
            action=SnapshotAction.UNCHANGED,
            match_reason=match.reason,
            old_hash=existing_hash,
            new_hash=incoming_hash,
            changes={},
        )

    changes = build_change_summary(
        existing,
        incoming,
    )

    return SnapshotDecision(
        action=SnapshotAction.UPDATE_WITH_SNAPSHOT,
        match_reason=match.reason,
        old_hash=existing_hash,
        new_hash=incoming_hash,
        changes=changes,
    )
