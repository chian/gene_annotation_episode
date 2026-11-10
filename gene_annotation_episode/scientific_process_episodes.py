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

from .communication import (ReportBoundaryError, interpretation_schema, plain,
    validate_closed_schema, validate_form)
from .domain import ContractError, identity, obj, validate_schema
from .episode_bindings import reference_in_context
from .scientific_process_records import (scientific_digest, scientific_invocation_ref,
    validate_child_selection, validate_filled_process, validate_option_ref,
    validate_revision_origin, validate_selection, selection_fields, selector_selection,
    SELECTION_VERSION, LEGACY_SELECTION_VERSION)
from .scientific_process_reports import (build_process_result, merge_process_results,
    report_sources, validate_process_result)
from .scientific_support_metadata import (SUPPORT_ENTRY_VERSION,
    support_observation_kinds, validate_support_entry)
from .evidence_axis_contracts import (VERSION as EVIDENCE_AXIS_VERSION,
    validate_evidence_axis_entry)
from .evidence_axis_instructions import (VERSION as INSTRUCTION_VERSION,
    instruction_view, validate_instruction_entry)
from .scientific_process_library import evidence_axis_instruction_view
from .alignment_site_returns import (alignment_site_fact_sources,
    requested_site_projections, project_site_action_return, validate_frozen_site_return)
from .restriction_mapping_returns import (restriction_mapping_fact_sources,
    requested_restriction_projections, project_restriction_action_return,
    validate_frozen_restriction_return)
from .molecular_result_facts import (molecular_fact_sources, merge_molecular_facts,
    requested_molecular_fact_sources, requested_molecular_fact_fields,
    validate_frozen_molecular_return)
from .protein_structure_action_records import (
    FACT_SOURCES as PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources,
    merge_protein_structure_action_facts, requested_protein_structure_action_fields,
    validate_frozen_protein_structure_action_return)


def original_axis_task_projector(axis, assignment, *, merged_a102=False):
    """Resolve the commissioned scientific task's own saved credit definition.

    The root calls this only after authenticating the original child assignment.
    It does not choose a continuation policy or infer credit from a report.
    """
    assigned = plain(assignment)
    context = assigned.get('context', {})
    if axis == 'A101':
        from .a101_credit import A101SequenceCredit
        return A101SequenceCredit()
    if axis == 'A102':
        from .a102_credit import (A102StructuralCredit, A102FeatureGeometryCredit,
            A102FunctionalContrastCredit, A102ReferenceAttributionCredit,
            A102LocalTraitCredit, A102InterfaceContactCredit)
        if not merged_a102:
            return A102StructuralCredit()
        from .a102_structural_evidence import credit_projector, task_context
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
        from .a103_credit import A103ContextCredit
        return A103ContextCredit()
    if axis == 'A104':
        from .a104_credit import (A104EvolutionaryCredit, A104PanelIdentityCredit,
            A104AlignmentSuitabilityCredit, A104RobustnessCredit)
        from .a104_investigation import TASKS
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
        from .investigation_progress import FindingProgressPolicy, ScientificFindingProgress
        return ScientificFindingProgress(FindingProgressPolicy(task['credit_unit']))
    if axis in {'A107', 'A110'}:
        from .component_axis_workflow import finding_progress, task_context
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


