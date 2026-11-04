"""Actual MinHash acquisition custody and requested immediate-child returns.

Only selected own acquisitions and successful original typed returns supply
values. A stored source, an inherited reference or an unrelated receiver does
not supply numerical facts. No acquisition, recalculation or observation occurs
here; saved grades and runtime return records remain authoritative.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from method_loop.identities import EpisodeRef

from .communication import REFERENCE_FORMATS, plain
from .bvbrc_minhash_contracts import (
    validate_minhash_result_selector, validate_minhash_pair_metadata,
    validate_minhash_publication_inputs,
)
from .domain import ContractError, identity
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .practical_execution_state import _read
from .tool_grading_artifacts import SCHEMA as ARTIFACT_SCHEMA


SERVICE = 'bvbrc_minhash'
FACT_SOURCES = ('bvbrc_minhash_matches', 'bvbrc_minhash_counts',
    'bvbrc_minhash_calculations', 'bvbrc_minhash_calculation_diagnostics')


def _same(left, right):
    return canonical(left) == canonical(right)


def requested_sources(schema):
    return tuple(dict.fromkeys(node['x-source']
        for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in FACT_SOURCES))


def _references(value, schema):
    if isinstance(value, dict):
        for name, item in value.items():
            yield from _references(item, schema.get('properties', {}).get(name, {}))
    elif isinstance(value, list):
        for item in value:
            yield from _references(item, schema.get('items', {}))
    elif isinstance(value, str) and schema.get('format') in REFERENCE_FORMATS:
        yield value, schema.get('x-reference-namespace')


class BVBRCMinhashHost(EpisodeReturnRecords):
    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix='bvbrc_minhash_host_')
        self.api = execution

    def _artifact(self, reference):
        raw = self.store.get_artifact(reference)
        self._require(reference == 'artifact_' + hashlib.sha256(raw).hexdigest(),
            'artifact_identity_conflict')
        return raw

    @staticmethod
    def _input_failure(code, **detail):
        raise ContractError(code, detail=detail)

    def _source(self, reference, *, code, **detail):
        try:
            source = self.store.get(reference)
        except (ValueError, KeyError, OSError) as error:
            raise ContractError(code, detail={"source_ref": reference, **detail}) from error
        payload = {key: value for key, value in source.items()
            if key not in {'id', 'record_type', 'origin'}}
        if (source.get('record_type') != 'source' or reference != identity('source', {
                'origin': source.get('origin'), 'record': payload})):
            self._input_failure(code, source_ref=reference, **detail)
        return source

    @staticmethod
    def _selected_input_refs(assignment):
        if assignment.get('version') != 'execution_results_assignment_v1':
            return []
        selector = assignment.get('selector', {})
        if selector.get('version') != 'bvbrc_minhash_result_selector_v2':
            return []
        selector = validate_minhash_result_selector(selector)
        return list(dict.fromkeys([
            *([selector['saved_result_ref']] if selector['saved_result_ref'] is not None else []),
            *(field['source_ref'] for record in selector['pair_metadata']
                for field in record['provenance']['fields'])]))

    def possession(self, context, reference, *, before=None, visiting=(),
                   code='minhash_metadata_source_not_received'):
        """Prove actual receipt; scope or an existing Store record is insufficient."""
        self.authenticate(context, allow_unsaved=True)
        marker = (context.episode_id, reference)
        if marker in visiting:
            self._input_failure(code, source_ref=reference)
        visiting = (*visiting, marker)
        sql = ('SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND result IS NOT NULL '
            'AND EXISTS (SELECT 1 FROM json_each(result,\'$.record_refs\') WHERE value=?)')
        args = [self.run_id, context.episode_id, reference]
        if before is not None:
            sql += ' AND decision_index<?'
            args.append(before)
        for row in self.db.execute(sql, args):
            action, outcome = json.loads(row['action']), json.loads(row['result'])
            if action.get('kind') == 'tool' and outcome.get('status') in {'completed', 'partial'}:
                self.api._selected(context, action['tool'], action['arguments'],
                    f'{self.run_id}:{context.episode_id}:{row["decision_index"]}')
                return 'own_completed_action'
        for attempt in self._attempts(context):
            if before is not None and attempt['decision_index'] >= before:
                continue
            child, form, schema = self._attempt(context, attempt['decision_index'])
            if any(value == reference and namespace in {None, 'source', 'execution_result'}
                    for value, namespace in _references(form, schema)):
                self.possession(child, reference, visiting=visiting, code=code)
                return 'admitted_return'
        if reference in self._selected_input_refs(plain(context.assignment)) and len(context.path) > 1:
            parent = self.context(EpisodeRef(self.run_id, context.path[:-1]).episode_id)
            label = context.path[-1][1]
            if re.fullmatch(r'child_(0|[1-9][0-9]*)', label) is None:
                self._input_failure(code, source_ref=reference)
            index = int(label[6:])
            row = self.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? AND decision_index=?', (self.run_id, parent.episode_id, index)).fetchone()
            action = {} if row is None else json.loads(row['action'])
            if (action.get('kind') not in {'episode_child', 'job_child'}
                    or action.get('role') != context.role
                    or not _same(action.get('assignment'), plain(context.assignment))):
                self._input_failure(code, source_ref=reference)
            self.possession(parent, reference, before=index, visiting=visiting, code=code)
            return 'parent_assignment'
        self._input_failure(code, source_ref=reference)

    def _metadata_artifact(self, source_ref, artifact_ref, **detail):
        source = self._source(source_ref, code='minhash_metadata_source_missing', **detail)
        if artifact_ref not in [source.get('artifact_ref'), *source.get('auxiliary_artifact_refs', [])]:
            self._input_failure('minhash_metadata_artifact_conflict', source_ref=source_ref,
                artifact_ref=artifact_ref, **detail)
        try:
            artifact = self.store.get(artifact_ref)
            raw = self._artifact(artifact_ref)
            if artifact.get('record_type') != 'artifact':
                raise ValueError('artifact_required')
        except (ValueError, KeyError, OSError, TypeError) as error:
            raise ContractError('minhash_metadata_artifact_conflict', detail={
                'source_ref': source_ref, 'artifact_ref': artifact_ref, **detail}) from error
        return raw

    @staticmethod
    def _json_value(raw):
        def pairs(items):
            value = {}
            for key, item in items:
                if key in value:
                    raise ValueError('duplicate_json_key')
                value[key] = item
            return value
        def invalid(value):
            raise ValueError('nonfinite_json')
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        canonical(value)
        return value

    @staticmethod
    def _pointer(value, pointer):
        for token in pointer.split('/')[1:]:
            token = token.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if re.fullmatch(r'0|[1-9][0-9]*', token) is None:
                    raise KeyError(token)
                value = value[int(token)]
            elif isinstance(value, dict):
                value = value[token]
            else:
                raise KeyError(token)
        return value

    def metadata_bindings(self, context, records):
        """Bind each explicit nonnull scalar to its original input occurrence."""
        bindings = []
        for index, record in enumerate(records):
            for evidence in record['provenance']['fields']:
                field, reference = evidence['field'], evidence['source_ref']
                detail = {'pair_metadata_index': index, 'row_index': record['row_index'],
                    'genome_id': record['genome_id'], 'field': field,
                    'record_path': evidence['record_path']}
                self._source(reference, code='minhash_metadata_source_missing', **detail)
                try:
                    self.possession(context, reference)
                except ValueError as error:
                    raise ContractError('minhash_metadata_source_not_received',
                        detail={'source_ref': reference, **detail}) from error
                raw = self._metadata_artifact(reference, evidence['artifact_ref'], **detail)
                try:
                    value = self._json_value(raw)
                    source = self.store.get(reference)
                    if (evidence['artifact_ref'] != source['artifact_ref']
                            and isinstance(value, dict) and value.get('schema') == ARTIFACT_SCHEMA
                            and (value.get('native_artifact_ref') != source['artifact_ref']
                                 or value.get('provider') != source.get('provider'))):
                        raise ValueError('auxiliary_publication_conflict')
                except (ValueError, TypeError, UnicodeError) as error:
                    raise ContractError('minhash_metadata_artifact_conflict', detail={
                        'source_ref': reference, 'artifact_ref': evidence['artifact_ref'], **detail}) from error
                try:
                    scalar = self._pointer(value, evidence['record_path'])
                except (KeyError, IndexError, TypeError, ValueError) as error:
                    raise ContractError('minhash_metadata_pointer_unavailable', detail={
                        'source_ref': reference, 'artifact_ref': evidence['artifact_ref'], **detail}) from error
                if type(scalar) is not int or scalar != record[field]:
                    self._input_failure('minhash_metadata_value_conflict', source_ref=reference,
                        artifact_ref=evidence['artifact_ref'], **detail)
                bindings.append({'pair_metadata_index': index, 'source_ref': reference,
                    'artifact_ref': evidence['artifact_ref'], 'artifact_sha256': hashlib.sha256(raw).hexdigest(),
                    'field': field, 'record_path': evidence['record_path'], 'value': scalar})
        return bindings

    def read_received_result(self, reference, *, context):
        """Open saved numerical inputs only for an explicit selection with custody."""
        self.possession(context, reference, code='minhash_saved_result_not_received')
        source = self._source(reference, code='minhash_saved_result_not_received')
        if source.get('provider') != SERVICE:
            self._input_failure('minhash_saved_result_not_received', source_ref=reference)
        body = self.api.read_result(reference, context.scope)
        owner = self.context(body['episode_id'])
        return self.read_own(reference, context=owner)

    def validate_inputs(self, context, selector, *, request, handoff_ref):
        selected = validate_minhash_result_selector(plain(selector))
        if not selected:
            return None
        try:
            records = validate_minhash_pair_metadata(selected['pair_metadata'], request=plain(request))
        except ValueError as error:
            if str(error) == 'minhash_metadata_query_conflict':
                index, record = next((index, record) for index, record in enumerate(selected['pair_metadata'])
                    if record['provenance']['query_mode'] != request['mode']
                    or record['provenance']['query_operand'] != request['query'])
                self._input_failure(str(error), pair_metadata_index=index, row_index=record['row_index'],
                    genome_id=record['genome_id'], field='query')
            raise
        self.authenticate(context, allow_unsaved=True)
        target = self.api.read_target(handoff_ref, context.scope)
        if (target['assignment'].get('service') != SERVICE
                or not _same(target['assignment'].get('request'), plain(request))):
            self._input_failure('minhash_publication_inputs_conflict', handoff_ref=handoff_ref)
        bindings = self.metadata_bindings(context, records)
        saved = None
        if selected['mode'] == 'saved_sheet':
            reference = selected['saved_result_ref']
            qualified = self.read_received_result(reference, context=context)
            grading = qualified['grading']
            if not _same(grading['request'], plain(request)):
                self._input_failure('minhash_saved_result_request_conflict', source_ref=reference,
                    handoff_ref=handoff_ref)
            source = self.store.get(reference)
            raw = self._artifact(source['artifact_ref'])
            snapshot = self.api._load_snapshot(self.api._read_handoff(handoff_ref, context.scope)['snapshot'])
            if raw != snapshot.content:
                self._input_failure('minhash_saved_result_response_conflict', source_ref=reference,
                    handoff_ref=handoff_ref)
            grading_ref, = source['auxiliary_artifact_refs']
            saved = {'source_ref': reference, 'native_artifact_ref': source['artifact_ref'],
                'native_sha256': hashlib.sha256(raw).hexdigest(), 'grading_artifact_ref': grading_ref,
                'grading_sha256': hashlib.sha256(self._artifact(grading_ref)).hexdigest(),
                'sheet': deepcopy(grading['sheet']), 'original_components': deepcopy(grading['components'])}
        return validate_minhash_publication_inputs({
            'version': 'bvbrc_minhash_publication_inputs_v1', 'selector': selected,
            'pair_metadata': records, 'metadata_bindings': bindings, 'saved_result': saved},
            request=plain(request), selector=selected)

    def publication_inputs(self, context, *, request, selector, handoff_ref):
        return self.validate_inputs(context, selector, request=request, handoff_ref=handoff_ref)

    def _frozen_inputs(self, context, directory, grading):
        """Authenticate retained operands without extracting pointers or calculating."""
        inputs = validate_minhash_publication_inputs(_read(directory/'publication_inputs.json'),
            request=grading['request'], selector=grading['selector'])
        receipt = _read(directory/'acquisition.json')
        if (receipt.get('publication_inputs_sha256') != digest(inputs)
                or not _same(inputs, grading.get('publication_inputs'))):
            self._input_failure('minhash_publication_inputs_conflict')
        for binding in inputs['metadata_bindings']:
            self.possession(context, binding['source_ref'])
            raw = self._metadata_artifact(binding['source_ref'], binding['artifact_ref'],
                pair_metadata_index=binding['pair_metadata_index'], field=binding['field'])
            if hashlib.sha256(raw).hexdigest() != binding['artifact_sha256']:
                self._input_failure('minhash_metadata_artifact_conflict', source_ref=binding['source_ref'],
                    artifact_ref=binding['artifact_ref'])
        saved = inputs['saved_result']
        if saved is not None:
            previous = self.read_received_result(saved['source_ref'], context=context)
            source = self.store.get(saved['source_ref'])
            if (source['artifact_ref'] != saved['native_artifact_ref']
                    or source['auxiliary_artifact_refs'] != [saved['grading_artifact_ref']]
                    or hashlib.sha256(self._artifact(saved['native_artifact_ref'])).hexdigest() != saved['native_sha256']
                    or hashlib.sha256(self._artifact(saved['grading_artifact_ref'])).hexdigest() != saved['grading_sha256']
                    or not _same(previous['grading']['sheet'], saved['sheet'])
                    or not _same(previous['grading']['components'], saved['original_components'])
                    or not _same(previous['grading']['request'], grading['request'])):
                self._input_failure('minhash_publication_inputs_conflict', source_ref=saved['source_ref'])
        return inputs

    def read_own(self, reference, *, context):
        """Read only this results episode's actual acquisition and saved grading."""
        from .bvbrc_minhash_views import project_minhash_facts
        self.authenticate(context)
        self._require(context.role == 'results', 'results_owner_required')
        body = self.api.read_result(reference, context.scope, episode_id=context.episode_id)
        self._require(body.get('version') == 'api_service_acquired_result_v1'
            and body['episode_id'] == context.episode_id
            and body['source_ref'] == reference
            and body['target']['assignment']['service'] == SERVICE
            and _same(body['assignment'], context.assignment), 'acquisition_owner_conflict')
        source = self.store.get(reference)
        payload = {key: value for key, value in source.items()
            if key not in {'id', 'record_type', 'origin'}}
        self._require(source.get('record_type') == 'source'
            and source.get('provider') == SERVICE and source.get('origin') == 'external'
            and reference == identity('source', {'origin': 'external', 'record': payload}),
            'source_identity_conflict')
        raw = self._artifact(source['artifact_ref'])
        self._require(hashlib.sha256(raw).hexdigest() == body['snapshot_sha256'],
            'native_bytes_conflict')
        for directory, outcome in self.api._own_outcomes(context):
            if outcome.get('status') not in {'completed', 'partial'} or reference not in outcome.get('record_refs', []):
                continue
            intent = _read(directory/'intent.json')
            selected = self.api._selected(context, intent['name'], intent['arguments'], intent['operation_key'])
            actual = None if selected['result'] is None else json.loads(selected['result'])
            self._require(actual is not None and all(key in actual and _same(actual[key], value)
                for key, value in outcome.items()), 'completed_acquisition_required')
            result = outcome['result']
            grading_ref = result['grading_artifact_ref']
            self._require(source.get('auxiliary_artifact_refs') == [grading_ref]
                and result['source_ref'] == reference
                and result['raw_artifact_ref'] == source['artifact_ref'], 'grading_link_conflict')
            envelope = self.api._artifact_json(grading_ref)
            self._require(set(envelope) == {'schema', 'provider', 'native_artifact_ref', 'grading'}
                and envelope['schema'] == ARTIFACT_SCHEMA and envelope['provider'] == SERVICE
                and envelope['native_artifact_ref'] == source['artifact_ref'], 'grading_artifact_conflict')
            grading = envelope['grading']
            prepared = intent['prepared']
            self._require(_same(grading['request'], body['service_request'])
                and _same(grading['request'], prepared['request'])
                and _same(grading['rpc_request'], prepared['rpc_request'])
                and _same(grading['selector'], context.assignment['selector'])
                and grading['parse_status'] == result['parse_status'], 'original_selection_conflict')
            metadata = _read(directory/'snapshot.json')
            retained = self.api._artifact_json(source['request_ref'])
            rpc_ref = retained.get('rpc_request_artifact_ref')
            self._require(_same({key: value for key, value in retained.items()
                if key not in {'sha256', 'rpc_request_artifact_ref'}}, metadata)
                and retained.get('sha256') == body['snapshot_sha256'], 'source_request_conflict')
            rpc_bytes = self._artifact(rpc_ref)
            self._require(_same(json.loads(rpc_bytes), prepared['rpc_request'])
                and hashlib.sha256(rpc_bytes).hexdigest() == metadata['transport']['request']['body_sha256'],
                'native_request_bytes_conflict')
            inputs = None
            if grading.get('schema') == 'bvbrc_minhash_grading_v2':
                self._require(_same(prepared.get('selector'), grading['selector']), 'original_selection_conflict')
                inputs = self._frozen_inputs(context, directory, grading)
            provenance = grading['sheet']['provenance']
            expected_provenance = ({'service': metadata['service'], 'url': metadata['url'],
                'retrieved_at': metadata['retrieved_at'], 'response_sha256': body['snapshot_sha256']}
                if inputs is None or inputs['saved_result'] is None else
                inputs['saved_result']['sheet']['provenance'])
            self._require(_same(provenance, expected_provenance)
                and provenance['response_sha256'] == body['snapshot_sha256'], 'sheet_provenance_conflict')
            qualified = {'source_ref': reference, 'grading': grading}
            # This checks saved relationships. It never calls current graders.
            project_minhash_facts([qualified], requested_sources=())
            return qualified
        raise ValueError(self.failure_prefix + 'publication_unavailable')

    def _own_results(self, context):
        if context.role != 'results':
            return []
        result, seen = [], set()
        for _, outcome in self.api._own_outcomes(context):
            if outcome.get('status') not in {'completed', 'partial'}:
                continue
            for reference in outcome.get('record_refs', []):
                if reference not in seen and self.store.get(reference).get('provider') == SERVICE:
                    result.append(self.read_own(reference, context=context))
                    seen.add(reference)
        return result

    def facts(self, context, schema):
        from .bvbrc_minhash_views import project_minhash_facts
        sources = requested_sources(schema)
        return project_minhash_facts(self._own_results(context) if sources else [],
            requested_sources=sources)

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        # A successful attempt is saved only after the parent's typed contract
        # admits the form. In both blocking and durable paths this precedes
        # receipt/credit projection; it is not a newly completed action.
        return self.db.execute('SELECT decision_index,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
            'ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()

    def _validate_values(self, context, form, schema):
        if context.role == 'results':
            expected = self.facts(context, schema)
        elif context.role in {'annotation', 'scientific_process'}:
            expected = self.received_facts(context, schema)
        else:
            raise ValueError(self.failure_prefix + 'unsupported_return_owner')
        for name, node in plain(schema).get('properties', {}).items():
            source = node.get('x-source')
            if source in FACT_SOURCES:
                self._require(name in form and _same(form[name], expected[source]),
                    'returned_facts_conflict')

    def received_context(self, context):
        grouped, seen = {}, {}
        for attempt in self._attempts(context):
            schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
            if not requested_sources(schema):
                continue
            child, form, original = self._attempt(context, attempt['decision_index'])
            self._validate_values(child, form, original)
            for name, node in original['properties'].items():
                source = node.get('x-source')
                if source not in FACT_SOURCES:
                    continue
                rows = grouped.setdefault(source, [])
                identities = seen.setdefault(source, set())
                for row in form[name]:
                    key = canonical(row)
                    if key not in identities:
                        rows.append(deepcopy(row))
                        identities.add(key)
        return [{'fact_source': source, 'facts': rows} for source, rows in grouped.items()]

    def received_facts(self, context, schema):
        sources = requested_sources(schema)
        result = {source: [] for source in sources}
        for value in self.received_context(context) if sources else ():
            if value['fact_source'] in result:
                result[value['fact_source']] = value['facts']
        return result

    def validate_received_report(self, context, form, schema):
        if not requested_sources(schema):
            return
        self._validate_values(context, plain(form), plain(schema))
        frozen = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        if frozen is not None:
            actual, saved = self.received_facts(context, schema), json.loads(frozen['facts'])
            self._require(all(source in saved and _same(saved[source], actual[source])
                for source in requested_sources(schema)), 'frozen_received_facts_conflict')

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        child, original, original_schema = self._attempt(context,
            self._admission_index(context, operation_key))
        self._require(_same(form, original) and _same(schema, original_schema), 'admitted_form_conflict')
        self._validate_values(child, original, original_schema)
        return list(dict.fromkeys(row['source_ref'] for name, node in original_schema['properties'].items()
            if node.get('x-source') in FACT_SOURCES for row in original[name]))

    def resolve_own(self, context, reference, namespace):
        if namespace != 'bvbrc_minhash_genome':
            return None
        from .bvbrc_minhash_views import project_minhash_facts
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        sources = tuple(source for source in requested_sources(schema)
            if source in {'bvbrc_minhash_matches', 'bvbrc_minhash_calculations'})
        facts = project_minhash_facts(self._own_results(context) if sources else [], requested_sources=sources)
        return any(row['genome_id'] == reference for rows in facts.values() for row in rows)

    def resolve_received(self, context, reference, namespace):
        if namespace == 'bvbrc_minhash_genome':
            return any(row['genome_id'] == reference for value in self.received_context(context)
                if value['fact_source'] in {'bvbrc_minhash_matches', 'bvbrc_minhash_calculations'}
                for row in value['facts'])
        if namespace not in {None, 'source', 'execution_result'}:
            return None
        try:
            if self.store.get(reference).get('provider') != SERVICE:
                return None
        except (ValueError, KeyError):
            return None
        # An opaque source can be passed on when that source was requested.
        # This does not add matches/counts to received_context or expose grading.
        for attempt in self._attempts(context):
            child, form, schema = self._attempt(context, attempt['decision_index'])
            if not any(value == reference and kind in {None, 'source', 'execution_result'}
                    for value, kind in _references(form, schema)):
                continue
            if child.role == 'results':
                self.read_own(reference, context=child)
                return True
            if child.role in {'annotation', 'scientific_process'}:
                if self.resolve_received(child, reference, 'execution_result'):
                    return True
        return False


__all__ = ['BVBRCMinhashHost', 'requested_sources']
