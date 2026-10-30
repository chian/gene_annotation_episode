"""Persist selected A105 aggregation over the parent's possessed grade rows."""
from copy import deepcopy
from hashlib import sha256
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_a105_aggregation import (
    COMPONENTS, SCOPE, aggregate_a105, aggregation_population_schema,
    aggregation_cell_schema, aggregation_sheet_schema,
)
from .literature_assay_grading_storage import LiteratureAssayGradingRepository, assay_grading_cells_schema
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = 'literature.a105.aggregation'
VERSION = 'literature_a105_aggregation_record_v1'
NAMESPACE = 'literature_a105_aggregation_cells'
REQUESTED = 'requested_a105_aggregation_components'
OPERATION_DESCRIPTION = (
    'Combine the retained experimental A105 components selected by the parent. '
    'Use one actual possessed numerical component per experiment and metric: '
    'reliability SUM, validity SUM, relevance MAX, attribution MAX, overall SUM. '
    'Preserve the selected native values, units and meanings, with no weighting, '
    'rescaling or orthogonality correction. Select one assessment of each experiment '
    'so duplicate reports or revisions do not become additional experiments. '
    'Keep missing values explicit and report available partial totals separately. '
    'The comparison reference is a parent declaration; no alternative hypothesis '
    'identity is inferred from the native prediction numbers. Return exactly the '
    'requested saved metrics. This is A105 evidence aggregation, not W05 annotation credit.'
)


