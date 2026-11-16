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
from gene_annotation_episode.episodic_workflow.root.a108.communication import ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a108.episode_bindings import reference_in_context
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process_records import scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION
from gene_annotation_episode.episodic_workflow.root.a108.library.scientific_process_reports import build_process_result, merge_process_results, report_sources, validate_process_result
from gene_annotation_episode.episodic_workflow.root.a108.library.scientific_support_metadata import support_observation_kinds
from gene_annotation_episode.episodic_workflow.root.a108.library.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry
from gene_annotation_episode.episodic_workflow.root.a108.library.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view, validate_instruction_entry
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process_library import evidence_axis_instruction_view
VERSION = 'scientific_process_episode_v10'
AXIS = 'A108'
ROLE = 'scientific_process'
ROLES = (ROLE,)
_COMMON_TOOLS = ('process.search', 'process.entry', 'process.sources', 'process.tools', 'knowledge.search', 'knowledge.entry', 'knowledge.read', 'episode.history', 'episode.credit', 'episode.annotation_score', 'episode.monitoring_information', 'episode.estimate_wait', 'shared.request_information', 'shared.publish_information', 'shared.resolve_information_need', 'shared.read_information', 'shared.list_information')
_REFERENCE = {'type': 'string', 'pattern': '^[a-z][a-z_]*_[a-f0-9]{24,64}$'}
_SHA256 = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
_SCIENTIFIC_NAMESPACES = frozenset({'scientific_invocation', 'scientific_preparation', 'scientific_process_library', 'scientific_option_digest', 'scientific_credit_binding'})

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
    return obj({'version': {'const': 'scientific_process_option_ref_v1'}, 'library_id': _SHA256, 'slot': {'const': slot}, 'option_id': {'type': 'string', 'pattern': '^' + prefix + '[0-9]+$'}, 'entry_sha256': _SHA256})
_EVIDENCE_AXIS = _ref_schema('evidence_axis', 'A')
_EVIDENCE_AXIS['properties']['option_id'] = {'const': AXIS}
_THOUGHT_REF = _ref_schema('thought_pattern', 'P')
_TOOL_SELECTOR = obj({'name': {'type': 'string', 'minLength': 1}, 'resources': {'enum': ['api', 'local', 'hpc']}})
_TOOL_INFO = obj({**_TOOL_SELECTOR['properties'], 'description': {'type': 'string', 'minLength': 1}, 'instructions': {'type': 'string', 'minLength': 1}})
_SELECTION = obj({'version': {'const': SELECTION_VERSION}, 'evidence_axis': _EVIDENCE_AXIS, 'thought_pattern': _THOUGHT_REF, 'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
_CANONICAL_SELECTION = deepcopy(_SELECTION)
_CANONICAL_SELECTION['properties']['child_tool_info']['items'] = _TOOL_INFO
_REVISION_ORIGIN = obj({'version': {'const': 'scientific_process_revision_origin_v1'}, 'parent_invocation_ref': {'type': 'string', 'pattern': '^scientific_invocation_[a-f0-9]{24}$'}, 'preparation_operation_ref': {'type': 'string', 'pattern': '^operation_[a-f0-9]{24}$'}})
_EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task_v1'}, 'kind': {'const': 'whole_axis_findings'}, 'evidence_axis': {'const': AXIS}, 'credit_unit': {'type': 'number', 'exclusiveMinimum': 0, 'description': 'Use the finding unit in the explicitly configured credit definition for this exact task; do not select or change its cutoff.'}})
_ASSIGNMENT = obj({'selection': _SELECTION, 'proposed_annotation_ref': {**_REFERENCE, 'description': 'The proposed annotation this task evaluates.'}, 'evidence_refs': {'type': 'array', 'items': _REFERENCE, 'uniqueItems': True}, 'constraints': {'type': 'object'}, 'context': {'type': 'object', 'properties': {'evidence_task': _EVIDENCE_TASK}}, 'revision_origin': _REVISION_ORIGIN}, required=['selection', 'evidence_refs', 'constraints', 'context'])
_RECORDED_ASSIGNMENT = deepcopy(_ASSIGNMENT)
_RECORDED_ASSIGNMENT['properties']['selection'] = _CANONICAL_SELECTION
_REVISION_ARGUMENTS = obj({'thought_pattern': _THOUGHT_REF, 'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
