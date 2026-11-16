"""Read and authenticate received A105 grading sheets for A104 correspondence.

The frozen schemas are the original A105 v1/v2 contracts. This reader performs
no A105 population or grading and writes no repository state.
"""
from copy import deepcopy
from functools import cache
from hashlib import sha256
import json
from pathlib import Path

from .communication import plain
from .domain import ContractError, canonical, identity, validate_schema


@cache
def _contracts():
    return json.loads(Path(__file__).with_name(
        'a104_assay_grading_contracts.json').read_text())


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
        'source_log_evidence_ratio': _contracts()['criteria_by_type'][sheet['assay_type']],
    }
    predictive = tuple(name for name in _contracts()['criteria_by_type'][sheet['assay_type']]
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


class A104AssayGradingReader:
    provider = 'literature.a105.assay_grading'
    record_version = 'literature_assay_grading_record_v2'
    operations_table = 'literature_assay_grading_operations'
    rows = staticmethod(_rows)

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _native_provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('literature_source_outside_scope')
        source = self.store.get(reference)
        if source['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return source

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
                or source.get('provider') != self.provider or source.get('version') != self.record_version):
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
        contracts = _contracts()
        validate_schema(saved['selection'], contracts['population_schema'])
        if 'experiment_ref' not in saved['selection']:
            raise ContractError('assay_grading_saved_experiment_missing')
        validate_schema(saved['extraction'], contracts['input_schema'])
        validate_schema(saved['sheet'], contracts['sheet_schema'])
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
        validate_schema(rows, contracts['cells_schema'])
        if canonical(rows) != canonical(outcome['result']['cells']):
            raise ContractError('assay_grading_saved_cells_mismatch')
        return saved
