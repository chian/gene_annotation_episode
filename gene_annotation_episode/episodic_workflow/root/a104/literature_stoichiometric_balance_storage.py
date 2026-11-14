"""Selected source-bound CcCdP balance section of the single A105 worksheet."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_stoichiometric_balance_inputs import (
    stoichiometric_balance_population_schema, read_stoichiometric_balance_inputs)
from .literature_stoichiometric_balance_calculations import (
    COMPONENTS, populate_stoichiometric_balance_components)

PROVIDER = 'literature.a105.stoichiometric_balance_population'
VERSION = 'literature_stoichiometric_balance_record_v1'
NAMESPACE = 'literature_stoichiometric_balance_cells'
REQUESTED = 'requested_stoichiometric_balance_components'


def stoichiometric_balance_cells_schema():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    artifact = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'artifact'}
    text = {'type': 'string'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj({
        'sheet_ref': ref, 'evidence_source_ref': ref, 'workbook_artifact_ref': artifact,
        'component': {'type': 'string', 'enum': list(COMPONENTS)},
        'evaluation_scope': {'const': 'source_soluble_product_stoichiometric_balance'},
        'value': {'type': 'number'}, 'exact_decimal': text,
        'unit': {'type': 'string', 'enum': ['mM', 'fraction']},
        'status': {'const': 'point'},
        'origin': {'enum': ['source_time_zero_nominal_matching', 'reported_mean', 'reported_sd', 'calculated']},
        'meaning': text, 'formula': text,
        'source_cell_addresses': {'type': 'array', 'minItems': 1, 'items': text},
        'input_measurement_keys': {'type': 'array', 'minItems': 1, 'items': text},
        'panel': {'const': 'D'}, 'sheet_name': {'const': 'Data'},
        'assayed_molecule': {'const': 'Cellodextrin phosphorylase from Clostridium cellulosi'},
        'construct_status': {'const': 'not_reported_in_workbook'},
        'expression_host': {'type': 'null'},
        'row_number': {'type': 'integer', 'minimum': 53},
        'time_minutes': {'type': 'number', 'minimum': 0},
        'reaction_conditions': obj({
            'nominal_donor_mM': {'type': 'number'},
            'nominal_acceptor_mM': {'type': 'number'},
            'enzyme_U_per_mL': {'type': 'number'},
            'MES_mM': {'type': 'number'},
            'pH': {'type': 'number'},
            'temperature_C': {'type': 'number'}}),
        'calibration_source_cell': {'const': 'Metadata!A22'},
        'one_pi_per_transfer_source_cell': {'const': 'Metadata!A29'},
        'one_pi_per_transfer_premise': text,
        'pi_method_source_cell': {'const': 'Metadata!A23'},
        'reported_sd_basis': {'const': 'duplicate_reactions'},
        'initial_baseline_status': {'const': 'source_printed_zero_measurement_and_detection_limit_unestablished'},
        'ratio_sd': {'type': 'null'}, 'ratio_se': {'type': 'null'},
        'ratio_confidence_interval': {'type': 'null'}, 'joint_covariance': {'type': 'null'},
        'matched_no_enzyme_arm': {'type': 'null'},
        'independent_preparation_count': {'type': 'null'},
        'molecule_specific_attribution': {'type': 'null'},
        'assay_validity_multiplier': {'type': 'null'},
        'annotation_credit': {'type': 'null'}})}


def _rows(saved, sheet_ref, components):
    e, s = saved['extraction'], saved['sheet']
    conditions = e['conditions']
    reaction_conditions = {
        'nominal_donor_mM': float(conditions['aGlc1-P']['value']['exact_decimal']),
        'nominal_acceptor_mM': float(conditions['Cellobiose (G2)']['value']['exact_decimal']),
        'enzyme_U_per_mL': float(conditions['Cellodextrin phosphorylase from Clostridium cellulosi']['value']['exact_decimal']),
        'MES_mM': float(conditions['MES buffer']['value']['exact_decimal']),
        'pH': float(conditions['pH']['value']['exact_decimal']),
        'temperature_C': float(conditions['Temperature']['value']['exact_decimal'])}
    return [{'sheet_ref': sheet_ref, 'evidence_source_ref': e['source_ref'],
        'workbook_artifact_ref': saved['input_artifact_ref'],
        'component': component, 'evaluation_scope': s['evaluation_scope'],
        **deepcopy(s['cells'][component]),
        'panel': e['panel'], 'sheet_name': e['sheet_name'],
        'assayed_molecule': e['assayed_molecule'],
        'construct_status': e['construct_status'],
        'expression_host': e['expression_host'],
        'row_number': e['row_number'], 'time_minutes': e['time_minutes'],
        'reaction_conditions': reaction_conditions,
        'calibration_source_cell': e['calibration_source_cell'],
        'one_pi_per_transfer_source_cell': e['model_premise']['source_cell'],
        'one_pi_per_transfer_premise': e['model_premise']['meaning'],
        'pi_method_source_cell': e['pi_method']['source_cell'],
        'reported_sd_basis': 'duplicate_reactions',
        'initial_baseline_status': e['initial_baseline_status'],
        'ratio_sd': s['ratio_sd'], 'ratio_se': s['ratio_se'],
        'ratio_confidence_interval': s['ratio_confidence_interval'],
        'joint_covariance': s['joint_covariance'],
        'matched_no_enzyme_arm': s['matched_no_enzyme_arm'],
        'independent_preparation_count': s['independent_preparation_count'],
        'molecule_specific_attribution': s['molecule_specific_attribution'],
        'assay_validity_multiplier': s['assay_validity_multiplier'],
        'annotation_credit': s['annotation_credit']}
        for component in components]


class LiteratureStoichiometricBalanceRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION
    operations_table = 'literature_stoichiometric_balance_operations'
    received_table = 'literature_stoichiometric_balance_received'
    binding_fields = ()

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, stoichiometric_balance_population_schema())
        request = {'run_id': self.run_id, 'episode_id': context.episode_id,
            'operation_key': operation_key, 'arguments': args, 'scope': plain(context.scope)}
        signature = canonical(request)
        old = (self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone()
            if self._installed(self.operations_table) else None)
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            self.read(outcome['result']['sheet_ref'])
            self._native_source(context, args['source_ref'])
            return outcome
        source = self._native_source(context, args['source_ref'])
        extraction = read_stoichiometric_balance_inputs(args, self.store.get_artifact(source['artifact_ref']))
        sheet = populate_stoichiometric_balance_components(extraction)
        payload = {'version': VERSION, 'input_source_ref': args['source_ref'],
            'input_artifact_ref': source['artifact_ref'], 'selection': args,
            'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(canonical(request), 'application/json')
            record = {'provider': PROVIDER, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
                'version': VERSION, 'retrieved_at': None,
                'parent_source_refs': [args['source_ref']]}
            sheet_ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (sheet_ref,)).fetchone()
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = _rows(payload, sheet_ref, COMPONENTS)
            validate_schema(rows, stoichiometric_balance_cells_schema())
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
            raise ContractError('stoichiometric_balance_saved_hash_mismatch')
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError('stoichiometric_balance_saved_json_required') from error
        if not isinstance(value, dict):
            raise ContractError('stoichiometric_balance_saved_object_required')
        return value

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool'
                or source.get('provider') != PROVIDER or source.get('version') != VERSION):
            raise ContractError('stoichiometric_balance_sheet_required')
        record = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != sheet_ref:
            raise ContractError('stoichiometric_balance_saved_source_identity_mismatch')
        request = self._artifact_json(source['request_ref'])
        if request.get('run_id') != self.run_id or set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments', 'scope'}:
            raise ContractError('stoichiometric_balance_saved_selection_mismatch')
        original_scope = self.store.validate_scope(request['scope'])
        self._native_provenance(original_scope, sheet_ref)
        operation = (self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
            if self._installed(self.operations_table) else None)
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('stoichiometric_balance_saved_operation_mismatch')
        outcome = json.loads(operation['outcome'])
        saved = self._artifact_json(source['artifact_ref'])
        validate_schema(saved['selection'], stoichiometric_balance_population_schema())
        if (set(saved) != {'version', 'input_source_ref', 'input_artifact_ref', 'selection', 'extraction', 'sheet'}
                or saved['version'] != VERSION or saved['selection'] != request['arguments']
                or saved['input_source_ref'] != request['arguments']['source_ref']
                or saved['extraction']['source_ref'] != saved['input_source_ref']
                or saved['extraction']['workbook_sha256'] != saved['selection']['expected_sha256']
                or source['parent_source_refs'] != [saved['input_source_ref']]
                or self._native_provenance(original_scope, saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']
                or outcome.get('status') != 'completed'
                or outcome.get('result', {}).get('sheet_ref') != sheet_ref
                or outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id,
                    'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('stoichiometric_balance_saved_selection_mismatch')
        rows = _rows(saved, sheet_ref, COMPONENTS)
        validate_schema(rows, stoichiometric_balance_cells_schema())
        if canonical(rows) != canonical(outcome['result']['cells']):
            raise ContractError('stoichiometric_balance_saved_cells_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = COMPONENTS if components is None else components
        if (not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected)
                or any(c not in COMPONENTS for c in selected)):
            raise ContractError('stoichiometric_balance_component_selection_invalid')
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            rows.extend(_rows(self.read(ref), ref, selected))
        return rows

    def received_cells(self, context):
        return super().received_cells(context) if self._installed(self.received_table) else []

    def available_sheet_refs(self, context):
        refs = []
        for ref in context.received_record_refs:
            try:
                row = self.store.get(ref)
            except (LookupError, ContractError):
                continue
            if row.get('record_type') == 'source' and row.get('provider') == PROVIDER and row.get('version') == VERSION:
                self.read(ref)
                refs.append(ref)
        return list(dict.fromkeys(refs))

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(ref for row in cells for ref in
            (row['sheet_ref'], row['evidence_source_ref'], row['workbook_artifact_ref'])))


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'COMPONENTS',
    'LiteratureStoichiometricBalanceRepository', 'stoichiometric_balance_cells_schema']
