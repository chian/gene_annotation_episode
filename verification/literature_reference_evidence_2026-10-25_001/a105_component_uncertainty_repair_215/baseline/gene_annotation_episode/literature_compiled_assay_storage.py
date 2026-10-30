"""Selected saved-component compilation and exact scoped numerical returns.

Population alone reads source context and computes. Saved projection authenticates
original receipts and content-addressed snapshots without upstream acquisition,
unit conversion, scientific arithmetic or additional controller observations.
"""
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_compiled_assay_inputs import (
    ROLES, ALLOWLIST, ASSAY_LITERAL_FIELDS, ENDPOINTS, ARRANGEMENTS, STAGES, STAGE_VALUES, LINKS, LINK_LIMITS,
    compiled_assay_population_schema, read_compiled_assay_inputs, source_schema,
    NS_ASSAY, NS_OPTICAL, NS_RECOVERY, NS_ACTIVE, NS_AMOUNT, NS_NATIVE, NS_REPLICATE,
)
from .literature_compiled_assay_calculations import (
    VERSION as SHEET_VERSION, PRIMITIVES, COMPONENTS, SECTIONS, MEANINGS, REASONS, FORMULA_VARIANTS, QUALIFICATIONS, populate_compiled_assay,
)

PROVIDER = 'literature.a105.compiled_assay'
VERSION = 'literature_compiled_assay_record_v1'
NAMESPACE = 'literature_compiled_assay_cells'
REQUESTED = 'requested_compiled_assay_components'
VIEW = 'compiled_assay_components'


def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}


def _ref(namespace='source', nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference',
            'x-reference-namespace': namespace}


def _text(nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'minLength': 1}


def _selector():
    return obj({'namespace': {'type': 'string', 'enum': list(dict.fromkeys(ns for choices in ALLOWLIST.values() for ns in choices))},
        'sheet_ref': _ref(), 'component': {'type': 'string', 'enum': list(dict.fromkeys(name for choices in ALLOWLIST.values() for names in choices.values() for name in names))}})


def _dependency():
    return obj({'role': {'type': 'string', 'enum': list(ROLES)},
        'selection': {'anyOf': [_selector(), {'type': 'null'}]}, 'component_key': _text(True),
        'quantity_key': _text(True), 'canonical_physical_keys': _array(_text(), True),
        'recorded_dependency_keys': _array(_text(), True),
        'physical_identity_status': {'type': 'string', 'enum': ['partly_canonical', 'cross_component_identity_unknown', 'definition_identity']},
        'identity_stage': {'type': ['string', 'null'], 'enum': [*STAGES, None]}})


def _numerical_cell():
    return obj({'value': {'type': ['number', 'null']}, 'unit': {'type': ['string', 'null'], 'enum': ['uM/min', 'uM', 'dimensionless', 'per_min', 'per_min_squared', 'min_squared', 'nM', 'fraction', 'umol/min', 'nmol/min', 'mmol/min', 'nM/min', 'per_s', 'umol/min/mg', 'nmol/min/mg', 'mg/ml', None]},
        'status': {'type': 'string', 'enum': ['populated', 'unavailable']},
        'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *REASONS]},
        'formula': {'type': 'string', 'enum': list(FORMULA_VARIANTS)},
        'origin': {'type': 'string', 'enum': ['reported', 'derived', 'graph_derived', 'synthetic', 'proposed', 'definition_identity']},
        'section': {'type': 'string', 'enum': list(dict.fromkeys(SECTIONS.values()))},
        'meaning': {'type': 'string', 'enum': list(dict.fromkeys(MEANINGS.values()))},
        'conditional_on': _array({'type': 'string', 'enum': ['first_order_covariance_propagation', 'known_variance', 'known_normal_nonnegative_presence']}),
        'qualifications': _array({'type': 'string', 'enum': list(QUALIFICATIONS)})})


def _native_quantity_schema():
    # Copy only the selected component's own numerical domain. Original family
    # schemas constrain the preserved domain; no neighboring operand is exposed.
    properties = [source_schema(ns)['items']['properties'] for ns in
        (NS_ASSAY, NS_OPTICAL, NS_RECOVERY, NS_ACTIVE, NS_AMOUNT, NS_NATIVE, NS_REPLICATE)]
    def union(field, fallback):
        choices = [deepcopy(p[field]) for p in properties if field in p]
        return {'anyOf': [*choices, fallback]}
    return {'anyOf': [obj({
        'value': {'type': ['number', 'null']},
        'source_unit': union('unit', {'type': 'null'}),
        'threshold': {'type': ['number', 'null']},
        'bound': {'type': 'string', 'enum': ['none', 'point', 'lt', 'le', 'gt', 'ge']},
        'approximate': {'type': ['boolean', 'null']},
        'reported_domain': union('reported_domain', {'type': 'null'}),
        'exact_domain': union('exact_domain', {'type': 'null'}),
        'meaning': {'type': 'string', 'const': 'unchanged_selected_native_component_domain'},
        'domain_conversion': {'type': 'string', 'const': 'not_converted'},
    }), {'type': 'null'}]}


