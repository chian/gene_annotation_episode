"""Selected masking-result acquisition in the existing results episode.

All numerical values come from the shared retained result publisher. This host
authenticates selected actions and original custody, preserves failures, and
returns frozen requested values. It chooses no native work or continuation.
"""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest, obj
from gene_annotation_episode.episodic_workflow.root.a110.form_reference_validation import _binding_key, form_validation_value
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_acquisition import capture_local_bundle, is_native_blast_masking_target, original_source_payload
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_contracts import BUNDLE_VERSION
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_result_publication import validate_masking_publication, validate_prepared_masking_result
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_sequence_masking_contracts import validate_sequence_masking_record
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_sequence_masking_result_views import FACT_SOURCES, IDENTIFIER_NAMESPACES, validate_masking_result_selector
VERSION = 'native_blast_masking_acquired_result_v1'
_PROJECTION_FIELDS = ('status', 'artifacts', 'quantities', 'checks', 'statistics', 'failures', 'saved_data', 'record_refs')
_ARRAY_FIELDS = ('artifacts', 'quantities', 'checks', 'statistics', 'failures', 'saved_data')

def operation_catalog():
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Retain original masking outputs and return the assigned preparation facts and artifacts.', 'input_schema': obj({})}]

def _require(condition, code):
    if not condition:
        raise ContractError('native_blast_masking_result_' + code)

def _selector(assignment, target):
    job = target['assignment']['requested_job']['native_blast_masking']
    return validate_masking_result_selector(assignment['selector'], operation=job['operation'])

def _virtual_references(body, namespace=None):
    if namespace in (None, 'native_blast_masking_record'):
        for field in ('quantities', 'checks', 'failures'):
            yield from (row['record_key'] for row in body[field] if row['record_key'] is not None)
    if namespace in (None, 'native_blast_masking_occurrence'):
        yield from (row['occurrence_id'] for row in body['artifacts'])
    if namespace in (None, 'native_blast_masking_statistics'):
        yield from (row['statistics_ref'] for row in body['statistics'])

def _complete(body):
    return bool(body['capture'] is not None and body['capture']['bundle_validated'] and (body['prepared'] is not None) and (not body['operational_failures']) and (body['status'] is not None) and (body['status']['state'] == 'complete'))

class NativeBLASTMaskingResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.directory = owner.directory / 'native-blast-masking-result-index'
        self.target_directory = owner.directory / 'native-blast-masking-target-index'

    def applies(self, context):
        return context.role == 'results' and is_native_blast_masking_target(self.owner._target(context))

    def _saved_directory(self, episode_id, operation_key):
        return self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id]) / 'native-blast-masking-actions' / digest(operation_key)

    def _receipt(self, row, scope):
        _require(set(row) == {'run_id', 'episode_id', 'operation_key'} and row['run_id'] == self.owner.run_id, 'index_owner_conflict')
        return self._validate_body(_read(self._saved_directory(row['episode_id'], row['operation_key']) / 'receipt.json'), scope)

    def _known(self, context):
        self.owner.native_blast_masking_returns.authenticate(context, allow_unsaved=True)
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = (self.store, self.store.db, self.owner.run_id)
        try:
            receipts.manifest(context.episode_id)
        except ValueError:
            return set()
        return set(receipts.known(context.episode_id))

    def _explicit_grant(self, context, reference):
        """Use original receipt prefixes and explicit selected return references."""
        current, through, seen = (context.episode_id, None, set())
        while current is not None:
            _require(current not in seen, 'receipt_inheritance_cycle')
            seen.add(current)
            try:
                manifest = EpisodeReceipts.read_manifest(self.store.db, self.owner.run_id, current)
            except ValueError:
                return False
            rows = self.store.db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=? AND (? IS NULL OR receipt_index<=?)', (self.owner.run_id, current, reference, through, through)).fetchall()
            for row in rows:
                if row['receipt_kind'] == 'initial':
                    return True
                if row['receipt_kind'] == 'own_action':
                    saved = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.owner.run_id, current, row['source_index'])).fetchone()
                    if saved is not None and saved['result'] is not None and (reference in json.loads(saved['result']).get('record_refs', [])):
                        return True
                if row['receipt_kind'] in {'child_form', 'report_redelivery'}:
                    parent = self.owner.native_blast_masking_returns.context(current)
                    child, form, schema = self.owner.native_blast_masking_returns._attempt(parent, row['source_index'])
                    if self.owner.native_blast_masking_returns._handles(child, schema):
                        values = self.owner.native_blast_masking_returns._validate_historical(child, form, schema)
                        if reference in self.owner.native_blast_masking_returns._references(values):
                            return True
            current, through = (manifest['parent_episode_id'], manifest['through_receipt_index'])
        return False

    def retained_target(self, context, *, assignment=None, scope=None):
        """Authenticate a saved target without polling or opening native paths."""
        selected = plain(context.assignment if assignment is None else assignment)
        selected_scope = plain(context.scope if scope is None else scope)
        if selected.get('selector', {}).get('version') != 'native_blast_masking_result_selector_v1':
            return None
        self.store.validate_scope(selected_scope, parent_scope=plain(context.scope))
        if selected['selector']['mode'] == 'saved_recalculation':
            sheet = selected['selector']['saved_sheet_ref']
            known = self._known(context)
            _require(sheet in known and selected['handoff_ref'] in known and self._explicit_grant(context, sheet), 'saved_sheet_not_received')
            body = self.read_result(sheet, selected_scope)
            _require(body['prepared'] is not None and body['prepared']['sheet_artifact_ref'] == sheet and (body['assignment']['handoff_ref'] == selected['handoff_ref']), 'saved_sheet_target_conflict')
            _selector(selected, body['target'])
            return deepcopy(body['target'])
        if context.role != 'results' or selected != plain(context.assignment):
            return None
        directory = self.owner.directory / 'execution-results' / digest([context.run_id, context.episode_id]) / 'native-blast-masking-actions'
        if not directory.exists():
            return None
        self.owner.native_blast_masking_returns.authenticate(context, allow_unsaved=True)
        for path in sorted(directory.glob('*/receipt.json')):
            body = self._validate_body(_read(path), context.scope)
            _require(body['assignment'] == plain(context.assignment) and body['episode_id'] == context.episode_id, 'owner_context_conflict')
            return deepcopy(body['target'])
        return None

    def _validate_body(self, value, scope):
        body = plain(value)
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'capture', 'prepared', 'source_ref', 'reused_from', 'operational_failures', 'complete', *_PROJECTION_FIELDS}
        _require(type(body) is dict and set(body) == fields and (body['version'] == VERSION) and (body['run_id'] == self.owner.run_id), 'receipt_invalid')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], body['scope'])
        _require(target == body['target'] and is_native_blast_masking_target(target), 'original_target_conflict')
        selector = _selector(body['assignment'], target)
        _require(body['tool_name'] in {row['name'] for row in operation_catalog()} and body['arguments'] == {}, 'original_operation_conflict')
        selected = self.owner._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.owner.run_id, body['episode_id'])).fetchone()
        _require(episode is not None, 'original_episode_missing')
        message = json.loads(episode['request'])['message']
        _require(message.get('episode_assignment') == body['assignment'] and message['scope'] == body['scope'] and (json.loads(episode['path'])[-1][0] == 'results'), 'original_assignment_conflict')
        directory = self._saved_directory(body['episode_id'], body['operation_key'])
        _require(_read(directory / 'receipt.json') == body, 'original_receipt_conflict')
        _require(_read(directory / 'intent.json') == {key: body[key] for key in ('target', 'assignment', 'operation_key', 'tool_name', 'arguments', 'scope')}, 'original_intent_conflict')
        _require(_read(directory / 'observation.json') == body['observation'], 'observation_conflict')
        if selected['result'] is not None:
            outcome = json.loads(selected['result'])
            _require(outcome.get('status') == 'completed' and outcome.get('result') == body and (outcome.get('record_refs') == body['record_refs']), 'saved_outcome_conflict')
        if body['tool_name'] == 'execution.results.status':
            _require(body['capture'] is None and body['reused_from'] is None, 'status_acquisition_conflict')
        else:
            _require(body['capture'] is not None, 'collect_capture_required')
        if body['capture'] is not None:
            if body['reused_from'] is None:
                _require((directory / 'capture' / 'capture.json').is_file(), 'capture_receipt_missing')
                _require(capture_local_bundle(self.store, target=target, directory=directory / 'capture') == body['capture'], 'capture_receipt_conflict')
            else:
                previous = body['reused_from']
                _require(previous != {'run_id': body['run_id'], 'episode_id': body['episode_id'], 'operation_key': body['operation_key']}, 'cyclic_result_reuse')
                original_path = self._saved_directory(previous['episode_id'], previous['operation_key']) / 'receipt.json'
                _require(_read(original_path).get('reused_from') is None, 'original_acquisition_required')
                original = self._receipt(previous, scope)
                _require(original['target'] == target and original['capture'] == body['capture'] and (original['observation'] == body['observation']), 'reused_result_conflict')
        bundle = None
        if body['source_ref'] is not None:
            _require(body['capture'] is not None and body['capture']['bundle_validated'], 'source_capture_required')
            bundle = json.loads(self.store.get_artifact(body['capture']['bundle_artifact_ref']))
            source = self.store.get(body['source_ref'])
            expected = original_source_payload(bundle=bundle, capture=body['capture'], prepared=body['prepared'])
            _require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and ({k: v for k, v in source.items() if k not in {'id', 'record_type', 'origin'}} == expected), 'source_content_conflict')
            _require(body['source_ref'] in body['record_refs'], 'source_reference_missing')
        else:
            _require(body['prepared'] is None and (not body['record_refs']), 'source_required')
        if body['prepared'] is not None:
            validate_prepared_masking_result(self.store, body['prepared'], bundle=bundle)
        publication_path = directory / 'publication.json'
        if publication_path.exists():
            _require(body['prepared'] is not None, 'prepared_result_required')
            publication = validate_masking_publication(self.store, source_ref=body['source_ref'], prepared=body['prepared'], selector=selector, publication=_read(publication_path))
            _require(all((body[key] == publication[key] for key in _PROJECTION_FIELDS)), 'publication_receipt_conflict')
        else:
            _require(body['status'] is None and (not any((body[key] for key in _ARRAY_FIELDS if key != 'failures'))) and (body['record_refs'] == ([] if body['source_ref'] is None else [body['source_ref']])), 'publication_required')
            expected_failures = [] if body['source_ref'] is None else [{'source_ref': body['source_ref'], **failure} for failure in body['operational_failures']]
            _require(body['failures'] == expected_failures, 'operational_failure_projection_conflict')
        diagnostics = directory / 'operational-diagnostics.json'
        rows = _read(diagnostics) if diagnostics.exists() else []
        _require(type(rows) is list and [row['failure'] for row in rows] == body['operational_failures'], 'operational_failure_receipt_conflict')
        for row in rows:
            _require(type(row) is dict and set(row) == {'failure', 'exception_type', 'detail'} and (type(row['exception_type']) is str) and (type(row['detail']) is str), 'operational_diagnostics_invalid')
            validate_sequence_masking_record('Failure', row['failure'])
        _require(type(body['complete']) is bool and body['complete'] == _complete(body), 'completion_conflict')
        return body

    def read_result(self, reference, scope, assignment=None):
        directory = self.directory / digest(reference)
        for path in sorted(directory.glob('*.json')) if directory.exists() else ():
            body = self._receipt(_read(path), scope)
            if assignment is not None and body['assignment'] != plain(assignment):
                continue
            _require(reference in body['record_refs'] or reference in set(_virtual_references(body)), 'index_reference_conflict')
            return body
        raise ContractError('not_a_native_blast_masking_acquired_result')

    def _own_bodies(self, context):

        def load():
            self.owner.native_blast_masking_returns.authenticate(context, allow_unsaved=True)
            directory = self.owner.directory / 'execution-results' / digest([context.run_id, context.episode_id]) / 'native-blast-masking-actions'
            bodies = [_read(path) for path in directory.glob('*/receipt.json')] if directory.exists() else []
            result = []
            for body in sorted(bodies, key=lambda item: int(item['operation_key'].rsplit(':', 1)[1])):
                _require(body['run_id'] == context.run_id and body['episode_id'] == context.episode_id and (body['assignment'] == plain(context.assignment)) and (body['scope'] == plain(context.scope)), 'owner_context_conflict')
                result.append(self._validate_body(body, context.scope))
            return {'bodies': result}
        yield from form_validation_value(('native_blast_masking_own_bodies', id(self), _binding_key(context)), load)['bodies']

    def facts(self, context):
        bodies = list(self._own_bodies(context))
        references = list(dict.fromkeys((ref for body in bodies for ref in body['record_refs'])))
        result = {'execution_handoff_refs': [], 'execution_blast_hsps': [], 'execution_result_refs': references, 'execution_result_origin': None, 'execution_completed': any((body['complete'] for body in bodies)), **{source: [] for source in FACT_SOURCES}}
        requested = {node.get('x-source') for node in plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {}).get('properties', {}).values()}
        for source in FACT_SOURCES:
            if source not in requested:
                continue
            field, seen = (source.removeprefix('execution.masking_'), set())
            for body in bodies:
                values = ([body[field]] if body[field] is not None else []) if field == 'status' else body[field]
                for value in values:
                    key = canonical(value)
                    if key not in seen:
                        result[source].append(deepcopy(value))
                        seen.add(key)
        return result

    def retained_reference_access(self, context, reference, namespace):
        if namespace not in {None, 'source', 'artifact', 'execution_result'}:
            return None
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        if record['record_type'] == 'source':
            owns = record.get('provider') == 'episode.execution_result' and record.get('version') == BUNDLE_VERSION
        elif record['record_type'] == 'artifact':
            owns = self.store.db.execute("SELECT 1 FROM records r WHERE r.record_type='source' AND json_extract(r.data,'$.provider')='episode.execution_result' AND json_extract(r.data,'$.version')=? AND (json_extract(r.data,'$.artifact_ref')=? OR EXISTS (SELECT 1 FROM json_each(r.data,'$.auxiliary_artifact_refs') a WHERE a.value=?)) LIMIT 1", (BUNDLE_VERSION, reference, reference)).fetchone() is not None
            if not owns:
                owns = (self.directory / digest(reference)).exists()
        else:
            return None
        if not owns:
            return None
        if context.role in {'annotation', 'scientific_process'}:
            received = self.owner.native_blast_masking_returns.resolve_received_reference_metadata(context, reference, namespace)
            if received is not None:
                return received
        if context.role == 'results' and any((reference in body['record_refs'] for body in self._own_bodies(context))):
            return namespace in {None, 'execution_result', record['record_type']}
        return None if self._explicit_grant(context, reference) else False

    def resolve(self, context, reference, namespace):
        if not self.applies(context):
            return False
        bodies = list(self._own_bodies(context))
        if namespace in IDENTIFIER_NAMESPACES:
            return any((reference in set(_virtual_references(body, namespace)) for body in bodies))
        if namespace not in {None, 'source', 'artifact', 'execution_result'}:
            return False
        return any((reference in body['record_refs'] for body in bodies)) and (namespace not in {'source', 'artifact'} or self.store.get(reference)['record_type'] == namespace)
