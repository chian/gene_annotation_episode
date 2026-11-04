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

from .communication import REFERENCE_FORMATS, plain
from .domain import identity
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical
from .practical_execution_state import _read
from .tool_grading_artifacts import SCHEMA as ARTIFACT_SCHEMA


SERVICE = 'bvbrc_minhash'
FACT_SOURCES = ('bvbrc_minhash_matches', 'bvbrc_minhash_counts')


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
            provenance = grading['sheet']['provenance']
            self._require(_same(provenance, {'service': metadata['service'], 'url': metadata['url'],
                'retrieved_at': metadata['retrieved_at'], 'response_sha256': body['snapshot_sha256']}),
                'sheet_provenance_conflict')
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
        facts = project_minhash_facts(self._own_results(context),
            requested_sources=('bvbrc_minhash_matches',))
        return any(row['genome_id'] == reference for row in facts['bvbrc_minhash_matches'])

    def resolve_received(self, context, reference, namespace):
        if namespace == 'bvbrc_minhash_genome':
            return any(row['genome_id'] == reference for value in self.received_context(context)
                if value['fact_source'] == 'bvbrc_minhash_matches' for row in value['facts'])
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