class ScientificProcessEpisodes:
    """One recursive C7 role with parent-selected A/P and actual tool assignment data."""

    roles = ROLES
    entry_roles = ROLES

    def __init__(self, services, *, library, tool_library, child_roles, tool_retrieval=None,
                 contract_information_profile=None, yield_bindings=None):
        if (not isinstance(child_roles, (tuple, list)) or not child_roles
                or any(not isinstance(role, str) or not role for role in child_roles)
                or len(set(child_roles)) != len(child_roles) or ROLE not in child_roles):
            raise ContractError("scientific_child_roles_invalid")
        self.services, self.library, self.tool_library = services, library, tool_library
        self._child_roles = tuple(child_roles)
        self._library_record = _object(library.as_record(), "scientific_library_invalid")
        self._tools_record = _object(tool_library.as_record(), "scientific_tool_library_invalid")
        axes = [header['option_ref'] for header in library.headers()
                if header['option_ref']['slot'] in ('evidence_axis', 'annotation_distinction')]
        # This existing runtime capability is binding-wide. Opt in only for a
        # wholly instruction-only publication; legacy and mixed catalogs retain
        # their original default instruction composition.
        self.replaces_default_instructions = bool(axes) and all(
            library.resolve(reference).get('entry_version') == INSTRUCTION_VERSION
            for reference in axes)
        from .scientific_tool_retrieval import configuration
        self.tool_retrieval = configuration(tool_retrieval)
        from .composition_information import CONTRACT_INFORMATION_PROFILE
        if contract_information_profile not in (None, CONTRACT_INFORMATION_PROFILE):
            raise ContractError('unsupported_scientific_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        self._yield_bindings = (None if yield_bindings is None else
            _object(yield_bindings, 'scientific_yield_bindings_invalid'))
        if self._yield_bindings is not None:
            if not isinstance(self._yield_bindings, dict):
                raise ContractError('scientific_yield_bindings_invalid')
            from .numerical import (BoundedYieldController, CompletionYieldController,
                YieldController, YieldParameters)
            for task, declaration in self._yield_bindings.items():
                if (not isinstance(task, str) or ':' not in task
                        or not isinstance(declaration, dict)
                        or set(declaration) != {'kind', 'cutoff', 'parameters',
                                                'credit_definition'}
                        or declaration['kind'] not in {'accumulation', 'bounded_quality', 'completion'}
                        or not isinstance(declaration['parameters'], dict)
                        or set(declaration['parameters']) != {'uncertainty_alpha'}
                        or not isinstance(declaration['credit_definition'], dict)
                        or not declaration['credit_definition']):
                    raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
                try:
                    parameters = YieldParameters(**declaration['parameters'])
                    if declaration['kind'] == 'bounded_quality':
                        BoundedYieldController('configuration', 0, declaration['cutoff'], 1., parameters)
                    elif declaration['kind'] == 'completion':
                        CompletionYieldController('configuration', 0, declaration['cutoff'], parameters)
                    else:
                        YieldController('configuration', 0, declaration['cutoff'], parameters)
                except (TypeError, ValueError) as error:
                    raise ContractError('scientific_yield_task_binding_invalid:' + task) from error

    def as_record(self):
        files = _IMPLEMENTATION_FILES
        # Include the axis-specific pure presentation adapters available in
        # this build without requiring unrelated future modules to exist.
        files = (*files, *(name for name in ('a102_work_report.py', 'a103_work_report.py',
            'a104_work_report.py', 'a106_work_report.py', 'a107_work_report.py', 'a110_work_report.py')
            if Path(__file__).with_name(name).is_file()))
        if self._contract_information_profile is not None:
            files = (*files, 'composition_information.py', 'schema_information_text.py')
        implementation = scientific_digest({name: hashlib.sha256(
            Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in files})
        return {"version": VERSION, "binding_id": ROLE,
            "implementation_sha256": implementation, "configuration": {
                "library": deepcopy(self._library_record),
                "tool_library": deepcopy(self._tools_record),
                "child_roles": list(self._child_roles),
                **({"tool_retrieval": deepcopy(self.tool_retrieval)} if self.tool_retrieval else {}),
                **({'contract_information_profile': self._contract_information_profile}
                   if self._contract_information_profile is not None else {}),
                **({'yield_bindings': deepcopy(self._yield_bindings)}
                   if self._yield_bindings is not None else {})}}

    def contract_information_profile(self, context):
        """Expose frozen contract information to scientific commissioning parents."""
        return (self._contract_information_profile
                if context.role in ('annotation', ROLE) else None)

    @property
    def private_yield_binding(self):
        return self._yield_bindings is not None

    @staticmethod
    def _role(role):
        if role != ROLE:
            raise ContractError("scientific_process_role_not_bound")

    def child_roles(self, role):
        self._role(role)
        return self._child_roles

    def required_return_sources(self, parent, role):
        self._role(role)
        if (parent is not None
                and getattr(self.services, 'annotation_task_required', lambda: False)()):
            if len(parent.path) == 1:
                return ('scientific_process_results', 'committed_record_refs')
            return ('committed_record_refs',)
        return ()

    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    def assignment_schema(self, role):
        self._role(role)
        return deepcopy(_ASSIGNMENT)

    def child_assignment_schema(self, parent, role):
        schema = self.assignment_schema(role)
        required = getattr(self.services, 'annotation_task_required', lambda: False)()
        if required:
            schema['required'].append('proposed_annotation_ref')
        schema['allOf'] = [{'if': {'properties': {'selection': {'properties': {
            'evidence_axis': {'properties': {'option_id': {'const': axis}}, 'required': ['option_id']}},
            'required': ['evidence_axis']}}, 'required': ['selection']},
            'then': {'required': ['proposed_annotation_ref'], 'properties': {'context': {
                'required': ['evidence_task'], 'properties': {'evidence_task': {
                    'properties': {'evidence_axis': {'const': axis}}}}}}}}
            for axis in ('A105', 'A106', 'A108')]
        return schema

    def _selection(self, value):
        selection = validate_selection(value)
        fields = selection_fields(selection)
        for key in fields[:2]:
            reference = selection[key]
            if reference["library_id"] != self._library_record["library_id"]:
                raise ContractError("scientific_selection_library_mismatch")
            # Resolution checks the selected body's identity, not merely its ID.
            entry = self.library.resolve(reference)
            if key == fields[0]:
                if entry.get('entry_version') == INSTRUCTION_VERSION:
                    validate_instruction_entry(entry)
                elif entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
                    validate_evidence_axis_entry(entry)
                elif entry.get("entry_version") != SUPPORT_ENTRY_VERSION:
                    raise ContractError("scientific_support_metadata_required")
                else:
                    validate_support_entry(entry)
        if selection['version'] == LEGACY_SELECTION_VERSION:
            self.tool_library.resolve(selection['tools'])
        else:
            self.tool_library.resolve_tool_info(selection['child_tool_info'])
        return selection

    def _assignment(self, value, scope, *, materialize=False, context=None):
        assignment = _object(value, "scientific_assignment_invalid")
        if context is not None and (materialize
                or assignment != plain(context.assignment) or plain(scope) != plain(context.scope)):
            raise ContractError('scientific_filled_identity_mismatch')
        if (materialize and isinstance(assignment.get('selection'), dict)
                and assignment['selection'].get('version') == SELECTION_VERSION):
            # Descriptions and resource-specific instructions are host facts.
            # The model chooses only the exact name/resource identity pair.
            selected = assignment['selection']
            selected['child_tool_info'] = self.tool_library.resolve_tool_info(
                selected.get('child_tool_info'), self._information_catalog(scope))
        validate_schema(assignment, _RECORDED_ASSIGNMENT)
        proposed = assignment.get('proposed_annotation_ref')
        if proposed is not None and not self.services.reference_in_scope(proposed, scope, 'hypothesis'):
            raise ContractError('proposed_annotation_outside_assigned_scope')
        assignment["selection"] = self._selection(assignment["selection"])
        if "revision_origin" in assignment:
            assignment["revision_origin"] = validate_revision_origin(assignment["revision_origin"])
        for reference in assignment["evidence_refs"]:
            if (not re.fullmatch(_REFERENCE["pattern"], reference)
                    or not self.services.reference_in_scope(reference, scope, None)):
                raise ContractError("scientific_evidence_reference_unavailable", detail={
                    "reference": reference})
        # Construction must bind actual current callables before publishing a
        # child or computing its initial credit. Recovery repeats the same
        # comparison, never substituting another operation for a stale name.
        self._tool_resolution_for(assignment['selection'], scope, context=context)
        return assignment

    @staticmethod
    def _invocation(invocation, scope):
        value = _object(invocation, "scientific_invocation_invalid")
        if (set(value) != {"objective", "purpose", "report_schema", "initial_report"}
                or not isinstance(value["objective"], str) or not value["objective"]
                or not isinstance(value["purpose"], str) or not value["purpose"]
                or not isinstance(value["initial_report"], dict)):
            raise ContractError("scientific_invocation_invalid")
        schema = validate_closed_schema(value["report_schema"])
        requested_site_projections(schema)
        requested_restriction_projections(schema)
        requested_molecular_fact_sources(schema)
        validate_schema(value["initial_report"], interpretation_schema(schema))
        return {"objective": value["objective"],
            "scope": _object(scope, "scientific_scope_invalid"),
            "purpose": value["purpose"], "report_schema": schema,
            "initial_report": value["initial_report"]}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if parent is None:
            raise ContractError("scientific_parent_invocation_required")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        selection = plain(selection)
        inherited = getattr(self.services, 'proposed_annotation_for', lambda context: None)(parent)
        if inherited is not None:
            if selection.get('proposed_annotation_ref', inherited) != inherited:
                raise ContractError('child_proposed_annotation_differs_from_original_task')
            selection['proposed_annotation_ref'] = inherited
        required = getattr(self.services, 'annotation_task_required', lambda: False)()
        proposed = selection.get('proposed_annotation_ref')
        if required and proposed is None:
            raise ContractError('scientific_task_requires_proposed_annotation')
        if proposed is not None and proposed not in parent.received_record_refs:
            raise ContractError('proposed_annotation_not_received_by_parent')
        if getattr(parent, 'role', None) == ROLE:
            parent_selection = self._original_selection(parent)
            parent_axis = parent_selection[selection_fields(parent_selection)[0]]['option_id']
            child_selection = _object(selection['selection'], 'scientific_selection_invalid')
            child_axis = _object(child_selection[selection_fields(child_selection)[0]],
                'scientific_axis_reference_required').get('option_id')
            if parent_axis == 'A102' and child_axis != 'A102':
                raise ContractError('a102_cross_axis_descendant_requires_shared_parent')
            if parent_axis == 'A103' and child_axis != 'A103':
                raise ContractError('a103_cross_axis_descendant_requires_shared_parent')
            if parent_axis == 'A104' and child_axis != 'A104':
                raise ContractError('a104_cross_axis_descendant_requires_shared_parent')
            if parent_axis in {'A107', 'A110'} and child_axis != parent_axis:
                raise ContractError('component_axis_cross_axis_descendant_requires_shared_parent')
        assignment = self._assignment(selection, scope, materialize=True)
        if "revision_origin" in assignment:
            self._validate_origin(parent, assignment, owner="self")
        return assignment

    def _validate_origin(self, context, assignment, *, owner):
        origin = validate_revision_origin(assignment["revision_origin"])
        preparation = _object(self.services.scientific_preparation(context,
            origin["preparation_operation_ref"], owner=owner),
            "scientific_revision_preparation_invalid")
        if set(preparation) != {"operation_ref", "owner_invocation_ref", "owner_selection",
                "arguments", "proposal", "revision_origin"}:
            raise ContractError("scientific_revision_preparation_invalid")
        initial = self._selection(preparation["owner_selection"])
        arguments = _object(preparation["arguments"], "scientific_revision_preparation_invalid")
        proposal = validate_child_selection(preparation["proposal"])
        argument_schema = (_LEGACY_REVISION_ARGUMENTS if proposal['selection']['version'] == LEGACY_SELECTION_VERSION
                           else _REVISION_ARGUMENTS)
        validate_schema(arguments, argument_schema)
        prepared_origin = validate_revision_origin(preparation["revision_origin"])
        expected_path = context.path if owner == "self" else context.path[:-1]
        expected_owner = scientific_invocation_ref(context.run_id, expected_path)
        if (preparation["operation_ref"] != origin["preparation_operation_ref"]
                or preparation["owner_invocation_ref"] != expected_owner
                or origin["parent_invocation_ref"] != expected_owner
                or prepared_origin != origin
                or proposal["parent_selection_sha256"] != scientific_digest(initial)
                or proposal["selection"] != assignment["selection"]
                or proposal["selection"] != self._proposed_selection(initial, arguments,
                    proposal['selection']['version'], context.scope)):
            raise ContractError("scientific_revision_preparation_mismatch")

    def prepare_invocation(self, parent, role, inputs, scope, operation_key, *, invocation,
                           closed_context=None):
        original = self._invocation(invocation, scope)
        sources = [node.get('x-source') for node in
            original['report_schema'].get('properties', {}).values()]
        for source in self.required_return_sources(parent, role):
            if sources.count(source) != 1:
                raise ContractError('scientific_child_return_requires_' + source)
        if closed_context is not None:
            # Only an authenticated completed commission can resolve its
            # original frozen tools before reconstructing the closed child.
            # A new invocation still takes the current-catalog path below.
            from .episode_return_records import EpisodeReturnRecords
            self._role(role)
            workflow = getattr(self.services, 'workflow', None)
            if (parent is None or workflow is None
                    or workflow.scientific_process_binding is not self
                    or parent.run_id != workflow.run_id
                    or closed_context.run_id != parent.run_id
                    or closed_context.role != role
                    or closed_context.path[:-1] != parent.path):
                raise ContractError('scientific_closed_commission_conflict')
            records = EpisodeReturnRecords(workflow.store, parent.run_id,
                failure_prefix='scientific_closed_')
            records.authenticate(parent)
            records.authenticate(closed_context)
            match = re.fullmatch(r'child_(0|[1-9][0-9]*)', closed_context.path[-1][1])
            if (match is None or operation_key !=
                    f'{parent.run_id}:{parent.episode_id}:{match[1]}'):
                raise ContractError('scientific_closed_commission_conflict')
            index = int(match[1])
            row = workflow.journal.row('runtime_actions', parent.episode_id, index)
            if row is None or row['result'] is None:
                raise ContractError('scientific_closed_commission_required')
            selected, outcome = json.loads(row['action']), json.loads(row['result'])
            if (not isinstance(outcome, dict) or outcome.get('status') != 'completed'
                    or selected.get('kind') != 'episode_child' or selected.get('role') != role
                    or not records._equal(selected.get('assignment'), inputs)
                    or not records._equal(selected.get('scope'), scope)
                    or not records._equal(selected.get('goal'), original['objective'])
                    or not records._equal(selected.get('purpose'), original['purpose'])
                    or not records._equal(json.loads(selected['initial_report_json']),
                        original['initial_report'])):
                raise ContractError('scientific_closed_commission_conflict')
            child, _, schema = records._attempt(parent, index)
            filled = self.restore_closed_process(closed_context)
            if (filled is None or child.episode_id != closed_context.episode_id
                    or not records._equal(child.request, closed_context.request)):
                raise ContractError('scientific_closed_commission_conflict')
            request = plain(child.request)
            saved_invocation = self._invocation({
                'objective': request['goal']['objective'],
                'purpose': request['report_contract']['decision'],
                'report_schema': schema,
                'initial_report': request['message']['initial_report']}, child.scope)
            assignment = plain(child.assignment)
            selectors = {**assignment, 'selection': selector_selection(assignment['selection'])}
            if (not records._equal(saved_invocation, original)
                    or not (records._equal(inputs, assignment)
                        or records._equal(inputs, selectors))):
                raise ContractError('scientific_closed_commission_conflict')
            assignment = self._assignment(assignment, scope, context=closed_context)
            if 'revision_origin' in assignment:
                self._validate_origin(parent, assignment, owner='self')
            return {'assignment': assignment, 'scientific_process': filled}
        assignment = self.prepare_assignment(parent, role, inputs, scope, operation_key)
        from .component_axis_reports import validate_native_return_channels
        validate_native_return_channels(assignment['selection'], original['report_schema'])
        filled = validate_filled_process({"version": "filled_scientific_process_v1",
            "selection": assignment["selection"],
            "assignment_sha256": scientific_digest(assignment),
            "invocation_sha256": scientific_digest(original),
            "mechanics_binding": self.as_record()})
        return {"assignment": assignment, "scientific_process": filled}

    def restore_closed_process(self, context) -> dict | None:
        """Restore only the original mechanics identity of an exact closed request."""
        self._role(context.role)
        read_closed = getattr(self.services, 'scientific_closed_request', None)
        if not callable(read_closed):
            return None
        original = read_closed(context)
        if original is None:
            return None
        original = _object(original, 'scientific_closed_request_invalid')
        candidate = _object(context.request, 'scientific_filled_request_required')
        try:
            saved = validate_filled_process(original['message']['scientific_process'])
            filled = validate_filled_process(candidate['message']['scientific_process'])
            saved_binding = saved['mechanics_binding']
            saved_hash = saved_binding['implementation_sha256']
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_closed_request_invalid') from error
        if not isinstance(saved_hash, str) or re.fullmatch(_SHA256['pattern'], saved_hash) is None:
            raise ContractError('scientific_closed_implementation_identity_invalid')
        current = self.as_record()
        # No other mechanics field, assignment operand or requested meaning is
        # relaxed. The candidate must carry today's binding or this exact saved
        # binding; an unrelated caller-supplied hash is not a replay identity.
        if ({**saved_binding, 'implementation_sha256': current['implementation_sha256']} != current
                or filled['mechanics_binding'] not in (current, saved_binding)):
            raise ContractError('scientific_filled_identity_mismatch')
        candidate['message']['scientific_process']['mechanics_binding']['implementation_sha256'] = saved_hash
        if (candidate != original
                or plain(context.scope) != original['message'].get('scope')
                or plain(context.assignment) != original['message'].get('episode_assignment')):
            raise ContractError('scientific_filled_identity_mismatch')
        return saved

    def restore_saved_process(self, context, *, original_request, active_only=True) -> dict | None:
        """Project an approved repair onto the exact saved journal request.

        Workflow supplies its existing active row before its unchanged full
        request comparison. Inspection can also finish an authenticated yielded
        request's first form. New commissions keep the current implementation.
        """
        from .episode_composition import scientific_binding_compatible
        self._role(context.role)
        original = _object(original_request, 'scientific_saved_request_invalid')
        read_saved = getattr(self.services, 'scientific_saved_request', None)
        recorded = read_saved(context, active_only=active_only) if callable(read_saved) else None
        if recorded is None:
            return None
        if scientific_digest(recorded) != scientific_digest(original):
            raise ContractError('scientific_saved_request_mismatch')
        candidate = _object(context.request, 'scientific_filled_request_required')
        try:
            saved = validate_filled_process(original['message']['scientific_process'])
            filled = validate_filled_process(candidate['message']['scientific_process'])
            current = self.as_record()
            if not scientific_binding_compatible(current, saved['mechanics_binding']):
                return None
            if scientific_digest(filled['mechanics_binding']) not in {
                    scientific_digest(current), scientific_digest(saved['mechanics_binding'])}:
                raise ContractError('scientific_saved_identity_mismatch')
            candidate['message']['scientific_process']['mechanics_binding'] = deepcopy(saved['mechanics_binding'])
            if (scientific_digest(candidate) != scientific_digest(original)
                    or scientific_digest(plain(context.scope)) != scientific_digest(original['message']['scope'])
                    or scientific_digest(plain(context.assignment)) != scientific_digest(
                        original['message']['episode_assignment'])):
                raise ContractError('scientific_saved_identity_mismatch')
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_saved_request_invalid') from error
        return saved

    def validate_context(self, context):
        self._role(context.role)
        request = _object(context.request, "scientific_filled_request_required")
        try:
            message = request["message"]
            filled = validate_filled_process(message["scientific_process"])
            contract = request["report_contract"]
            original = self._invocation({"objective": request["goal"]["objective"],
                "purpose": contract["decision"],
                "report_schema": contract["measurements"]["schema"],
                "initial_report": message["initial_report"]}, message["scope"])
            assignment = self._assignment(context.assignment, context.scope, context=context)
        except (KeyError, TypeError) as error:
            raise ContractError("scientific_filled_request_required") from error
        if (assignment != message.get("episode_assignment")
                or plain(context.scope) != message["scope"]
                or message.get("scientific_invocation_ref") != scientific_invocation_ref(
                    context.run_id, context.path)
                or filled["selection"] != assignment["selection"]
                or filled["assignment_sha256"] != scientific_digest(assignment)
                or filled["invocation_sha256"] != scientific_digest(original)):
            raise ContractError("scientific_filled_identity_mismatch")
        if scientific_digest(self.as_record()) != scientific_digest(filled['mechanics_binding']):
            read_saved = getattr(self.services, 'scientific_saved_request', None)
            recorded = read_saved(context, active_only=False) if callable(read_saved) else None
            restored = (self.restore_saved_process(context, original_request=recorded, active_only=False)
                        if recorded is not None else None)
            if restored != filled and self.restore_closed_process(context) != filled:
                raise ContractError("scientific_filled_identity_mismatch")
        if "revision_origin" in assignment:
            self._validate_origin(context, assignment, owner="parent")

    def validate_execution_context(self, context) -> None:
        """Historical closure permits inspection/replay, never new dispatch."""
        from .episode_composition import scientific_binding_compatible
        self.validate_context(context)
        current = self.as_record()
        filled = plain(context.request['message']['scientific_process']['mechanics_binding'])
        if (self.restore_closed_process(context) is not None
                or not scientific_binding_compatible(current, filled)):
            raise ContractError('scientific_execution_identity_mismatch')
        read_saved = getattr(self.services, 'scientific_saved_request', None)
        active = read_saved(context) if callable(read_saved) else None
        if active is None and callable(read_saved) and read_saved(context, active_only=False) is not None:
            raise ContractError('scientific_execution_identity_mismatch')
        if scientific_digest(current) != scientific_digest(filled):
            if active is None:
                raise ContractError('scientific_execution_identity_mismatch')

    def _original_selection(self, context):
        self.validate_context(context)
        return validate_selection(context.assignment["selection"])

    def permitted_common_actions(self, context):
        self.validate_context(context)
        selection = context.assignment['selection']
        if selection[selection_fields(selection)[0]]['option_id'] == 'A104':
            # Native work waits inside the shared operational HPC service.
            # An idle scientific calendar wait cannot make its suspended
            # annotation parent supply a requested sibling investigation.
            return ('tool', 'reason', 'child', 'redeliver_report')
        return ("tool", "reason", "child", "wait", "redeliver_report")

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        selection=parent.assignment['selection']
        if selection[selection_fields(selection)[0]]['option_id']=='A103':
            return tuple(role for role in self._child_roles if role in {'scientific_process','literature'})
        if selection[selection_fields(selection)[0]]['option_id']=='A104':
            return tuple(role for role in self._child_roles if role in {'scientific_process', 'hpc'})
        return self._child_roles

    def instructions(self, context):
        self.validate_context(context)
        selection = context.assignment['selection']
        axis = self.library.resolve(selection[selection_fields(selection)[0]])
        axis_guidance = ("A101 owns sequence similarity evidence. For an NCBI BLAST search that may run "
            "remotely, use the configured Launch API job when available: submit once, return its "
            "execution_handoff_refs to this episode, and let a separately selected monitor or Results "
            "episode check that same RID. The handoff is operational progress, not homology evidence. "
            "If that RID is waiting and no useful A101 work remains, return the handoff reference and "
            "current credit to your parent so it can choose another evidence axis. Consider ClusteredNR "
            "(nr_clustered_seq) for an initial blastx search; choose the database for the scientific "
            "question and preserve the selected database in the original request.\n\n"
            if axis.get('id') == 'A101' else '')
        axis_guidance += ("A102 owns structural work only. Scientific descendants remain A102. "
            "Use available shared operations to send the immediate parent specific missing operands or useful "
            "received evidence. That parent chooses within its own options or relays the need upward. "
            "Reuse qualified retained alignments. "
            "Native comparison results automatically populate the A102 numerical sheet before credit inspection; "
            "unknown functional features do not erase measured native correspondence. "
            "Follow up for missing structural cells, preserve original scope and model uncertainty, "
            "and distinguish fold resemblance from exact function. Novel folding requires an explicit configured "
            "remote/API/HPC binding; use structure.model_request when it is missing.\n\n"
            if axis.get('id') == 'A102' else '')
        if axis.get('id') == 'A102':
            from .a102_structural_evidence import is_merged_entry
            if is_merged_entry(axis):
                # The complete selected entry below owns both structural paths.
                # Keep the legacy native-only guidance on its original catalog.
                axis_guidance = ('A102 owns comparative and experimental structural evidence. '
                    'Scientific descendants remain A102. Use either path or both as useful, '
                    'and return their separate scientific quantities and shared dependencies.\n\n')
        if axis.get('id') == 'A103':
            axis_guidance = ('A103 owns gene-context work. Scientific descendants remain A103. '
                'Use available shared operations to send the immediate parent specific missing operands or '
                'useful received evidence; that parent chooses within its own options or relays the need upward. '
                'Context measurements are automatically graded at publication/receipt. '
                'Each target/locus, neighboring component, domain and regulatory footprint retains its own attribution. '
                'An identity score, source label or fetched record alone is not an association score. Unknown flanks '
                'and unevaluated detections are not absence. Preserve optional modules, paralogs and related sampling. '
                'Use one small local job at a time, current resource_context and admission feedback. '
                'Root/owner credit comes from actual measured context, not narrative judgments.\n\n')
        if axis.get('id') in {'A107', 'A110'}:
            from .component_axis_workflow import INSTRUCTIONS
            axis_guidance = (INSTRUCTIONS[axis['id']] + '\n\nScientific descendants remain '
                + axis['id'] + '. Use available shared operations for specific parent information needs '
                'or useful received findings. The immediate parent chooses within its own options or relays '
                'the need upward; publication does not commission work or promise a reply. '
                'Preserve named scientific components separately from controller progress.\n\n')
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            return (
                axis_guidance + "Determine what the supplied target does within the parent's assigned question, scope "
                "and constraints. Start with the supplied sequence, selected file contents or snippets, "
                "preserving their boundaries, completeness and known context. No initial candidate "
                "annotation or publicly searchable name is required. Possible functions can emerge "
                "from the evidence and be compared or revised. Apply the complete selected investigation "
                "instructions and thought-pattern guidance on every decision. Use actual outcomes and "
                "received child results to choose and revise your approach. Selected instructions "
                "describe how to investigate; they are not evidence about this target. Preserve the "
                "measured subject, conditions, controls, native measurements, uncertainty and limits of "
                "inference when interpreting evidence. Missing information remains unknown.\n\n"
                "Choose an available tool action, commit a scientific interpretation through the "
                "reasoning action, commission a scoped child with its own typed return form, or wait "
                "for selected pending work when that informs the investigation. Use only the selected "
                "actual tools and their supplied resource instructions; choose callable operands "
                "through the declared response contract. Preserve the parent's exact requested result "
                "meanings and allowed values. Recorded facts come from actual records. Keep inherited "
                "information distinct from new findings and completed work distinct from attempts. "
                "Return valid partial findings and specific failures through the requested form.\n\n"
                "Keep the assigned evidence axis, thought pattern and selected tools for this episode. "
                "process.revise prepares a different thought pattern and/or tool selection for a new "
                "child; it does not change this episode or start that child. To commission that "
                "alternative, copy its selection and revision_origin into a separately selected child "
                "assignment with the child's job, scope, constraints and typed return. Children own "
                "their iterative choices. The configured controller "
                "owns continuation. Waiting and unchanged observations do not manufacture progress.")
        return ("Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. "
            "The selected scientific support proposition and operands define the support problem; "
            "the thought pattern supplies alternatives "
            "and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. "
            "Choose your own actions using actual outcomes and received child forms. The selection is no "
            "prescribed sequence or automatic compatibility verdict. Library sources are instruction "
            "provenance, not scientific evidence about this target. Inspect actual source subjects, "
            "conditions and target applicability before interpreting evidence. annotation_support_routes "
            "describes the actual separately bound annotation policy's kind dispatch. An unmapped kind "
            "has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot "
            "declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself "
            "earns no credit and never replaces or filters the actual projectors, annotation formula or "
            "continuation rule. Keep the parent's objective, scope, constraints "
            "and exact typed form; support metadata never adds form fields or scoring axes. Use common reasoning "
            "to commit scientific interpretations. Keep the originally assigned scientific support, "
            "thought pattern and selected tool set throughout this episode. Explicit process.revise prepares "
            "a selection for a new child; a separately selected episode_child action commissions that "
            "child with its own job, scope, constraints and typed return form. Preparation changes no "
            "current process and starts no child. Copy both result.selection and revision_origin into "
            "that child's assignment to identify it as an alternative approach. Request the recorded "
            "scientific_process_results source in child forms when their process relationships and "
            "existing closed credit/yield are needed for steering. Only retrieved actual tools are available; "
            "their descriptions do not grant execution. The configured controller owns continuation.")

    def _information_catalog(self, scope):
        # Older injected ordinary-only service ports have no resource routes.
        # This fallback grants no operation beyond their original direct map.
        callback = getattr(self.services, 'tool_information_catalog', self.services.tool_catalog)
        return callback(scope)

    def _closed_tool_resolution(self, context, selection):
        """Read only an authenticated closed owner's original frozen contracts."""
        original = self.restore_closed_process(context)
        if original is None:
            return None
        if scientific_digest(selection) != scientific_digest(original['selection']):
            raise ContractError('scientific_filled_identity_mismatch')
        return (self.tool_library.resolve(selection['tools'])
            if selection['version'] == LEGACY_SELECTION_VERSION else
            self.tool_library.resolve_invocations(selection['child_tool_info']))

    def _tool_resolution_for(self, selection, scope, *, context=None):
        if context is not None:
            if plain(scope) != plain(context.scope):
                raise ContractError('scientific_filled_identity_mismatch')
            closed = self._closed_tool_resolution(context, selection)
            if closed is not None:
                return closed
        return (self.tool_library.resolve(selection['tools'], self.services.tool_catalog(scope))
            if selection['version'] == LEGACY_SELECTION_VERSION else
            self.tool_library.resolve_invocations(selection['child_tool_info'], self._information_catalog(scope)))

    def _tool_resolution(self, context, selection):
        entries = self._tool_resolution_for(selection, context.scope, context=context)
        if any(entry["name"] in {*_COMMON_TOOLS, "process.revise"} for entry in entries):
            raise ContractError("scientific_primitive_uses_common_tool_name")
        return entries

    def _proposed_selection(self, initial, arguments, version, scope):
        axis_field = selection_fields(initial)[0]
        if version == LEGACY_SELECTION_VERSION:
            validate_schema(arguments, _LEGACY_REVISION_ARGUMENTS)
            return self._selection({'version': version, 'annotation_ref': initial[axis_field],
                'thought_ref': arguments['thought_ref'], 'tools': arguments['tools']})
        validate_schema(arguments, _REVISION_ARGUMENTS)
        return self._selection({'version': SELECTION_VERSION, 'evidence_axis': initial[axis_field],
            'thought_pattern': arguments['thought_pattern'], 'child_tool_info':
                self.tool_library.resolve_tool_info(arguments['child_tool_info'], self._information_catalog(scope))})

    def catalog(self, context):
        selection = self._original_selection(context)
        resolved = self._tool_resolution(context, selection)
        if selection['version'] != LEGACY_SELECTION_VERSION:
            direct = [row for row in resolved
                      if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
            if self._closed_tool_resolution(context, selection) is not None:
                resolved = direct
            else:
                resolved = self.tool_library.resolve_invocations(
                    [{'name': row['name'], 'resources': row['resources']} for row in direct],
                    self.services.tool_catalog(context.scope))
        entries = [{key: deepcopy(value) for key, value in row.items()
                    if key not in {'instructions', 'invocation_route'}} for row in plain(resolved)]
        description = (
            "Prepare a pinned thought pattern and selected actual tools for a new child using the original "
            "scientific support and library. Return its selection for a separately selected episode_child "
            "commission with the child's job, scope, constraints and typed form. Copy result.selection "
            "and revision_origin into that assignment; request scientific_process_results in the form "
            "when process provenance and existing closed results are needed. Changes no current "
            "process, starts no child and records no biological observation. Supply the actual tool names "
            "returned by process.tools for the desired alternative investigation.")
        axis = self.library.resolve(selection[selection_fields(selection)[0]])
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            description = (
                "Prepare a different thought pattern and/or selected actual tools for a new child "
                "investigating the same evidence axis. Return its selection for a separately selected "
                "episode_child commission with the child's job, scope, constraints and typed return "
                "form. Copy result.selection and revision_origin into that assignment. Changes no "
                "current process, starts no child and records no biological observation. Select the "
                "actual tool/resource choices returned by process.tools for the desired investigation.")
        entries.append({"name": "process.revise", "description": description,
            "input_schema": deepcopy(_LEGACY_REVISION_ARGUMENTS
                if selection['version'] == LEGACY_SELECTION_VERSION else _REVISION_ARGUMENTS)})
        if getattr(self.services, 'workflow', None) is not None and self.tool_library.supports_tool_info:
            from .execution_planning import catalog
            entries.extend(catalog())
        return entries

    def common_tool_names(self, context):
        # Runtime applies this after adding its helpers, so retain selected
        # primitives and the child-selection preparation as well as retrieval.
        return (*_COMMON_TOOLS, *(entry["name"] for entry in self.catalog(context)))

    def decision_context(self, context, current_view):
        selection = self._original_selection(context)
        annotation, thought = (self.library.resolve(selection[key]) for key in selection_fields(selection)[:2])
        resolved = self._tool_resolution(context, selection)
        def selected_fields(entry, names):
            return {name: deepcopy(entry[name]) for name in names if name in entry}
        fields = selection_fields(selection)
        current = selection['version'] == SELECTION_VERSION
        assignment = plain(context.assignment)
        if current:
            assignment = {**assignment, 'selection': selector_selection(selection)}
        published = annotation.get('entry_version') == INSTRUCTION_VERSION
        if published:
            axis_view = instruction_view(annotation)
        elif annotation.get('entry_version') == EVIDENCE_AXIS_VERSION:
            axis_view = evidence_axis_instruction_view(annotation)
        else:
            axis_view = selected_fields(annotation, ("id", "name", "description", "support"))
        return {"scientific_process": {"selection": selector_selection(selection),
            "initial_selection_sha256": scientific_digest(plain(context.assignment["selection"])),
            ('evidence_axis' if current else 'annotation'): axis_view,
            **({} if published else {"annotation_support_routes": self.services.scientific_support_routes(context,
                observation_kinds=support_observation_kinds(annotation))}),
            ('thought_pattern' if current else 'thought'): selected_fields(thought, ("id", "name", "description", "use_when",
                "live_alternatives", "decision_guidance", "outcome_contingencies", "boundary")),
            **({'child_tool_info': deepcopy(selection[fields[2]])} if current else {'tools': deepcopy(resolved)}),
            "assignment": assignment, "permitted_children": list(self.allowed_children(context,None))}}

    async def execute(self, context, tool_name, arguments, operation_key):
        self.validate_execution_context(context)
        selection = validate_selection(context.assignment['selection'])
        try:
            if not isinstance(operation_key, str) or not operation_key:
                raise ContractError("operation_key_required")
            entries = {entry["name"]: entry for entry in self.catalog(context)}
            if tool_name not in entries:
                raise ContractError("scientific_operation_unavailable")
            axis = self.library.resolve(selection[selection_fields(selection)[0]])
            if axis.get('id')=='A103' and tool_name=='sequence.align':
                raise ContractError('a103_new_sequence_comparison_requires_shared_parent')
            if axis.get('id')=='A104' and tool_name=='sequence.align':
                raise ContractError('a104_new_sequence_comparison_requires_shared_parent')
            arguments = _object(arguments, "scientific_arguments_invalid")
            validate_schema(arguments, entries[tool_name]["input_schema"])
            if tool_name == 'process.execution':
                from .execution_planning import read
                return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                        'result': read(self, context, arguments)}
            if tool_name == 'sequence.align':
                self.services.authenticate_structure_alignment_operands(context, arguments)
            elif tool_name == 'execution.estimate' and arguments['tool'] == 'sequence.align':
                self.services.authenticate_structure_alignment_operands(context, arguments['arguments'])
            if tool_name in {'material.from_source', 'material.parse', 'material.read',
                             'source.read', 'source.locate'}:
                self.services.authenticate_source_byte_operands(context, tool_name, arguments)
            if tool_name == "process.revise":
                proposed = self._proposed_selection(selection, arguments, selection['version'], context.scope)
                self._tool_resolution(context, proposed)
                child_selection = validate_child_selection({
                    "version": "scientific_process_child_selection_v1",
                    "parent_selection_sha256": scientific_digest(selection),
                    "selection": proposed})
                operation_ref = identity("operation", {
                    "key": operation_key, "name": tool_name, "arguments": arguments})
                origin = validate_revision_origin({"version": "scientific_process_revision_origin_v1",
                    "parent_invocation_ref": scientific_invocation_ref(context.run_id, context.path),
                    "preparation_operation_ref": operation_ref})
                return {"status": "completed", "operation_ref": operation_ref,
                    "record_refs": [], "changed_record_refs": [], "result": child_selection,
                    "revision_origin": origin, "feedback": None}
        except ValueError as error:
            return {"status": "invalid", "operation_ref": identity("operation", {
                "key": operation_key, "name": tool_name}), "record_refs": [],
                "changed_record_refs": [], "result": None,
                "feedback": {"category": "arguments_or_reference", "code": str(error),
                    **({"detail": error.detail} if getattr(error, "detail", None) else {})}}
        outcome = self.services.execute_tool(tool_name, arguments,
            scope=context.scope, operation_key=operation_key,
            **({'permitted_record_refs': context.received_record_refs}
               if tool_name.startswith(('structure.','context.','phylogeny.','partner.','chemistry.')) or tool_name in {'reference.neighborhood','result.blast.hsp', 'source.locate',
                   'find_restriction_sites', 'find_restriction_enzymes'} else {}))
        return await outcome if inspect.isawaitable(outcome) else outcome

    def fact_sources(self, role):
        self._role(role)
        from .a103_investigation import context_fact_sources
        from .a104_investigation import fact_sources as evolutionary_fact_sources
        from .a107_qualification import fact_sources as partner_qualification_sources
        from .component_axis_native_hpc import fact_sources as component_native_sources
        from .a110_qualification import fact_sources as chemical_qualification_sources
        return {**report_sources(self.library, self.tool_library),
                **context_fact_sources(), **evolutionary_fact_sources(),
                **partner_qualification_sources(),
                **component_native_sources(),
                **chemical_qualification_sources(),
                **alignment_site_fact_sources(), **restriction_mapping_fact_sources(),
                **molecular_fact_sources(), **protein_structure_action_fact_sources()}

    def facts(self, context, completion_snapshot):
        from .scientific_process_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)
        def project(value):
            return project_process_result(value, library=self.library,
                tool_library=self.tool_library)
        facts = {"scientific_process_results": merge_process_results(
            None if own is None else project(own), [project(value) for value in received])}
        schema = plain(context.request)['report_contract']['measurements']['schema']
        from .component_axis_native_hpc import (FACT_SOURCE as NATIVE_COMPONENTS,
            EXECUTION_SOURCE as NATIVE_EXECUTION, received_components,
            execution_findings as native_execution_findings)
        axis = context.assignment.get('selection', {}).get('evidence_axis', {}).get('option_id')
        for source, reader in ((NATIVE_COMPONENTS, received_components), (NATIVE_EXECUTION, native_execution_findings)):
            if any(node.get('x-source') == source for node in schema.get('properties', {}).values()):
                workflow = getattr(self.services, 'workflow', None)
                if workflow is None:
                    raise ContractError('component_native_report_store_required')
                facts[source] = [row['source_ref'] for row in reader(workflow.store,
                    context.received_record_refs, context.scope, axis=axis if axis in {'A107', 'A110'} else None)]
        from .a107_qualification import FACT_SOURCE as PARTNER_QUALIFICATIONS, received_qualifications
        from .a110_qualification import FACT_SOURCE as CHEMICAL_QUALIFICATIONS, received as chemical_qualifications
        if any(node.get('x-source') == CHEMICAL_QUALIFICATIONS for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a110_qualification_report_store_required')
            facts[CHEMICAL_QUALIFICATIONS] = [row['source_ref'] for row in chemical_qualifications(
                workflow.store, context.received_record_refs, context.scope)]
        if any(node.get('x-source') == PARTNER_QUALIFICATIONS for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a107_qualification_report_store_required')
            facts[PARTNER_QUALIFICATIONS] = [row['source_ref'] for row in received_qualifications(
                workflow.store, context.received_record_refs, context.scope)]
        from .a107_qualification import EXECUTION_SOURCE as PARTNER_EXECUTION, execution_findings as partner_execution_findings
        if any(node.get('x-source') == PARTNER_EXECUTION for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a107_genomic_execution_report_store_required')
            facts[PARTNER_EXECUTION] = [row['source_ref'] for row in partner_execution_findings(
                workflow.store, context, set(context.received_record_refs))]
        from .a103_investigation import CONTEXT_RECORD_SOURCE,received_context_records
        if any(node.get('x-source')==CONTEXT_RECORD_SOURCE for node in schema.get('properties',{}).values()):
            workflow=getattr(self.services,'workflow',None)
            if workflow is None:raise ContractError('a103_report_store_required')
            facts[CONTEXT_RECORD_SOURCE]=received_context_records(workflow.store,
                context.received_record_refs,plain(context.scope),
                committed=completion_snapshot.get('committed_record_refs',()))
        from .a104_investigation import RECORD_SOURCE as EVOLUTIONARY_RECORD_SOURCE, received_records as received_evolutionary_records
        if any(node.get('x-source') == EVOLUTIONARY_RECORD_SOURCE for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a104_report_store_required')
            facts[EVOLUTIONARY_RECORD_SOURCE] = received_evolutionary_records(workflow.store,
                context.received_record_refs, plain(context.scope),
                committed=completion_snapshot.get('committed_record_refs', ()))
        for source, requested in requested_site_projections(schema).items():
            facts[source], cursor = [], None
            while True:
                page = self.services.alignment_site_own_action_results(context,
                    source=source, selection=requested['selection'],
                    after_decision_index=cursor, limit=64)
                facts[source].extend(project_site_action_return(record, requested['fields'])
                    for record in page['records'])
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
        for source, requested in requested_restriction_projections(schema).items():
            facts[source], cursor = [], None
            while True:
                page = self.services.restriction_mapping_own_action_results(context,
                    selection=requested['selection'], after_decision_index=cursor, limit=64)
                facts[source].extend(project_restriction_action_return(record, requested['fields'])
                    for record in page['records'])
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
        for source in requested_molecular_fact_sources(schema):
            facts[source] = merge_molecular_facts(
                self.services.molecular_received_facts(context, fact_source=source),
                self.services.molecular_own_facts(context, fact_source=source), fact_source=source)
        for source in PROTEIN_ACTION_FACT_SOURCES:
            if requested_protein_structure_action_fields(schema, fact_source=source):
                facts[source] = merge_protein_structure_action_facts(
                    self.services.protein_structure_action_received_facts(context, fact_source=source),
                    self.services.protein_structure_action_own_facts(context, fact_source=source),
                    fact_source=source)
        facts.update(self._component_scoring_facts(context))
        return facts

    def _component_scoring_facts(self, context):
        from .component_axis_reports import current_scoring_sheets, SCORING_FACT
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            return {}
        sheets = current_scoring_sheets(workflow.store, context=context, services=self.services)
        return {SCORING_FACT: sheets} if sheets else {}

    def current_report_facts(self, context):
        return self._component_scoring_facts(context)

    def received_report_sources(self, role):
        # Scientific roles declare their own source above; the registry rejects
        # duplicate own/received names. Annotation has no such specialist map.
        return {**molecular_fact_sources(), **protein_structure_action_fact_sources()} if role == 'annotation' else {}

    def received_report_facts(self, context):
        if context.role != 'annotation':
            return {}
        contract = plain(context.request).get('report_contract')
        schema = {} if contract is None else contract.get('measurements', {}).get('schema', {})
        facts = {source: merge_molecular_facts(
            self.services.molecular_received_facts(context, fact_source=source), fact_source=source)
            for source in requested_molecular_fact_sources(schema)}
        for source in PROTEIN_ACTION_FACT_SOURCES:
            if requested_protein_structure_action_fields(schema, fact_source=source):
                facts[source] = merge_protein_structure_action_facts(
                    self.services.protein_structure_action_received_facts(context, fact_source=source),
                    fact_source=source)
        facts.update(self._component_scoring_facts(context))
        return facts

    def initial_decision_context(self, context):
        """Present admitted scientific outputs through the existing fresh-call hook."""
        from .a102_structural_evidence import is_merged_entry
        from .a102_structural_report import received_reports
        if context.role not in {'annotation', ROLE}:
            return {}
        workflow = getattr(self.services, 'workflow', None)
        result = self._component_scoring_facts(context)
        if workflow is not None and (context.role == 'annotation' or context.assignment.get(
                'selection', {}).get('evidence_axis', {}).get('option_id') in {'A107', 'A110'}):
            from .component_axis_reports import received_reports as component_reports, mark_native_execution
            reports = component_reports(workflow.store, context=context, services=self.services)
            if reports:
                result['received_partner_and_chemical_evidence'] = reports
            from .component_axis_native_hpc import received_components, execution_findings as native_execution_findings
            axis_id = context.assignment.get('selection', {}).get('evidence_axis', {}).get('option_id')
            selected_axis = axis_id if context.role == ROLE else None
            native = received_components(workflow.store, context.received_record_refs, context.scope, axis=selected_axis)
            execution = native_execution_findings(workflow.store, context.received_record_refs, context.scope, axis=selected_axis)
            if native or execution:
                execution = mark_native_execution(execution, native)
                result['received_partner_and_chemical_native_components'] = {
                    'scientific_results': native, 'execution_findings': execution}
                from .component_axis_execution_context import prepared_assignments
                prepared = prepared_assignments(workflow.store, context=context,
                    execution_findings=execution,
                    resources=getattr(workflow.tools, 'component_native_resources', None))
                if prepared is not None:
                    result['received_partner_and_chemical_native_components']['prepared_hpc_assignments'] = prepared
            from .a107_qualification import received_qualifications
            from .a110_qualification import received as chemical_qualifications
            qualifications = {}
            for selected, reader in (('A107', received_qualifications), ('A110', chemical_qualifications)):
                if context.role == 'annotation' or selected_axis == selected:
                    rows = reader(workflow.store, context.received_record_refs, context.scope)
                    if rows:
                        qualifications[selected] = rows
            if qualifications:
                result['received_partner_and_chemical_qualifications'] = qualifications
        if (workflow is not None and getattr(workflow.tools,'a103_execution_resources',None) is not None
                and (context.role=='annotation' or context.assignment.get('selection',{}).get('evidence_axis',{}).get('option_id') in {'A103','A107'})):
            from .a103_hpc import execution_findings
            result['received_gene_context_execution'] = execution_findings(workflow.store,context,set(context.received_record_refs))
        axis = next((row['option_ref'] for row in self.library.headers()
            if row['option_ref']['option_id'] == 'A102'), None)
        if axis is None or not is_merged_entry(self.library.resolve(axis)):
            return result
        if workflow is None:
            raise ContractError('a102_report_store_required')
        result['received_structural_evidence'] = received_reports(workflow.store,
            context=context, structure_repository=self.services.literature_structure_repository(),
            axis_reference=axis)
        return result

    def _validate_structural_report(self, context, form, schema):
        from dataclasses import replace
        from .a102_structural_evidence import is_merged_entry
        from .a102_structural_report import is_structural_report_schema, resolve_report
        if not is_structural_report_schema(schema):
            return
        axis = self.library.reference('A102')
        if not is_merged_entry(self.library.resolve(axis)):
            raise ContractError('a102_merged_structural_evidence_catalog_required')
        if context.role == ROLE:
            selection = self._original_selection(context)
            if selection[selection_fields(selection)[0]] != axis:
                raise ContractError('a102_structural_report_requires_merged_axis')
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            raise ContractError('a102_report_store_required')
        # C4 can retain a commission-time context while the child acquires new
        # evidence. Refresh only this reporting episode's actual durable set.
        selected = self.services.record_selection(context)
        if selected.get('run_id') != context.run_id or selected.get('episode_id') != context.episode_id:
            raise ContractError('a102_report_receiver_mismatch')
        current = replace(context, received_record_refs=tuple(selected['known_record_refs']))
        try:
            resolve_report(workflow.store, plain(form), context=current,
                structure_repository=self.services.literature_structure_repository())
        except ContractError as error:
            fields = {'a102_comparative_status_differs_from_delivered_evidence': 'comparative_status',
                'a102_experimental_status_differs_from_delivered_evidence': 'experimental_status'}
            if str(error) not in fields:
                raise
            raise ReportBoundaryError('A102 interpretation requires its delivered structural evidence',
                code=str(error), field=fields[str(error)]) from error

    def _validate_component_axis_report(self, context, form, schema):
        from dataclasses import replace
        from .component_axis_reports import report_axis, resolve_report
        axis = report_axis(schema)
        if axis is None:
            return
        if context.role == ROLE:
            selected = self._original_selection(context)
            if selected[selection_fields(selected)[0]]['option_id'] != axis:
                raise ContractError('component_axis_report_requires_original_axis')
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            raise ContractError('component_axis_report_store_required')
        received = self.services.record_selection(context)
        if received.get('run_id') != context.run_id or received.get('episode_id') != context.episode_id:
            raise ContractError('component_axis_report_receiver_mismatch')
        current = replace(context, received_record_refs=tuple(received['known_record_refs']))
        try:
            resolve_report(workflow.store, plain(form), context=current, services=self.services, axis=axis)
        except ContractError as error:
            raise ReportBoundaryError('The axis report requires its actual received component evidence',
                code=str(error)) from error

    def _validate_molecular_report(self, context, form, schema):
        for source in requested_molecular_fact_sources(plain(schema)):
            fields = requested_molecular_fact_fields(plain(schema), fact_source=source)
            label, missing_code = {
                _ITC_PARAMETER_SOURCE: ('ITC parameter', 'itc_parameter_facts_not_frozen'),
                'liftover_point_mappings': ('point-liftover', 'liftover_facts_not_frozen'),
                'circular_dichroism_summaries': ('CD summary', 'circular_dichroism_facts_not_frozen'),
                'orf_measurements': ('ORF measurement', 'ordinary_orf_facts_not_frozen'),
                'n_glycosylation_motif_outcomes': ('literal N-glycosylation motif', 'ordinary_n_glycosylation_facts_not_frozen'),
                'o_glycosylation_hotspot_outcomes': ('S/T-density candidate', 'ordinary_o_glycosylation_facts_not_frozen'),
                'primer_placement_outcomes': ('literal primer placement', 'primer_placement_facts_not_frozen'),
                'reference_edit_outcomes': ('reference editing outcome', 'reference_edit_outcome_facts_not_frozen'),
                'macs2_peak_outcomes': ('native MACS2 peak measurement', 'macs2_peak_facts_not_frozen'),
                'homer_motif_outcomes': ('native HOMER motif measurement', 'homer_motif_facts_not_frozen'),
                'tf_binding_outcomes': ('native TF score measurement', 'tf_binding_facts_not_frozen'),
                'protease_kinetics_outcomes': ('protease kinetics measurement', 'protease_kinetics_facts_not_frozen'),
                'arsenic_speciation_outcomes': ('arsenic speciation measurement', 'arsenic_speciation_facts_not_frozen'),
                'protein_disorder_outcomes': ('protein disorder measurement', 'protein_disorder_facts_not_frozen'),
                'protein_conservation_outcomes': ('literal conservation', 'protein_conservation_facts_not_frozen'),
                'protein_phylogeny_outcomes': ('native protein phylogeny', 'protein_phylogeny_facts_not_frozen'),
                'somatic_variant_outcomes': ('native somatic variant', 'somatic_variant_facts_not_frozen'),
                'esm_gene_embedding_outcomes': ('ESM representation', 'esm_gene_embedding_facts_not_frozen'),
                'vcf_result_outcomes': ('retained VCF result', 'vcf_result_facts_not_frozen'),
            }[source]
            try:
                frozen = self.services.molecular_frozen_facts(context, fact_source=source)
                if frozen is None:
                    raise ValueError(missing_code)
                validate_frozen_molecular_return(plain(form), plain(schema), frozen, fact_source=source)
            except ReportBoundaryError:
                raise
            except ValueError as error:
                raise ReportBoundaryError(f'Return differs from the frozen {label} facts',
                    code=str(error), field=fields[0]) from error

    def _validate_protein_structure_action_report(self, context, form, schema):
        for source in PROTEIN_ACTION_FACT_SOURCES:
            fields = requested_protein_structure_action_fields(plain(schema), fact_source=source)
            if not fields:
                continue
            try:
                frozen = self.services.protein_structure_action_frozen_facts(context, fact_source=source)
            except ValueError as error:
                raise ReportBoundaryError('Original protein action facts unavailable',
                    code=str(error), field=fields[0]) from error
            validate_frozen_protein_structure_action_return(plain(form), plain(schema), frozen,
                fact_source=source)

    _validate_itc_parameter_report = _validate_molecular_report

    def validate_received_report(self, context, form, schema):
        # Scientific roles use their own validate_report branch. This hook also
        # runs for annotation receivers, without adding a new episode binding.
        if context.role == 'annotation':
            self._validate_molecular_report(context, form, schema)
            self._validate_protein_structure_action_report(context, form, schema)
            self._validate_structural_report(context, form, schema)
            self._validate_component_axis_report(context, form, schema)

    def resolve(self, context, reference, namespace):
        self.validate_context(context)
        if namespace == 'restriction_enzyme':
            return self.services.restriction_mapping_reference(context, reference, namespace)
        if namespace is None or namespace in _SCIENTIFIC_NAMESPACES:
            if self.services.scientific_reference(context, reference, namespace):
                return True
            if namespace in _SCIENTIFIC_NAMESPACES:
                return False
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace:
            self.resolve(context, reference, namespace))
        self._validate_molecular_report(context, form, original_schema)
        self._validate_protein_structure_action_report(context, form, original_schema)
        self._validate_structural_report(context, form, original_schema)
        self._validate_component_axis_report(context, form, original_schema)
        from .a102_investigation import (report_schema as a102_report_schema,
            legacy_report_schema as a102_legacy_report_schema, resolve_report as resolve_a102_report)
        if plain(original_schema) in (a102_report_schema(), a102_legacy_report_schema()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a102_report_store_required')
            resolve_a102_report(workflow.store, plain(form), scope=plain(context.scope))
        from .a103_investigation import (resolve_report as resolve_a103_report,
            legacy_report_schema as a103_legacy_report_schema,
            measurement_report_schema as a103_measurement_report_schema,resolve_measurement_report)
        a103_axis=plain(context.assignment).get('selection',{}).get('evidence_axis',{}).get('option_id')=='A103'
        a103_fields=set(plain(original_schema).get('properties',{}))
        if a103_axis and a103_fields == set(a103_legacy_report_schema()['properties']):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a103_report_store_required')
            try:
                resolve_a103_report(workflow.store, plain(form), scope=plain(context.scope))
            except ContractError as error:
                fields={
                    'a103_association_statement_requires_actual_measurement':'context_summary',
                    'a103_system_statement_requires_qualified_context':'functional_support',
                    'a103_function_interpretation_requires_explicit_hypothesis_and_assessment':'functional_support',
                    'a103_trait_statement_requires_local_feature_attribution':'functional_support',
                    'a103_contrast_statement_requires_context_panel':'functional_support',
                    'a103_discriminating_contrast_requires_qualified_separated_bounds':'functional_support'}
                if str(error) not in fields:raise
                raise ReportBoundaryError('A103 interpretation requires its declared supporting records',
                    code=str(error),field=fields[str(error)]) from error
        elif a103_axis and a103_fields==set(a103_measurement_report_schema()['properties']):
            workflow=getattr(self.services,'workflow',None)
            if workflow is None:raise ContractError('a103_report_store_required')
            resolve_measurement_report(workflow.store,plain(form),scope=plain(context.scope))
        from .a104_investigation import (report_schema as a104_report_schema,
            legacy_report_schema as a104_legacy_report_schema, resolve_report as resolve_a104_report)
        a104_axis = plain(context.assignment).get('selection', {}).get('evidence_axis', {}).get('option_id') == 'A104'
        if a104_axis and set(plain(original_schema).get('properties', {})) in (
                set(a104_report_schema()['properties']), set(a104_legacy_report_schema()['properties'])):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a104_report_store_required')
            try:
                resolve_a104_report(workflow.store, plain(form), scope=plain(context.scope))
            except ContractError as error:
                interpretation_errors = {
                    'a104_report_numeric_credit_conflict': 'phylogenetic_credit',
                    'a104_native_tree_statement_requires_received_original_execution': 'phylogeny_status',
                    'a104_placement_statement_requires_native_measurement': 'phylogeny_status',
                    'a104_history_statement_requires_actual_two_tree_comparison': 'phylogeny_status',
                    'a104_history_agreement_requires_supported_native_comparison': 'history_interpretation',
                    'a104_discordance_statement_requires_native_comparison': 'history_interpretation',
                    'a104_function_clade_requires_exact_characterized_reference_links': 'function_scope',
                    'a104_mixed_function_statement_requires_characterized_members': 'function_scope',
                    'a104_function_statement_requires_explicit_hypothesis_and_assessment': 'function_scope'}
                interpretation_errors.update({
                    'a104_function_hypothesis_requires_original_target': 'hypothesis_refs',
                    'a104_function_statement_requires_corresponding_assessment_relation': 'assessment_refs'})
                if str(error) not in interpretation_errors:
                    raise
                raise ReportBoundaryError('A104 interpretation requires the particular native evidence and attribution',
                    code=str(error), field=interpretation_errors[str(error)]) from error
        fields = [name for name, node in plain(original_schema)["properties"].items()
                  if node.get("x-source") == "scientific_process_results"]
        projections = requested_site_projections(plain(original_schema))
        if projections:
            try:
                frozen_sites = self.services.alignment_site_frozen_facts(context,
                    sources=tuple(projections))
            except ValueError as error:
                raise ReportBoundaryError('Original site results unavailable',
                    code=str(error)) from error
            validate_frozen_site_return(plain(form), plain(original_schema), frozen_sites)
        restrictions = requested_restriction_projections(plain(original_schema))
        if restrictions:
            try:
                frozen = self.services.restriction_mapping_frozen_facts(context,
                    sources=tuple(restrictions))
            except ValueError as error:
                raise ReportBoundaryError('Original restriction results unavailable',
                    code=str(error)) from error
            validate_frozen_restriction_return(plain(form), plain(original_schema), frozen)
        if not fields:
            return
        # The child's source was frozen before the existing admission callback.
        # Comparing it here also protects the blocking and redelivery paths;
        # no closure quantity is recomputed while validating a returned form.
        try:
            read_frozen = getattr(self.services, "scientific_frozen_results", None)
            if not callable(read_frozen):
                raise ValueError("scientific_frozen_results_unavailable")
            frozen = read_frozen(context)
        except ValueError as error:
            raise ReportBoundaryError("Original process results unavailable",
                code=str(error), field=fields[0]) from error
        for name in fields:
            values = plain(form)[name]
            try:
                for value in values:
                    validate_process_result(value, library=self.library, tool_library=self.tool_library)
                if frozen is None or scientific_digest(values) != scientific_digest(frozen):
                    raise ValueError("scientific_process_result_source_mismatch")
            except ValueError as error:
                raise ReportBoundaryError("Return differs from the original process result",
                    code=str(error), field=name) from error

    def credit_projector(self, context):
        """Axis-owned deterministic numerical dispatch, never a model choice."""
        if context.role != ROLE:
            return None
        if (getattr(self, '_yield_bindings', None) is not None
                and not context.assignment.get('proposed_annotation_ref')):
            raise ContractError('scientific_task_proposed_annotation_required')
        selection = self._original_selection(context)
        axis = selection[selection_fields(selection)[0]]
        if axis['option_id'] in {'A105', 'A106', 'A108'} and self.library.resolve(axis).get('entry_version') in {
                INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION}:
            if not context.assignment.get('proposed_annotation_ref'):
                raise ContractError('axis_finding_task_requires_proposed_annotation')
            return original_axis_task_projector(axis['option_id'], context.assignment)
        if axis['option_id'] == 'A101' and self.library.resolve(axis).get('entry_version') in {
                INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION}:
            return original_axis_task_projector('A101', context.assignment)
        if axis['option_id'] == 'A102' and self.library.resolve(axis).get('entry_version') in {
                INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION}:
            from .a102_structural_evidence import is_merged_entry, credit_projector
            if is_merged_entry(self.library.resolve(axis)):
                return original_axis_task_projector('A102', context.assignment, merged_a102=True)
            return original_axis_task_projector('A102', context.assignment)
        if axis['option_id'] == 'A103' and self.library.resolve(axis).get('entry_version') in {
                'evidence_axis_instruction_v1'}:
            return original_axis_task_projector('A103', context.assignment)
        if axis['option_id'] == 'A104' and self.library.resolve(axis).get('entry_version') in {'evidence_axis_instruction_v1'}:
            return original_axis_task_projector('A104', context.assignment)
        if axis['option_id'] in {'A107', 'A110'} and self.library.resolve(axis).get('entry_version') == INSTRUCTION_VERSION:
            return original_axis_task_projector(axis['option_id'], context.assignment)
        return None

    def continuation_task(self, context):
        """Name the original scientific task whose own units price continuation."""
        projector = self.credit_projector(context)
        if projector is None:
            raise ContractError('scientific_task_credit_not_declared')
        selection = self._original_selection(context)
        axis = selection[selection_fields(selection)[0]]['option_id']
        if axis in {'A105', 'A106', 'A108'}:
            return axis + ':whole_axis_findings'
        assigned = plain(context.assignment).get('context', {}).get(axis.lower() + '_task')
        if assigned is not None:
            if not isinstance(assigned, dict) or not isinstance(assigned.get('name'), str) or not assigned['name']:
                raise ContractError('scientific_continuation_original_task_required')
            return axis + ':' + assigned['name']
        return axis + ':' + projector.as_record()['kind']

    def yield_controller(self, context, initial_credit, epoch):
        """Bind this commissioned scientific task to its own credit forecast.

        A saved task declaration fixes the estimator, its parameters, the
        continuation cutoff and the exact credit units. An old workflow with
        no private declarations keeps its recorded controller contract.
        """
        if self._yield_bindings is None:
            return None
        if context.role != ROLE:
            raise ContractError('scientific_yield_role_not_bound')
        task = self.continuation_task(context)
        declaration = self._yield_bindings.get(task)
        if declaration is None:
            raise ContractError('scientific_yield_binding_missing_for_task:' + task)
        projector = self.credit_projector(context)
        if scientific_digest(plain(projector.as_record())) != scientific_digest(
                declaration['credit_definition']):
            raise ContractError('scientific_yield_credit_definition_mismatch:' + task)
        if getattr(projector, 'yield_method', None) != declaration['kind']:
            raise ContractError('scientific_yield_method_credit_mismatch:' + task)
        if declaration['kind'] == 'accumulation':
            from .numerical import YieldController, YieldParameters
            return YieldController(epoch, initial_credit, declaration['cutoff'],
                YieldParameters(**declaration['parameters']))
        if declaration['kind'] == 'bounded_quality':
            from .numerical import BoundedYieldController, YieldParameters
            return BoundedYieldController(epoch, initial_credit, declaration['cutoff'],
                projector.native_score_maximum, YieldParameters(**declaration['parameters']))
        if declaration['kind'] == 'completion':
            from .numerical import CompletionYieldController, YieldParameters
            return CompletionYieldController(epoch, initial_credit, declaration['cutoff'],
                YieldParameters(**declaration['parameters']))
        raise ContractError('scientific_yield_method_unavailable:' + task)

    def credit_view(self, context, receiver_selection):
        self.validate_context(context)
        return self.services.scientific_credit(context, receiver_selection)

    def initial_references(self, context):
        if context.role != ROLE:
            return []
        self.validate_context(context)
        return list(dict.fromkeys([*context.assignment["evidence_refs"],
            *([context.assignment['proposed_annotation_ref']]
              if context.assignment.get('proposed_annotation_ref') else [])]))

    def received_form_references(self, context, form, schema, operation_key):
        from .protein_structure_action_records import protein_structure_action_form_references
        from .macs2_peak_result_contracts import validate_macs2_peak_return
        from .homer_motif_result_contracts import validate_homer_motif_return
        from .tf_binding_result_contracts import validate_tf_binding_return
        from .protease_kinetics_result_contracts import validate_ordinary_protease_kinetics_return
        from .arsenic_speciation_result_contracts import validate_ordinary_arsenic_return
        from .protein_disorder_result_contracts import validate_ordinary_disorder_return
        from .protein_conservation_result_contracts import validate_conservation_return
        from .protein_phylogeny_result_contracts import validate_phylogeny_return
        from .esm_gene_embedding_contracts import validate_esm_embedding_return
        from .somatic_variant_contracts import validate_somatic_return
        from .vcf_result_measurements import validate_vcf_return
        from .molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
        from .primer_placement_result_contracts import validate_ordinary_primer_placement_return
        form, schema = plain(form), plain(schema)
        references = protein_structure_action_form_references(form, schema)
        for field in requested_molecular_fact_fields(schema, fact_source='somatic_variant_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('somatic_variant_return_array_required')
            references.extend(validate_somatic_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='esm_gene_embedding_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('esm_gene_embedding_return_array_required')
            references.extend(validate_esm_embedding_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protein_conservation_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_conservation_return_array_required')
            references.extend(validate_conservation_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protein_phylogeny_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_phylogeny_return_array_required')
            references.extend(validate_phylogeny_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='arsenic_speciation_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('arsenic_speciation_return_array_required')
            references.extend(validate_ordinary_arsenic_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protein_disorder_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_disorder_return_array_required')
            references.extend(validate_ordinary_disorder_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='vcf_result_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('vcf_result_return_array_required')
            references.extend(validate_vcf_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='macs2_peak_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('macs2_peak_return_array_required')
            references.extend(validate_macs2_peak_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='homer_motif_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('homer_motif_return_array_required')
            references.extend(validate_homer_motif_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='tf_binding_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('tf_binding_return_array_required')
            references.extend(validate_tf_binding_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protease_kinetics_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protease_kinetics_return_array_required')
            references.extend(validate_ordinary_protease_kinetics_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='n_glycosylation_motif_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('ordinary_n_glycosylation_return_array_required')
            references.extend(validate_ordinary_molecular_sequence_return(value,
                operation='find_n_glycosylation_motifs')['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='o_glycosylation_hotspot_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('ordinary_o_glycosylation_return_array_required')
            references.extend(validate_ordinary_molecular_sequence_return(value,
                operation='predict_o_glycosylation_hotspots')['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='primer_placement_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('ordinary_primer_placement_return_array_required')
            references.extend(validate_ordinary_primer_placement_return(value)['source_ref'] for value in form[field])
        return list(dict.fromkeys(references))

    def resolve_received_reference(self, context, reference, namespace):
        # This registry port also runs for the actual receiving parent's role.
        # It precedes generic Store fallback and grants only proved names.
        if namespace == 'restriction_enzyme':
            return self.services.restriction_mapping_reference(context, reference, namespace)
        callback = getattr(self.services, 'protein_structure_reference_access', None)
        return callback(context, reference, namespace) if callable(callback) else None


__all__ = ["ScientificProcessEpisodes", "ROLE", "ROLES", "VERSION"]
