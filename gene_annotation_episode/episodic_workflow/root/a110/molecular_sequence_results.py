"""One private molecular custody, selected-action and immediate-child owner.

Public/Episodes registration and the independent scientific launch binding do
not exist in this revision. Ordinary byte/episode custody cannot substitute for
that missing producer association. Stored results are never regraded here.
"""
from __future__ import annotations
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.method_loop.identities import EpisodeRef
from .communication import plain, validate_form
from .bvbrc_appservice_custody import AppServiceCustody
from .episode_receipts import EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION, _validate_report_prefix
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest, validate_target
from .genomic_overlap_result_receipts import GenomicOverlapResultReceipts as _Actions
from .genomic_overlap_result_receipts import read_control, same, unique
from .molecular_sequence_result_contracts import FACT_SOURCES, FAILURE_SOURCE, FILE_ROLES, MODES, PROJECTION_SOURCE, SAVED_SOURCE, empty_file_state, failure, require, select_molecular_sequence_return_facts, select_stored_molecular_sequence_values, validate_file_state, validate_molecular_sequence_fact_values, validate_molecular_sequence_projection, validate_molecular_sequence_result_selector, SCHEMAS
from .native_file_capture import retained_native_file, _identity
from .native_flux_balance_storage import read_bytes
from . import molecular_sequence_result_contracts as supplied
from .domain import identity as record_identity
VERSION = 'molecular_sequence_result_receipt_v1'
PUBLIC_VERSION = 'molecular_sequence_public_result_v1'
PREFIX = 'molecular_sequence_received_report_prefix'
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}

def _json(raw):
    from .molecular_sequence_driver import _json as decode
    return decode(raw)

def _facts():
    return {source: [] for source in FACT_SOURCES}