def _native_quantity(extraction, component):
    role = next((r for r, name in PRIMITIVES.items() if name == component), None)
    operand = extraction['operands'][role] if role is not None else None
    if operand is None:
        return None
    row = operand['row']
    return {'value': row.get('value'), 'source_unit': row.get('unit'),
        'threshold': row.get('threshold'), 'bound': row.get('bound', 'none'),
        'approximate': row.get('approximate'),
        'reported_domain': deepcopy(row.get('reported_domain')),
        'exact_domain': deepcopy(row.get('exact_domain')),
        'meaning': 'unchanged_selected_native_component_domain', 'domain_conversion': 'not_converted'}


def compiled_assay_cells_schema():
    return {**_array(obj({'sheet_ref': _ref(), 'evidence_source_ref': _ref(),
        'evaluation_scope': {'type': 'string', 'const': 'compiled_source_endpoint'},
        'component': {'type': 'string', 'enum': list(COMPONENTS)},
        **_numerical_cell()['properties'],
        'formula_code': {'type': 'string', 'enum': [name + '_compiled_v1' for name in COMPONENTS]},
        'dependencies': _array(_dependency()),
        'native_quantity': _native_quantity_schema(),
        'operand_meanings': obj({role: {'type': 'string', 'enum': [*LINKS[role], *LINK_LIMITS]} for role in ROLES}),
        'assay_meanings': obj({name: _text(True) for name in ASSAY_LITERAL_FIELDS}),
        'endpoint_kind': {'type': 'string', 'enum': list(ENDPOINTS)},
        'arrangement_kind': {'type': 'string', 'enum': list(ARRANGEMENTS)},
        'correction_stages': obj({name: {'type': 'string', 'enum': list(STAGE_VALUES)} for name in STAGES}),
        'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']},
        'observation_model': {'type': 'string', 'enum': ['none', 'known_normal_nonnegative_presence']},
        'covariance_source_ref': _ref(nullable=True),
        'residual_variance_source_ref': _ref(nullable=True),
        'operand_eligibility': obj({role: {'type': ['string', 'null'], 'enum': [None, *REASONS]} for role in ROLES}),
        'partial_uncertainty_status': {'type': 'string', 'const': 'unimplemented'},
        'covariance_input_status': {'type': 'string', 'enum': ['not_selected', 'selected_known', 'selected_estimated', 'selected_unknown']},
        'annotation_credit': {'type': 'null'}})), 'x-source': NAMESPACE}


def _project_saved(saved, reference, components):
    sheet, extraction = saved['sheet'], saved['extraction']
    meanings = {name: None if extraction['assay'][name] is None else extraction['assay'][name]['value'] for name in ASSAY_LITERAL_FIELDS}
    return [{'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'],
        'evaluation_scope': 'compiled_source_endpoint', 'component': name,
        **deepcopy(sheet['cells'][name]), 'formula_code': name + '_compiled_v1',
        'dependencies': deepcopy(sheet['dependencies'][name]), 'assay_meanings': deepcopy(meanings),
        'native_quantity': _native_quantity(extraction, name),
        'operand_meanings': {role: extraction['relationships'][role]['value'] for role in ROLES},
        'endpoint_kind': extraction['assay']['endpoint']['value'],
        'arrangement_kind': extraction['assay']['arrangement']['value'],
        'correction_stages': {stage: extraction['correction_stages'][stage]['value'] for stage in STAGES},
        'variance_status': extraction['variance_status'], 'observation_model': extraction['observation_model'],
        'covariance_source_ref': extraction['covariance_source']['source_ref'] if extraction['covariance_source'] else None,
        'residual_variance_source_ref': extraction['distinct_residual_observation']['witness']['source_ref'] if extraction['distinct_residual_observation'] else None,
        'operand_eligibility': deepcopy(sheet['operand_eligibility_reasons']),
        'partial_uncertainty_status': 'unimplemented',
        'covariance_input_status': 'not_selected' if extraction['covariance_source'] is None else 'selected_' + extraction['variance_status'],
        'annotation_credit': None}
        for name in components]


