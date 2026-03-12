"""Collection context resolution for research runs."""

from __future__ import annotations

from medclaw.evidence.store import EvidenceStore
from medclaw.orchestrator.workflow_registry import WorkflowRegistry


class CollectionService:
    """Resolve saved collection context and workflow preferences."""

    def __init__(self, evidence_store: EvidenceStore, workflow_registry: WorkflowRegistry):
        self.evidence_store = evidence_store
        self.workflow_registry = workflow_registry

    def resolve_context(self, collection: str | None) -> dict[str, object] | None:
        """Load saved collection context when available and preserve ad-hoc collection names."""
        if not collection or not collection.strip():
            return None

        normalized = collection.strip()
        try:
            return self.evidence_store.load_collection_manifest(normalized)
        except FileNotFoundError:
            return {"name": normalized}

    def resolve_workflows(self, collection: str | None) -> list[str]:
        """Resolve preferred workflows for a collection, keeping only valid ids."""
        collection_context = self.resolve_context(collection)
        if not collection_context:
            return []

        preferred = collection_context.get("preferred_workflows", [])
        if not isinstance(preferred, list):
            return []
        return self.workflow_registry.filter_valid_workflow_ids(preferred)
