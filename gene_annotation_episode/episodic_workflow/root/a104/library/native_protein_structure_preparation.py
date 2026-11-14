"""Execute one selected retained-result worker and preserve its byte custody.

The caller owns input authority, publication and episode observations. This
adapter owns one existing native reservation. A diagnostic artifact is never a
grant to use scientific values; only the qualified worker manifest names usable
outputs, subject to the worker's unchanged scientific state and issues.
"""
from __future__ import annotations
from typing import Literal, TypedDict
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_contracts import ArtifactRef, StructuredIssue
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_result_worker import ProteinResultWorkerPlan, ProteinResultWorkerResult

class ProteinWorkerDiagnostic(TypedDict):
    filename: Literal['native-result.json', 'sheet.json', 'components.json', 'worker-result.json']
    artifact_ref: ArtifactRef

class ProteinWorkerFailure(TypedDict):
    code: str
    phase: str | None
    diagnostic: dict | None
    operational: dict | None

class ProteinWorkerExecution(TypedDict):
    version: Literal['protein_structure_worker_execution_v1']
    outcome: Literal['returned', 'failed']
    returncode: int | None
    metadata: dict | None
    failure: ProteinWorkerFailure | None
    stdout_artifact_ref: ArtifactRef | None
    stderr_artifact_ref: ArtifactRef | None
    handle_artifact_ref: ArtifactRef | None

class PreparedProteinWorker(TypedDict):
    version: Literal['protein_structure_prepared_worker_v1']
    plan_artifact_ref: ArtifactRef
    execution_receipt_artifact_ref: ArtifactRef
    worker_result_artifact_ref: ArtifactRef | None
    diagnostic_files: list[ProteinWorkerDiagnostic]
    issues: list[StructuredIssue]

class ValidatedProteinWorker(TypedDict):
    prepared: PreparedProteinWorker
    plan: ProteinResultWorkerPlan
    execution: ProteinWorkerExecution
    result: ProteinResultWorkerResult | None
