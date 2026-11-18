"""Selected utility-result acquisition in the existing results episode.

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
from gene_annotation_episode.episodic_workflow.root.a110.form_reference_validation import _binding_key, form_reference_validation, form_validation_value
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_acquisition import capture_local_utility_bundle, is_native_blast_utility_target, _source_payload
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_contracts import BUNDLE_VERSION
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_result_publication import validate_utility_publication, validate_prepared_utility_result
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_capture_failure import FILENAME as CAPTURE_FAILURE_PUBLICATION, validate_capture_failure
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_blast_utility_contracts import validate_blast_utility_record
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_blast_utility_result_views import FACT_SOURCES, IDENTIFIER_NAMESPACES, PROJECTION_FIELDS, PROJECTION_V2_FIELDS, projection_identifiers, validate_blast_utility_result_selector
VERSION = 'native_blast_utility_acquired_result_v1'
V2_VERSION = 'native_blast_utility_acquired_result_v2'
_PROJECTION_FIELDS = tuple(PROJECTION_FIELDS)
_SELECTOR_VERSIONS = {'native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2'}

def _body_version(selector):
    return V2_VERSION if selector['version'] == 'native_blast_utility_result_selector_v2' else VERSION

def _body_projection_fields(body):
    return PROJECTION_V2_FIELDS if body.get('version') == V2_VERSION else _PROJECTION_FIELDS

def _array_fields(projection_fields):
    return tuple((key for key in projection_fields if key not in {'status', 'record_refs'}))

def operation_catalog():
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Retain original utility outputs and return the assigned preparation facts and artifacts.', 'input_schema': obj({})}]

def _require(condition, code):
    if not condition:
        raise ContractError('native_blast_utility_result_' + code)

def _selector(assignment, target):
    job = target['assignment']['requested_job']['native_blast_utility']
    return validate_blast_utility_result_selector(assignment['selector'], operation=job['operation'])

def _virtual_references(body, namespace=None):
    yield from projection_identifiers({key: body[key] for key in _body_projection_fields(body)}, namespace)

def _has_parsed_result(prepared):
    return prepared is not None and prepared['result_artifact_ref'] is not None

def _current_bodies(bodies):
    """Project later parsed views without deleting unavailable action history."""
    parsed_bundles, current = (set(), [])
    for body in reversed(bodies):
        capture = body.get('capture')
        bundle = None if capture is None else capture['bundle_artifact_ref']
        if _has_parsed_result(body.get('prepared')):
            parsed_bundles.add(bundle)
        elif bundle is not None and bundle in parsed_bundles:
            continue
        current.append(body)
    return reversed(current)

def _complete(body):
    return bool(body['capture'] is not None and body['capture']['bundle_validated'] and (body['prepared'] is not None) and (not body['operational_failures']) and (body['status'] is not None) and (body['status']['state'] == 'complete'))

class NativeBLASTUtilityResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.directory = owner.directory / 'native-blast-utility-result-index'
        self.target_directory = owner.directory / 'native-blast-utility-target-index'

    def applies(self, context):
        return context.role == 'results' and is_native_blast_utility_target(self.owner._target(context))

    def _saved_directory(self, episode_id, operation_key):
        return self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id]) / 'native-blast-utility-actions' / digest(operation_key)

    def _receipt(self, row, scope):
        _require(set(row) == {'run_id', 'episode_id', 'operation_key'} and row['run_id'] == self.owner.run_id, 'index_owner_conflict')
        return self._validate_body(_read(self._saved_directory(row['episode_id'], row['operation_key']) / 'receipt.json'), scope)

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
                    parent = self.owner.native_blast_utility_returns.context(current)
                    child, form, schema = self.owner.native_blast_utility_returns._attempt(parent, row['source_index'])
                    if self.owner.native_blast_utility_returns._handles(child, schema):
                        values = self.owner.native_blast_utility_returns._validate_historical(child, form, schema)
                        if reference in self.owner.native_blast_utility_returns._references(values):
                            return True
            current, through = (manifest['parent_episode_id'], manifest['through_receipt_index'])
        return False

    def retained_target(self, context, *, assignment=None, scope=None):
        """Authenticate an original saved target without native observation."""
        selected = plain(context.assignment if assignment is None else assignment)
        selected_scope = plain(context.scope if scope is None else scope)
        if selected.get('selector', {}).get('version') not in _SELECTOR_VERSIONS:
            return None
        self.store.validate_scope(selected_scope, parent_scope=plain(context.scope))
        if context.role != 'results' or selected != plain(context.assignment):
            return None
        directory = self.owner.directory / 'execution-results' / digest([context.run_id, context.episode_id]) / 'native-blast-utility-actions'
        if not directory.exists():
            return None
        self.owner.native_blast_utility_returns.authenticate(context, allow_unsaved=True)
        for path in sorted(directory.glob('*/receipt.json')):
            body = self._validate_body(_read(path), context.scope)
            _require(body['assignment'] == selected and body['episode_id'] == context.episode_id, 'owner_context_conflict')
            return deepcopy(body['target'])
        return None

    def _validate_body(self, value, scope):
        with form_reference_validation():
            return self._validate_body_in_frame(value, scope)

    def _validate_body_in_frame(self, value, scope):
        body = plain(value)
        _require(type(body) is dict and body.get('version') in {VERSION, V2_VERSION}, 'receipt_invalid')
        projection_fields = _body_projection_fields(body)
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'capture', 'prepared', 'source_ref', 'reused_from', 'operational_failures', 'complete', *projection_fields}
        _require(set(body) == fields and body['run_id'] == self.owner.run_id, 'receipt_invalid')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], body['scope'])
        _require(target == body['target'] and is_native_blast_utility_target(target), 'original_target_conflict')
        selector = _selector(body['assignment'], target)
        _require(body['version'] == _body_version(selector), 'receipt_version_selection_conflict')
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
                _require(capture_local_utility_bundle(self.store, target=target, directory=directory / 'capture') == body['capture'], 'capture_receipt_conflict')
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
            expected = _source_payload(body['capture'])
            _require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and ({k: v for k, v in source.items() if k not in {'id', 'record_type', 'origin'}} == expected), 'source_content_conflict')
            _require(body['source_ref'] in body['record_refs'], 'source_reference_missing')
        else:
            _require(body['prepared'] is None and (not body['record_refs']), 'source_required')
        if body['prepared'] is not None:
            validate_prepared_utility_result(self.store, body['prepared'])
            _require(body['prepared']['source_ref'] == body['source_ref'], 'prepared_source_conflict')
        publication_path = directory / 'publication.json'
        if publication_path.exists():
            _require(body['prepared'] is not None, 'prepared_result_required')
            publication = validate_utility_publication(self.store, source_ref=body['source_ref'], prepared=body['prepared'], selector=selector, publication=_read(publication_path))
            _require(all((body[key] == publication[key] for key in projection_fields)), 'publication_receipt_conflict')
            _require(not (directory / CAPTURE_FAILURE_PUBLICATION).exists(), 'competing_publication_receipts')
        elif (directory / CAPTURE_FAILURE_PUBLICATION).exists():
            _require(body['version'] == V2_VERSION and body['prepared'] is None and (body['source_ref'] is not None) and (body['tool_name'] == 'execution.results.collect'), 'capture_failure_publication_conflict')
            publication = validate_capture_failure(self.store, capture=body['capture'], selector=selector, operational_failures=body['operational_failures'], publication=_read(directory / CAPTURE_FAILURE_PUBLICATION))
            _require(all((body[key] == publication['projection'][key] for key in projection_fields)), 'capture_failure_projection_conflict')
        else:
            _require(body['status'] is None and (not any((body[key] for key in _array_fields(projection_fields) if key != 'failures'))) and (body['record_refs'] == ([] if body['source_ref'] is None else [body['source_ref']])), 'publication_required')
            expected_failures = [] if body['source_ref'] is None else [{'source_ref': body['source_ref'], **failure} for failure in body['operational_failures']]
            _require(body['failures'] == expected_failures, 'operational_failure_projection_conflict')
        diagnostics = directory / 'operational-diagnostics.json'
        rows = _read(diagnostics) if diagnostics.exists() else []
        _require(type(rows) is list and [row['failure'] for row in rows] == body['operational_failures'], 'operational_failure_receipt_conflict')
        for row in rows:
            _require(type(row) is dict and set(row) == {'failure', 'exception_type', 'detail'} and (type(row['exception_type']) is str) and (type(row['detail']) is str), 'operational_diagnostics_invalid')
            validate_blast_utility_record('UtilityFailure', row['failure'])
        _require(type(body['complete']) is bool and body['complete'] == _complete(body), 'completion_conflict')
        return body

    def _own_bodies(self, context):

        def load():
            self.owner.native_blast_utility_returns.authenticate(context, allow_unsaved=True)
            directory = self.owner.directory / 'execution-results' / digest([context.run_id, context.episode_id]) / 'native-blast-utility-actions'
            bodies = [_read(path) for path in directory.glob('*/receipt.json')] if directory.exists() else []
            result = []
            for body in sorted(bodies, key=lambda item: int(item['operation_key'].rsplit(':', 1)[1])):
                _require(body['run_id'] == context.run_id and body['episode_id'] == context.episode_id and (body['assignment'] == plain(context.assignment)) and (body['scope'] == plain(context.scope)), 'owner_context_conflict')
                result.append(self._validate_body(body, context.scope))
            return {'bodies': result}
        yield from form_validation_value(('native_blast_utility_own_bodies', id(self), _binding_key(context)), load)['bodies']

    def facts(self, context):
        bodies = list(self._own_bodies(context))
        references = list(dict.fromkeys((ref for body in bodies for ref in body['record_refs'])))
        result = {'execution_handoff_refs': [], 'execution_blast_hsps': [], 'execution_result_refs': references, 'execution_result_origin': None, 'execution_completed': any((body['complete'] for body in bodies)), **{source: [] for source in FACT_SOURCES}}
        requested = {node.get('x-source') for node in plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {}).get('properties', {}).values()}
        current = list(_current_bodies(bodies))
        for source in FACT_SOURCES:
            if source not in requested:
                continue
            field, seen = (source.removeprefix('execution.blast_utility_'), set())
            for body in current:
                values = ([body[field]] if body[field] is not None else []) if field == 'status' else body.get(field, [])
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
        if context.role in {'annotation', 'biochemical_feasibility_evidence'}:
            received = self.owner.native_blast_utility_returns.resolve_received_reference_metadata(context, reference, namespace)
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
