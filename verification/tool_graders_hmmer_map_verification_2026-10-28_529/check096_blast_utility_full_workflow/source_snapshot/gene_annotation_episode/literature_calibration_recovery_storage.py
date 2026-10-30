"""Selected recovery controls, saved numerical sections and exact typed custody.

The operation assigns no experimental meaning itself. It executes the caller's
source selection and saves the reader/calculator result once. Returning or
reconstructing that result validates custody without scientific source IO.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_calibration_recovery_inputs import (
    VERSION as INPUT_VERSION, SOURCE_KINDS, LITERAL_FIELDS, CONTROL_KINDS,
    APPLICABILITIES, SPREAD_KINDS, NUMBER_ROLES,
    calibration_recovery_population_schema, calibration_recovery_extraction_schema,
)
from .literature_calibration_recovery_calculations import VERSION as SHEET_VERSION, COMPONENTS, FORMULAS, REASONS

PROVIDER = 'literature.a105.calibration_recovery'
VERSION = 'literature_calibration_recovery_record_v1'
NAMESPACE = 'literature_calibration_recovery_cells'
REQUESTED = 'requested_calibration_recovery_components'
VIEW = 'calibration_recovery_components'
TEXT = {'type': 'string', 'minLength': 1}
SECTIONS = ('calibration_validity', 'matrix_activity_response', 'recovery_control_role_unresolved')
SCOPE_REASONS = ('control_dimension_mismatch', 'control_kind_unknown', 'control_kind_conflicting', None)
QUALIFICATIONS = ('source_quotes_do_not_prove_scientific_roles', 'shared_units_do_not_establish_comparison_linkage',
    'no_target_measurement_supplied', 'replicate_independence_not_established',
    'denominator_uncertainty_and_covariance_not_supplied', 'recovery_bias_and_inverse_share_original_operands',
    'no_overall_reliability_grade', 'no_annotation_credit')
PRECISION_COMPONENTS = ['reported_measured_spread', 'measured_sd', 'measured_cv']


def _array(schema, *, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}


def _exact():
    return {'anyOf': [obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
        'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}}), {'type': 'null'}]}


def _cell(component=None):
    return obj({'value': {'type': ['number', 'null']},
        'unit': {'enum': ['nmol', 'nmol/min', 'fraction', 'percent', 'fraction_squared', None]},
        'status': {'enum': ['populated', 'unavailable']},
        'origin': {'enum': ['reported', 'derived', 'synthetic']},
        'input_origins': _array({'enum': ['reported', 'derived', 'synthetic']}, unique=True),
        'unavailable_reason': {'enum': [*REASONS, None]},
        'formula': {'const': FORMULAS[component]} if component else {'enum': list(FORMULAS.values())},
        'exact_value': _exact(), 'input_measurement_keys': _array(TEXT, unique=True),
        'conditional_on': {'const': ['source_role_assignments']}})


def _sheet_schema():
    return obj({'version': {'const': SHEET_VERSION}, 'axis': {'const': 'A105'},
        'scope': {'const': 'source_recovery_control'}, 'extraction': calibration_recovery_extraction_schema(),
        'cells': obj({name: _cell(name) for name in COMPONENTS}), 'section': {'enum': list(SECTIONS)},
        'interpretation_scope_unavailable_reason': {'enum': list(SCOPE_REASONS)},
        'precision_components': {'const': list(PRECISION_COMPONENTS)},
        'qualifications': {'const': list(QUALIFICATIONS)}, 'annotation_credit': {'type': 'null'}})


def calibration_recovery_cells_schema():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    row = obj({'sheet_ref': deepcopy(ref), 'evidence_source_ref': deepcopy(ref),
        'evaluation_scope': {'const': 'source_calibration_recovery'},
        'component': {'enum': list(COMPONENTS)}, **_cell()['properties'],
        'source_kind': {'enum': list(SOURCE_KINDS)}, 'section': {'enum': list(SECTIONS)},
        'control_kind': {'enum': list(CONTROL_KINDS)}, 'applicability': {'enum': list(APPLICABILITIES)},
        'spread_kind': {'enum': list(SPREAD_KINDS)},
        'source_meanings': obj({name: {'type': ['string', 'null'], 'minLength': 1} for name in LITERAL_FIELDS}),
        'interpretation_scope_unavailable_reason': {'enum': list(SCOPE_REASONS)},
        'qualifications': {'const': list(QUALIFICATIONS)}})
    return {**_array(row), 'x-source': NAMESPACE}


def _project_saved(saved, reference, components):
    sheet = saved['sheet']; data = sheet['extraction']
    meanings = {name: None if literal is None else literal['value'] for name, literal in data['literals'].items()}
    return [{'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'],
        'evaluation_scope': 'source_calibration_recovery', 'component': name,
        **deepcopy(sheet['cells'][name]), 'source_kind': data['source_kind'], 'section': sheet['section'],
        **{field: data[field]['value'] for field in ('control_kind', 'applicability', 'spread_kind')},
        'source_meanings': deepcopy(meanings),
        'interpretation_scope_unavailable_reason': sheet['interpretation_scope_unavailable_reason'],
        'qualifications': deepcopy(sheet['qualifications'])} for name in components]


class LiteratureCalibrationRecoveryRepository(LiteratureRateRepository):
    provider, components, record_version = PROVIDER, COMPONENTS, VERSION
    operations_table = 'literature_calibration_recovery_operations'
    received_table = 'literature_calibration_recovery_received'
    binding_fields = ()

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    @staticmethod
    def _components(components):
        if (not isinstance(components, (list, tuple)) or any(type(name) is not str or name not in COMPONENTS for name in components)
                or len(set(components)) != len(components)):
            raise ContractError('literature_calibration_recovery_component_selection_invalid')
        return list(components)

    def _ancestors(self, scope, references):
        result = list(dict.fromkeys(references))
        for reference in result:
            for parent in self._native_provenance(scope, reference).get('parent_source_refs', ()):
                if parent not in result:
                    result.append(parent)
        return result

    def populate(self, context, arguments, operation_key):
        from .literature_calibration_recovery_inputs import read_calibration_recovery_inputs
        from .literature_calibration_recovery_calculations import populate_calibration_recovery
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments); validate_schema(args, calibration_recovery_population_schema())
        source = self._native_source(context, args['source_ref'])
        requested = self._components(plain(context.assignment.get(REQUESTED, [])))
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key,
            'arguments': args, 'scope': plain(context.scope), 'components': requested}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome']); saved = self.read(outcome['result']['sheet_ref'])
            for reference in saved['direct_input_source_refs']:
                self._native_source(context, reference)
            return outcome

        def read_source(reference, representation):
            row = self._native_source(context, reference)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}

        extraction = read_calibration_recovery_inputs(args, read_source=read_source)
        sheet = populate_calibration_recovery(extraction); validate_schema(sheet, _sheet_schema())
        ancestors = self._ancestors(context.scope, extraction['source_refs'])
        payload = {'version': VERSION, 'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'],
            'direct_input_source_refs': extraction['source_refs'], 'input_source_refs': ancestors, 'selection': args, 'sheet': sheet}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': request_ref, 'version': VERSION, 'retrieved_at': None,
                'parent_source_refs': ancestors}
            reference = identity('source', {'origin': 'tool', 'record': value})
            existed = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (reference,)).fetchone()
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [reference],
                'changed_record_refs': [] if existed else [reference], 'result': {'sheet_ref': reference,
                    'view': VIEW, 'cells': _project_saved(payload, reference, requested)}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json_artifact(self, reference):
        content = self.store.get_artifact(reference)
        if 'artifact_' + hashlib.sha256(content).hexdigest() != reference:
            raise ContractError('calibration_recovery_saved_artifact_hash_mismatch')
        try:
            return json.loads(content)
        except (TypeError, ValueError) as error:
            raise ContractError('calibration_recovery_saved_json_invalid') from error

    def read(self, sheet_ref):
        """Authenticate the original saved result; parse no scientific input."""
        source = self.store.get(sheet_ref)
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER
                or source.get('version') != VERSION or identity('source', {'origin': 'tool', 'record': value}) != sheet_ref):
            raise ContractError('literature_calibration_recovery_sheet_required')
        request = self._json_artifact(source['request_ref'])
        if set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments', 'scope', 'components'} or request['run_id'] != self.run_id:
            raise ContractError('calibration_recovery_saved_request_mismatch')
        validate_schema(request['arguments'], calibration_recovery_population_schema()); self._components(request['components'])
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('literature_sheet_not_selected_output')
        saved = self._json_artifact(source['artifact_ref'])
        if (set(saved) != {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs', 'input_source_refs', 'selection', 'sheet'}
                or saved['version'] != VERSION or saved['selection'] != request['arguments']
                or saved['input_source_ref'] != request['arguments']['source_ref'] or saved['input_source_refs'] != source['parent_source_refs']):
            raise ContractError('calibration_recovery_saved_selection_mismatch')
        validate_schema(saved['sheet'], _sheet_schema()); self._validate_saved_bindings(saved, request)
        outcome = json.loads(operation['outcome'])
        expected = {'sheet_ref': sheet_ref, 'view': VIEW, 'cells': _project_saved(saved, sheet_ref, request['components'])}
        if (outcome.get('status') != 'completed' or canonical(outcome.get('result')) != canonical(expected)
                or outcome.get('record_refs') != [sheet_ref] or outcome.get('feedback') is not None
                or outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('calibration_recovery_saved_outcome_mismatch')
        return saved

    def _validate_saved_bindings(self, saved, request):
        args = request['arguments']; data = saved['sheet']['extraction']
        original = self._native_provenance(request['scope'], saved['input_source_ref'])
        if (original['artifact_ref'] != saved['input_artifact_ref'] or data['artifact_ref'] != saved['input_artifact_ref']
                or data['source_ref'] != saved['input_source_ref'] or data['source_kind'] != args['source_kind']
                or data['source_refs'] != saved['direct_input_source_refs']
                or self._ancestors(request['scope'], data['source_refs']) != saved['input_source_refs']):
            raise ContractError('calibration_recovery_saved_source_binding_mismatch')
        def witness(selected):
            source = self._native_provenance(request['scope'], selected['source_ref'])
            artifact = source['artifact_ref'] if selected['representation'] == 'original' else source.get('text_ref')
            if selected['source_ref'] not in data['source_refs'] or artifact is None:
                raise ContractError('calibration_recovery_saved_source_binding_mismatch')
            return {**deepcopy(selected), 'artifact_ref': artifact}
        for name in LITERAL_FIELDS:
            expected = None if args[name] is None else {'value': args[name]['quote'], 'witness': witness(args[name])}
            if data['literals'][name] != expected:
                raise ContractError('calibration_recovery_saved_literal_binding_mismatch')
        for name in ('control_kind', 'applicability', 'spread_kind'):
            expected = {'kind': 'source_interpretation', 'value': args[name]['value'],
                'witnesses': [witness(w) for w in args[name]['witnesses']]}
            if data[name] != expected:
                raise ContractError('calibration_recovery_saved_interpretation_binding_mismatch')
        for name in NUMBER_ROLES:
            selected, observation = args[name], data['observations'][name]
            if (selected is None) != (observation is None):
                raise ContractError('calibration_recovery_saved_measurement_binding_mismatch')
            if selected is not None:
                expected = {**deepcopy(selected), 'witness': witness(selected['witness'])}
                if observation['selector'] != expected:
                    raise ContractError('calibration_recovery_saved_measurement_binding_mismatch')
        for name in ('shared_unit', 'reported_recovery_unit'):
            selected = args[name]; record = data[name]
            if (selected is None) != (record is None):
                raise ContractError('calibration_recovery_saved_unit_binding_mismatch')
            if selected is not None:
                unit_witness = selected['witness'] if name == 'reported_recovery_unit' else selected
                if record['witness'] != witness(unit_witness) or record['raw_unit'] != unit_witness['quote']:
                    raise ContractError('calibration_recovery_saved_unit_binding_mismatch')
        for cell in saved['sheet']['cells'].values():
            if ((cell['value'] is None) != (cell['status'] == 'unavailable')
                    or (cell['unavailable_reason'] is None) != (cell['status'] == 'populated')):
                raise ContractError('calibration_recovery_saved_cell_binding_mismatch')

    def owned_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        references = []
        for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id)):
            outcome = json.loads(row['outcome'])
            if outcome.get('status') == 'completed' and outcome['result']['sheet_ref'] in context.received_record_refs:
                references.append(outcome['result']['sheet_ref'])
        return list(dict.fromkeys(references))

    def available_sheet_refs(self, context):
        references = self.owned_sheet_refs(context)
        references.extend(row['sheet_ref'] for row in self.received_cells(context) if row['sheet_ref'] in context.received_record_refs)
        return list(dict.fromkeys(references))

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self._components(COMPONENTS if components is None else components)
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            result.extend(_project_saved(self.read(reference), reference, selected))
        return result

    def fact_cells(self, context, sheet_refs, *, components):
        refs = list(dict.fromkeys(sheet_refs))
        if self.store.reference_subset(refs, plain(context.scope)) != refs:
            raise ContractError('literature_source_outside_scope')
        return super().fact_cells(context, refs, components=components)

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install(); return super().receive_cells(context, cells, operation_key)

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(ref for row in cells for ref in (row['sheet_ref'], row['evidence_source_ref'])))
