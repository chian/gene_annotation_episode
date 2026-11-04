"""Persist selected assay grading and deliver exact requested A105 components.

Only population reads scientific inputs and calculates. Reconstruction validates
committed identities and typed cells; it does not rerun a reader or grader.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_assay_grading import (
    COMPONENTS, CRITERIA_BY_TYPE, grade_assay, assay_grading_input_schema, assay_grading_sheet_schema,
    assay_grading_cell_schema,
)
from .literature_assay_grading_inputs import assay_grading_population_schema as grading_population_schema, read_assay_grading_inputs
from .literature_assay_grading_prompt import ASSAY_GRADING_OPERATION_DESCRIPTION
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = 'literature.a105.assay_grading'
LEGACY_VERSION = 'literature_assay_grading_record_v1'
VERSION = 'literature_assay_grading_record_v2'
NAMESPACE = 'literature_assay_grading_cells'
REQUESTED = 'requested_assay_grading_components'
SCOPE = 'assay_type_experimental_evidence'
OPERATION_DESCRIPTION = ASSAY_GRADING_OPERATION_DESCRIPTION


def assay_grading_cells_schema():
    cell_schema = assay_grading_cell_schema()
    fields = deepcopy(cell_schema['properties'])
    sheet = assay_grading_sheet_schema()['properties']
    fields.update({
        'sheet_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
        'evidence_source_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
        **{name: deepcopy(sheet[name]) for name in (
            'evaluation_scope', 'assay_type', 'assertion_ref', 'quantity_kind',
            'interpretations', 'prediction_model', 'annotation_credit')},
    })
    fields['experiment_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'reference'}
    fields['assertion_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis'}
    fields['source_refs']['items'] = {'type': 'string', 'format': 'reference'}
    for criterion in fields['interpretations']['properties'].values():
        criterion['properties']['support_refs']['items'] = {'type': 'string', 'format': 'reference'}
    fields['prediction_model']['anyOf'][0]['properties']['support_refs']['items'] = {
        'type': 'string', 'format': 'reference'}
    return {'type': 'array', 'x-source': NAMESPACE,
        'items': obj(fields, required=[*cell_schema['required'],
            'sheet_ref', 'evidence_source_ref', 'evaluation_scope', 'assay_type',
            'assertion_ref', 'quantity_kind', 'interpretations', 'prediction_model', 'annotation_credit'])}


def legacy_assay_grading_cells_schema():
    """Original frozen four-type parent contract; never infer new old fields."""
    return json.loads(Path(__file__).with_name('literature_assay_grading_legacy_cells_v1.json').read_text())


def _rows(saved, sheet_ref, components):
    sheet = saved['sheet']
    shared = {name: deepcopy(sheet[name]) for name in (
        'evaluation_scope', 'assay_type', 'assertion_ref', 'quantity_kind',
        'annotation_credit')}
    if 'experiment_ref' in saved['selection']:
        shared['experiment_ref'] = saved['selection']['experiment_ref']
    by_component = {
        'measured_effect': (), 'effect_variance': ('variance_correspondence',),
        'effect_precision': ('variance_correspondence',),
        'recovery_deviation': ('calibration_applicability',),
        'attributed_fraction': ('measurement_identity', 'attribution_supported'),
        'condition_response': ('measurement_identity', 'condition_scope'),
        'source_log_evidence_ratio': CRITERIA_BY_TYPE[sheet['assay_type']],
    }
    predictive = tuple(name for name in CRITERIA_BY_TYPE[sheet['assay_type']]
        if name not in ('variance_correspondence', 'sampling_basis'))
    rows = []
    for component in components:
        selected = by_component.get(component, predictive)
        rows.append({'sheet_ref': sheet_ref, 'evidence_source_ref': saved['selection']['source_ref'],
            **deepcopy(sheet['cells'][component]), **deepcopy(shared),
            'interpretations': {name: deepcopy(sheet['interpretations'][name])
                for name in selected if name in sheet['interpretations']},
            'prediction_model': deepcopy(sheet['prediction_model']) if component == 'source_log_evidence_ratio' else None})
    return rows


class LiteratureAssayGradingRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION
    operations_table = 'literature_assay_grading_operations'
    received_table = 'literature_assay_grading_received'
    binding_fields = ()

    legacy_version = LEGACY_VERSION
    requested = REQUESTED
    population_schema = staticmethod(grading_population_schema)
    read_inputs = staticmethod(read_assay_grading_inputs)
    input_schema = staticmethod(assay_grading_input_schema)
    grade = staticmethod(grade_assay)
    sheet_schema = staticmethod(assay_grading_sheet_schema)
    rows = staticmethod(_rows)
    cells_schema = staticmethod(assay_grading_cells_schema)

    def before_publish(self, context, arguments):
        """Optional axis-specific identity/revision checks inside the transaction."""

    def __init__(self, store, run_id, *, read_cells=None):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id
        self._read_cells = read_cells

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    def _record(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError('assay_grading_record_not_received')
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError('assay_grading_record_outside_scope')
        return self.store.get(reference)

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        if 'experiment_ref' not in args:
            raise ContractError('assay_grading_experiment_reference_required')
        validate_schema(args, self.population_schema())
        requested = list(context.assignment.get(self.requested, ()))
        if len(set(requested)) != len(requested) or any(name not in self.components for name in requested):
            raise ContractError('assay_grading_component_selection_invalid')
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

        if 'experiment_ref' not in args:
            raise ContractError('assay_grading_experiment_reference_required')

        record_bindings, direct, artifact_bindings, input_component_rows = {}, [], {}, []
        def retain(record, *, possessed=False):
            reference = record['id']
            record_bindings[reference] = identity('assay_grading_input_record', record)
            if possessed and reference not in direct:
                direct.append(reference)
            return record
        def read_record(reference):
            return retain(self._record(context, reference), possessed=True)
        def read_source(reference, representation):
            source = retain(self._native_source(context, reference), possessed=True)
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            raw = self.store.get_artifact(artifact)
            if artifact != 'artifact_' + sha256(raw).hexdigest():
                raise ContractError('assay_grading_input_artifact_hash_mismatch')
            artifact_bindings[(reference, representation)] = artifact
            return {'artifact_ref': artifact, 'content': raw}
        def read_cells(namespace, sheet_ref, components):
            retain(self._native_source(context, sheet_ref), possessed=True)
            if self._read_cells is None:
                raise ContractError('assay_grading_component_reader_unbound')
            rows = self._read_cells(context, namespace, sheet_ref, components)
            input_component_rows.append({'namespace': namespace, 'sheet_ref': sheet_ref,
                'components': list(components), 'rows': deepcopy(rows)})
            return rows
        def read_database_request(reference):
            source = retain(self._native_source(context, reference), possessed=True)
            request_ref = source.get('request_ref')
            if request_ref is None:
                raise ContractError('database_measurement_request_unavailable')
            receipt = self._artifact_json(request_ref)
            artifact_bindings[(reference, 'request')] = request_ref
            return receipt

        retain(self._native_source(context, args['source_ref']), possessed=True)
        extraction = self.read_inputs(args, read_source=read_source,
            read_cells=read_cells, read_record=read_record, read_database_request=read_database_request)
        validate_schema(extraction, self.input_schema())
        sheet = self.grade(extraction)
        validate_schema(sheet, self.sheet_schema())
        # Retain public provenance from every quantity without expanding a
        # delivered numerical subset into private reader operands.
        sources = [args['source_ref']]
        for quantity in extraction['quantities'].values():
            if quantity is not None:
                sources.extend(quantity['source_refs'])
        for reference in list(record_bindings):
            record = self.store.get(reference)
            if record['record_type'] == 'source':
                sources.append(reference)
            elif record.get('source_ref'):
                sources.append(record['source_ref'])
        sources = list(dict.fromkeys(sources))
        for reference in sources:
            source = retain(self._native_provenance(context.scope, reference))
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        payload = {'version': self.record_version, 'selection': args, 'extraction': extraction,
            'sheet': sheet, 'direct_record_refs': direct, 'input_source_refs': sources,
            'record_bindings': record_bindings,
            'input_component_rows': input_component_rows,
            'artifact_bindings': [{'source_ref': ref, 'representation': rep, 'artifact_ref': artifact}
                for (ref, rep), artifact in artifact_bindings.items()]}
        with self.store.transaction():
            self._install()
            self.before_publish(context, args)
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(signature, 'application/json')
            record = {'provider': self.provider, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
                'version': self.record_version, 'retrieved_at': None, 'parent_source_refs': sources}
            sheet_ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (sheet_ref,)).fetchone()
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = self.rows(payload, sheet_ref, requested)
            validate_schema(rows, self.cells_schema())
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
            raise ContractError('assay_grading_saved_hash_mismatch')
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError('assay_grading_saved_json_required') from error
        if not isinstance(value, dict):
            raise ContractError('assay_grading_saved_object_required')
        return value

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool'
                or source.get('provider') != self.provider or source.get('version') not in (self.record_version, self.legacy_version)):
            raise ContractError('assay_grading_sheet_required')
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != sheet_ref:
            raise ContractError('assay_grading_saved_identity_mismatch')
        request = self._artifact_json(source['request_ref'])
        if (set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments', 'scope', 'requested_components'}
                or request['run_id'] != self.run_id):
            raise ContractError('assay_grading_saved_selection_mismatch')
        scope = self.store.validate_scope(request['scope'])
        self._native_provenance(scope, sheet_ref)
        operation = self.store.db.execute(
            f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('assay_grading_saved_operation_mismatch')
        saved = self._artifact_json(source['artifact_ref'])
        outcome = json.loads(operation['outcome'])
        if (set(saved) != {'version', 'selection', 'extraction', 'sheet', 'direct_record_refs',
                'input_source_refs', 'record_bindings', 'artifact_bindings', 'input_component_rows'}
                or saved['version'] != source['version'] or saved['selection'] != request['arguments']
                or saved['input_source_refs'] != source['parent_source_refs']
                or outcome.get('status') != 'completed'
                or outcome.get('result', {}).get('sheet_ref') != sheet_ref
                or outcome.get('record_refs') != [sheet_ref]
                or outcome.get('operation_ref') != identity('operation', {
                    'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('assay_grading_saved_selection_mismatch')
        validate_schema(saved['selection'], self.population_schema(legacy=source['version'] != self.record_version))
        if source['version'] == self.record_version and 'experiment_ref' not in saved['selection']:
            raise ContractError('assay_grading_saved_experiment_missing')
        validate_schema(saved['extraction'], self.input_schema())
        validate_schema(saved['sheet'], self.sheet_schema())
        for reference, digest in saved['record_bindings'].items():
            if (not self.store.reference_subset([reference], plain(scope))
                    or identity('assay_grading_input_record', self.store.get(reference)) != digest):
                raise ContractError('assay_grading_saved_input_mismatch')
        if not set(saved['direct_record_refs']) <= set(saved['record_bindings']):
            raise ContractError('assay_grading_saved_input_mismatch')
        for binding in saved['artifact_bindings']:
            native = self.store.get(binding['source_ref'])
            field = {'original': 'artifact_ref', 'text': 'text_ref', 'request': 'request_ref'}[binding['representation']]
            if native.get(field) != binding['artifact_ref']:
                raise ContractError('assay_grading_saved_input_mismatch')
        rows = self.rows(saved, sheet_ref, request['requested_components'])
        validate_schema(rows, self.cells_schema())
        if canonical(rows) != canonical(outcome['result']['cells']):
            raise ContractError('assay_grading_saved_cells_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self.components if components is None else components
        if (not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected)
                or any(component not in self.components for component in selected)):
            raise ContractError('assay_grading_component_selection_invalid')
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            rows.extend(self.rows(self.read(reference), reference, selected))
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
            if row.get('record_type') == 'source' and row.get('provider') == self.provider and row.get('version') in (self.record_version, self.legacy_version):
                self.read(reference)
                refs.append(reference)
        return list(dict.fromkeys(refs))

    def experiment_sheets(self, context, *, components=None):
        """All possessed assessments, grouped by experiment, without pooling.

        Multiple assessments of an experiment remain distinct immutable sheets.
        Parent possession grants only the delivered cells, never private child
        operands. Historical sheets with no experiment binding stay separate.
        Shared measurement keys remain on each cell; distinct experiment refs
        do not assert statistical independence.
        """
        selected = self.components if components is None else components
        rows = self.fact_cells(context, self.available_sheet_refs(context), components=selected)
        experiments, assessments = {}, {}
        for row in rows:
            experiment = row.get('experiment_ref')
            key = experiment if experiment is not None else row['sheet_ref']
            group = experiments.setdefault(key, {'experiment_ref': experiment, 'sheets': []})
            sheet_key = (key, row['sheet_ref'])
            if sheet_key not in assessments:
                assessment = {name: row[name] for name in
                    ('sheet_ref', 'assay_type', 'assertion_ref', 'quantity_kind', 'evidence_source_ref')}
                assessment['cells'] = []
                assessments[sheet_key] = assessment
                group['sheets'].append(assessment)
            assessments[sheet_key]['cells'].append(deepcopy(row))
        return list(experiments.values())

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        for row in cells:
            refs.extend((row['sheet_ref'], row['evidence_source_ref'], row['assertion_ref']))
            if row.get('experiment_ref') is not None:
                refs.append(row['experiment_ref'])
            refs.extend(row.get('source_refs', ()))
            for interpretation in row['interpretations'].values():
                refs.extend(interpretation['support_refs'])
            if row['prediction_model']:
                refs.extend(row['prediction_model']['support_refs'])
        return list(dict.fromkeys(ref for ref in refs if ref is not None))


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'SCOPE', 'COMPONENTS',
    'OPERATION_DESCRIPTION', 'LiteratureAssayGradingRepository', 'assay_grading_cells_schema',
    'legacy_assay_grading_cells_schema']
