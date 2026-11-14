"""Original substantive ordinary-tool methods: tool_source_publication."""
from __future__ import annotations
from datetime import datetime
from datetime import timezone
from typing import Any
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import RECORD_SCHEMAS
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.domain import validate_schema

class ToolSourcePublication:
    def _source(self, provider: str, body: Any, *, snapshot: SourceSnapshot | None = None,
                text: str | None = None, accession: str | None = None, software_version: str | None = None,
                parent_source_refs: list[str] | None = None,
                stdout_ref: str | None = None, stderr_ref: str | None = None,
                auxiliary_artifact_refs: list[str] | None = None,
                operand_refs: list[str] | None = None, query_selection_ref: str | None = None,
                publication_identifiers: list[dict] | None = None,
                tool_grading: dict | None = None) -> dict:
        artifact = self.store.artifact(snapshot.content if snapshot else canonical(body),
                                       snapshot.media_type if snapshot else "application/json")
        if tool_grading is not None:
            from .library.tool_grading_artifacts import retain_tool_grading
            retained = retain_tool_grading(self.store, provider=provider,
                native_artifact_ref=artifact, grading=tool_grading)
            auxiliary_artifact_refs = list(dict.fromkeys([
                *(auxiliary_artifact_refs or ()), retained]))
        request = None
        if snapshot:
            request = self.store.artifact(canonical({"request": snapshot.request, "transport": snapshot.transport}), "application/json")
            if software_version is None and provider not in {'alphafold', 'emdb', 'rcsb_pdb',
                    'string', 'kegg', 'reactome', 'quickgo', 'pubchem', 'hpa', 'ucsc', 'ensembl', 'eva', 'gnomad',
                    'public.ncbi.entrez', 'public.ncbi.geo', 'public.ncbi.sra.file', 'public.jaspar', 'public.encode', 'public.screen'}:
                if snapshot.service == "uniprot":
                    # Source custody precedes projection, including an absent or
                    # malformed transport envelope. Its complete original value
                    # remains in request_ref; the old version label is optional.
                    transport = snapshot.transport if isinstance(snapshot.transport, dict) else {}
                    response = transport.get("response")
                    headers = (response.get("headers", transport.get("headers"))
                               if isinstance(response, dict) else transport.get("headers"))
                    candidate = headers.get("x-uniprot-release") if isinstance(headers, dict) else None
                    try:
                        validate_schema(candidate, RECORD_SCHEMAS["source"]["properties"]["version"])
                    except ContractError:
                        candidate = None
                    software_version = candidate
                elif snapshot.service not in {"rcsb_pdb", "alphafold", "emdb", "string", "kegg", "reactome", "quickgo", "pubchem", "hpa", "ucsc", "ensembl", "eva", "gnomad"}:
                    details = snapshot.transport.get("job_details") or {}
                    database = details.get("database")
                    software_version = (database.get("version") if isinstance(database, dict) else None) or snapshot.transport.get("response", {}).get("headers", {}).get("x-uniprot-release")
        return self._put("source", {
            "provider": provider, "accession": accession, "uri": snapshot.url if snapshot else None,
            "artifact_ref": artifact, "text_ref": self.store.artifact(text, "text/plain") if text is not None else None,
            "request_ref": request, "version": software_version,
            "retrieved_at": snapshot.retrieved_at if snapshot else datetime.now(timezone.utc).isoformat(),
            **({"parent_source_refs": parent_source_refs} if parent_source_refs is not None else {}),
            **({"stdout_ref": stdout_ref} if stdout_ref is not None else {}),
            **({"stderr_ref": stderr_ref} if stderr_ref is not None else {}),
            **({"auxiliary_artifact_refs": auxiliary_artifact_refs} if auxiliary_artifact_refs is not None else {}),
            **({"operand_refs": operand_refs} if operand_refs is not None else {}),
            **({"query_selection_ref": query_selection_ref} if query_selection_ref is not None else {}),
            **({'publication_identifiers': publication_identifiers} if publication_identifiers else {}),
        }, origin="external" if snapshot else "tool")

    def _observation(self, kind: str, subjects: list[str], source: dict, values: list[dict],
                     *, references: list[str] | None = None, dependencies: list[str] | None = None,
                     operand_intervals: list[dict] | None = None) -> dict:
        return self._put("observation", {"kind": kind, "subject_refs": subjects,
            "source_subject_refs": references or [], "source_ref": source["id"], "measurements": values,
            "dependencies": dependencies or [], "anchor": None,
            "operand_intervals": operand_intervals}, origin="tool")

    def _put(self, kind: str, record: dict, **kwargs: Any) -> dict:
        result = self.store.put(kind, record, **kwargs)
        self._written.append(result["id"])
        return result

    def _begin_publication_batch(self, *, failures: bool = False) -> dict:
        """Declare generated publication metadata, never a scientific verdict.

        Mutable counters belong to this selected operation. Keeping the same
        declaration until _save also preserves truthful partial-publication
        counts when a later native row fails.
        """
        batch = {"representation": "native_publications_v1", "published_rows_total": 0,
                 "failure_rows_total": 0 if failures else None, "observation_query": None}
        self._publication_batch.set(batch)
        return batch

    @staticmethod
    def _batch_observations(batch: dict, source_ref: str) -> None:
        batch["observation_query"] = {"kind": "observation", "references": [source_ref], "offset": 0}

    def _source_bytes(self, provider: str, content: bytes, media_type: str, metadata: dict) -> dict:
        artifact = self.store.artifact(content, media_type)
        return self._put("source", {"provider": provider, "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact if media_type.startswith("text/") else None,
            "request_ref": self.store.artifact(canonical(metadata), "application/json"),
            "version": metadata.get("software_version") or metadata.get("adapter_version"),
            "parent_source_refs": [metadata["parent_source_ref"]],
            "stdout_ref": metadata["stdout_ref"], "stderr_ref": metadata["stderr_ref"],
            "retrieved_at": metadata.get("finished_at") or datetime.now(timezone.utc).isoformat()}, origin="tool")

