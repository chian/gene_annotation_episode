"""Selected A105 product/cofactor views with authenticated, scoped custody.

Fresh population alone reads scientific source bytes and runs the frozen pure
reader/calculator. Saved reads check original records and structural bindings;
they do not parse source statistics or recalculate scientific components.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .library.literature_product_coupling_inputs import (
    CONTEXT_FIELDS, QUANTITY_MEANINGS, RELATIONSHIPS, NU_STATUSES, ORIGINS,
    product_coupling_population_schema, product_coupling_extraction_schema,
    read_product_coupling_inputs,
)
from .library.literature_product_coupling_calculations import (
    COMPONENTS, FORMULAS, QUALIFICATIONS, product_coupling_cell_schema,
    product_coupling_sheet_schema, populate_product_coupling,
)

from .library.literature_product_coupling_projection import (
    PROVIDER, VERSION, NAMESPACE, REQUESTED, VIEW, SCOPE, PROJECTION_VERSION, MODEL_COMPONENTS, UNCERTAINTY_COMPONENTS, _array, _ref, _nullable, _exact_schema, _location_schema, _meaning_schema, product_coupling_cells_schema, _locations, _meaning_v1, _meaning, _projection_policy, _project_saved,
)

_FROZEN = {
    'literature_product_coupling_inputs.py': 'fcf0115c9d9e98b362fa0ee51086d30a11efc5af5669a985f167100cb462f139',
    'literature_product_coupling_calculations.py': 'd7f99c4b12de0254e662250546526a2ef67ceb165e38099d839c7bde819cb25f',
    'literature_product_coupling_prompt.py': 'e520365b878325623f86a1874ce0454dc56f8ad35679e21fb5b45d26a36a3c8a',
}


class LiteratureProductCouplingRepository(LiteratureRateRepository):
    provider, record_version, components = PROVIDER, VERSION, COMPONENTS
    operations_table = 'literature_product_coupling_operations'
    received_table = 'literature_product_coupling_received'
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
    def _components(values):
        if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
                or len(set(values)) != len(values)):
            raise ContractError('product_coupling_component_selection_invalid')
        return list(values)

    def _ancestors(self, scope, references):
        result = list(dict.fromkeys(references))
        for ref in result:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in result:
                    result.append(parent)
        return result

    def _implementation_receipt(self):
        if __name__ == 'gene_annotation_episode.episodic_workflow.root.literature_product_coupling_storage':
            from .literature_product_kinetic_relocation import prospective
            return prospective('product_coupling')
        actual = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in _FROZEN}
        if actual != _FROZEN:
            raise ContractError('product_coupling_prospective_dependency_mismatch')
        return {'version': 'product_coupling_original_implementation_v1', 'files': actual}

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments); validate_schema(args, product_coupling_population_schema())
        requested = self._components(plain(context.assignment.get(REQUESTED, [])))
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key,
            'scope': plain(context.scope), 'arguments': args, 'components': requested, 'role': context.role,
            'assignment': plain(context.assignment), 'received_record_refs': list(context.received_record_refs)}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome']); self.read(outcome['result']['sheet_ref'])
            return outcome
        source = self._native_source(context, args['source_ref']); receipt = self._implementation_receipt()
        read_sizes = {}
        def read_source(ref, representation):
            row = self._native_source(context, ref)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            raw = self.store.get_artifact(artifact)
            if artifact != 'artifact_' + hashlib.sha256(raw).hexdigest():
                raise ContractError('product_coupling_source_artifact_hash_mismatch')
            read_sizes[(ref, representation)] = len(raw)
            return {'artifact_ref': artifact, 'content': raw}
        extraction = read_product_coupling_inputs(args, read_source=read_source)
        sheet = populate_product_coupling(extraction)
        direct = extraction['source_refs']; parents = self._ancestors(context.scope, direct)
        locations = _locations(extraction)
        cov = extraction['covariance']
        if cov['source_ref'] is not None and read_sizes[(cov['source_ref'], 'original')] > 0:
            locations.append({'source_ref': cov['source_ref'], 'artifact_ref': cov['artifact_ref'],
                'representation': 'original', 'start': 0, 'end': read_sizes[(cov['source_ref'], 'original')]})
        payload = {'version': VERSION, 'projection_version': PROJECTION_VERSION,
            'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'],
            'selection': args, 'direct_input_source_refs': direct, 'input_source_refs': parents,
            'source_metadata': {ref: self.store.get(ref) for ref in parents}, 'numerical_scope_locations': locations,
            'original_implementation': receipt, 'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': req_ref, 'version': VERSION, 'retrieved_at': None, 'parent_source_refs': parents}
            reference = identity('source', {'origin': 'tool', 'record': value})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (reference,)).fetchone()
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            rows = _project_saved(payload, reference, requested); validate_schema(rows, product_coupling_cells_schema())
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
            raise ContractError('product_coupling_saved_artifact_hash_mismatch')
        try:
            value = json.loads(raw)
        except (ValueError, TypeError) as error:
            raise ContractError('product_coupling_saved_json_invalid') from error
        if not isinstance(value, dict):
            raise ContractError('product_coupling_saved_object_required')
        return value

    def _validate_bindings(self, saved, request):
        """No scientific parsing/arithmetic: bind retained typed fields to selection."""
        e = saved['extraction']; args = request['arguments']; sheet = saved['sheet']
        validate_schema(e, product_coupling_extraction_schema()); validate_schema(sheet, product_coupling_sheet_schema())
        if (e['source_ref'] != saved['input_source_ref'] or e['artifact_ref'] != saved['input_artifact_ref']
                or e['source_kind'] != args['source_kind'] or e['source_refs'] != saved['direct_input_source_refs']
                or e['source_ref'] not in e['source_refs'] or len(set(e['source_refs'])) != len(e['source_refs'])
                or sheet['extraction'] != e or e['input_origins'] != [ORIGINS[args['source_kind']]]):
            raise ContractError('product_coupling_saved_extraction_mismatch')
        def witness(selected):
            source = self._native_provenance(request['scope'], selected['source_ref'])
            artifact = source['artifact_ref'] if selected['representation'] == 'original' else source.get('text_ref')
            if (artifact is None or selected['source_ref'] not in e['source_refs']
                    or selected['source_ref'] not in request['received_record_refs']
                    or selected['end'] - selected['start'] != len(selected['quote'].encode())):
                raise ContractError('product_coupling_saved_source_binding_mismatch')
            return {**deepcopy(selected), 'artifact_ref': artifact}
        def interpreted(selected):
            value = {'kind': 'source_interpretation', 'value': selected['value'],
                'witnesses': [witness(w) for w in selected['witnesses']]}
            spans = {(w['artifact_ref'], w['start'], w['end']) for w in value['witnesses']}
            required = 0 if selected['value'] == 'unknown' else 2 if selected['value'] == 'conflicting' else 1
            if len(spans) < required:
                raise ContractError('product_coupling_saved_interpretation_binding_mismatch')
            return value
        for name, selected in args['context'].items():
            expected = None if selected is None else {'value': selected['quote'], 'witness': witness(selected)}
            if e['context'][name] != expected:
                raise ContractError('product_coupling_saved_meaning_mismatch')
        for name, selected in args['relationships'].items():
            if e['relationships'][name] != interpreted(selected):
                raise ContractError('product_coupling_saved_relationship_mismatch')
        for role, selected in args['quantities'].items():
            item = e['quantities'][role]
            if (selected is None) != (item is None):
                raise ContractError('product_coupling_saved_quantity_mismatch')
            if selected is None:
                continue
            expected = {name: interpreted(selected[name]) for name in QUANTITY_MEANINGS}
            expected.update(quantity_label=None if selected['quantity_label'] is None else witness(selected['quantity_label']),
                physical_identity=None if selected['physical_identity'] is None else witness(selected['physical_identity']),
                dependency_witnesses=[witness(w) for w in selected['dependency_witnesses']])
            if any(item[name] != value for name, value in expected.items()):
                raise ContractError('product_coupling_saved_quantity_mismatch')
            if (selected['number'] is None) != (item['number'] is None) or (selected['unit'] is None) != (item['unit'] is None):
                raise ContractError('product_coupling_saved_quantity_mismatch')
            number = item['number']
            if number is not None:
                n = selected['number']; w = witness(n['witness']); a, b = n['number_start'], n['number_end']
                start, end = w['start']+len(w['quote'][:a].encode()), w['start']+len(w['quote'][:b].encode())
                key = identity('literature_measurement', {'artifact_ref': w['artifact_ref'], 'number_start': start, 'number_end': end})
                rep = number['representation_witness']
                if (number['selector'] != {**n, 'witness': w} or not 0 <= a < b <= len(w['quote'])
                        or number['raw_number'] != w['quote'][a:b] or number['measurement_key'] != key
                        or number['number_start_bytes'] != start or number['number_end_bytes'] != end
                        or number['origin'] != ORIGINS[args['source_kind']] or rep['artifact_ref'] != w['artifact_ref']
                        or rep['source_ref'] != w['source_ref'] or rep['representation'] != w['representation']
                        or not rep['start'] <= start < end <= rep['end']
                        or rep['quote'].encode()[start-rep['start']:end-rep['start']] != number['raw_number'].encode()):
                    raise ContractError('product_coupling_saved_number_binding_mismatch')
            if item['unit'] is not None and (item['unit']['witness'] != witness(selected['unit'])
                    or item['unit']['raw_unit'] != selected['unit']['quote']):
                raise ContractError('product_coupling_saved_unit_binding_mismatch')
            span_key = lambda w: identity('physical_source_span', {k: w[k] for k in ('artifact_ref', 'start', 'end')})
            deps = list(dict.fromkeys(([number['measurement_key']] if number else []) + [span_key(w) for w in item['dependency_witnesses']]))
            if item['dependency_keys'] != deps or item['physical_identity_key'] != (None if item['physical_identity'] is None else span_key(item['physical_identity'])):
                raise ContractError('product_coupling_saved_dependency_mismatch')
            cell_name = {'product': 'reported_product_activity', 'cofactor': 'reported_cofactor_activity', 'reported_coupling': 'reported_coupling_percent'}[role]
            cell = sheet['cells'][cell_name]
            if (cell['source_value'] != (None if number is None else number['native_value'])
                    or cell['source_exact_value'] != (None if number is None else number['native_exact_value'])
                    or cell['source_unit'] != (None if item['unit'] is None else item['unit']['raw_unit'])
                    or cell['native_measurement_semantics'] != item['measurement_semantics']['value']):
                raise ContractError('product_coupling_saved_native_binding_mismatch')
            available = (number is not None and number['capability_reason'] is None
                and item['unit'] is not None and item['unit']['unavailable_reason'] is None)
            if (cell['value'] != (item['canonical_value'] if available else None)
                    or cell['exact_value'] != (item['canonical_exact_value'] if available else None)
                    or cell['unit'] != item['canonical_unit'] or cell['input_measurement_keys'] != item['dependency_keys']):
                raise ContractError('product_coupling_saved_native_binding_mismatch')
        nu = e['nu_cofactor_per_product']; selected_nu = args['nu_cofactor_per_product']
        expected_nu = {**selected_nu, 'witnesses': [witness(w) for w in selected_nu['witnesses']]}
        spans = sorted({(w['artifact_ref'], w['start'], w['end']) for w in expected_nu['witnesses']})
        model = None if nu['exact_value'] is None else identity('product_coupling_stoichiometric_model',
            {'direction': nu['direction'], 'status': nu['status'], 'exact_value': nu['exact_value'],
             'witnesses': [{'artifact_ref': a, 'start': s, 'end': z} for a, s, z in spans]})
        if nu != {**expected_nu, 'model_key': model}:
            raise ContractError('product_coupling_saved_model_binding_mismatch')
        if ((nu['status'] == 'unknown' and nu['exact_value'] is not None)
                or nu['status'] in ('fixed_model', 'uncertain_model') and nu['exact_value'] is None
                or len(spans) < (0 if nu['status'] == 'unknown' else 2 if nu['status'] == 'conflicting' else 1)):
            raise ContractError('product_coupling_saved_model_binding_mismatch')
        covariance = e['covariance']; cov_ref = args['covariance_source_ref']
        if (covariance['source_ref'] != cov_ref or cov_ref is not None and
                (cov_ref not in e['source_refs'] or cov_ref not in request['received_record_refs']
                 or covariance['artifact_ref'] != saved['source_metadata'][cov_ref]['artifact_ref'])):
            raise ContractError('product_coupling_saved_covariance_binding_mismatch')
        if covariance['status'].startswith('valid_'):
            owners = [e['quantities'][role]['number']['measurement_key'] for role in ('product', 'cofactor')]
            if (covariance['measurement_keys'] != owners or covariance['units'] != ['per_min', 'per_min']
                    or covariance['basis'] != 'joint_covariance_of_selected_rate_estimates'
                    or covariance['status'] != 'valid_' + covariance['variance_status']
                    or covariance['unavailable_reason'] is not None):
                raise ContractError('product_coupling_saved_covariance_binding_mismatch')
        expected_locations = _locations(e)
        if cov_ref is not None:
            size = self.store.get(covariance['artifact_ref'])['size']
            if size > 0:
                expected_locations.append({'source_ref': cov_ref, 'artifact_ref': covariance['artifact_ref'],
                    'representation': 'original', 'start': 0, 'end': size})
        if saved['numerical_scope_locations'] != expected_locations:
            raise ContractError('product_coupling_saved_scope_locations_mismatch')
        def typed_numbers(value):
            if isinstance(value, dict):
                if set(value) == {'numerator', 'denominator'}:
                    validate_schema(value, _exact_schema())
                for child in value.values():
                    typed_numbers(child)
            elif isinstance(value, list):
                for child in value:
                    typed_numbers(child)
            elif isinstance(value, float) and not math.isfinite(value):
                raise ContractError('product_coupling_saved_nonfinite_number')
        typed_numbers(e); typed_numbers(sheet['cells'])
        if (sheet['cells']['reconstructed_product_activity']['contribution_key'] !=
                sheet['cells']['reported_product_activity']['contribution_key']
                and e['quantities']['product'] is not None and e['quantities']['product']['number'] is not None):
            raise ContractError('product_coupling_saved_contribution_mismatch')
        for name, cell in sheet['cells'].items():
            if cell['formula'] != FORMULAS[name]:
                raise ContractError('product_coupling_saved_formula_binding_mismatch')
            if name not in ('reported_product_activity', 'reported_cofactor_activity', 'reported_coupling_percent') and any(
                    cell[k] is not None for k in ('source_value', 'source_exact_value', 'source_unit', 'native_measurement_semantics')):
                raise ContractError('product_coupling_saved_derived_native_expansion')

    def read(self, reference):
        source = self.store.get(reference)
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER
                or source.get('version') != VERSION or identity('source', {'origin': 'tool', 'record': value}) != reference):
            raise ContractError('literature_product_coupling_sheet_required')
        request = self._json(source['request_ref'])
        if (set(request) != {'run_id', 'episode_id', 'operation_key', 'scope', 'arguments', 'components', 'role', 'assignment', 'received_record_refs'}
                or request['run_id'] != self.run_id or not all(isinstance(request[f], str) and request[f] for f in ('episode_id', 'operation_key', 'role'))
                or request['components'] != request['assignment'].get(REQUESTED, [])):
            raise ContractError('product_coupling_saved_request_mismatch')
        validate_schema(request['arguments'], product_coupling_population_schema()); self._components(request['components'])
        self._native_provenance(request['scope'], reference)
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('literature_sheet_not_selected_output')
        saved = self._json(source['artifact_ref'])
        original_keys = {'version', 'input_source_ref', 'input_artifact_ref', 'selection', 'direct_input_source_refs',
            'input_source_refs', 'source_metadata', 'numerical_scope_locations', 'original_implementation', 'extraction', 'sheet'}
        _projection_policy(saved)
        if (set(saved) not in (original_keys, original_keys | {'projection_version'})
                or saved['version'] != VERSION or saved['selection'] != request['arguments']
                or saved['input_source_ref'] != request['arguments']['source_ref'] or source['text_ref'] != source['artifact_ref']
                or saved['input_source_refs'] != source['parent_source_refs']
                or self._ancestors(request['scope'], saved['direct_input_source_refs']) != saved['input_source_refs']
                or set(saved['source_metadata']) != set(saved['input_source_refs'])
                or any(canonical(self._native_provenance(request['scope'], ref)) != canonical(row) for ref, row in saved['source_metadata'].items())
                or self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']
                or any(ref not in request['received_record_refs'] for ref in saved['direct_input_source_refs'])):
            raise ContractError('product_coupling_saved_source_mismatch')
        receipt = saved['original_implementation']
        if type(receipt) is dict and receipt.get('version') == 'root_product_coupling_implementation_v1':
            from .literature_product_kinetic_relocation import retained
            retained('product_coupling', receipt)
        elif receipt != {'version': 'product_coupling_original_implementation_v1', 'files': _FROZEN}:
            raise ContractError('product_coupling_saved_original_receipt_mismatch')
        self._validate_bindings(saved, request)
        rows = _project_saved(saved, reference, request['components']); validate_schema(rows, product_coupling_cells_schema())
        outcome = json.loads(operation['outcome'])
        if (outcome.get('status') != 'completed' or outcome.get('record_refs') != [reference] or outcome.get('feedback') is not None
                or canonical(outcome.get('result')) != canonical({'sheet_ref': reference, 'view': VIEW, 'cells': rows})
                or outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('product_coupling_saved_outcome_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = None if components is None else self._components(components); rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(ref); requested = self._json(self.store.get(ref)['request_ref'])['components']
            if selected is not None and any(name not in requested for name in selected):
                raise ContractError('product_coupling_component_not_selected')
            rows.extend(_project_saved(saved, ref, requested if selected is None else selected))
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, product_coupling_cells_schema()); seen = set()
        for row in cells:
            key = row['sheet_ref'], row['component']
            if key in seen:
                raise ContractError('duplicate_product_coupling_return_cell')
            seen.add(key)
            expected = self.project_cells([row['sheet_ref']], permitted_record_refs=permitted_record_refs, components=[row['component']])
            if len(expected) != 1 or canonical(row) != canonical(expected[0]):
                raise ContractError('product_coupling_return_differs_from_saved_cells')

    def fact_cells(self, context, sheet_refs, *, components):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        refs = list(dict.fromkeys(sheet_refs)); selected = self._components(components)
        if self.store.reference_subset(refs, plain(context.scope)) != refs:
            raise ContractError('literature_source_outside_scope')
        received = None; result = []
        for ref in refs:
            if ref not in context.received_record_refs:
                raise ContractError('literature_sheet_not_received')
            if self._sheet_owner(ref) == context.episode_id:
                requested = self._json(self.store.get(ref)['request_ref'])['components']
                result.extend(self.project_cells([ref], permitted_record_refs=context.received_record_refs,
                    components=[name for name in requested if name in selected]))
            else:
                if received is None:
                    received = self.received_cells(context)
                result.extend(deepcopy(row) for row in received if row['sheet_ref'] == ref and row['component'] in selected)
        return result

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        if not cells:
            return
        with self.store.transaction():
            self._install(); return super().receive_cells(context, cells, operation_key)

    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        refs = list(dict.fromkeys(json.loads(row['outcome'])['result']['sheet_ref'] for row in self.store.db.execute(
            f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))))
        for ref in refs:
            self.read(ref)
        return refs

    def owned_sheet_refs(self, context):
        return [ref for ref in self.selected_sheet_refs(context) if ref in context.received_record_refs]

    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*self.owned_sheet_refs(context), *(row['sheet_ref'] for row in self.received_cells(context)
            if row['sheet_ref'] in context.received_record_refs)]))

    def has_work(self, context):
        return bool(self.available_sheet_refs(context))

    @staticmethod
    def cell_record_refs(cells):
        result = []
        def visit(value):
            if isinstance(value, dict):
                for name, child in value.items():
                    if name.endswith('_ref') and isinstance(child, str) and child.startswith(('source_', 'artifact_')):
                        result.append(child)
                    elif name in ('source_scope',):
                        result.extend(child)
                    else:
                        visit(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    visit(child)
        visit(cells)
        return list(dict.fromkeys(result))


__all__ = ['LiteratureProductCouplingRepository', 'product_coupling_cells_schema',
    'PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'VIEW', 'COMPONENTS', 'SCOPE']
