"""Private A110 scientific from_parent."""
from __future__ import annotations
from .scientific_assignment_contracts import ContractError, EVIDENCE_AXIS_VERSION, INSTRUCTION_VERSION, LEGACY_SELECTION_VERSION, SELECTION_VERSION, SUPPORT_ENTRY_VERSION, _ASSIGNMENT, _LEGACY_REVISION_ARGUMENTS, _RECORDED_ASSIGNMENT, _REFERENCE, _REVISION_ARGUMENTS, _object, deepcopy, interpretation_schema, json, plain, re, scientific_digest, scientific_invocation_ref, selection_fields, selector_selection, validate_child_selection, validate_closed_schema, validate_evidence_axis_entry, validate_filled_process, validate_instruction_entry, validate_revision_origin, validate_schema, validate_selection, validate_support_entry

class ScientificFromParent:

    def assignment_schema(self, role):
        self._role(role)
        return deepcopy(_ASSIGNMENT)

    def child_assignment_schema(self, parent, role):
        schema = self.assignment_schema(role)
        required = getattr(self.services, 'annotation_task_required', lambda: False)()
        if required:
            schema['required'].append('proposed_annotation_ref')
        return schema

    def _selection(self, value):
        selection = validate_selection(value)
        fields = selection_fields(selection)
        for key in fields[:2]:
            reference = selection[key]
            if reference['library_id'] != self._library_record['library_id']:
                raise ContractError('scientific_selection_library_mismatch')
            entry = self.library.resolve(reference)
            if key == fields[0]:
                if entry.get('entry_version') == INSTRUCTION_VERSION:
                    validate_instruction_entry(entry)
                elif entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
                    validate_evidence_axis_entry(entry)
                elif entry.get('entry_version') != SUPPORT_ENTRY_VERSION:
                    raise ContractError('scientific_support_metadata_required')
                else:
                    validate_support_entry(entry)
        if selection['version'] == LEGACY_SELECTION_VERSION:
            self.tool_library.resolve(selection['tools'])
        else:
            self.tool_library.resolve_tool_info(selection['child_tool_info'])
        return selection

    def _assignment(self, value, scope, *, materialize=False, context=None):
        assignment = _object(value, 'scientific_assignment_invalid')
        if context is not None and (materialize or assignment != plain(context.assignment) or plain(scope) != plain(context.scope)):
            raise ContractError('scientific_filled_identity_mismatch')
        if materialize and isinstance(assignment.get('selection'), dict) and (assignment['selection'].get('version') == SELECTION_VERSION):
            selected = assignment['selection']
            selected['child_tool_info'] = self.tool_library.resolve_tool_info(selected.get('child_tool_info'), self._information_catalog(scope))
        validate_schema(assignment, _RECORDED_ASSIGNMENT)
        proposed = assignment.get('proposed_annotation_ref')
        if proposed is not None and (not self.services.reference_in_scope(proposed, scope, 'hypothesis')):
            raise ContractError('proposed_annotation_outside_assigned_scope')
        assignment['selection'] = self._selection(assignment['selection'])
        if 'revision_origin' in assignment:
            assignment['revision_origin'] = validate_revision_origin(assignment['revision_origin'])
        for reference in assignment['evidence_refs']:
            if not re.fullmatch(_REFERENCE['pattern'], reference) or not self.services.reference_in_scope(reference, scope, None):
                raise ContractError('scientific_evidence_reference_unavailable', detail={'reference': reference})
        self._tool_resolution_for(assignment['selection'], scope, context=context)
        return assignment

    @staticmethod
    def _invocation(invocation, scope):
        value = _object(invocation, 'scientific_invocation_invalid')
        if set(value) != {'objective', 'purpose', 'report_schema', 'initial_report'} or not isinstance(value['objective'], str) or (not value['objective']) or (not isinstance(value['purpose'], str)) or (not value['purpose']) or (not isinstance(value['initial_report'], dict)):
            raise ContractError('scientific_invocation_invalid')
        schema = validate_closed_schema(value['report_schema'])
        validate_schema(value['initial_report'], interpretation_schema(schema))
        return {'objective': value['objective'], 'scope': _object(scope, 'scientific_scope_invalid'), 'purpose': value['purpose'], 'report_schema': schema, 'initial_report': value['initial_report']}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if parent is None:
            raise ContractError('scientific_parent_invocation_required')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
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
        assignment = self._assignment(selection, scope, materialize=True)
        if 'revision_origin' in assignment:
            self._validate_origin(parent, assignment, preparation_reader=self.services.scientific_preparation, expected_path=parent.path)
        return assignment

    def _validate_origin(self, context, assignment, *, preparation_reader, expected_path):
        origin = validate_revision_origin(assignment['revision_origin'])
        preparation = _object(preparation_reader(context, origin['preparation_operation_ref']), 'scientific_revision_preparation_invalid')
        if set(preparation) != {'operation_ref', 'invocation_ref', 'selection', 'arguments', 'proposal', 'revision_origin'}:
            raise ContractError('scientific_revision_preparation_invalid')
        initial = self._selection(preparation['selection'])
        arguments = _object(preparation['arguments'], 'scientific_revision_preparation_invalid')
        proposal = validate_child_selection(preparation['proposal'])
        argument_schema = _LEGACY_REVISION_ARGUMENTS if proposal['selection']['version'] == LEGACY_SELECTION_VERSION else _REVISION_ARGUMENTS
        validate_schema(arguments, argument_schema)
        prepared_origin = validate_revision_origin(preparation['revision_origin'])
        expected_invocation = scientific_invocation_ref(context.run_id, expected_path)
        if preparation['operation_ref'] != origin['preparation_operation_ref'] or preparation['invocation_ref'] != expected_invocation or origin['parent_invocation_ref'] != expected_invocation or (prepared_origin != origin) or (proposal['parent_selection_sha256'] != scientific_digest(initial)) or (proposal['selection'] != assignment['selection']) or (proposal['selection'] != self._proposed_selection(initial, arguments, proposal['selection']['version'], context.scope)):
            raise ContractError('scientific_revision_preparation_mismatch')

    def prepare_invocation(self, parent, role, inputs, scope, operation_key, *, invocation, closed_context=None):
        original = self._invocation(invocation, scope)
        sources = [node.get('x-source') for node in original['report_schema'].get('properties', {}).values()]
        for source in self.required_return_sources(parent, role):
            if sources.count(source) != 1:
                raise ContractError('scientific_child_return_requires_' + source)
        if closed_context is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
            self._role(role)
            workflow = getattr(self.services, 'workflow', None)
            if parent is None or workflow is None or workflow.scientific_process_binding is not self or (parent.run_id != workflow.run_id) or (closed_context.run_id != parent.run_id) or (closed_context.role != role) or (closed_context.path[:-1] != parent.path):
                raise ContractError('scientific_closed_commission_conflict')
            records = EpisodeReturnRecords(workflow.store, parent.run_id, failure_prefix='scientific_closed_')
            records.authenticate(parent)
            records.authenticate(closed_context)
            match = re.fullmatch('child_(0|[1-9][0-9]*)', closed_context.path[-1][1])
            if match is None or operation_key != f'{parent.run_id}:{parent.episode_id}:{match[1]}':
                raise ContractError('scientific_closed_commission_conflict')
            index = int(match[1])
            row = workflow.journal.row('runtime_actions', parent.episode_id, index)
            if row is None or row['result'] is None:
                raise ContractError('scientific_closed_commission_required')
            selected, outcome = (json.loads(row['action']), json.loads(row['result']))
            if not isinstance(outcome, dict) or outcome.get('status') != 'completed' or selected.get('kind') != 'episode_child' or (selected.get('role') != role) or (not records._equal(selected.get('assignment'), inputs)) or (not records._equal(selected.get('scope'), scope)) or (not records._equal(selected.get('goal'), original['objective'])) or (not records._equal(selected.get('purpose'), original['purpose'])) or (not records._equal(json.loads(selected['initial_report_json']), original['initial_report'])):
                raise ContractError('scientific_closed_commission_conflict')
            child, _, schema = records._attempt(parent, index)
            filled = self.restore_closed_process(closed_context)
            if filled is None or child.episode_id != closed_context.episode_id or (not records._equal(child.request, closed_context.request)):
                raise ContractError('scientific_closed_commission_conflict')
            request = plain(child.request)
            saved_invocation = self._invocation({'objective': request['goal']['objective'], 'purpose': request['report_contract']['decision'], 'report_schema': schema, 'initial_report': request['message']['initial_report']}, child.scope)
            assignment = plain(child.assignment)
            selectors = {**assignment, 'selection': selector_selection(assignment['selection'])}
            if not records._equal(saved_invocation, original) or not (records._equal(inputs, assignment) or records._equal(inputs, selectors)):
                raise ContractError('scientific_closed_commission_conflict')
            assignment = self._assignment(assignment, scope, context=closed_context)
            if 'revision_origin' in assignment:
                self._validate_origin(parent, assignment, preparation_reader=self.services.scientific_preparation, expected_path=parent.path)
            return {'assignment': assignment, 'scientific_process': filled}
        assignment = self.prepare_assignment(parent, role, inputs, scope, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a110.component_axis_reports import validate_native_return_channels
        validate_native_return_channels(assignment['selection'], original['report_schema'])
        filled = validate_filled_process({'version': 'filled_scientific_process_v1', 'selection': assignment['selection'], 'assignment_sha256': scientific_digest(assignment), 'invocation_sha256': scientific_digest(original), 'mechanics_binding': self.as_record()})
        return {'assignment': assignment, 'scientific_process': filled}

    def required_return_sources(self, parent, role):
        self._role(role)
        if parent is not None and getattr(self.services, 'annotation_task_required', lambda: False)():
            if len(parent.path) == 1:
                return ('scientific_process_results', 'committed_record_refs')
            return ('committed_record_refs',)
        return ()
