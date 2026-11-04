"""Native selected printed-signal custody and saved-only typed projection.

This adapter performs no episode decisions, model calls or observation accounting.
It authenticates host records; source custody does not certify interpreted meaning.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .communication import plain
from .domain import ContractError, canonical, identity, validate_schema
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = 'literature.experimental.relative_signal_source'
VERSION = 'literature_relative_signal_source_record_v3'
COMPONENTS = ('reported_ratio', 'difference_from_reference', 'log_reported_ratio',
    'calibrated_amount_ratio', 'amount_adjusted_effect', 'source_profile_log_ratio', 'source_signed_index')
MEANINGS = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
    'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment',
    'condition', 'endpoint', 'normalization')
FLAGS = ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict')
PAYLOAD_FIELDS = {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs',
    'input_source_refs', 'input_view_refs', 'selection', 'extraction', 'sheet',
    'calculation_artifact_ref', 'experimental_bindings', 'measurement_bindings'}


def _sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode('utf8')).hexdigest()


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _unique(values):
    return list(dict.fromkeys(values))


def _calculator_implementation_descriptor():
    #009 binds the actual numerical semantics and their input contract, not
    # only the thin wrapper. Saved reads never rehash future current modules.
    return {'version': 'relative_signal_calculator_implementation_v1', 'modules': {
        name: _sha(Path(__file__).with_name(name).read_bytes()) for name in (
            'literature_ratio_source_inputs.py', 'literature_ratio_source_calculations.py',
            'literature_ratio_source_validation.py')}}


def ratio_source_population_schema():
    from .literature_ratio_source_inputs import relative_signal_source_arguments_schema
    return relative_signal_source_arguments_schema()


def ratio_source_cells_schema():
    return deepcopy(_RETURN_SCHEMA)


class LiteratureRatioSourceRepository(LiteratureRateRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = 'literature_ratio_source_operations'
    received_table = 'literature_ratio_source_received'
    binding_fields = tuple(name + '_ref' for name in MEANINGS)

    def __init__(self, store, run_id, *, evidence_origin='reported_source'):
        if type(run_id) is not str or not run_id:
            raise ValueError('explicit_literature_run_required')
        if evidence_origin not in ('reported_source', 'synthetic_fixture'):
            raise ContractError('relative_signal_evidence_origin_invalid')
        self.store, self.run_id, self.evidence_origin = store, run_id, evidence_origin
        # Existing saved state, including mode=ro connections, needs no DDL.
        for table, columns in ((self.operations_table,
                'run_id TEXT NOT NULL,episode_id TEXT NOT NULL,operation_key TEXT NOT NULL,'
                'signature TEXT NOT NULL,outcome TEXT NOT NULL'),
                (self.received_table,
                'run_id TEXT NOT NULL,episode_id TEXT NOT NULL,operation_key TEXT NOT NULL,cells TEXT NOT NULL')):
            if not self._has_table(table):
                if store.db.execute('PRAGMA query_only').fetchone()[0]:
                    raise ContractError('relative_signal_saved_state_unavailable')
                # Opening a fresh writable repository is the explicit install path.
                try:
                    store.db.execute(f'CREATE TABLE {table}({columns},PRIMARY KEY(run_id,episode_id,operation_key))')
                except Exception as error:
                    if 'readonly' in str(error).lower():
                        raise ContractError('relative_signal_saved_state_unavailable') from error
                    raise

    def _has_table(self, name):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

    def _record(self, reference, kind=None):
        row = self.store.get(reference)
        if kind and row['record_type'] != kind:
            raise ContractError('relative_signal_record_type_mismatch')
        body = {key: value for key, value in row.items() if key not in ('id', 'record_type', 'origin')}
        if identity(row['record_type'], {'origin': row['origin'], 'record': body}) != reference:
            raise ContractError('relative_signal_record_identity_mismatch')
        return row

    def _artifact_metadata(self, reference):
        row = self.store.get(reference)
        if (set(row) != {'id', 'record_type', 'sha256', 'media_type', 'size'}
                or row['record_type'] != 'artifact' or row['id'] != reference
                or type(row['sha256']) is not str or len(row['sha256']) != 64
                or any(ch not in '0123456789abcdef' for ch in row['sha256'])
                or reference != 'artifact_' + row['sha256']
                or type(row['size']) is not int or row['size'] < 0
                or type(row['media_type']) is not str):
            raise ContractError('relative_signal_artifact_identity_mismatch')
        return row

    def _bytes(self, reference):
        self._artifact_metadata(reference)
        data = self.store.get_artifact(reference)
        if type(data) is not bytes or 'artifact_' + _sha(data) != reference:
            raise ContractError('relative_signal_artifact_identity_mismatch')
        return data

    def _json(self, reference):
        data = self._bytes(reference)
        def pairs(values):
            result = {}
            for key, value in values:
                if key in result:
                    raise ContractError('relative_signal_duplicate_json_key')
                result[key] = value
            return result
        try:
            return json.loads(data, object_pairs_hook=pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
        except (ValueError, UnicodeError) as error:
            raise ContractError('relative_signal_saved_json_invalid') from error

    def _source(self, context, reference, *, direct=True):
        if direct and reference not in context.received_record_refs:
            raise ContractError('literature_source_not_received')
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError('literature_source_outside_scope')
        row = self._record(reference, 'source')
        self._artifact_metadata(row['artifact_ref'])
        page = context.assignment if context.role == 'literature_page' else context.assignment.get('page')
        if page and direct:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._source(context, current, direct=False)
                if current == page['source_ref']:
                    break
                pending.extend(ancestor.get('parent_source_refs', ()))
            else:
                raise ContractError('literature_reading_outside_assigned_source')
        return row

    def _view_records(self, view_ref):
        view = self._record(view_ref, 'image_view')
        display = self._record(view['source_ref'], 'source')
        original = self._record(view['input_source_ref'], 'source')
        self._artifact_metadata(original['artifact_ref'])
        self._artifact_metadata(display['artifact_ref'])
        if (view['origin'] != 'tool' or display['origin'] != 'tool'
                or display['provider'] != 'image.view'
                or view['representation'] != 'selected_native_image_frame_v1'
                or original['artifact_ref'] != view['original_artifact_ref']
                or display['artifact_ref'] != view['image_artifact_ref']
                or display.get('text_ref') is not None
                or display.get('parent_source_refs') != [original['id']]
                or display.get('version') != view['software_version']):
            raise ContractError('relative_signal_native_view_mismatch')
        return view, display

    def _dependencies(self, context, selection):
        # Authorize the complete declared metadata closure before any byte access.
        nodes = list(_walk(selection))
        # Custody rosters describe dependency sets, not scientific array order.
        # Canonical JSON sorts object keys, so traversal insertion order cannot
        # define durable source/view order (075; pure074 uses the same rule).
        direct = sorted({node['source_ref'] for node in nodes if 'source_ref' in node})
        views = sorted({node['view_ref'] for node in nodes if 'view_ref' in node})
        for view_ref in views:
            if view_ref not in context.received_record_refs:
                raise ContractError('relative_signal_view_not_received')
            if not self.store.reference_subset([view_ref], plain(context.scope)):
                raise ContractError('literature_source_outside_scope')
            view, _ = self._view_records(view_ref)
            direct.extend(ref for ref in (view['input_source_ref'], view['source_ref']) if ref not in direct)
        direct.sort()
        for reference in direct:
            self._source(context, reference)
        closure = list(direct)
        for reference in closure:
            row = self._source(context, reference, direct=False)
            for parent in row.get('parent_source_refs', ()):
                self._source(context, parent, direct=False)
                if parent not in closure:
                    closure.append(parent)
        return direct, closure, views

    def _own_view_receipt(self, context, view_ref, *, saved_receipt=None):
        view, display = self._view_records(view_ref)
        body = {key: value for key, value in view.items()
                if key not in ('id', 'record_type', 'origin', 'source_ref')}
        if display.get('request_ref') is None or self._json(display['request_ref']) != body:
            raise ContractError('relative_signal_native_view_request_mismatch')
        if not self._has_table('runtime_actions') or not self._has_table('tool_operations'):
            raise ContractError('relative_signal_own_view_action_required')
        rows = self.store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND json_extract(action,'$.kind')='tool' AND json_extract(action,'$.tool')='image.view' "
            "AND json_extract(result,'$.status')='completed' ORDER BY decision_index",
            (self.run_id, context.episode_id))
        for row in rows:
            action, result = json.loads(row['action']), json.loads(row['result'])
            if result.get('result', {}).get('view_ref') != view_ref:
                continue
            index = row['decision_index']
            if type(index) is not int or index < 0:
                raise ContractError('relative_signal_own_view_action_mismatch')
            key = f'{self.run_id}:{context.episode_id}:{index}'
            native = self.store.db.execute('SELECT * FROM tool_operations WHERE operation_key=?', (key,)).fetchone()
            args = action.get('arguments')
            if (set(action) != {'kind', 'tool', 'arguments'} or not isinstance(args, dict)
                    or set(args) - {'source_ref', 'frame', 'colour_conversion'}
                    or args.get('source_ref') != view['input_source_ref']
                    or args.get('frame', 0) != view['frame']
                    or args.get('colour_conversion', 'preserve') != view['colour_conversion']
                    or native is None or native['name'] != 'image.view'
                    or native['arguments'] != canonical(args) or native['scope'] != canonical(plain(context.scope))
                    or canonical(result) != native['result']
                    or result.get('operation_ref') != native['id']
                    or native['id'] != identity('operation', {'key': key, 'name': 'image.view', 'arguments': args})
                    or result.get('result') != {'view_ref': view_ref, 'view': view}
                    or result.get('visual_inputs') != [view]
                    or result.get('feedback') is not None
                    or result.get('record_refs') != [view['source_ref'], view_ref]):
                raise ContractError('relative_signal_own_view_action_mismatch')
            receipt = {'run_id': self.run_id, 'episode_id': context.episode_id, 'decision_index': index,
                'operation_ref': native['id'], 'result_sha256': _sha(result), 'view_ref': view_ref}
            if saved_receipt is None or receipt == saved_receipt:
                return receipt
        raise ContractError('relative_signal_own_view_action_required')

    def _binding_specs(self, extraction, source_ref):
        """Source-qualified interpreted identities; equality of labels proves nothing."""
        def specification(meaning, role):
            if meaning['status'] != 'known' or not any(w['authentication'] != 'unavailable' for w in meaning['witnesses']):
                return None
            qualification = {'owner_source_ref': source_ref, 'role': role, 'meaning': meaning}
            if role == 'condition':
                return ('context', {'context_type': 'assay_condition', 'name': meaning['value'],
                    'source_ref': source_ref,
                    'attributes': [], 'related_refs': [identity('reference', {'origin': 'tool',
                        'record': {'reference_type': 'literature_result', 'source_ref': source_ref,
                        'accession': identity('ratio_source_meaning', qualification), 'label': meaning['value'],
                        'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}})]},
                    {'reference_type': 'literature_result', 'source_ref': source_ref,
                        'accession': identity('ratio_source_meaning', qualification), 'label': meaning['value'],
                        'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []})
            return ('reference', {'reference_type': 'literature_result', 'source_ref': source_ref,
                'accession': identity('ratio_source_meaning', qualification), 'label': meaning['value'],
                'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []})
        entities = {name + '_ref': specification(extraction['comparison'][name], name) for name in MEANINGS}
        measurements = []
        for row in extraction['representations']:
            measurements.append({'representation_id': row['representation_id'],
                'input_measurement_ref': specification(row['physical_measurement'], 'physical_measurement'),
                'reference_measurement_ref': specification(row['reference_measurement'], 'reference_measurement')})
        return entities, measurements

    def _bindings(self, extraction, source_ref, publish=None):
        def bind(spec):
            if spec is None:
                return None
            kind, value = spec[:2]
            if len(spec) == 3:
                bind(('reference', spec[2]))
            reference = identity(kind, {'origin': 'tool', 'record': value})
            if publish:
                return publish(kind, value)
            actual = self._record(reference, kind)
            if actual['origin'] != 'tool' or {k: v for k, v in actual.items()
                    if k not in ('id', 'record_type', 'origin')} != value:
                raise ContractError('relative_signal_saved_binding_mismatch')
            return reference
        entities, measurements = self._binding_specs(extraction, source_ref)
        return ({key: bind(value) for key, value in entities.items()},
            [{key: value if key == 'representation_id' else bind(value) for key, value in row.items()}
             for row in measurements])

    def _entity_refs(self, bindings):
        refs = [ref for ref in bindings.values() if ref]
        if bindings['condition_ref']:
            refs.extend(self._record(bindings['condition_ref'], 'context')['related_refs'])
        return _unique(refs)

    def populate(self, context, selection, operation_key):
        from .literature_ratio_source_inputs import (validate_relative_signal_source_selection,
            read_relative_signal_source_inputs)
        from . import literature_ratio_source_calculations as calculations
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if type(operation_key) is not str or not operation_key:
            raise ContractError('operation_key_required')
        args = validate_relative_signal_source_selection(plain(selection))
        direct, closure, views = self._dependencies(context, args)
        # Exact original fixture origin is part of immutable selected work.
        signature = canonical({'arguments': args, 'scope': plain(context.scope), 'evidence_origin': self.evidence_origin,
            'role': context.role, 'assignment': plain(context.assignment)})
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            self.read(outcome['result']['sheet_ref'])
            return outcome
        receipts = {view_ref: self._own_view_receipt(context, view_ref) for view_ref in views}
        def read_source(reference, representation):
            source = self._source(context, reference)
            artifact = source['artifact_ref'] if representation == 'original' else source.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self._bytes(artifact)}
        def read_view(view_ref):
            if view_ref not in receipts:
                raise ContractError('relative_signal_view_not_selected')
            view, _ = self._view_records(view_ref)
            return {'metadata': view, 'original_bytes': self._bytes(view['original_artifact_ref']),
                'display_bytes': self._bytes(view['image_artifact_ref']),
                'own_action_receipt': receipts[view_ref]}
        extraction = read_relative_signal_source_inputs(args, read_source=read_source,
            read_view=read_view, evidence_origin=self.evidence_origin)
        sheet = calculations.populate_relative_signal_v2(extraction)
        root = self._source(context, args['source_ref'])
        with self.store.transaction():
            created = []
            def publish(kind, value):
                reference = identity(kind, {'origin': 'tool', 'record': value})
                exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (reference,)).fetchone()
                row = self.store.put(kind, value, origin='tool', scope=plain(context.scope))
                if exists is None:
                    created.append(row['id'])
                return row['id']
            bindings, measurements = self._bindings(extraction, root['id'], publish)
            calculation = {'version': 'relative_signal_calculation_v2', 'input_extraction_sha256': _sha(extraction),
                'calculator_implementation_sha256': _sha(_calculator_implementation_descriptor()), 'sheet': sheet}
            calculation_ref = self.store.artifact(canonical(calculation), 'application/json')
            payload = {'version': VERSION, 'input_source_ref': root['id'], 'input_artifact_ref': root['artifact_ref'],
                'direct_input_source_refs': direct, 'input_source_refs': closure, 'input_view_refs': views,
                'selection': args, 'extraction': extraction, 'sheet': sheet,
                'calculation_artifact_ref': calculation_ref, 'experimental_bindings': bindings,
                'measurement_bindings': measurements}
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request = self.store.artifact(canonical({'run_id': self.run_id, 'episode_id': context.episode_id,
                'operation_key': operation_key, 'arguments': args}), 'application/json')
            sheet_ref = publish('source', {'provider': PROVIDER, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request, 'version': VERSION,
                'retrieved_at': None, 'parent_source_refs': closure})
            references = _unique([sheet_ref, *self._entity_refs(bindings),
                *(row[key] for row in measurements for key in ('input_measurement_ref', 'reference_measurement_ref') if row[key])])
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': references,
                'changed_record_refs': created, 'result': {'sheet_ref': sheet_ref, 'cells': sheet['cells'],
                **{key: sheet[key] for key in FLAGS}}, 'feedback': None}
            from .literature_ratio_source_validation import validate_relative_signal_saved
            validate_relative_signal_saved(args, extraction, sheet, outcome)
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return deepcopy(outcome)

    def read(self, sheet_ref):
        from .literature_ratio_source_validation import validate_relative_signal_saved
        source = self._record(sheet_ref, 'source')
        if (source['origin'] != 'tool' or source['provider'] != PROVIDER or source.get('version') != VERSION
                or source.get('request_ref') is None or source['text_ref'] != source['artifact_ref']
                or any(source.get(key) is not None for key in ('accession', 'uri', 'retrieved_at'))):
            raise ContractError('relative_signal_saved_source_mismatch')
        request = self._json(source['request_ref'])
        if (set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments'}
                or request['run_id'] != self.run_id
                or any(type(request[key]) is not str or not request[key] for key in ('episode_id', 'operation_key'))):
            raise ContractError('relative_signal_saved_request_mismatch')
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        if operation is None:
            raise ContractError('literature_sheet_not_selected_output')
        outcome, signature = json.loads(operation['outcome']), json.loads(operation['signature'])
        payload = self._json(source['artifact_ref'])
        if (set(payload) != PAYLOAD_FIELDS or payload['version'] != VERSION
                or payload['selection'] != request['arguments']
                or payload['input_source_ref'] != request['arguments']['source_ref']
                or source['parent_source_refs'] != payload['input_source_refs']
                or set(signature) != {'arguments', 'scope', 'evidence_origin', 'role', 'assignment'}
                or signature['arguments'] != payload['selection']
                or signature['evidence_origin'] != payload['extraction']['evidence_origin']):
            raise ContractError('relative_signal_saved_payload_mismatch')
        validate_relative_signal_saved(payload['selection'], payload['extraction'], payload['sheet'], outcome)
        if (outcome['result']['sheet_ref'] != sheet_ref
                or outcome['operation_ref'] != identity('operation', {'run_id': self.run_id,
                    'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('literature_sheet_not_selected_output')
        # Reconstruct only host custody metadata. This does not grant a receiver
        # possession: fact_cells applies original-owner/admitted-subset rules.
        context = SimpleNamespace(run_id=self.run_id, episode_id=request['episode_id'], role=signature['role'], assignment=signature['assignment'],
            scope=signature['scope'], received_record_refs=payload['direct_input_source_refs'] + payload['input_view_refs'])
        direct, closure, views = self._dependencies(context, payload['selection'])
        if (direct != payload['direct_input_source_refs'] or closure != payload['input_source_refs']
                or views != payload['input_view_refs']
                or self._record(payload['input_source_ref'], 'source')['artifact_ref'] != payload['input_artifact_ref']):
            raise ContractError('relative_signal_saved_roster_mismatch')
        for item in payload['extraction']['sources']:
            original = self._record(item['source_ref'], 'source')
            artifact = original['artifact_ref'] if item['representation'] == 'original' else original.get('text_ref')
            if artifact is not None:
                self._artifact_metadata(artifact)
            if (item['state'] == 'available' and (item['artifact_ref'] != artifact
                    or artifact != 'artifact_' + item['byte_sha256'])):
                raise ContractError('relative_signal_saved_input_identity_mismatch')
        for item in payload['extraction']['views']:
            actual, _ = self._view_records(item['view_ref'])
            receipt = self._own_view_receipt(context, item['view_ref'], saved_receipt=item['own_action_receipt'])
            if item['state'] == 'available' and (item['metadata'] != actual or receipt != item['own_action_receipt']
                    or 'artifact_' + item['original_sha256'] != actual['original_artifact_ref']
                    or 'artifact_' + item['display_sha256'] != actual['image_artifact_ref']):
                raise ContractError('relative_signal_saved_view_identity_mismatch')
        calculation = self._json(payload['calculation_artifact_ref'])
        if (set(calculation) != {'version', 'input_extraction_sha256', 'calculator_implementation_sha256', 'sheet'}
                or calculation['version'] != 'relative_signal_calculation_v2'
                or calculation['input_extraction_sha256'] != _sha(payload['extraction'])
                or calculation['sheet'] != payload['sheet']
                or type(calculation['calculator_implementation_sha256']) is not str
                or len(calculation['calculator_implementation_sha256']) != 64
                or any(ch not in '0123456789abcdef' for ch in calculation['calculator_implementation_sha256'])):
            raise ContractError('relative_signal_saved_calculation_mismatch')
        bindings, measurements = self._bindings(payload['extraction'], payload['input_source_ref'])
        expected_refs = _unique([sheet_ref, *self._entity_refs(bindings),
            *(row[key] for row in measurements for key in ('input_measurement_ref', 'reference_measurement_ref') if row[key])])
        if (bindings != payload['experimental_bindings'] or measurements != payload['measurement_bindings']
                or expected_refs != outcome['record_refs']):
            raise ContractError('relative_signal_saved_binding_mismatch')
        return deepcopy(payload)

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple)) or any(type(name) is not str or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError('relative_signal_component_selection_invalid')
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(reference)
            sheet, extraction = saved['sheet'], saved['extraction']
            rows, comparison = extraction['representations'], extraction['comparison']
            def states(field, key):
                return _unique(row[field][key] for row in rows)
            common = {'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'],
                **saved['experimental_bindings'], **{key: sheet[key] for key in FLAGS},
                'independent_preparation_count': None, 'candidate_basis': 'selected_received_source_representations',
                'uncertainty_kind': 'unknown', 'uncertainty_evaluation': 'numeric_uncertainty_reader_unimplemented',
                'interpretation_kind': 'episode_source_interpretation',
                'source_origins': _unique(row['origin'] for row in rows),
                'representation_reading_states': _unique(row['reading_state'] for row in rows),
                **{key: comparison[key]['value'] if comparison[key]['status'] == 'known' else comparison[key]['status']
                   for key in ('signal_kind', 'reference_role', 'arrangement', 'signal_use')},
                'meaning_statuses': {key: comparison[key]['status'] for key in MEANINGS},
                'comparison_relation_states': states('comparison_relation', 'value'),
                'signal_scale_states': _unique(row['selection']['signal_scale']['value']
                    if row['kind'] != 'jats_percent' else 'not_applicable' for row in rows),
                'physical_identity_states': states('physical_measurement', 'status'),
                'reference_identity_states': states('reference_measurement', 'status'),
                'input_measurement_refs': _unique(row['input_measurement_ref'] for row in saved['measurement_bindings'] if row['input_measurement_ref']),
                'reference_measurement_refs': _unique(row['reference_measurement_ref'] for row in saved['measurement_bindings'] if row['reference_measurement_ref'])}
            for name in components:
                result.append({**deepcopy(common), 'component': name,
                    **{key: deepcopy(value) for key, value in sheet['cells'][name].items() if key != 'formula'}})
        validate_schema(result, ratio_source_cells_schema())
        return result

    def validate_fact_values(self, context, cells):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().validate_fact_values(context, cells)

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, ratio_source_cells_schema())
        return super().validate_returned_values(cells, permitted_record_refs=permitted_record_refs)


__all__ = ['LiteratureRatioSourceRepository', 'ratio_source_population_schema', 'ratio_source_cells_schema']

# Exact006 closed return declaration. The request has a single owner in inputs.
_RETURN_SCHEMA = {'type': 'array',
 'items': {'type': 'object',
           'properties': {'value': {'type': ['number', 'null']},
                          'value_candidates': {'type': 'array',
                                               'items': {'type': 'number'},
                                               'uniqueItems': True},
                          'reported_domains': {'type': 'array',
                                               'items': {'type': 'object',
                                                         'properties': {'lower': {'type': ['number',
                                                                                           'null']},
                                                                        'lower_infinite': {'type': 'boolean'},
                                                                        'lower_closed': {'type': 'boolean'},
                                                                        'upper': {'type': ['number',
                                                                                           'null']},
                                                                        'upper_infinite': {'type': 'boolean'},
                                                                        'upper_closed': {'type': 'boolean'},
                                                                        'meaning': {'const': 'reported_estimate_domain',
                                                                                    'type': 'string'}},
                                                         'required': ['lower',
                                                                      'lower_infinite',
                                                                      'lower_closed',
                                                                      'upper',
                                                                      'upper_infinite',
                                                                      'upper_closed',
                                                                      'meaning'],
                                                         'additionalProperties': False}},
                          'unit': {'type': ['string', 'null'],
                                   'enum': ['fraction', 'dimensionless', None]},
                          'status': {'type': 'string',
                                     'enum': ['populated', 'conflicting', 'unavailable']},
                          'origin': {'type': 'string',
                                     'enum': ['reported',
                                              'visual_transcription',
                                              'derived',
                                              'proposed',
                                              'synthetic']},
                          'unavailable_reason': {'type': ['string', 'null'],
                                                 'enum': ['no_selected_representations',
                                                          'source_dependency_unavailable',
                                                          'unreadable_transcription',
                                                          'ambiguous_transcription',
                                                          'source_representation_conflict',
                                                          'incomplete_conflicting_representations',
                                                          'comparison_association_unresolved',
                                                          'signal_scale_unresolved',
                                                          'unsupported_expression',
                                                          'negative_reported_signal_unsupported',
                                                          'reported_limit_not_point',
                                                          'positive_denominator_not_established',
                                                          'zero_reported_ratio',
                                                          'numerical_model_range',
                                                          'jats_expression_capability_partial',
                                                          'calibrated_amount_conversion_unimplemented',
                                                          'functional_response_conversion_unimplemented',
                                                          'observation_model_unimplemented',
                                                          'different_reported_quantities',
                                                          'signal_scales_differ',
                                                          None]},
                          'conditional_on': {'type': 'array',
                                             'items': {'type': 'string',
                                                       'enum': ['source_comparison_interpretation',
                                                                'nominated_printed_signal_pair']},
                                             'uniqueItems': True},
                          'sheet_ref': {'type': 'string',
                                        'format': 'reference',
                                        'x-reference-namespace': 'source'},
                          'evidence_source_ref': {'type': 'string',
                                                  'format': 'reference',
                                                  'x-reference-namespace': 'source'},
                          'component': {'type': 'string',
                                        'enum': ['reported_ratio',
                                                 'difference_from_reference',
                                                 'log_reported_ratio',
                                                 'calibrated_amount_ratio',
                                                 'amount_adjusted_effect',
                                                 'source_profile_log_ratio',
                                                 'source_signed_index']},
                          'selected_roster_resolved': {'type': 'boolean'},
                          'point_candidate_set_complete': {'type': 'boolean'},
                          'known_source_conflict': {'type': 'boolean'},
                          'independent_preparation_count': {'type': 'null'},
                          'candidate_basis': {'const': 'selected_received_source_representations',
                                              'type': 'string'},
                          'uncertainty_kind': {'const': 'unknown', 'type': 'string'},
                          'interpretation_kind': {'const': 'episode_source_interpretation',
                                                  'type': 'string'},
                          'source_origins': {'type': 'array',
                                             'items': {'type': 'string',
                                                       'enum': ['reported',
                                                                'visual_transcription',
                                                                'synthetic']},
                                             'uniqueItems': True},
                          'representation_reading_states': {'type': 'array',
                                                            'items': {'type': 'string',
                                                                      'enum': ['exact',
                                                                               'ambiguous',
                                                                               'unreadable',
                                                                               'conflicting',
                                                                               'not_applicable']},
                                                            'uniqueItems': True},
                          'signal_kind': {'type': 'string',
                                          'enum': ['protein_band',
                                                   'transcript_signal',
                                                   'other_reported_signal',
                                                   'unknown',
                                                   'conflicting']},
                          'reference_role': {'type': 'string',
                                             'enum': ['tagged_wt_complementation',
                                                      'endogenous_wt',
                                                      'other_reported_reference',
                                                      'unknown',
                                                      'conflicting']},
                          'arrangement': {'type': 'string',
                                          'enum': ['single_preparation',
                                                   'replacement',
                                                   'coexistence',
                                                   'not_applicable',
                                                   'unknown',
                                                   'conflicting']},
                          'subject_ref': {'type': ['string', 'null'],
                                          'format': 'reference',
                                          'x-reference-namespace': 'reference'},
                          'variant_ref': {'type': ['string', 'null'],
                                          'format': 'reference',
                                          'x-reference-namespace': 'reference'},
                          'reference_ref': {'type': ['string', 'null'],
                                            'format': 'reference',
                                            'x-reference-namespace': 'reference'},
                          'organism_ref': {'type': ['string', 'null'],
                                           'format': 'reference',
                                           'x-reference-namespace': 'reference'},
                          'genotype_ref': {'type': ['string', 'null'],
                                           'format': 'reference',
                                           'x-reference-namespace': 'reference'},
                          'construct_variant_ref': {'type': ['string', 'null'],
                                                    'format': 'reference',
                                                    'x-reference-namespace': 'reference'},
                          'construct_reference_ref': {'type': ['string', 'null'],
                                                      'format': 'reference',
                                                      'x-reference-namespace': 'reference'},
                          'preparation_variant_ref': {'type': ['string', 'null'],
                                                      'format': 'reference',
                                                      'x-reference-namespace': 'reference'},
                          'preparation_reference_ref': {'type': ['string', 'null'],
                                                        'format': 'reference',
                                                        'x-reference-namespace': 'reference'},
                          'experiment_ref': {'type': ['string', 'null'],
                                             'format': 'reference',
                                             'x-reference-namespace': 'reference'},
                          'condition_ref': {'type': ['string', 'null'],
                                            'format': 'reference',
                                            'x-reference-namespace': 'context'},
                          'endpoint_ref': {'type': ['string', 'null'],
                                           'format': 'reference',
                                           'x-reference-namespace': 'reference'},
                          'normalization_ref': {'type': ['string', 'null'],
                                                'format': 'reference',
                                                'x-reference-namespace': 'reference'},
                          'input_measurement_refs': {'type': 'array',
                                                     'items': {'type': 'string',
                                                               'format': 'reference',
                                                               'x-reference-namespace': 'reference'},
                                                     'uniqueItems': True},
                          'reference_measurement_refs': {'type': 'array',
                                                         'items': {'type': 'string',
                                                                   'format': 'reference',
                                                                   'x-reference-namespace': 'reference'},
                                                         'uniqueItems': True},
                          'comparison_relation_states': {'type': 'array',
                                                         'items': {'type': 'string',
                                                                   'enum': ['supported',
                                                                            'different',
                                                                            'unknown',
                                                                            'conflicting']},
                                                         'uniqueItems': True},
                          'signal_scale_states': {'type': 'array',
                                                  'items': {'type': 'string',
                                                            'enum': ['supported',
                                                                     'different',
                                                                     'unknown',
                                                                     'conflicting',
                                                                     'not_applicable']},
                                                  'uniqueItems': True},
                          'signal_use': {'type': 'string',
                                         'enum': ['experimental_comparability',
                                                  'measured_endpoint',
                                                  'other',
                                                  'unknown',
                                                  'conflicting']},
                          'meaning_statuses': {'type': 'object',
                                               'properties': {'subject': {'type': 'string',
                                                                          'enum': ['known',
                                                                                   'unknown',
                                                                                   'conflicting']},
                                                              'variant': {'type': 'string',
                                                                          'enum': ['known',
                                                                                   'unknown',
                                                                                   'conflicting']},
                                                              'reference': {'type': 'string',
                                                                            'enum': ['known',
                                                                                     'unknown',
                                                                                     'conflicting']},
                                                              'organism': {'type': 'string',
                                                                           'enum': ['known',
                                                                                    'unknown',
                                                                                    'conflicting']},
                                                              'genotype': {'type': 'string',
                                                                           'enum': ['known',
                                                                                    'unknown',
                                                                                    'conflicting']},
                                                              'construct_variant': {'type': 'string',
                                                                                    'enum': ['known',
                                                                                             'unknown',
                                                                                             'conflicting']},
                                                              'construct_reference': {'type': 'string',
                                                                                      'enum': ['known',
                                                                                               'unknown',
                                                                                               'conflicting']},
                                                              'preparation_variant': {'type': 'string',
                                                                                      'enum': ['known',
                                                                                               'unknown',
                                                                                               'conflicting']},
                                                              'preparation_reference': {'type': 'string',
                                                                                        'enum': ['known',
                                                                                                 'unknown',
                                                                                                 'conflicting']},
                                                              'experiment': {'type': 'string',
                                                                             'enum': ['known',
                                                                                      'unknown',
                                                                                      'conflicting']},
                                                              'condition': {'type': 'string',
                                                                            'enum': ['known',
                                                                                     'unknown',
                                                                                     'conflicting']},
                                                              'endpoint': {'type': 'string',
                                                                           'enum': ['known',
                                                                                    'unknown',
                                                                                    'conflicting']},
                                                              'normalization': {'type': 'string',
                                                                                'enum': ['known',
                                                                                         'unknown',
                                                                                         'conflicting']}},
                                               'required': ['subject',
                                                            'variant',
                                                            'reference',
                                                            'organism',
                                                            'genotype',
                                                            'construct_variant',
                                                            'construct_reference',
                                                            'preparation_variant',
                                                            'preparation_reference',
                                                            'experiment',
                                                            'condition',
                                                            'endpoint',
                                                            'normalization'],
                                               'additionalProperties': False},
                          'physical_identity_states': {'type': 'array',
                                                       'items': {'type': 'string',
                                                                 'enum': ['known',
                                                                          'unknown',
                                                                          'conflicting']},
                                                       'uniqueItems': True},
                          'reference_identity_states': {'type': 'array',
                                                        'items': {'type': 'string',
                                                                  'enum': ['known',
                                                                           'unknown',
                                                                           'conflicting']},
                                                        'uniqueItems': True},
                          'uncertainty_evaluation': {'const': 'numeric_uncertainty_reader_unimplemented',
                                                     'type': 'string'}},
           'required': ['value',
                        'value_candidates',
                        'reported_domains',
                        'unit',
                        'status',
                        'origin',
                        'unavailable_reason',
                        'conditional_on',
                        'sheet_ref',
                        'evidence_source_ref',
                        'component',
                        'selected_roster_resolved',
                        'point_candidate_set_complete',
                        'known_source_conflict',
                        'independent_preparation_count',
                        'candidate_basis',
                        'uncertainty_kind',
                        'interpretation_kind',
                        'source_origins',
                        'representation_reading_states',
                        'signal_kind',
                        'reference_role',
                        'arrangement',
                        'subject_ref',
                        'variant_ref',
                        'reference_ref',
                        'organism_ref',
                        'genotype_ref',
                        'construct_variant_ref',
                        'construct_reference_ref',
                        'preparation_variant_ref',
                        'preparation_reference_ref',
                        'experiment_ref',
                        'condition_ref',
                        'endpoint_ref',
                        'normalization_ref',
                        'input_measurement_refs',
                        'reference_measurement_refs',
                        'comparison_relation_states',
                        'signal_scale_states',
                        'signal_use',
                        'meaning_statuses',
                        'physical_identity_states',
                        'reference_identity_states',
                        'uncertainty_evaluation'],
           'additionalProperties': False},
 'x-source': 'literature_ratio_source_cells'}