class MolecularSequenceResults(EpisodeReturnRecords):
    """One owner for five profiles; no per-profile receipt or episode types."""
    locked_action = _Actions.locked_action
    require_action = _Actions.require_action
    _artifact_value = _Actions._artifact_value
    capture_control = _Actions.capture_control
    observation = _Actions.observation
    _selection = AppServiceCustody._selection
    _selected_form = AppServiceCustody._selected_form
    _child_contract = AppServiceCustody._child_contract
    _report_contract = staticmethod(AppServiceCustody._report_contract)
    _contract_information = AppServiceCustody._contract_information
    _json = AppServiceCustody._json
    _table = AppServiceCustody._table
    _attempt = AppServiceCustody._attempt

    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix='molecular_sequence_result_')
        self.owner, self._active = (owner, {})

    @property
    def returns(self):
        return self

    def applies(self, context):
        return context.role == 'results' and plain(context.assignment).get('selector', {}).get('version') in ('molecular_sequence_result_selector_v1', supplied.SUPPLIED_SELECTOR_VERSION)

    def action_directory(self, episode_id, operation_key):
        return Path(self.owner.directory) / 'execution-results' / digest([self.run_id, episode_id]) / 'molecular-sequence-actions' / digest(operation_key)

    def file_metadata(self, file, *, value=None, newline=False):
        file = _identity(file)
        metadata = self.store.get(file['artifact_ref'])
        require(metadata['record_type'] == 'artifact' and metadata['id'] == file['artifact_ref'] and (metadata['sha256'] == file['sha256']) and (metadata['size'] == file['size_bytes']), 'molecular_sequence_file_identity_conflict')
        if value is not None:
            raw = canonical(value).encode() + (b'\n' if newline else b'')
            require(hashlib.sha256(raw).hexdigest() == file['sha256'] and len(raw) == file['size_bytes'], 'molecular_sequence_file_value_conflict')
        return file

    def _commission(self, parent, child, *, construction=False):
        self.authenticate(parent, allow_unsaved=construction)
        self.authenticate(child, allow_unsaved=construction)
        require(child.path[:-1] == parent.path, 'molecular_sequence_commission_parent_conflict')
        self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        slot = child.path[-1][1]
        require(slot.startswith('child_') and slot[6:].isdecimal(), 'molecular_sequence_commission_slot_conflict')
        index = int(slot[6:])
        require(str(index) == slot[6:])
        selected, sent = self._selection(parent, index, unsaved=construction)
        require(selected.get('kind') in ('episode_child', 'job_child', 'child'), 'molecular_sequence_original_commission_required')
        require(selected.get('kind') == 'child' or selected.get('role') == child.role, 'molecular_sequence_commission_role_conflict')
        require(same(selected.get('scope'), plain(child.scope)), 'molecular_sequence_commission_scope_conflict')
        if child.role in ('results', 'launch', 'launch_local'):
            require(same(selected.get('assignment'), plain(child.assignment)), 'molecular_sequence_commission_assignment_conflict')
        self._child_contract(child, selected, sent)

    def _context(self, context):
        self.authenticate(context)
        require(self.applies(context) and len(context.path) > 1, 'molecular_sequence_results_context_required')
        assignment = plain(context.assignment)
        if assignment.get('selector', {}).get('version') == supplied.SUPPLIED_SELECTOR_VERSION:
            require(set(assignment) == {'version', 'selector', 'constraints'} and assignment['version'] == supplied.SUPPLIED_ASSIGNMENT_VERSION)
            supplied.validate_molecular_sequence_supplied_selector(assignment['selector'])
            supplied.supplied_execution_constraints(assignment['constraints'])
        else:
            require(set(assignment) == {'version', 'handoff_ref', 'selector'} and assignment['version'] == 'execution_results_assignment_v1')
            validate_molecular_sequence_result_selector(assignment['selector'])
        self.store.validate_scope(plain(context.scope))
        self._commission(self.context(EpisodeRef(self.run_id, context.path[:-1]).episode_id), context)
        return assignment

    def intent(self, context, target, tool_name, arguments, operation_key):
        if tool_name in supplied.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS:
            self.authenticate(context)
            require(target is None)
            self.store.validate_scope(plain(context.scope))
            value = supplied.validate_ordinary_molecular_sequence_intent(dict(version=supplied.ordinary_molecular_sequence_intent_version(tool_name, arguments), run_id=self.run_id, episode_id=context.episode_id, path=plain(context.path), scope=plain(context.scope), assignment=plain(context.assignment), original_request_sha256=digest(plain(context.request)), operation_key=operation_key, tool_name=tool_name, arguments=deepcopy(arguments), target=None), operation=tool_name)
            self._selected(value)
            return value
        assignment = self._context(context)
        require(tool_name in ('execution.results.status', 'execution.results.collect') and arguments == {} and (type(arguments) is dict))
        if assignment['selector'].get('version') == supplied.SUPPLIED_SELECTOR_VERSION:
            require(target is None)
        elif assignment['selector']['mode'] == MODES[0]:
            target = validate_target(plain(target))
            require(target['run_id'] == self.run_id and target['handle'] == assignment['handoff_ref'] and (target['resource_kind'] == 'local'))
            self.store.validate_scope(target['scope'], parent_scope=plain(context.scope))
        else:
            require(target is None)
        value = dict(version='molecular_sequence_result_intent_v1', run_id=self.run_id, episode_id=context.episode_id, path=plain(context.path), scope=plain(context.scope), assignment=assignment, original_request_sha256=digest(plain(context.request)), operation_key=operation_key, tool_name=tool_name, arguments={}, target=deepcopy(target))
        self._selected(value)
        return value

    def _selected(self, intent):
        operation = intent.get('tool_name')
        if operation not in supplied.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS:
            return _Actions._selected(self, intent)
        intent = supplied.validate_ordinary_molecular_sequence_intent(intent, operation=operation)
        context = self.context(intent['episode_id'])
        require(same(intent, self._ordinary_context_intent(context, intent['arguments'], intent['operation_key'], operation=operation)), 'molecular_sequence_ordinary_context_conflict')
        row = self.owner._selected_result_action(intent['episode_id'], intent['operation_key'], operation, intent['arguments'])
        require(same(_json(row['action'].encode()), dict(kind='tool', tool=operation, arguments=intent['arguments'])), 'molecular_sequence_ordinary_selected_action_conflict')
        return row

    def _ordinary_context_intent(self, context, arguments, operation_key, *, operation=supplied.ORDINARY_ORF_TOOL):
        EpisodeReturnRecords(self.store, context.run_id, failure_prefix='molecular_sequence_ordinary_').authenticate(context)
        return supplied.validate_ordinary_molecular_sequence_intent(dict(version=supplied.ordinary_molecular_sequence_intent_version(operation, arguments), run_id=context.run_id, episode_id=context.episode_id, path=plain(context.path), scope=plain(context.scope), assignment=plain(context.assignment), original_request_sha256=digest(plain(context.request)), operation_key=operation_key, tool_name=operation, arguments=deepcopy(arguments), target=None), operation=operation)

    def _ordinary_value(self, file):
        return _json(read_bytes(retained_native_file(self.store, self.file_metadata(file))))

    def _ordinary_retained_metadata(self, plan, original):
        """Use the one existing metadata parser against retained original bytes."""
        from . import molecular_sequence_ordinary as ordinary
        attempt = Path(plan['attempt_directory'])
        files = {str(attempt / 'attempt-bundle.json'): original['bundle_file'], str(attempt / 'driver-output' / 'declaration.json'): original['declaration_file']}

        def read(path):
            selected = files[str(path)]
            if selected is None:
                raise FileNotFoundError(str(path))
            return self._ordinary_value(selected)
        return ordinary._result_metadata(plan, read_json=read)

    def _ordinary_match_metadata(self, execution, metadata, *, original):
        bundle, declaration, declarations, _issues = metadata
        if bundle is not None:
            require(same(bundle, execution['bundle']), 'molecular_sequence_ordinary_original_metadata_conflict')
        if declaration is not None:
            require(same(declaration, execution['declaration']) and same(declarations, execution['declarations']), 'molecular_sequence_ordinary_original_metadata_conflict')
            if bundle is not None:
                observed = next((row for row in bundle['files'] if row['role'] == 'declaration'))['observed']
                require(observed is not None and original['declaration_file'] is not None and all((observed[key] == original['declaration_file'][key] for key in ('sha256', 'size_bytes'))), 'molecular_sequence_ordinary_original_metadata_conflict')

    def _ordinary_bundle_role_states(self, sources, bundle):
        """Qualify actual retained bytes against independent original observations."""
        result = deepcopy(sources)
        if bundle is None:
            return result
        observed = {row['role']: row for row in bundle['files']}
        for role in ('capture', 'sheet', 'components'):
            state, observation = (result[role], observed.get(role))
            file = state['file']
            if file is None or observation is None or observation['observed_state'] == 'unavailable':
                continue
            pin = observation['observed']
            if observation['observed_state'] == 'present' and all((file[key] == pin[key] for key in ('sha256', 'size_bytes'))):
                continue
            result[role] = empty_file_state('identity_conflict', declared=state['declared'], issue=failure('artifact_identity_conflict', 'capture', role=role, source_ref=file['artifact_ref']))
            result[role]['observed_identity'] = {key: file[key] for key in ('sha256', 'size_bytes')}
        return result

    def _ordinary_failed_capture_refs(self, sources):
        """Index only captured failures whose typed observation matches Store metadata."""
        references = []
        for role in ('capture', 'sheet', 'components'):
            state = sources[role]
            issue, observed = (state['failure'], state['observed_identity'])
            if state['state'] != 'identity_conflict' or state['file'] is not None or observed is None or (issue is None) or (issue['code'] != 'artifact_identity_conflict') or (issue['stage'] != 'capture') or (issue['role'] != role) or (issue['source_ref'] != 'artifact_' + observed['sha256']):
                continue
            try:
                self.file_metadata(dict(artifact_ref=issue['source_ref'], format='json', **observed))
            except (ValueError, KeyError):
                continue
            references.append(issue['source_ref'])
        return references

    def _placement_context(self, sources, *, operand=None, parent_context=None):
        """Copy authenticated stored input/population facts, without calculation."""
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.primer_placement_result_contracts import context, native_arguments, operand_files, scientific_context
        documents = {}
        for role in ('sheet', 'components'):
            file = sources[role]['file']
            try:
                documents[role] = None if file is None else self._ordinary_value(file)
            except (OSError, ValueError, UnicodeError):
                documents[role] = None
        original_files = None if parent_context is None else parent_context['original_operand_files']
        frozen_input = None if parent_context is None else parent_context['input']
        if operand is not None:
            primers = operand['primers']
            args = dict(target_ref=operand['target']['subject']['id'], primer_refs=[row['subject']['id'] for row in primers] if type(primers) is list else primers['subject']['id'])
            native = native_arguments(args, operand)
            frozen_input = dict(target_sequence=native['long_seq'], primers=native['short_seqs'], **scientific_context(args, operand))
            original_files = operand_files(operand)
        return context(sheet=documents['sheet'], components=documents['components'], source_files=sources, original_files=original_files, frozen_input=frozen_input)

    def _validate_ordinary_molecular_sequence_custody(self, custody, intent, *, _seen=()):
        operation = intent['tool_name']
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        if type(custody) is dict and custody.get('version') == profile['saved_custody_version']:
            return self._validate_ordinary_molecular_sequence_saved_custody(custody, intent, _seen=_seen)
        custody = supplied.validate_ordinary_molecular_sequence_custody(custody, operation=operation)
        require(custody['intent'] == intent, 'molecular_sequence_ordinary_custody_intent_conflict')
        original = custody['original']
        binding = self._ordinary_value(custody['request']['input_binding_file'])
        execution = supplied.validate_ordinary_molecular_sequence_execution(self._ordinary_value(original['execution_file']), operation=operation)
        producer = EpisodeReturnRecords(self.store, intent['run_id'], failure_prefix='molecular_sequence_ordinary_').context(intent['episode_id'])
        require(binding['context'] == producer.as_record() and binding['arguments'] == intent['arguments'] and (binding['operation_key'] == intent['operation_key']) and (execution['plan']['identity'] == original['identity']), 'molecular_sequence_ordinary_binding_conflict')
        from . import molecular_sequence_ordinary as ordinary
        ordinary._closed(binding, ('version', 'context', 'operation_key', 'arguments', 'frozen_operand', 'selected', 'policy'), 'retained_binding_fields_invalid')
        ordinary._closed(binding['selected'], ('resource_id', 'workspace', 'deployment', 'software', 'environment'), 'retained_selection_fields_invalid')
        ordinary._deployment(operation, binding['selected']['deployment'])
        operand = ordinary._operand(binding['frozen_operand'], intent['arguments'] if operation == 'align_sequences' else intent['arguments']['subject_ref'], operation=operation)
        plan = execution['plan']
        require(set(binding) == {'version', 'context', 'operation_key', 'arguments', 'frozen_operand', 'selected', 'policy'} and binding['version'] == profile['binding_version'] and (binding['policy'] == POLICY) and all((plan['identity'][key] == intent[key] for key in ('run_id', 'episode_id', 'operation_key'))) and (plan['identity']['assignment_sha256'] == digest(intent['assignment'])) and (binding['selected']['software'] == plan['software']) and (binding['selected']['environment'] == ordinary.ENVIRONMENT_SELECTION) and (binding['selected']['resource_id'] == plan['identity']['resource_id']) and (binding['selected']['deployment'] == plan['selection']['driver_request']['selection']['deployment']), 'molecular_sequence_ordinary_plan_binding_conflict')
        for retained, selected in ((custody['request']['input_binding_file'], execution['binding_file']), (original['plan_file'], execution['plan_file']), (original['driver_request_file'], execution['driver_request_file'])):
            require(all((retained[key] == selected[key] for key in ('sha256', 'size_bytes'))), 'molecular_sequence_ordinary_retained_control_conflict')
        request = self._ordinary_value(original['driver_request_file'])
        require(self._ordinary_value(original['plan_file']) == plan and request == plan['selection']['driver_request'] and (request['selection']['arguments'] == ordinary._native_arguments(operation, intent['arguments'], operand)) and (request['scientific_context'] == ordinary._scientific_context(operation, intent['arguments'], operand)), 'molecular_sequence_ordinary_request_conflict')
        handle, native_request = (self._ordinary_value(original['native_handle_file']), self._ordinary_value(original['native_request_file']))
        from .molecular_sequence_execution_contracts import molecular_sequence_adapter_argv
        require(handle == execution['handle'] and handle['command'] == molecular_sequence_adapter_argv(plan) and (handle['cwd'] == str(Path(plan['identity']['execution_id']).parent)) and (handle['metadata']['policy'] == POLICY) and (native_request == ordinary._native_request(plan, handle['paths'])) and (hashlib.sha256(read_bytes(retained_native_file(self.store, original['native_request_file']))).hexdigest() == handle['request_sha256']), 'molecular_sequence_ordinary_native_request_conflict')
        proof = self._ordinary_value(original['association_file'])
        require(proof == dict(version='molecular_sequence_ordinary_association_v1', intent_sha256=digest(intent), original_identity=original['identity'], input_binding_file=custody['request']['input_binding_file'], controls={key: original[key] for key in ('plan_file', 'driver_request_file', 'native_handle_file', 'native_request_file', 'execution_file')}, terminal=True, quiescent=True, metadata=execution['metadata'], returncode=execution['returncode']), 'molecular_sequence_ordinary_association_conflict')
        metadata = self._ordinary_retained_metadata(plan, original)
        self._ordinary_match_metadata(execution, metadata, original=original)
        bundle, declaration, declarations, _issues = metadata
        require(same(self._ordinary_bundle_role_states(custody['source_files'], bundle), custody['source_files']), 'molecular_sequence_ordinary_bundle_role_identity_conflict')
        raw_roles = {} if declaration is None else declaration['files']
        for role in ('capture', 'sheet', 'components'):
            state = custody['source_files'][role]
            if role in declarations:
                require(same(state['declared'], declarations[role]), 'molecular_sequence_ordinary_role_declaration_conflict')
                if state['file'] is not None:
                    require(declarations[role]['state'] == 'present' and all((state['file'][key] == declarations[role][key] for key in ('sha256', 'size_bytes'))), 'molecular_sequence_ordinary_role_identity_conflict')
            elif role in raw_roles:
                require(state['file'] is None and state['failure'] == failure('schema_invalid', 'capture', role=role), 'molecular_sequence_ordinary_invalid_role_conflict')
            else:
                require(state['declared'] is None and state['state'] != 'retained', 'molecular_sequence_ordinary_undeclared_role_conflict')
        packet = supplied.validate_ordinary_molecular_sequence_packet(self._ordinary_value(custody['public_packet_file']), operation=operation)
        if operation == 'align_sequences':
            require(same(custody['context'], self._placement_context(custody['source_files'], operand=operand)), 'molecular_sequence_ordinary_placement_context_conflict')
        require(packet == supplied.ordinary_molecular_sequence_packet(custody, operation=operation), 'molecular_sequence_ordinary_packet_conflict')
        return custody

    def _ordinary_molecular_sequence_source_record(self, custody, capsule):
        operation = custody['intent']['tool_name']
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        if custody['version'] == profile['saved_custody_version']:
            refs = [custody['request']['source_admission_file']['artifact_ref'], custody['calculation']['started_file']['artifact_ref'], custody['calculation']['result_file']['artifact_ref'], custody['calculation']['diagnostic_file']['artifact_ref']]
            if custody['source_files']['components']['file'] is not None:
                refs.append(custody['source_files']['components']['file']['artifact_ref'])
            if operation == 'align_sequences' and custody['context']['original_operand_files'] is not None:
                files = custody['context']['original_operand_files']
                inputs = {file['artifact_ref'] for file in [files['target'], *(files['primers'] if type(files['primers']) is list else [files['primers']])]}
                refs = [ref for ref in refs if ref not in inputs]
            return dict(provider=operation, version=profile['source_version'], artifact_ref=custody['public_packet_file']['artifact_ref'], request_ref=capsule['artifact_ref'], text_ref=None, accession=None, uri=None, retrieved_at=custody['retrieved_at'], parent_source_refs=[custody['original_source']['source_ref']], auxiliary_artifact_refs=list(dict.fromkeys(refs)))
        refs = [row['file']['artifact_ref'] for row in custody['source_files'].values() if row['file'] is not None]
        refs.extend(self._ordinary_failed_capture_refs(custody['source_files']))
        refs.extend((file['artifact_ref'] for file in custody['original'].values() if type(file) is dict and 'artifact_ref' in file))
        refs.append(custody['request']['input_binding_file']['artifact_ref'])
        operand = self._ordinary_value(custody['request']['input_binding_file'])['frozen_operand']
        if operation == 'align_sequences':
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.primer_placement_result_contracts import operand_records
            inputs = {row['input_file']['artifact_ref'] for row in operand_records(operand)}
            refs = [ref for ref in dict.fromkeys(refs) if ref not in inputs]
        else:
            refs = [ref for ref in dict.fromkeys(refs) if ref != operand['input_file']['artifact_ref']]
        return dict(provider=operation, version=profile['source_version'], artifact_ref=custody['public_packet_file']['artifact_ref'], request_ref=capsule['artifact_ref'], text_ref=None, accession=None, uri=None, retrieved_at=custody['retrieved_at'], parent_source_refs=[], auxiliary_artifact_refs=refs)

    def read_ordinary_molecular_sequence_publication(self, context, source_ref, *, operation, read_received=None, pending_operation_key=None):
        """Authenticate real action metadata before opening private publication bytes."""
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        with self.store.read_snapshot():
            return self._read_ordinary_molecular_sequence_publication(context, source_ref, operation=operation, read_received=read_received, pending_operation_key=pending_operation_key)

    def _read_ordinary_molecular_sequence_publication(self, context, source_ref, *, operation, read_received, pending_operation_key, _seen=()):
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        require(source_ref not in _seen, 'molecular_sequence_ordinary_source_cycle')
        if _seen and context.run_id != self.run_id:
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix='molecular_sequence_ordinary_').authenticate(context)
        else:
            self.authenticate(context)
        source = self.store.get(source_ref)
        require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and (source.get('provider') == operation) and (source.get('version') == profile['source_version']), 'molecular_sequence_ordinary_source_required')
        payload = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        require(source_ref == record_identity('source', {'origin': 'tool', 'record': payload}), 'molecular_sequence_ordinary_source_identity_conflict')
        rows = self.db.execute("SELECT operation.*, action.run_id AS producer_run_id,\n            action.episode_id AS producer_episode_id, action.decision_index AS producer_decision_index,\n            action.action AS selected_action, action.result AS recorded_outcome\n            FROM tool_operations operation JOIN runtime_actions action\n              ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index\n            WHERE operation.name=? AND json_extract(operation.result,'$.result.source_ref')=?\n              AND (json_extract(operation.arguments,'$.mode') IS NULL\n                   OR json_extract(operation.arguments,'$.mode')='calculate_saved'\n                   OR (operation.name='align_sequences' AND json_extract(operation.arguments,'$.mode')='run_native'))\n              AND json_extract(operation.result,'$.status') IN ('completed','partial')", (operation, source_ref)).fetchall()
        require(len(rows) == 1, 'molecular_sequence_ordinary_producer_required')
        row = rows[0]
        records = EpisodeReturnRecords(self.store, row['producer_run_id'], failure_prefix='molecular_sequence_ordinary_')
        producer = records.context(row['producer_episode_id'])
        arguments, outcome = (_json(row['arguments'].encode()), _json(row['result'].encode()))
        intent = self._ordinary_context_intent(producer, arguments, row['operation_key'], operation=operation)
        require(row['scope'] == canonical(plain(producer.scope)) and same(_json(row['selected_action'].encode()), dict(kind='tool', tool=operation, arguments=arguments)) and (row['id'] == record_identity('operation', {'key': row['operation_key'], 'name': operation, 'arguments': arguments})) and (outcome.get('operation_ref') == row['id']) and (outcome.get('record_refs') == [source_ref]), 'molecular_sequence_ordinary_producer_conflict')
        pending = row['recorded_outcome'] is None
        if pending:
            require(pending_operation_key == row['operation_key'] and context.run_id == producer.run_id and (context.episode_id == producer.episode_id), 'molecular_sequence_ordinary_completed_action_required')
        else:
            actual = _json(row['recorded_outcome'].encode())
            require({key: value for key, value in actual.items() if key != 'pending_work_after_action'} == outcome, 'molecular_sequence_ordinary_outcome_conflict')
        if context.episode_id != producer.episode_id or context.run_id != producer.run_id:
            require(callable(read_received), 'molecular_sequence_ordinary_source_admission_required')
        if read_received is not None:
            receipts = EpisodeReceipts.__new__(EpisodeReceipts)
            receipts.store, receipts.db, receipts.run_id = (self.store, self.db, context.run_id)
            require(source_ref in set(receipts.known(context.episode_id)), 'molecular_sequence_ordinary_source_not_received')
            admitted = read_received(context, source_ref, 'source', source_metadata_only=True)
            require(admitted['failure'] is None and admitted['input']['witness']['record'] == source, 'molecular_sequence_ordinary_source_not_received')
        self.store.validate_scope(plain(producer.scope), parent_scope=plain(context.scope))
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.molecular_measurement_tools import _publication_bytes
        custody = self._validate_ordinary_molecular_sequence_custody(_json(_publication_bytes(self.store, source['request_ref'])), intent, _seen=(*_seen, source_ref))
        capsule = dict(artifact_ref=source['request_ref'], sha256=source['request_ref'][9:], size_bytes=self.store.get(source['request_ref'])['size'], format=custody['version'])
        require(payload == self._ordinary_molecular_sequence_source_record(custody, capsule), 'molecular_sequence_ordinary_source_control_conflict')
        packet = supplied.validate_ordinary_molecular_sequence_packet(_json(_publication_bytes(self.store, source['artifact_ref'])), operation=operation)
        public = supplied.validate_ordinary_molecular_sequence_return(dict(source_ref=source_ref, **packet), operation=operation)
        require(public == outcome['result'] and packet == supplied.ordinary_molecular_sequence_packet(custody, operation=operation), 'molecular_sequence_ordinary_saved_values_conflict')
        return dict(admission_kind='source_only', source=source, stored=public, control=custody, grading_ref=None)

    def _ordinary_recorded_operation(self, intent):
        """One current-action/ToolOperation association for execution and facts."""
        operation = intent['tool_name']
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        selected = self._selected(intent)
        row = self.db.execute('SELECT * FROM tool_operations WHERE operation_key=?', (intent['operation_key'],)).fetchone()
        if row is None:
            return None
        require(row['name'] == operation and row['arguments'] == canonical(intent['arguments']) and (row['scope'] == canonical(intent['scope'])) and (row['id'] == record_identity('operation', {'key': intent['operation_key'], 'name': operation, 'arguments': intent['arguments']})), 'molecular_sequence_ordinary_action_conflict')
        outcome = _json(row['result'].encode())
        require(outcome.get('operation_ref') == row['id'], 'molecular_sequence_ordinary_action_conflict')
        if selected['result'] is not None:
            actual = _json(selected['result'].encode())
            require(same({key: value for key, value in actual.items() if key != 'pending_work_after_action'}, outcome), 'molecular_sequence_ordinary_action_conflict')
        return outcome

    def read_ordinary_molecular_sequence_action_result(self, context, arguments, operation_key, *, operation, read_received=None):
        """Authenticate this recorded action separately from its Source producer."""
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        intent = self._ordinary_context_intent(context, arguments, operation_key, operation=operation)
        outcome = self._ordinary_recorded_operation(intent)
        require(outcome is not None and outcome.get('status') in ('completed', 'partial'), 'molecular_sequence_ordinary_action_conflict')
        if arguments.get('mode') in ('read_stored', 'calculate_saved'):
            self._ordinary_original_source_admission(context, arguments['result_ref'], operation_key)
        public = supplied.validate_ordinary_molecular_sequence_return(outcome['result'], operation=operation)
        require(outcome.get('record_refs') == [public['source_ref']], 'molecular_sequence_ordinary_action_conflict')
        publication = self.read_ordinary_molecular_sequence_publication(context, public['source_ref'], operation=operation, read_received=read_received if arguments.get('mode') == 'read_stored' else None, pending_operation_key=operation_key)
        if arguments.get('mode') == 'read_stored':
            receipt = read_control(self.action_directory(context.episode_id, operation_key) / 'ordinary-read-receipt.json')
            require(type(receipt) is dict and set(receipt) == {'version', 'intent', 'source_sha256', 'public'} and (receipt['version'] == profile['read_receipt_version']) and same(receipt['intent'], intent) and (arguments['result_ref'] == public['source_ref']) and (receipt['source_sha256'] == digest(publication['source'])) and same(receipt['public'], public) and same(self.project_ordinary_molecular_sequence_view(publication, rows=arguments['rows']), public), 'molecular_sequence_ordinary_saved_view_conflict')
            return public
        require(publication['control']['request']['invocation']['operation_key'] == operation_key and same(publication['stored'], public), 'molecular_sequence_ordinary_action_source_conflict')
        return public

    def _ordinary_saved_admission(self, context, source_ref, received):
        from .molecular_sequence_input_contracts import validate_molecular_sequence_received_source, input_record_digest
        received = validate_molecular_sequence_received_source(received)
        require(received['failure'] is None and received['selection'] == dict(reference=source_ref, namespace='source'), 'molecular_sequence_ordinary_source_not_received')
        item = received['input']
        manifest = EpisodeReceipts.read_manifest(self.db, context.run_id, context.episode_id)
        require(item['receiver'] == dict(run_id=context.run_id, episode_id=context.episode_id, request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment))) and same(item['scope'], self.store.validate_scope(plain(context.scope))) and same(item['inheritance_manifest'], manifest) and same(plain(context.request)['message'].get('knowledge_inheritance'), manifest) and (item['witness']['record'] == self.store.get(source_ref)), 'molecular_sequence_ordinary_source_admission_conflict')
        return received

    def _ordinary_original_source_admission(self, context, source_ref, operation_key):
        """Use original selected-action receipt authority without opening bytes."""
        records = EpisodeReturnRecords(self.store, context.run_id, failure_prefix='molecular_sequence_ordinary_')
        records.authenticate(context)
        return records.source_admission_before(context, source_ref, int(operation_key.rsplit(':', 1)[1]))

    def project_ordinary_molecular_sequence_view(self, publication, *, rows):
        """Select literal retained cells without recalculating their populations."""
        operation = publication['control']['projection']['public']['operation']
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        control = publication['control']
        selector = {**control['projection']['selector'], 'rows': deepcopy(rows)}
        projection = self._admit_projection(selector=selector, sources=control['source_files'], association=control['projection']['association'], calculation=control['projection']['calculation'])
        packet = supplied.ordinary_molecular_sequence_packet({**control, 'intent': {'arguments': {'rows': rows}}, 'projection': projection, 'failures': unique([*control['failures'], *projection['public']['failures']])}, operation=operation)
        return supplied.validate_ordinary_molecular_sequence_return(dict(source_ref=publication['source']['id'], **packet), operation=operation)

    def _ordinary_saved_calculation(self, result, *, intent, publication):
        operation = intent['tool_name']
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        require(type(result) is dict and set(result) == {'version', 'intent_sha256', 'source_ref', 'source_sha256', 'sheet_file', 'native_call_state', 'state', 'call_count', 'components_pin', 'diagnostic_pin'} and (result['version'] == profile['calculation_result_version']) and (result['intent_sha256'] == digest(intent)) and (result['source_ref'] == publication['source']['id']) and (result['source_sha256'] == digest(publication['source'])) and (result['sheet_file'] == publication['control']['source_files']['sheet']['file']) and (result['native_call_state'] == 'not_requested') and (result['state'] in ('returned', 'raised')) and (result['call_count'] is None or (type(result['call_count']) is int and result['call_count'] == 1)) and (result['state'] != 'returned' or result['call_count'] == 1) and (result['components_pin'] is not None if result['state'] == 'returned' else result['components_pin'] is None), 'molecular_sequence_ordinary_calculation_conflict')
        from .molecular_sequence_execution_contracts import file_pin as validate_pin
        validate_pin(result['diagnostic_pin'])
        if result['components_pin'] is not None:
            validate_pin(result['components_pin'])
        return result

    def _validate_ordinary_molecular_sequence_saved_custody(self, custody, intent, *, _seen):
        operation = intent['tool_name']
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        custody = supplied.validate_ordinary_molecular_sequence_saved_custody(custody, operation=operation)
        require(same(custody['intent'], intent), 'molecular_sequence_ordinary_custody_intent_conflict')
        context = EpisodeReturnRecords(self.store, intent['run_id'], failure_prefix='molecular_sequence_ordinary_').context(intent['episode_id'])
        original = custody['original_source']
        self._ordinary_original_source_admission(context, original['source_ref'], intent['operation_key'])
        received = self._ordinary_saved_admission(context, original['source_ref'], self._ordinary_value(custody['request']['source_admission_file']))
        publication = self._read_ordinary_molecular_sequence_publication(context, original['source_ref'], operation=operation, read_received=lambda *_args, **_kwargs: received, pending_operation_key=None, _seen=_seen)
        require(digest(publication['source']) == original['record_sha256'] and original['custody_file']['artifact_ref'] == publication['source']['request_ref'] and (original['custody_file']['format'] == publication['control']['version']) and (original['packet_file']['artifact_ref'] == publication['source']['artifact_ref']) and (original['packet_file']['format'] == profile['packet_format']) and same(custody['source_files']['sheet'], publication['control']['source_files']['sheet']), 'molecular_sequence_ordinary_saved_source_conflict')
        for key in ('custody_file', 'packet_file'):
            self.file_metadata(original[key])
        calculated = self._ordinary_saved_calculation(self._ordinary_value(custody['calculation']['result_file']), intent=intent, publication=publication)
        require(same(self._ordinary_value(custody['calculation']['started_file']), dict(version=profile['calculation_started_version'], intent_sha256=digest(intent), source_ref=publication['source']['id'], source_sha256=digest(publication['source']), sheet_file=calculated['sheet_file'], native_call_state='not_requested', calculator_id=profile['calculator_id'])), 'molecular_sequence_ordinary_calculation_intent_conflict')
        diagnostic = self._ordinary_value(custody['calculation']['diagnostic_file'])
        require(type(diagnostic) is dict and set(diagnostic) == {'version', 'native_call_state', 'calculator_id', 'state', 'call_count', 'exception_type', 'exception_message'} and (diagnostic['version'] == profile['calculation_diagnostic_version']) and (diagnostic['call_count'] is None or (type(diagnostic['call_count']) is int and diagnostic['call_count'] == 1)) and all((diagnostic[key] is None or type(diagnostic[key]) is str for key in ('exception_type', 'exception_message'))) and (all((diagnostic[key] is None for key in ('exception_type', 'exception_message'))) if diagnostic['state'] == 'returned' else all((type(diagnostic[key]) is str for key in ('exception_type', 'exception_message')))) and all((diagnostic[key] == custody['calculation'][key] == calculated[key] for key in ('native_call_state', 'state', 'call_count'))) and (diagnostic['calculator_id'] == profile['calculator_id']), 'molecular_sequence_ordinary_calculation_conflict')
        for pin, file in ((calculated['diagnostic_pin'], custody['calculation']['diagnostic_file']), (calculated['components_pin'], custody['source_files']['components']['file'])):
            require((pin is None) == (file is None))
            if file is not None:
                self.file_metadata(file)
                require(all((pin[key] == file[key] for key in ('sha256', 'size_bytes'))), 'molecular_sequence_ordinary_calculation_conflict')
        projection = self._admit_projection(selector=custody['projection']['selector'], sources=custody['source_files'], association=publication['control']['projection']['association'], calculation=dict(kind='selected_saved_calculation', calculator_id=profile['calculator_id']))
        require(same(projection, custody['projection']) and same(self._ordinary_value(custody['public_packet_file']), supplied.ordinary_molecular_sequence_packet(custody, operation=operation)), 'molecular_sequence_ordinary_saved_values_conflict')
        if operation == 'align_sequences':
            require(same(custody['context'], self._placement_context(custody['source_files'], parent_context=publication['control']['context'])), 'molecular_sequence_ordinary_placement_context_conflict')
        return custody

    def read_ordinary_orf_publication(self, context, source_ref, *, read_received=None, pending_operation_key=None):
        return self.read_ordinary_molecular_sequence_publication(context, source_ref, operation=supplied.ORDINARY_ORF_TOOL, read_received=read_received, pending_operation_key=pending_operation_key)

    def read_ordinary_orf_action_result(self, context, arguments, operation_key, *, read_received=None):
        return self.read_ordinary_molecular_sequence_action_result(context, arguments, operation_key, operation=supplied.ORDINARY_ORF_TOOL, read_received=read_received)

    def _admit_projection(self, *, selector, sources, association, calculation):
        documents = {'sheet': None, 'components': None}
        issues = []
        for role in documents:
            if sources[role]['file'] is not None:
                try:
                    document = _json(read_bytes(retained_native_file(self.store, sources[role]['file'])))
                    expected = SCHEMAS[selector['operation']][0 if role == 'sheet' else 1]
                    require(type(document) is dict and (document.get('schema') == expected if role == 'sheet' else document.get('schema') in expected))
                    if selector['version'] in (supplied.N_SELECTOR_VERSION, supplied.O_SELECTOR_VERSION):
                        require(type(document.get('inputs')) is dict and document['inputs'].get('operation') == selector['operation'] if role == 'sheet' else document.get('operation') == selector['operation'], 'molecular_sequence_ordinary_document_operation_conflict')
                    documents[role] = document
                except (OSError, ValueError):
                    issues.append(failure('schema_invalid', 'load', role=role, source_ref=sources[role]['file']['artifact_ref']))
        projection = select_stored_molecular_sequence_values(operation=selector['operation'], sheet=documents['sheet'], components=documents['components'], selection=selector, source_files=sources, association=association, calculation=calculation)
        projection['public']['failures'].extend(issues)
        return projection

    def _publication(self, selector, sources, projection, failures):
        groups = _facts()
        if projection is not None:
            groups[PROJECTION_SOURCE] = validate_molecular_sequence_fact_values(PROJECTION_SOURCE, [projection['public']])
        components_schema = None if projection is None else projection['public']['components_schema']
        for role in selector['return_files']:
            if sources[role]['file'] is not None:
                groups[SAVED_SOURCE].append(dict(operation=selector['operation'], role=role, artifact_ref=sources[role]['file']['artifact_ref'], source_kind='original_stored' if selector['mode'] == MODES[0] else 'selected_saved_calculation', source_sheet_ref=None if sources['sheet']['file'] is None else sources['sheet']['file']['artifact_ref'], components_schema=components_schema))
        groups[FAILURE_SOURCE] = unique([*failures, *(row['failure'] for row in sources.values() if row['failure'] is not None), *([] if projection is None else projection['public']['failures'])])
        return groups

    def _outcome(self, receipt):
        files = receipt['facts'][SAVED_SOURCE]
        return {'status': 'completed', 'record_refs': [row['artifact_ref'] for row in files], 'changed_record_refs': [row['artifact_ref'] for row in files], 'feedback': None, 'result': {'version': 'molecular_sequence_public_result_v2' if receipt['version'] == 'molecular_sequence_result_receipt_v2' else PUBLIC_VERSION, 'facts': deepcopy(receipt['facts']), 'delivery_complete': receipt['delivery_complete']}}

    def _validate_receipt(self, receipt, intent):
        if receipt.get('version') == 'molecular_sequence_result_receipt_v2':
            return self._validate_supplied_receipt(receipt, intent)
        require(type(receipt) is dict and set(receipt) == {'version', 'intent', 'source_files', 'association', 'received_sheet_receipt_file', 'worker_plan', 'worker_result', 'projection', 'failures', 'facts', 'acquired_population', 'delivery_complete'})
        require(receipt['version'] == VERSION and same(receipt['intent'], intent) and (receipt['acquired_population'] is None))
        require(receipt['association']['state'] in ('unavailable', 'conflict'), 'molecular_sequence_independent_scientific_binding_unavailable')
        require(set(receipt['source_files']) == set(FILE_ROLES) and set(receipt['facts']) == set(FACT_SOURCES))
        for row in receipt['source_files'].values():
            validate_file_state(row)
            if row['file'] is not None:
                self.file_metadata(row['file'])
        for source, values in receipt['facts'].items():
            validate_molecular_sequence_fact_values(source, values)
        if receipt['projection'] is not None:
            validate_molecular_sequence_projection(receipt['projection'])
            require(same(receipt['projection']['source_files'], receipt['source_files']))
            require(same(receipt['projection']['association'], receipt['association']))
            require(not receipt['facts'][PROJECTION_SOURCE] or same(receipt['facts'][PROJECTION_SOURCE], [receipt['projection']['public']]))
        expected = self._publication(intent['assignment']['selector'], receipt['source_files'], receipt['projection'], receipt['failures'])
        schema = plain(self.context(intent['episode_id']).request)['report_contract']['measurements']['schema']
        wanted = select_molecular_sequence_return_facts(expected, schema=schema)
        require(same(receipt['facts'], {source: rows if source in wanted else [] for source, rows in expected.items()}), 'molecular_sequence_publication_conflict')
        require(type(receipt['delivery_complete']) is bool)
        return deepcopy(receipt)

    def _completed(self, context):
        self.authenticate(context)
        result = []
        for row in self.db.execute('SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index', (self.run_id, context.episode_id)):
            action = json.loads(row['action'])
            if action.get('tool') != 'execution.results.collect' or row['result'] is None:
                continue
            key = f"{self.run_id}:{context.episode_id}:{row['decision_index']}"
            receipt = read_control(self.action_directory(context.episode_id, key) / 'receipt.json')
            require(receipt is not None and same(json.loads(row['result']), self._outcome(receipt)), 'molecular_sequence_completed_action_conflict')
            result.append(self._validate_receipt(receipt, self.intent(context, receipt['intent']['target'], action['tool'], {}, key)))
        return result

    def own_fact_groups(self, context, *, verify_artifacts):
        require(type(verify_artifacts) is bool and self.applies(context))
        groups = _facts()
        for receipt in self._completed(context):
            if verify_artifacts:
                for row in receipt['source_files'].values():
                    if row['file'] is not None:
                        retained_native_file(self.store, row['file'])
            for source in FACT_SOURCES:
                groups[source].extend(receipt['facts'][source])
        return {source: unique(rows) for source, rows in groups.items()}

    def facts(self, context):
        groups = self.own_fact_groups(context, verify_artifacts=False)
        if plain(context.assignment).get('selector', {}).get('version') == supplied.SUPPLIED_SELECTOR_VERSION:
            return {**groups, 'calculation_delivery_complete': self.calculation_completion(context) is not None}
        return {**groups, 'execution_completed': self.completion(context) is not None}

    def _values(self, form, schema):
        validate_form(plain(form), plain(schema), lambda *_: True)
        groups = {}
        for name, node in plain(schema)['properties'].items():
            source = node.get('x-source')
            if source in FACT_SOURCES:
                values = validate_molecular_sequence_fact_values(source, plain(form)[name])
                require(source not in groups or same(groups[source], values))
                groups[source] = values
        return groups

    def _received(self, context, sources, *, allowed=None):
        self.authenticate(context)
        require(context.role in ('annotation', 'biochemical_feasibility_evidence'))
        groups = {source: [] for source in sources}
        witnesses = []
        attempts = self.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()
        actual = []
        for attempt in attempts:
            witness = {k: attempt[k] for k in ('decision_index', 'delivery_ref', 'child_episode_id')}
            witness.update(contract_sha256=digest(json.loads(attempt['contract'])), form_sha256=digest(json.loads(attempt['form'])))
            actual.append(witness)
        if allowed is not None:
            require(all((any((same(w, current) for current in actual)) for w in allowed)), 'molecular_sequence_frozen_report_prefix_conflict')
        for attempt, witness in zip(attempts, actual):
            if allowed is not None and (not any((same(witness, w) for w in allowed))):
                continue
            schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
            if not any((node.get('x-source') in sources for node in schema.get('properties', {}).values())):
                continue
            child, form, schema = self._attempt(context, attempt['decision_index'])
            values = self._values(form, schema)
            if not any((source in values for source in sources)):
                continue
            frozen = json.loads(self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?', (self.run_id, child.episode_id)).fetchone()[0])
            if self.applies(child):
                expected = self.own_fact_groups(child, verify_artifacts=False)
            else:
                require(PREFIX in frozen, 'molecular_sequence_frozen_report_prefix_required')
                expected, _ = self._received(child, sources, allowed=_validate_report_prefix(frozen[PREFIX])['attempts'])
            for source in sources:
                for value in values.get(source, []):
                    require(any((same(value, item) for item in expected.get(source, []))), 'molecular_sequence_returned_value_conflict')
                    groups[source].append(value)
            witnesses.append(witness)
        return ({source: unique(values) for source, values in groups.items()}, witnesses)

    def received_facts(self, context, schema):
        sources = tuple(select_molecular_sequence_return_facts(_facts(), schema=plain(schema)))
        groups = self.own_fact_groups(context, verify_artifacts=False) if self.applies(context) else self._received(context, sources)[0]
        return select_molecular_sequence_return_facts(groups, schema=plain(schema))

    def facts_for_closure(self, context, schema):
        if self.applies(context):
            return self.received_facts(context, schema)
        sources = tuple(select_molecular_sequence_return_facts(_facts(), schema=plain(schema)))
        frozen = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        allowed = None if frozen is None else _validate_report_prefix(json.loads(frozen[0])[PREFIX])['attempts']
        groups, witnesses = self._received(context, sources, allowed=allowed)
        return {**select_molecular_sequence_return_facts(groups, schema=plain(schema)), PREFIX: _validate_report_prefix({'version': RECEIVED_REPORT_PREFIX_VERSION, 'attempts': witnesses})}

    def validate_received_report(self, context, form, schema):
        values = self._values(form, schema)
        if not values:
            return
        frozen = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if self.applies(context):
            expected = self.own_fact_groups(context, verify_artifacts=frozen is None)
        else:
            allowed = None if frozen is None else _validate_report_prefix(json.loads(frozen[0])[PREFIX])['attempts']
            expected = self._received(context, values, allowed=allowed)[0]
        for source, rows in values.items():
            require(all((any((same(row, original) for original in expected.get(source, []))) for row in rows)), 'molecular_sequence_returned_value_conflict')

    def record_admission(self, context, form, schema, operation_key):
        child, actual, declared = self._attempt(context, self._admission_index(context, operation_key))
        require(same(form, actual) and same(schema, declared))
        self.validate_received_report(child, actual, declared)
        return list(dict.fromkeys((row['artifact_ref'] for row in self._values(actual, declared).get(SAVED_SOURCE, []))))

    def resolve_own(self, context, reference, namespace):
        return namespace in (None, 'artifact') and self.applies(context) and any((row['artifact_ref'] == reference for row in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE]))

    def resolve_received(self, context, reference, namespace):
        return namespace in (None, 'artifact') and context.role in ('annotation', 'biochemical_feasibility_evidence') and any((row['artifact_ref'] == reference for row in self._received(context, (SAVED_SOURCE,))[0][SAVED_SOURCE]))

    def owns_reference(self, reference):
        if type(reference) is not str or not reference.startswith('artifact_'):
            return False
        for row in self.db.execute('SELECT episode_id,decision_index,action,result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL', (self.run_id,)):
            value = json.loads(row['result'])
            if value.get('result', {}).get('version') not in (PUBLIC_VERSION, 'molecular_sequence_public_result_v2'):
                continue
            receipt = read_control(self.action_directory(row['episode_id'], f"{self.run_id}:{row['episode_id']}:{row['decision_index']}") / 'receipt.json')
            require(receipt is not None)
            if value['result']['version'] == 'molecular_sequence_public_result_v2':
                context = self.context(row['episode_id'])
                action = json.loads(row['action'])
                intent = self.intent(context, None, action.get('tool'), action.get('arguments'), f"{self.run_id}:{row['episode_id']}:{row['decision_index']}")
                receipt = self._validate_supplied_receipt(receipt, intent)
                require(same(value, self._outcome(receipt)), 'molecular_sequence_completed_action_conflict')
                if self._supplied_produced_component(receipt) == reference:
                    return True
                continue
            if any((source['file'] is not None and source['file']['artifact_ref'] == reference for source in receipt['source_files'].values())):
                return True
        return False

    def completion(self, context):
        if plain(context.assignment).get('selector', {}).get('version') == supplied.SUPPLIED_SELECTOR_VERSION:
            return None
        for receipt in self._completed(context):
            if receipt['delivery_complete']:
                return dict(version='practical_completion_v1', run_id=self.run_id, episode_id=context.episode_id, assignment_sha256=digest(plain(context.assignment)), endpoint='usable_handoff', operation_key=receipt['intent']['operation_key'], receipt_sha256=digest(receipt), validation_keys=['selected_molecular_typed_delivery'])
        return None

    def _supplied_publication(self, selector, record):
        groups = _facts()
        has_components = record['validation_states']['components'] == 'valid'
        for role in selector['return_files']:
            file = record['source_files'][role]['file']
            if file is None:
                continue
            groups[SAVED_SOURCE].append(dict(version='molecular_sequence_retained_file_v2', operation=supplied.SUPPLIED_OPERATION, role=role, artifact_ref=file['artifact_ref'], source_kind='admitted_stored' if selector['action'] == 'read_stored' else 'admitted_input' if role == 'sheet' else 'selected_supplied_calculation', source_sheet_ref=None if record['source_files']['sheet']['file'] is None else record['source_files']['sheet']['file']['artifact_ref'], components_tag_key='version' if has_components else None, components_version=supplied.SUPPLIED_PROFILE['components_version'] if has_components else None, validation_state=record['validation_states'][role], calculation_origin=record['origin_state'], linkage_state=record['linkage_state']))
        groups[FAILURE_SOURCE] = unique([supplied.supplied_failure_view(issue) for issue in record['failures']])
        return groups

    def _validate_supplied_receipt(self, value, intent):
        require(type(value) is dict and set(value) == {'version', 'intent', 'calculation_record', 'calculation_record_file', 'source_files', 'facts', 'delivery_complete'} and (value['version'] == 'molecular_sequence_result_receipt_v2') and same(value['intent'], intent))
        record = supplied.validate_molecular_sequence_calculation_record(value['calculation_record'])
        selector = intent['assignment']['selector']
        require(record['operation'] == selector['operation'] and same(record['selection'], selector['calculation_selection']))
        if selector['action'] == 'calculate':
            require(record['kind'] == 'selected_supplied_calculation' and same(record['policy'], intent['assignment']['constraints']['policy']))
        else:
            require(record['kind'] == 'admitted_stored_read')
        for role, evidence_file in record['input_evidence_files'].items():
            control = _json(read_bytes(retained_native_file(self.store, self.file_metadata(evidence_file))))
            require(control['intent_sha256'] == digest(intent) and control['role'] == role)
            received = control['evidence']['received_input'] if control['interpret_sheet'] else control['evidence']
            selected = selector['input'] if selector['action'] == 'calculate' else selector['stored'][role]
            require(received['selection'] == selected)
            source = record['source_files'][role]
            require(source['file'] is None or (received['input'] is not None and received['input']['byte_verification'] == 'verified' and (source['file'] == received['input']['file'])))
        if record['worker_plan_file'] is not None:
            plan = supplied.validate_supplied_worker_plan(_json(read_bytes(retained_native_file(self.store, self.file_metadata(record['worker_plan_file'])))))
            require(same(plan['selector'], selector) and same(plan['input_file'], record['input_sheet_file']) and same(plan['software'], record['software']) and same(plan['selected_environment'], record['selected_environment']) and same(plan['policy'], record['policy']))
            if record['worker_result_file'] is not None:
                result = supplied.validate_supplied_worker_result(_json(read_bytes(retained_native_file(self.store, self.file_metadata(record['worker_result_file'])))))
                require(result['plan_sha256'] == digest(plan) and same(result['selector'], selector))
        if record['worker_diagnostics_file'] is not None:
            diagnostic = _json(read_bytes(retained_native_file(self.store, self.file_metadata(record['worker_diagnostics_file']))))
            require(diagnostic['calculation_call_count'] == record['calculation_call_count'] and same(diagnostic['selection'], selector['calculation_selection']) and (diagnostic['native_invocation'] == 'not_requested'))
        file = self.file_metadata(value['calculation_record_file'], value=record)
        require(same(_json(read_bytes(retained_native_file(self.store, file))), record))
        require(same(value['source_files'], record['source_files']))
        expected = self._supplied_publication(intent['assignment']['selector'], record)
        schema = plain(self.context(intent['episode_id']).request)['report_contract']['measurements']['schema']
        wanted = select_molecular_sequence_return_facts(expected, schema=schema)
        require(same(value['facts'], {source: rows if source in wanted else [] for source, rows in expected.items()}) and type(value['delivery_complete']) is bool)
        require(value['delivery_complete'] == bool(intent['tool_name'] == 'execution.results.collect' and all((any((row['role'] == role for row in value['facts'][SAVED_SOURCE])) for role in selector['return_files']))))
        return deepcopy(value)

    def calculation_completion(self, context):
        """Private delivered-file endpoint, never an original practical receipt."""
        for receipt in self._completed(context):
            if receipt['version'] == 'molecular_sequence_result_receipt_v2' and receipt['delivery_complete']:
                return {'version': 'molecular_sequence_calculation_delivery_v1', 'operation': supplied.SUPPLIED_OPERATION, 'endpoint': 'requested_scientific_files_delivered'}
        return None

    def _supplied_produced_component(self, receipt):
        """Classify produced bytes only; reading an input creates no ownership."""
        record = receipt['calculation_record']
        if record['kind'] != 'selected_supplied_calculation' or record['worker_result_file'] is None:
            return None
        produced = record['worker_outputs']['components']
        source = record['source_files']['components']
        if produced['state'] != 'retained' or produced['file'] is None:
            return None
        require(produced['file'] == source['file'], 'molecular_sequence_supplied_output_ownership_conflict')
        result = supplied.validate_supplied_worker_result(_json(read_bytes(retained_native_file(self.store, self.file_metadata(record['worker_result_file'])))))
        declaration = next((row['declaration'] for row in result['outputs'] if row['role'] == 'calculated_components'))
        require(declaration['state'] == 'present' and produced['declared'] == declaration and all((produced['file'][key] == declaration[key] for key in ('sha256', 'size_bytes'))), 'molecular_sequence_supplied_output_ownership_conflict')
        return produced['file']['artifact_ref']