class LiteratureCompiledAssayRepository(LiteratureRateRepository):
    provider, components, record_version = PROVIDER, COMPONENTS, VERSION
    operations_table = 'literature_compiled_assay_operations'
    received_table = 'literature_compiled_assay_received'
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
        if not isinstance(components, (list, tuple)) or any(type(name) is not str or name not in COMPONENTS for name in components) or len(set(components)) != len(components):
            raise ContractError('compiled_assay_component_selection_invalid')
        return list(components)

    def _input_repository(self, namespace):
        if namespace == NS_ASSAY:
            from .literature_assay_storage import LiteratureAssayRepository
            cls = LiteratureAssayRepository
        elif namespace == NS_OPTICAL:
            from .literature_optical_storage import LiteratureOpticalRepository
            cls = LiteratureOpticalRepository
        elif namespace == NS_RECOVERY:
            from .literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
            cls = LiteratureCalibrationRecoveryRepository
        elif namespace == NS_ACTIVE:
            from .literature_active_site_storage import LiteratureActiveSiteRepository
            cls = LiteratureActiveSiteRepository
        elif namespace == NS_AMOUNT:
            from .literature_amount_storage import LiteratureAmountRepository
            cls = LiteratureAmountRepository
        elif namespace == NS_REPLICATE:
            from .literature_rate_replicate_storage import LiteratureRateReplicateRepository
            cls = LiteratureRateReplicateRepository
        elif namespace == NS_NATIVE:
            from .literature_rate_meaning_delivery import LiteratureRateSourceMeaningProjection
            cls = LiteratureRateSourceMeaningProjection
        else:
            raise ContractError('unsupported_compilation_namespace')
        return cls(self.store, self.run_id)

    def _ancestors(self, scope, references):
        refs = list(dict.fromkeys(references))
        for ref in refs:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in refs:
                    refs.append(parent)
        return refs

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments); validate_schema(args, compiled_assay_population_schema())
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
            for ref in saved['direct_input_source_refs']:
                self._native_source(context, ref)
            for selected in saved['component_selections']:
                if selected['sheet_ref'] not in context.received_record_refs:
                    raise ContractError('literature_sheet_not_received')
            return outcome
        source = self._native_source(context, args['source_ref'])
        snapshots = []; selected_refs = []
        def read_source(ref, representation):
            row = self._native_source(context, ref)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
        def component(selection):
            repo = self._input_repository(selection['namespace'])
            refs = [selection['sheet_ref']]
            if self.store.reference_subset(refs, plain(context.scope)) != refs:
                raise ContractError('literature_source_outside_scope')
            rows = repo.fact_cells(context, refs, components=[selection['component']])
            if len(rows) != 1:
                raise ContractError('selected_component_not_received')
            snapshots.append({'selection': deepcopy(selection), 'row': deepcopy(rows[0])})
            selected_refs.extend(refs)
            return rows
        def record(ref):
            if self.store.reference_subset([ref], plain(context.scope)) != [ref]:
                raise ContractError('literature_source_outside_scope')
            return self.store.get(ref)
        extraction = read_compiled_assay_inputs(args, read_source=read_source, read_component=component, read_record=record)
        sheet = populate_compiled_assay(extraction)
        direct = extraction['source_refs']; parents = self._ancestors(context.scope, [*direct, *selected_refs])
        metadata = {ref: self.store.get(ref) for ref in parents}
        payload = {'version': VERSION, 'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'],
            'direct_input_source_refs': direct, 'input_source_refs': parents, 'selection': args,
            'component_selections': [item['selection'] for item in snapshots], 'input_snapshots': snapshots,
            'source_metadata': metadata, 'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': req_ref, 'version': VERSION, 'retrieved_at': None,
                'parent_source_refs': parents}
            reference = identity('source', {'origin': 'tool', 'record': value})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (reference,)).fetchone()
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            rows = _project_saved(payload, reference, requested); validate_schema(rows, compiled_assay_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [reference],
                'changed_record_refs': [] if exists else [reference],
                'result': {'sheet_ref': reference, 'view': VIEW, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if 'artifact_' + hashlib.sha256(raw).hexdigest() != reference:
            raise ContractError('compiled_assay_saved_artifact_hash_mismatch')
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as error:
            raise ContractError('compiled_assay_saved_json_invalid') from error

    def read(self, reference):
        source = self.store.get(reference)
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        if source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER or source.get('version') != VERSION or identity('source', {'origin': 'tool', 'record': value}) != reference:
            raise ContractError('literature_compiled_assay_sheet_required')
        request = self._json(source['request_ref'])
        if set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments', 'scope', 'components'} or request['run_id'] != self.run_id:
            raise ContractError('compiled_assay_saved_request_mismatch')
        validate_schema(request['arguments'], compiled_assay_population_schema()); self._components(request['components'])
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('literature_sheet_not_selected_output')
        saved = self._json(source['artifact_ref'])
        expected_fields = {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs', 'input_source_refs',
            'selection', 'component_selections', 'input_snapshots', 'source_metadata', 'extraction', 'sheet'}
        if set(saved) != expected_fields or saved['version'] != VERSION or saved['selection'] != request['arguments'] or saved['input_source_ref'] != request['arguments']['source_ref'] or saved['input_source_refs'] != source['parent_source_refs']:
            raise ContractError('compiled_assay_saved_selection_mismatch')
        if self._ancestors(request['scope'], [*saved['direct_input_source_refs'], *(s['sheet_ref'] for s in saved['component_selections'])]) != saved['input_source_refs']:
            raise ContractError('compiled_assay_saved_source_mismatch')
        if any(canonical(self.store.get(ref)) != canonical(metadata) for ref, metadata in saved['source_metadata'].items()):
            raise ContractError('compiled_assay_saved_source_mismatch')
        if self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']:
            raise ContractError('compiled_assay_saved_source_mismatch')
        extraction = saved['extraction']
        if extraction['source_ref'] != saved['input_source_ref'] or extraction['artifact_ref'] != saved['input_artifact_ref'] or extraction['source_refs'] != saved['direct_input_source_refs'] or saved['sheet']['version'] != SHEET_VERSION or saved['sheet']['original_extraction'] != extraction:
            raise ContractError('compiled_assay_saved_extraction_mismatch')
        selected = [request['arguments']['operands'][role] for role in ROLES if request['arguments']['operands'][role] is not None]
        if selected != saved['component_selections'] or selected != [row['selection'] for row in saved['input_snapshots']]:
            raise ContractError('compiled_assay_saved_operand_mismatch')
        for snapshot in saved['input_snapshots']:
            validate_schema([snapshot['row']], source_schema(snapshot['selection']['namespace']))
            if snapshot['row']['sheet_ref'] != snapshot['selection']['sheet_ref'] or snapshot['row']['component'] != snapshot['selection']['component']:
                raise ContractError('compiled_assay_saved_operand_mismatch')
        for role in ROLES:
            operand = extraction['operands'][role]
            selection = request['arguments']['operands'][role]
            if (operand is None) != (selection is None) or operand is not None and (operand['selection'] != selection or operand['row'] != next(s['row'] for s in saved['input_snapshots'] if s['selection'] == selection)):
                raise ContractError('compiled_assay_saved_operand_mismatch')
        if set(saved['sheet']['cells']) != set(COMPONENTS) or set(saved['sheet']['dependencies']) != set(COMPONENTS):
            raise ContractError('compiled_assay_saved_component_mismatch')
        for name, cell in saved['sheet']['cells'].items():
            validate_schema(cell, _numerical_cell())
            if cell['section'] != SECTIONS[name] or cell['meaning'] != MEANINGS[name] or (cell['value'] is None) != (cell['status'] == 'unavailable') or (cell['unavailable_reason'] is None) != (cell['status'] == 'populated'):
                raise ContractError('compiled_assay_saved_cell_mismatch')
        rows = _project_saved(saved, reference, request['components']); validate_schema(rows, compiled_assay_cells_schema())
        outcome = json.loads(operation['outcome'])
        expected = {'sheet_ref': reference, 'view': VIEW, 'cells': rows}
        if outcome.get('status') != 'completed' or canonical(outcome.get('result')) != canonical(expected) or outcome.get('record_refs') != [reference] or outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']}):
            raise ContractError('compiled_assay_saved_outcome_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self._components(COMPONENTS if components is None else components)
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            rows.extend(_project_saved(self.read(ref), ref, selected))
        return rows

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

    def has_work(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        own = self.store.db.execute(f'SELECT 1 FROM {self.operations_table} WHERE run_id=? AND episode_id=? LIMIT 1',
            (self.run_id, context.episode_id)).fetchone() if self._installed(self.operations_table) else None
        received = self.store.db.execute(f'SELECT 1 FROM {self.received_table} WHERE run_id=? AND episode_id=? LIMIT 1',
            (self.run_id, context.episode_id)).fetchone() if self._installed(self.received_table) else None
        return bool(own or received)

    def owned_sheet_refs(self, context):
        if not self._installed(self.operations_table):
            return []
        return [json.loads(row['outcome'])['result']['sheet_ref'] for row in self.store.db.execute(
            f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))
            if json.loads(row['outcome'])['result']['sheet_ref'] in context.received_record_refs]

    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*self.owned_sheet_refs(context), *(r['sheet_ref'] for r in self.received_cells(context) if r['sheet_ref'] in context.received_record_refs)]))

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(ref for row in cells for ref in [row['sheet_ref'], row['evidence_source_ref'],
            *(d['selection']['sheet_ref'] for d in row['dependencies'] if d['selection'] is not None),
            *[row[name] for name in ('covariance_source_ref', 'residual_variance_source_ref') if row[name] is not None]]))


__all__ = ['LiteratureCompiledAssayRepository', 'compiled_assay_cells_schema', 'PROVIDER', 'VERSION',
    'NAMESPACE', 'REQUESTED', 'VIEW', 'COMPONENTS']
