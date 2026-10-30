"""Custody and received values for selected BV-BRC Data acquisitions.

The host verifies persisted actions, bytes, selections and actual delivery.
Parsers and calculators have no access to this journal. This helper performs
no acquisition, model call, resource choice, scientific scoring or observation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from method_loop.identities import EpisodeRef

from .bvbrc_data_schema import json_digest, validate
from .bvbrc_data_views import (
    FACT_SCHEMAS, FACT_SOURCES, IDENTIFIER_NAMESPACES, materialize_bvbrc_received_values,
    project_bvbrc_data_facts, resolve_bvbrc_data_identifier,
    validate_bvbrc_data_return, validate_data_result_selector,
)
from .communication import REFERENCE_FORMATS, plain
from .domain import identity
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .practical_execution_state import _read
from .tool_grading_artifacts import SCHEMA as GRADING_SCHEMA


def is_bvbrc_request(request):
    return isinstance(request, dict) and request.get('version') == 'bvbrc_data_request_v2'


def requested_sources(schema):
    return tuple(dict.fromkeys(node['x-source'] for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in FACT_SOURCES))


def _require(condition, code):
    if not condition:
        raise ValueError('bvbrc_host_' + code)


def _same(left, right):
    return json_digest(plain(left)) == json_digest(plain(right))


def _json_bytes(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, 'duplicate_json_key')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('bvbrc_host_nonfinite_json')))
    json_digest(value)
    return value


def _references(value, schema):
    if value is None:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _references(child, schema.get('properties', {}).get(key, {}))
    elif isinstance(value, list):
        for child in value:
            yield from _references(child, schema.get('items', {}))
    elif isinstance(value, str) and schema.get('format') in REFERENCE_FORMATS:
        yield value, schema.get('x-reference-namespace')


def _pointer(value, pointer):
    _require(isinstance(pointer, str) and (not pointer or pointer.startswith('/'))
        and re.search(r'~(?![01])', pointer) is None, 'metadata_pointer_invalid')
    for part in pointer.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            _require(re.fullmatch(r'0|[1-9][0-9]*', part) is not None, 'metadata_array_index_invalid')
            index = int(part)
            _require(index < len(value), 'metadata_pointer_unavailable')
            value = value[index]
        else:
            _require(isinstance(value, dict) and part in value, 'metadata_pointer_unavailable')
            value = value[part]
    return value


def _materialize(qualified, form, schema):
    # Different received fields may describe different acquisitions. Expanding
    # every acquisition into every field would invent unreceived information.
    form, schema = plain(form), plain(schema)
    context = (qualified[0]['host_qualification'] if qualified else
        {'run_id': None, 'receiver_episode_id': None})
    result = []
    for name, node in schema.get('properties', {}).items():
        source = node.get('x-source')
        if source not in FACT_SOURCES:
            continue
        references = {row['source_ref'] for row in form[name]}
        selected = [value for value in qualified if value['binding']['source_ref'] in references]
        field_schema = {'type': 'object', 'properties': {name: node},
            'required': [name], 'additionalProperties': False}
        value, = materialize_bvbrc_received_values(selected,
            admitted_form={name: form[name]}, original_schema=field_schema)
        # Preserve the original full-schema content identity, including for
        # existing saved admissions and empty requested arrays.
        value['admission_key'] = json_digest({'run_id': context['run_id'],
            'receiver_episode_id': context['receiver_episode_id'], 'original_schema': schema,
            'form_field': name, 'fact_source': source, 'facts': value['facts']})
        result.append(value)
    # Object property order has no semantic meaning; native arrays keep theirs.
    return sorted(result, key=lambda item: item['form_field'])


def _selected_sources(qualified, form, schema, materialized):
    candidates = set()
    for result in qualified:
        candidates.add(result['binding']['source_ref'])
        candidates.update(item['binding']['source_ref'] for item in result['input_results'])
        candidates.update(item['source_ref'] for item in result['grading']['metadata_bindings'])
    references = []
    for reference, namespace in _references(plain(form), plain(schema)):
        if namespace in {'source', 'execution_result'} and reference in candidates:
            references.append(reference)
        elif namespace in IDENTIFIER_NAMESPACES and namespace != 'bvbrc_data_identifier':
            # The exact virtual reference must first resolve against the full
            # qualified projection. Its prefix alone never authorizes access.
            _require(resolve_bvbrc_data_identifier(qualified, reference=reference,
                namespace=namespace), 'returned_reference_conflict')
            references.extend(source for source in sorted(candidates) if reference.startswith(source + '#'))
    references.extend(cell['source_ref'] for value in materialized for cell in value['cells'])
    # Receipt membership is a set; form property order cannot change replay.
    return sorted(set(references))


class BVBRCDataHost(EpisodeReturnRecords):
    # Retain this existing host's exact finite-JSON comparison and failures.
    _equal = staticmethod(_same)

    def __init__(self, execution):
        self.api = execution
        super().__init__(execution.store, execution.run_id, failure_prefix="bvbrc_host_")

    def _table(self, name):
        return self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None



    def _artifact(self, reference):
        _require(self.store.get(reference).get('record_type') == 'artifact', 'artifact_required')
        raw = self.store.get_artifact(reference)
        _require(reference == 'artifact_' + hashlib.sha256(raw).hexdigest(), 'artifact_digest_conflict')
        return raw



    def _own(self, context, reference, *, before=None):
        sql = ('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL '
            'AND EXISTS (SELECT 1 FROM json_each(result,\'$.record_refs\') WHERE value=?)')
        args = [self.run_id, context.episode_id, reference]
        if before is not None:
            sql += ' AND decision_index<?'
            args.append(before)
        for row in self.db.execute(sql, args):
            if (json.loads(row['action']).get('kind') == 'tool'
                    and json.loads(row['result']).get('status') in {'completed', 'partial'}):
                return True
        return False

    def _selected_input_refs(self, assignment):
        if assignment.get('version') != 'execution_results_assignment_v1':
            return []
        selector = assignment.get('selector', {})
        if selector.get('version') != 'bvbrc_data_result_selector_v2':
            return []
        return list(dict.fromkeys([row['source_ref'] for row in selector['inputs']]
            + [row['provenance']['source_ref'] for row in selector['supplied_metadata']]))

    def possession(self, context, reference, *, before=None, visiting=()):
        self.authenticate(context, allow_unsaved=True)
        key = context.episode_id, reference
        _require(key not in visiting, 'cyclic_possession')
        visiting = (*visiting, key)
        if self._own(context, reference, before=before):
            return 'own_completed_action'
        if self._table('runtime_bvbrc_admissions'):
            sql = ('SELECT operation_key,received_sources FROM runtime_bvbrc_admissions WHERE run_id=? '
                'AND receiver_episode_id=? AND EXISTS (SELECT 1 FROM json_each(received_sources) WHERE value=?)')
            for row in self.db.execute(sql, (self.run_id, context.episode_id, reference)):
                index = self._admission_index(context, row['operation_key'])
                if before is None or index < before:
                    child, form, schema = self._attempt(context, index)
                    source_refs = list(dict.fromkeys(item['source_ref']
                        for name, node in schema['properties'].items() if node.get('x-source') in FACT_SOURCES
                        for item in form[name]))
                    qualified = [self.read(ref, context=child) for ref in source_refs]
                    values = _materialize(qualified, form, schema)
                    actually_returned = _selected_sources(qualified, form, schema, values)
                    if reference in actually_returned:
                        return 'admitted_return'
        # Ordinary source/execution-result returns can be named as later inputs.
        sql = ('SELECT decision_index,form,contract FROM runtime_report_attempts WHERE run_id=? '
            'AND parent_episode_id=? AND failure IS NULL AND form IS NOT NULL '
            'AND EXISTS (SELECT 1 FROM json_tree(form) WHERE type=\'text\' AND value=?)')
        for row in self.db.execute(sql, (self.run_id, context.episode_id, reference)):
            if before is not None and row['decision_index'] >= before:
                continue
            child, form, schema = self._attempt(context, row['decision_index'])
            if any(ref == reference and namespace in {'source', 'execution_result'}
                    for ref, namespace in _references(form, schema)):
                self.possession(child, reference, visiting=visiting)
                return 'admitted_return'
        if reference in self._selected_input_refs(plain(context.assignment)) and len(context.path) > 1:
            parent_id = EpisodeRef(self.run_id, context.path[:-1]).episode_id
            parent = self.context(parent_id)
            key = context.path[-1][1]
            _require(key.startswith('child_') and key[6:].isdecimal(), 'assignment_commission_required')
            self.possession(parent, reference, before=int(key[6:]), visiting=visiting)
            return 'parent_assignment'
        raise ValueError('bvbrc_host_reference_not_received')

    def _stored(self, reference, scope):
        body = self.api.read_result(reference, scope)
        _require(body['version'] == 'api_service_acquired_result_v1'
            and body['source_ref'] == reference and is_bvbrc_request(body['service_request'])
            and body['target']['assignment']['service'] == 'bvbrc_data', 'v2_result_required')
        owner = self.context(body['episode_id'])
        _require(owner.role == 'results' and _same(owner.assignment, body['assignment'])
            and _same(owner.scope, body['scope']), 'acquisition_owner_conflict')
        source = self.store.get(reference)
        payload = {k: v for k, v in source.items() if k not in {'id', 'record_type', 'origin'}}
        _require(source.get('origin') == 'external' and source.get('provider') == 'bvbrc_data'
            and reference == identity('source', {'origin': 'external', 'record': payload}), 'source_identity_conflict')
        raw = self._artifact(source['artifact_ref'])
        _require(hashlib.sha256(raw).hexdigest() == body['snapshot_sha256'], 'native_bytes_conflict')
        for directory, outcome in self.api._own_outcomes(owner):
            if outcome.get('status') not in {'completed', 'partial'} or reference not in outcome.get('record_refs', []):
                continue
            result, receipt = outcome['result'], _read(directory/'acquisition.json')
            intent, metadata = _read(directory/'intent.json'), _read(directory/'snapshot.json')
            selected = self.api._selected(owner, intent['name'], intent['arguments'], intent['operation_key'])
            actual = {} if selected['result'] is None else json.loads(selected['result'])
            _require(selected['result'] is not None and all(key in actual and _same(actual[key], value)
                for key, value in outcome.items()), 'completed_acquisition_required')
            grading_ref = result['grading_artifact_ref']
            _require(source.get('auxiliary_artifact_refs') == [grading_ref]
                and result['raw_artifact_ref'] == source['artifact_ref'], 'grading_link_conflict')
            envelope = _json_bytes(self._artifact(grading_ref))
            _require(set(envelope) == {'schema', 'provider', 'native_artifact_ref', 'grading'}
                and envelope['schema'] == GRADING_SCHEMA and envelope['provider'] == 'bvbrc_data'
                and envelope['native_artifact_ref'] == source['artifact_ref'], 'grading_custody_conflict')
            grading = validate('PublishedGrading', envelope['grading'])
            prepared = intent['prepared']['prepared_query']
            _require(_same(grading['prepared'], prepared)
                and _same(grading['selector'], owner.assignment['selector'])
                and _same(prepared['original_request'], body['service_request'])
                and grading['parse_result']['retained_native_sha256'] == body['snapshot_sha256'], 'original_selection_conflict')
            retained = _json_bytes(self._artifact(source['request_ref']))
            _require(_same(retained, {**metadata, 'sha256': body['snapshot_sha256'], 'prepared': prepared}), 'source_request_conflict')
            _require(receipt.get('publication_inputs_sha256') is not None, 'publication_custody_required')
            inputs = validate('PublicationInputs', _read(directory/'publication_inputs.json'))
            _require(json_digest(inputs) == receipt['publication_inputs_sha256']
                and _same(inputs['prepared'], prepared)
                and _same(grading['input_bindings'], [item['binding'] for item in inputs['input_results']])
                and _same(grading['metadata_bindings'], inputs['metadata_bindings']), 'publication_inputs_conflict')
            binding = validate('ResultBinding', {'source_ref': reference, 'native_artifact_ref': source['artifact_ref'],
                'native_sha256': body['snapshot_sha256'], 'grading_artifact_ref': grading_ref,
                'collection': body['service_request']['collection'],
                'acquisition_assignment_sha256': digest(owner.assignment), 'selector_sha256': digest(grading['selector'])})
            return body, owner, binding, grading, inputs
        raise ValueError('bvbrc_host_publication_unavailable')

    def metadata_bindings(self, context, records):
        bindings = []
        for record in records:
            provenance = record['provenance']
            reference, pointer = provenance['source_ref'], provenance['record_path']
            self.possession(context, reference)
            source = self.store.get(reference)
            _require(source.get('record_type') == 'source', 'metadata_source_required')
            raw = self._artifact(source['artifact_ref'])
            artifact = self.store.get(source['artifact_ref'])
            media = artifact.get('media_type', '').split(';', 1)[0]
            _require(media == 'application/json' or media.endswith('+json'), 'metadata_json_required')
            supplied = {key: value for key, value in record.items() if key != 'provenance'}
            _require(_same(_pointer(_json_bytes(raw), pointer), supplied), 'metadata_values_conflict')
            binding = validate('MetadataBinding', {'source_ref': reference, 'native_artifact_ref': source['artifact_ref'],
                'native_sha256': hashlib.sha256(raw).hexdigest(), 'record_path': pointer,
                'metadata_sha256': json_digest(supplied)})
            if binding not in bindings:
                bindings.append(binding)
        return bindings

    def read(self, reference, *, context, admission_operation_key=None, visiting=()):
        self.authenticate(context)
        _require(reference not in visiting, 'cyclic_input_results')
        body, owner, binding, grading, saved_inputs = self._stored(reference, context.scope)
        if admission_operation_key is None:
            basis = self.possession(context, reference)
        else:
            child, form, schema = self._attempt(context, self._admission_index(context, admission_operation_key))
            _require(any(row.get('source_ref') == reference for name, node in schema['properties'].items()
                if node.get('x-source') in FACT_SOURCES for row in form[name]), 'source_not_returned')
            self.possession(child, reference)
            basis = 'current_child_return'
        selector = grading['selector']
        inputs = []
        for selected in selector['inputs']:
            qualified = self.read(selected['source_ref'], context=owner, visiting=(*visiting, reference))
            sheet = qualified['grading']['parse_result']['sheet']
            _require(qualified['binding']['collection'] == selected['collection'] and sheet is not None, 'input_collection_or_sheet_conflict')
            inputs.append({'binding': qualified['binding'], 'sheet': sheet})
        metadata = self.metadata_bindings(owner, selector['supplied_metadata'])
        _require(_same(saved_inputs, {'version': 'bvbrc_data_publication_inputs_v1', 'prepared': grading['prepared'],
            'input_results': inputs, 'supplied_metadata': selector['supplied_metadata'], 'metadata_bindings': metadata}), 'frozen_inputs_conflict')
        result = validate('QualifiedResult', {'version': 'bvbrc_data_qualified_result_v1', 'service': 'bvbrc_data',
            'binding': binding, 'grading': grading, 'input_results': inputs,
            'host_qualification': {'run_id': self.run_id, 'source_episode_id': owner.episode_id,
                'receiver_episode_id': context.episode_id, 'scope_sha256': digest(context.scope),
                'receipt_verified': True, 'native_bytes_verified': True, 'grading_custody_verified': True,
                'original_selection_verified': True, 'input_bindings_verified': True,
                'receiver_possession_verified': True, 'possession_basis': basis}})
        # Check stored sheet and relationship semantics without recalculation.
        project_bvbrc_data_facts([result], selector=selector, requested_sources=())
        return result

    def validate_inputs(self, context, selector, *, request):
        selector = validate_data_result_selector(plain(selector), request=plain(request))
        inputs = []
        for selected in selector['inputs']:
            result = self.read(selected['source_ref'], context=context)
            sheet = result['grading']['parse_result']['sheet']
            _require(result['binding']['collection'] == selected['collection'] and sheet is not None
                and sheet['mode'] == 'page', 'join_input_conflict')
            inputs.append({'binding': result['binding'], 'sheet': sheet})
        return inputs, self.metadata_bindings(context, selector['supplied_metadata'])

    def publication_inputs(self, context, prepared):
        selector = plain(context.assignment)['selector']
        inputs, metadata = self.validate_inputs(context, selector, request=prepared['original_request'])
        return validate('PublicationInputs', {'version': 'bvbrc_data_publication_inputs_v1',
            'prepared': prepared, 'input_results': inputs, 'supplied_metadata': selector['supplied_metadata'],
            'metadata_bindings': metadata})

    def own_results(self, context):
        results, seen = [], set()
        for _, outcome in self.api._own_outcomes(context):
            if outcome.get('status') in {'completed', 'partial'}:
                for reference in outcome.get('record_refs', []):
                    source = self.store.get(reference)
                    if (reference not in seen and source.get('provider') == 'bvbrc_data'
                            and source.get('auxiliary_artifact_refs')):
                        results.append(self.read(reference, context=context))
                        seen.add(reference)
        return results

    def facts(self, context, schema):
        sources = requested_sources(schema)
        result = {source: [] for source in sources}
        for qualified in self.own_results(context) if sources else ():
            facts = project_bvbrc_data_facts([qualified], selector=qualified['grading']['selector'], requested_sources=sources)
            for source in sources:
                result[source].extend(facts[source])
        return result

    def received_facts(self, context, schema):
        """Forward only admitted rows, never other projections of their source."""
        sources = requested_sources(schema)
        result = {source: [] for source in sources}
        seen = {source: set() for source in sources}
        for value in self.received_context(context) if sources else ():
            source = value['fact_source']
            if source not in result:
                continue
            for row in value['facts']:
                key = json_digest(row)
                if key not in seen[source]:
                    result[source].append(deepcopy(row))
                    seen[source].add(key)
        return result

    def validate_received_report(self, context, form, schema):
        if not requested_sources(schema):
            return
        received = self.received_facts(context, schema)
        frozen = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        if frozen is not None:
            saved = json.loads(frozen['facts'])
            # Recorded closure remains authoritative; it must also agree with
            # actual received information, not an arbitrary stored source.
            for source in requested_sources(schema):
                _require(source in saved and _same(saved[source], received[source]),
                    'frozen_received_facts_conflict')
            received = saved
        validate_bvbrc_data_return(plain(form), original_schema=plain(schema), recorded_facts=received)

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, 'execution_result'):
            return None
        if namespace == 'execution_result':
            try:
                source = self.store.get(reference)
            except (ValueError, KeyError):
                return None
            if source.get('provider') != 'bvbrc_data':
                return None
        for value in self.received_context(context):
            if any(ref == reference and ns == namespace for ref, ns in
                    _references(value['facts'], FACT_SCHEMAS[value['fact_source']])):
                return True
        return False

    def own_values(self, context):
        """The results episode's selected values before any parent admission."""
        schema = plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {})
        sources = requested_sources(schema)
        if not sources:
            return []
        qualified = self.own_results(context)
        if not qualified:
            return []
        # Select only recorded BV-BRC fields; unrelated interpretation fields
        # have no role in this internal deterministic value insertion.
        fields = {name: node for name, node in schema['properties'].items() if node.get('x-source') in sources}
        selected_schema = {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
        facts = self.facts(context, selected_schema)
        form = {name: facts[node['x-source']] for name, node in fields.items()}
        return _materialize(qualified, form, selected_schema)

    def resolve(self, context, reference, namespace):
        try:
            if namespace not in IDENTIFIER_NAMESPACES:
                return False
            qualified = self.own_results(context)
            return resolve_bvbrc_data_identifier(qualified, reference=reference, namespace=namespace)
        except (ValueError, KeyError, OSError, TypeError):
            return False

    def _install(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS runtime_bvbrc_admissions ('
            'run_id TEXT NOT NULL, receiver_episode_id TEXT NOT NULL, operation_key TEXT NOT NULL, '
            'form TEXT NOT NULL, original_schema TEXT NOT NULL, bindings TEXT NOT NULL, '
            'received_sources TEXT NOT NULL, materializations TEXT NOT NULL, '
            'PRIMARY KEY(run_id,receiver_episode_id,operation_key))')

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        child, recorded_form, recorded_schema = self._attempt(context, self._admission_index(context, operation_key))
        _require(_same(form, recorded_form) and _same(schema, recorded_schema), 'admitted_form_conflict')
        # Full original child facts control inclusion/order; no arbitrary subset.
        if child.role == 'results':
            recorded = self.facts(child, schema)
            validate_bvbrc_data_return(plain(form), original_schema=plain(schema), recorded_facts=recorded)
        elif child.role in {'annotation', 'scientific_process'}:
            self.validate_received_report(child, form, schema)
        sources = list(dict.fromkeys(row['source_ref'] for name, node in plain(schema)['properties'].items()
            if node.get('x-source') in FACT_SOURCES for row in form[name]))
        qualified = [self.read(reference, context=context, admission_operation_key=operation_key) for reference in sources]
        materialized = _materialize(qualified, form, schema)
        received = _selected_sources(qualified, form, schema, materialized)
        bindings = [q['binding'] for q in qualified]
        record = {'form': plain(form), 'original_schema': plain(schema), 'bindings': bindings,
            'received_sources': received, 'materializations': materialized}
        with self.store.transaction():
            self._install()
            key = self.run_id, context.episode_id, operation_key
            old = self.db.execute('SELECT * FROM runtime_bvbrc_admissions WHERE run_id=? '
                'AND receiver_episode_id=? AND operation_key=?', key).fetchone()
            if old is not None:
                _require(all(_same(json.loads(old[k]), v) for k, v in record.items()), 'admission_replay_conflict')
            else:
                self.db.execute('INSERT INTO runtime_bvbrc_admissions VALUES(?,?,?,?,?,?,?,?)',
                    (*key, *(canonical(value) for value in record.values())))
        return received

    def received_context(self, context):
        result, seen = [], set()
        if not self._table('runtime_bvbrc_admissions'):
            return result
        self.authenticate(context, allow_unsaved=True)
        rows = self.db.execute('SELECT * FROM runtime_bvbrc_admissions WHERE run_id=? AND receiver_episode_id=? '
            'ORDER BY rowid', (self.run_id, context.episode_id)).fetchall()
        for row in rows:
            _, form, schema = self._attempt(context, self._admission_index(context, row['operation_key']))
            _require(_same(form, json.loads(row['form'])) and _same(schema, json.loads(row['original_schema'])), 'admission_record_conflict')
            bindings = json.loads(row['bindings'])
            qualified = [self.read(binding['source_ref'], context=context, admission_operation_key=row['operation_key']) for binding in bindings]
            _require(_same(bindings, [q['binding'] for q in qualified]), 'admission_binding_conflict')
            values = _materialize(qualified, form, schema)
            _require(_same(values, json.loads(row['materializations'])), 'admission_materialization_conflict')
            for value in values:
                if value['admission_key'] not in seen:
                    result.append(value)
                    seen.add(value['admission_key'])
        return result


__all__ = ['BVBRCDataHost', 'is_bvbrc_request', 'requested_sources']
