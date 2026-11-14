"""One selected retained comparison action inside the existing results role.

Original inputs and actions establish authority. The separate worker owns only
deterministic calculation/publication. No native observation or acquisition runs.
"""
from __future__ import annotations

from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import authenticate_rna_results_commission
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_contracts import CALCULATOR_VERSION, SELECTOR_VERSION, validate_rna_comparison_issue, validate_rna_comparison_selector
from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_operands import RNAComparisonInputError, SAVED_REFERENCE_FIELDS, _require, resolve_rna_comparison_operands, validate_rna_comparison_selected_inputs
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_views import PROJECTION_SOURCE

VERSION = "rna_structure_comparison_result_receipt_v1"
IDENTIFIER_NAMESPACES = ("rna_comparison_receipt", "rna_comparison_calculation")
FIELDS = {"version", "run_id", "episode_id", "scope_key", "assignment_digest", "operation_key",
    "tool_name", "arguments", "selected_action_digest", "anchor_handoff_ref", "selector",
    "original_receipt_keys", "selected_input_digests", "comparison_sheet_artifact_ref",
    "comparison_sheet_sha256", "components_artifact_ref", "components_sha256", "calculator_version",
    "projection_rows", "issues", "preparation_failure", "delivery_complete"}
PREPARED_COPY_FIELDS = ("original_receipt_keys", "selected_input_digests",
    "comparison_sheet_artifact_ref", "comparison_sheet_sha256", "components_artifact_ref",
    "components_sha256", "calculator_version", "projection_rows", "issues", "preparation_failure", "delivery_complete")
VALIDATION_KEYS = ["selected_original_operand_authority", "retained_operand_custody",
    "requested_comparison_projection_or_explicit_unavailability"]
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import POLICY, validate_recorded_rna_policy


def result_receipt_key(body):
    return "rna_comparison_receipt:" + digest({key: body[key] for key in ("run_id", "episode_id", "operation_key")})


def operation_catalog():
    return [{"name": "execution.results.status", "description":
        "Check only the explicitly selected retained RNA inputs and recorded comparison receipts.", "input_schema": obj({})},
        {"name": "execution.results.collect", "description":
        "Calculate the assigned comparison from independently received retained sheets and return exactly its selected projections.",
        "input_schema": obj({})}]


def _original_keys(selector):
    return [member["saved_input" if member["kind"] == "saved_sheet" else "failure"]["result_receipt_key"]
        for member in selector["question"]["membership"] if member["kind"] in {"saved_sheet", "received_failure"}]


