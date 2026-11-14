from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, LEGACY_SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _IMPLEMENTATION_FILES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOLS, _LEGACY_SELECTION, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, _LEGACY_REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)


class ScientificFromParent:

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
            from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
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
        from .native_return_admission import validate_native_return_channels
        validate_native_return_channels(assignment['selection'], original['report_schema'])
        filled = validate_filled_process({"version": "filled_scientific_process_v1",
            "selection": assignment["selection"],
            "assignment_sha256": scientific_digest(assignment),
            "invocation_sha256": scientific_digest(original),
            "mechanics_binding": self.as_record()})
        return {"assignment": assignment, "scientific_process": filled}