def aggregation_cells_schema():
    fields = deepcopy(aggregation_cell_schema()['properties'])
    fields['sheet_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}


def _rows(saved, sheet_ref, components):
    return [dict(sheet_ref=sheet_ref, **deepcopy(saved['sheet']['cells'][name])) for name in components]


class LiteratureA105AggregationRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION
    operations_table = 'literature_a105_aggregation_operations'
    received_table = 'literature_a105_aggregation_received'
    binding_fields = ()

    def __init__(self, store, run_id, *, read_cells=None):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id
        self._read_cells = read_cells

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    def _record(self, context, reference, kind=None):
        if reference not in context.received_record_refs:
            raise ContractError('a105_aggregation_record_not_received')
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError('a105_aggregation_record_outside_scope')
        record = self.store.get(reference)
        if kind is not None and record['record_type'] != kind:
            raise ContractError('a105_aggregation_record_type_mismatch')
        return record

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, aggregation_population_schema())
        requested = list(context.assignment.get(REQUESTED, ()))
        if len(set(requested)) != len(requested) or any(name not in COMPONENTS for name in requested):
            raise ContractError('a105_aggregation_component_selection_invalid')
        request = {'run_id': self.run_id, 'episode_id': context.episode_id,
            'operation_key': operation_key, 'arguments': args, 'scope': plain(context.scope),
            'requested_components': requested}
        signature = canonical(request)
        old = self.store.db.execute(
            f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            saved = self.read(outcome['result']['sheet_ref'])
            for reference in saved['direct_record_refs']:
                self._record(context, reference)
            return outcome

        direct, bindings = [], {}
        def retain(reference, kind=None, possessed=True):
            record = self._record(context, reference, kind) if possessed else self._native_provenance(context.scope, reference)
            bindings[reference] = identity('a105_aggregation_input_record', record)
            if possessed and reference not in direct:
                direct.append(reference)
            return record
        retain(args['assertion_ref'], 'hypothesis')
        if args['comparison_ref'] is not None:
            retain(args['comparison_ref'], 'hypothesis')
        selections = {}
        for experiment in args['experiments']:
            retain(experiment['experiment_ref'], 'reference')
            for selected in experiment['metrics'].values():
                if selected is not None:
                    key = selected['sheet_ref'], selected['component']
                    selections[key] = selected
        if selections and self._read_cells is None:
            raise ContractError('a105_aggregation_grade_reader_unbound')
        input_rows, sources, grouped = [], [], {}
        for sheet_ref, component in selections:
            grouped.setdefault(sheet_ref, []).append(component)
        native = LiteratureAssayGradingRepository(self.store, self.run_id)
        for sheet_ref, components in grouped.items():
            retain(sheet_ref, 'source')
            rows = self._read_cells(context, sheet_ref, components)
            validate_schema(rows, assay_grading_cells_schema())
            if [(row['sheet_ref'], row['component']) for row in rows] != [(sheet_ref, component) for component in components]:
                raise ContractError('a105_aggregation_component_not_received')
            # The callback supplies exact possessed rows. Revalidate numerical
            # identity against the saved native row without widening custody.
            expected_rows = native.fact_cells(context, [sheet_ref], components=components)
            if canonical(rows) != canonical(expected_rows):
                raise ContractError('a105_aggregation_component_not_received')
            input_rows.extend(deepcopy(rows))
            sources.append(sheet_ref)
        sheet = aggregate_a105(args, input_rows)
        for reference in list(dict.fromkeys(sources)):
            source = retain(reference, 'source')
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        # Retain closure facts, not source bytes or private numerical operands.
        for reference in sources:
            source = retain(reference, possessed=False)
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        payload = {'version': VERSION, 'selection': args, 'source_cells': input_rows,
            'sheet': sheet, 'direct_record_refs': direct, 'input_source_refs': sources,
            'record_bindings': bindings}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(signature, 'application/json')
            record = {'provider': PROVIDER, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
                'version': VERSION, 'retrieved_at': None, 'parent_source_refs': sources}
            sheet_ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (sheet_ref,)).fetchone()
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = _rows(payload, sheet_ref, requested)
            validate_schema(rows, aggregation_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {
                'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}),
                'record_refs': [sheet_ref], 'changed_record_refs': [] if exists else [sheet_ref],
                'result': {'sheet_ref': sheet_ref, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != 'artifact_' + sha256(raw).hexdigest():
            raise ContractError('a105_aggregation_saved_hash_mismatch')
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as cause:
            raise ContractError('a105_aggregation_saved_json_required') from cause
        if not isinstance(result, dict):
            raise ContractError('a105_aggregation_saved_object_required')
        return result

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool'
                or source.get('provider') != PROVIDER or source.get('version') != VERSION):
            raise ContractError('a105_aggregation_sheet_required')
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != sheet_ref:
            raise ContractError('a105_aggregation_saved_identity_mismatch')
        request = self._artifact_json(source['request_ref'])
        if (set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments', 'scope', 'requested_components'}
                or request['run_id'] != self.run_id):
            raise ContractError('a105_aggregation_saved_selection_mismatch')
        scope = self.store.validate_scope(request['scope'])
        self._native_provenance(scope, sheet_ref)
        operation = self.store.db.execute(
            f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('a105_aggregation_saved_operation_mismatch')
        saved = self._artifact_json(source['artifact_ref'])
        outcome = json.loads(operation['outcome'])
        if (set(saved) != {'version', 'selection', 'source_cells', 'sheet', 'direct_record_refs',
                'input_source_refs', 'record_bindings'} or saved['version'] != VERSION
                or saved['selection'] != request['arguments']
                or saved['input_source_refs'] != source['parent_source_refs']
                or outcome.get('status') != 'completed' or outcome.get('result', {}).get('sheet_ref') != sheet_ref
                or outcome.get('record_refs') != [sheet_ref]
                or outcome.get('operation_ref') != identity('operation', {
                    'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('a105_aggregation_saved_selection_mismatch')
        validate_schema(saved['selection'], aggregation_population_schema())
        validate_schema(saved['source_cells'], assay_grading_cells_schema())
        validate_schema(saved['sheet'], aggregation_sheet_schema())
        for reference, digest in saved['record_bindings'].items():
            if (not self.store.reference_subset([reference], plain(scope))
                    or identity('a105_aggregation_input_record', self.store.get(reference)) != digest):
                raise ContractError('a105_aggregation_saved_input_mismatch')
        if not set(saved['direct_record_refs']) <= set(saved['record_bindings']):
            raise ContractError('a105_aggregation_saved_input_mismatch')
        native = LiteratureAssayGradingRepository(self.store, self.run_id)
        grouped = {}
        for row in saved['source_cells']:
            grouped.setdefault(row['sheet_ref'], []).append(row)
        for reference, originals in grouped.items():
            expected_rows = native.project_cells([reference], permitted_record_refs=[reference],
                components=[row['component'] for row in originals])
            if canonical(originals) != canonical(expected_rows):
                raise ContractError('a105_aggregation_saved_input_mismatch')
        rows = _rows(saved, sheet_ref, request['requested_components'])
        validate_schema(rows, aggregation_cells_schema())
        if canonical(rows) != canonical(outcome['result']['cells']):
            raise ContractError('a105_aggregation_saved_cells_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = COMPONENTS if components is None else components
        if (not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected)
                or any(component not in COMPONENTS for component in selected)):
            raise ContractError('a105_aggregation_component_selection_invalid')
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            rows.extend(_rows(self.read(reference), reference, selected))
        return rows

    def received_cells(self, context):
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)

    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        rows = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid',
            (self.run_id, context.episode_id))
        return list(dict.fromkeys(json.loads(row['outcome'])['result']['sheet_ref'] for row in rows))

    def available_sheet_refs(self, context):
        refs = []
        for reference in context.received_record_refs:
            try:
                row = self.store.get(reference)
            except (LookupError, ContractError):
                continue
            if row.get('record_type') == 'source' and row.get('provider') == PROVIDER and row.get('version') == VERSION:
                self.read(reference)
                refs.append(reference)
        return list(dict.fromkeys(refs))

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        for row in cells:
            refs.extend((row['sheet_ref'], row['assertion_ref'], row['comparison_ref']))
            refs.extend(row['selected_experiment_refs'])
            refs.extend(row['source_refs'])
            refs.extend(LiteratureAssayGradingRepository.cell_record_refs(row['selected_components']))
        return list(dict.fromkeys(ref for ref in refs if ref is not None))


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'SCOPE', 'COMPONENTS',
    'OPERATION_DESCRIPTION', 'aggregation_cells_schema', 'LiteratureA105AggregationRepository']
