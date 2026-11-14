"""Fill one ordinary scientific Episode role from composable A/P options and actual retrieved tools.

The binding supplies the decision problem and actual callable restrictions.
The common Episode loop owns iteration; each assigned scientific task owns credit.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import re

from gene_annotation_episode.episodic_workflow.root.communication import (ReportBoundaryError, interpretation_schema, plain,
    validate_closed_schema, validate_form)
from gene_annotation_episode.domain import ContractError, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
from gene_annotation_episode.episodic_workflow.root.scientific_process_records import (scientific_digest, scientific_invocation_ref,
    validate_child_selection, validate_filled_process, validate_option_ref,
    validate_revision_origin, validate_selection, selection_fields, selector_selection,
    SELECTION_VERSION, LEGACY_SELECTION_VERSION)
from gene_annotation_episode.episodic_workflow.root.scientific_process.report_generation import (build_process_result, merge_process_results,
    report_sources)
from gene_annotation_episode.episodic_workflow.root.scientific_process_reports import validate_process_result
from gene_annotation_episode.episodic_workflow.root.scientific_support_metadata import (SUPPORT_ENTRY_VERSION,
    support_observation_kinds, validate_support_entry)
from gene_annotation_episode.episodic_workflow.root.evidence_axis_contracts import (VERSION as EVIDENCE_AXIS_VERSION,
    validate_evidence_axis_entry)
from gene_annotation_episode.episodic_workflow.root.evidence_axis_instructions import (VERSION as INSTRUCTION_VERSION,
    instruction_view, validate_instruction_entry)
from gene_annotation_episode.episodic_workflow.root.scientific_process_library import evidence_axis_instruction_view
from gene_annotation_episode.episodic_workflow.root.library.alignment_site_projection_requests import alignment_site_fact_sources, requested_site_projections
from gene_annotation_episode.episodic_workflow.root.library.alignment_site_returns import project_site_action_return, validate_frozen_site_return
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_returns import (restriction_mapping_fact_sources,
    requested_restriction_projections, project_restriction_action_return,
    validate_frozen_restriction_return)
from gene_annotation_episode.episodic_workflow.root.library.molecular_result_facts import molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return
from gene_annotation_episode.episodic_workflow.root.protein_structure_action_records import FACT_SOURCES as PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return


def original_axis_task_projector(axis, assignment, *, merged_a102=False):
    """Resolve the commissioned scientific task's own saved credit definition.

    The root calls this only after authenticating the original child assignment.
    It does not choose a continuation policy or infer credit from a report.
    """
    assigned = plain(assignment)
    context = assigned.get('context', {})
    if axis == 'A101':
        from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.native_correspondence_credit import A101SequenceCredit
        return A101SequenceCredit()
    if axis == 'A102':
        from gene_annotation_episode.episodic_workflow.root.a102.a102_credit import (A102StructuralCredit, A102FeatureGeometryCredit,
            A102FunctionalContrastCredit, A102ReferenceAttributionCredit,
            A102LocalTraitCredit, A102InterfaceContactCredit)
        if not merged_a102:
            return A102StructuralCredit()
        from gene_annotation_episode.episodic_workflow.root.a102.a102_structural_evidence import credit_projector, task_context
        task = context.get('a102_task')
        if task is not None and (not isinstance(task, dict)
                or task != task_context(task.get('name'))):
            raise ContractError('a102_original_task_definition_required')
        if task is None:
            return credit_projector(assigned)
        local = {
            'functional_feature_geometry': A102FeatureGeometryCredit,
            'functional_contrast': A102FunctionalContrastCredit,
            'reference_attribution': A102ReferenceAttributionCredit,
            'local_trait_attribution': A102LocalTraitCredit,
            'interface_constraints': A102InterfaceContactCredit,
        }.get(task['name'])
        return local() if local is not None else credit_projector(assigned)
    if axis == 'A103':
        from gene_annotation_episode.episodic_workflow.root.a103.a103_credit import A103ContextCredit
        return A103ContextCredit()
    if axis == 'A104':
        from gene_annotation_episode.episodic_workflow.root.a104.a104_credit import (A104EvolutionaryCredit, A104PanelIdentityCredit,
            A104AlignmentSuitabilityCredit, A104RobustnessCredit)
        from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import TASKS
        task = context.get('a104_task')
        if task is not None and (not isinstance(task, dict) or task.get('name') not in TASKS
                or 'allowed_tasks' in task and task['allowed_tasks'] != list(TASKS)):
            raise ContractError('a104_original_task_definition_required')
        if task is None:
            return A104EvolutionaryCredit()
        return {'panel_identity': A104PanelIdentityCredit,
            'alignment_suitability': A104AlignmentSuitabilityCredit,
            'robustness': A104RobustnessCredit}.get(task['name'], A104EvolutionaryCredit)()
    if axis in {'A105', 'A106', 'A108'}:
        task = context.get('evidence_task')
        if (not isinstance(task, dict) or set(task) != {
                'version', 'kind', 'evidence_axis', 'credit_unit'}
                or task['version'] != 'evidence_axis_task_v1'
                or task['kind'] != 'whole_axis_findings' or task['evidence_axis'] != axis):
            raise ContractError('original_axis_finding_task_required')
        from gene_annotation_episode.episodic_workflow.root.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
        return ScientificFindingProgress(FindingProgressPolicy(task['credit_unit']))
    if axis in {'A107', 'A110'}:
        from .finding_progress import finding_progress
        from gene_annotation_episode.episodic_workflow.root.library.component_investigation_instructions import task_context
        task = context.get(axis.lower() + '_task')
        if task is not None and (not isinstance(task, dict)
                or task != task_context(axis, task.get('name'))):
            raise ContractError('component_axis_original_task_context_mismatch')
        return finding_progress()
    raise ContractError('scientific_axis_credit_not_declared:' + axis)


VERSION = "scientific_process_episodes_v10"
ROLE = "scientific_process"
ROLES = (ROLE,)
_COMMON_TOOLS = ("process.search", "process.entry", "process.sources", "process.tools",
    "knowledge.search", "knowledge.entry", "knowledge.read", "episode.history",
    "episode.credit", "episode.annotation_score", "episode.monitoring_information",
    "episode.estimate_wait", "shared.request_information", "shared.publish_information",
    "shared.resolve_information_need", "shared.read_information", "shared.list_information")
_REFERENCE = {"type": "string", "pattern": r"^[a-z][a-z_]*_[a-f0-9]{24,64}$"}
_SHA256 = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
_SCIENTIFIC_NAMESPACES = frozenset({"scientific_invocation", "scientific_preparation",
    "scientific_process_library", "scientific_option_digest", "scientific_credit_binding"})
# Retained original compatibility declaration; the current descriptor reads
# DEFINITION_FILES from definition_inputs.py. This tuple is not current source
# membership, and its historical names do not select or restore implementations.
_IMPLEMENTATION_FILES = ("scientific_process_episodes.py", "scientific_process_setup.py",
    "episode_work_report.py", "api_error_feedback.py", "a101_work_report.py", "scientific_process_prompt.py",
    "scientific_process_records.py", "scientific_process_reports.py",
    "scientific_process_provenance.py", "scientific_tool_library.py",
    "scientific_support_metadata.py", "scientific_process_library.py",
    "evidence_axis_instructions.py", "episode_services.py", "resource_tool_information.py",
    "execution_planning.py", "execution_memory.py", "execution_guidance.py",
    "scientific_tool_retrieval.py", "tool_schema_validation.py",
    "alignment_site_action_records.py", "alignment_site_returns.py",
    "alignment_site_native.py", "episode_return_records.py",
    "restriction_mapping_action_records.py", "restriction_mapping_references.py",
    "restriction_mapping_returns.py", "restriction_mapping_bound_contracts.py",
    "restriction_mapping_publication.py", "restriction_mapping_jobs.py",
    "restriction_mapping_inputs.py", "restriction_mapping_worker.py",
    "restriction_mapping_contracts.py", "restriction_mapping_readers.py",
    "restriction_mapping_registry.py", "restriction_mapping_selection.py",
    "episode_contract_information.py", "episode_journal.py", "native_file_capture.py",
    "molecular_measurement_tools.py", "molecular_result_facts.py",
    "tf_binding_result_contracts.py", "tf_binding_measurements.py", "tf_binding_tools.py",
    "communication.py", "molecular_reference_privacy.py", "episode_receipts.py",
    "liftover_contracts.py", "liftover_measurements.py", "liftover_tools.py",
    "circular_dichroism_contracts.py", "circular_dichroism_measurements.py",
    "circular_dichroism_tools.py", "protein_structure_action_records.py",
    "a101_scoring.py", "a101_credit.py", "a101_investigation.py", "a102_investigation.py", "a102_scoring.py",
    "a102_credit.py", "a102_publication.py", "a102_structures.py", "a102_tools.py",
    "a102_structural_evidence.py", "a102_structural_catalog.py", "a102_structural_workflow.py",
    "a102_experimental_evidence.py", "a102_structural_report.py",
    "a102_native_worker.py", "a102_structural_bridge.py", "a102_hpc.py", "a102_hpc_worker.py",
    "hpc_result_receipts.py", "shared_information.py", "shared_information_results.py",
    "a102_resources.py", "protein_structure_sequences.py", "a102_attachments.py", "sequence_attribution.py",
    "a103_investigation.py", "a103_tools.py", "a103_scoring.py", "a103_publication.py",
    "a103_attachments.py", "a103_credit.py", "a103_native_worker.py", "a103_channels.py", "a103_detection.py",
    "a103_hpc.py", "a103_hpc_worker.py", "a103_native_requests.py", "hpc_scientific_commission.py", "homology_query.py",
    "a104_investigation.py", "a104_tools.py", "a104_scoring.py", "a104_publication.py", "a104_attachments.py",
    "a104_credit.py", "a104_hpc.py", "a104_hpc_worker.py", "a104_interpretation.py", "a104_characterization.py",
    "a107_investigation.py", "a107_tools.py", "a107_qualification.py", "a107_expression_components.py", "a107_expression_contracts.py",
    "a107_genomic_detection_hpc.py", "a107_genomic_detection_native.py",
    "a110_investigation.py", "a110_tools.py", "a110_chemical_accounting.py", "a110_qualification.py", "a110_chemical_contracts.py",
    "a110_experimental_qualification.py", "component_axis_cell_receipts.py",
    "a110_fba_hpc.py", "a110_fba_native.py", "partner_chemical_tools.py", "component_sequence_attribution.py",
    "component_axis_workflow.py", "component_axis_reports.py", "component_axis_native_contracts.py", "inprocess_replay.py",
    "component_axis_source_access.py", "component_axis_execution_context.py",
    "component_axis_native_tools.py", "component_axis_native_hpc.py", "component_axis_native_worker.py")
_ITC_PARAMETER_SOURCE = "itc_binding_parameters"


def _object(value, code):
    if not isinstance(value, Mapping):
        raise ContractError(code)
    try:
        scientific_digest(value)
        result = json.loads(json.dumps(plain(value), allow_nan=False))
        return result
    except (TypeError, ValueError, OverflowError) as error:
        raise ContractError(code) from error


def _ref_schema(slot, prefix):
    return obj({"version": {"const": "scientific_process_option_ref_v1"},
        "library_id": _SHA256, "slot": {"const": slot},
        "option_id": {"type": "string", "pattern": "^" + prefix + "[0-9]+$"},
        "entry_sha256": _SHA256})


_ANNOTATION_REF = _ref_schema("annotation_distinction", "A")
_EVIDENCE_AXIS = deepcopy(_ANNOTATION_REF)
_EVIDENCE_AXIS['properties']['slot'] = {'enum': ['evidence_axis', 'annotation_distinction']}
_THOUGHT_REF = _ref_schema("thought_pattern", "P")
_TOOLS = {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True}
_LEGACY_SELECTION = obj({"version": {"const": LEGACY_SELECTION_VERSION},
    "annotation_ref": _ANNOTATION_REF, "thought_ref": _THOUGHT_REF,
    "tools": _TOOLS})
_TOOL_SELECTOR = obj({'name': {'type': 'string', 'minLength': 1},
                     'resources': {'enum': ['api', 'local', 'hpc']}})
_TOOL_INFO = obj({**_TOOL_SELECTOR['properties'],
    'description': {'type': 'string', 'minLength': 1},
    'instructions': {'type': 'string', 'minLength': 1}})
_SELECTION = obj({'version': {'const': SELECTION_VERSION},
    'evidence_axis': _EVIDENCE_AXIS, 'thought_pattern': _THOUGHT_REF,
    'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
_CANONICAL_SELECTION = deepcopy(_SELECTION)
_CANONICAL_SELECTION['properties']['child_tool_info']['items'] = _TOOL_INFO
_REVISION_ORIGIN = obj({"version": {"const": "scientific_process_revision_origin_v1"},
    "parent_invocation_ref": {"type": "string",
        "pattern": "^scientific_invocation_[a-f0-9]{24}$"},
    "preparation_operation_ref": {"type": "string", "pattern": "^operation_[a-f0-9]{24}$"}})
_EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task_v1'},
    'kind': {'const': 'whole_axis_findings'},
    'evidence_axis': {'enum': ['A105', 'A106', 'A108']},
    'credit_unit': {'type': 'number', 'exclusiveMinimum': 0,
        'description': 'Use the finding unit in the explicitly configured credit definition for this exact task; do not select or change its cutoff.'}})
_ASSIGNMENT = obj({"selection": _SELECTION,
    "proposed_annotation_ref": {**_REFERENCE, "description": "The proposed annotation this task evaluates."},
    "evidence_refs": {"type": "array", "items": _REFERENCE, "uniqueItems": True},
    "constraints": {"type": "object"}, "context": {"type": "object",
        'properties': {'evidence_task': _EVIDENCE_TASK}},
    "revision_origin": _REVISION_ORIGIN},
    required=["selection", "evidence_refs", "constraints", "context"])
_RECORDED_ASSIGNMENT = deepcopy(_ASSIGNMENT)
_RECORDED_ASSIGNMENT['properties']['selection'] = {'anyOf': [_CANONICAL_SELECTION, _LEGACY_SELECTION]}
_REVISION_ARGUMENTS = obj({'thought_pattern': _THOUGHT_REF,
    'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
_LEGACY_REVISION_ARGUMENTS = obj({"thought_ref": _THOUGHT_REF, "tools": _TOOLS})


