"""Source-bound assay interpretation and numerical correction, without credit policy.

The episode assigns scientific meanings to exact source operands. This adapter
validates their custody and performs arithmetic; source quotation validation is
not a semantic proof of the episode's interpretation.
"""
from __future__ import annotations

import json
import math

from .communication import plain
from .domain import ContractError, canonical, identity
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = 'literature.a105.assay_population'
PRIMITIVE_CELLS = {'q': ('net_rate', 'uM/min'), 'g': ('contaminant_rate', 'uM/min'),
    'k': ('recovery', 'dimensionless'), 'E': ('protein_amount', 'uM'),
    'u': ('condition_test_rate', 'uM/min'), 'v': ('condition_reference_rate', 'uM/min')}
COMPONENTS = (*[row[0] for row in PRIMITIVE_CELLS.values()], 'attributed_rate', 'condition_response',
    'corrected_activity', 'effect_variance', 'effect_standard_uncertainty', 'effect_precision',
    'source_profile_log_ratio', 'source_presence_index')
BINDINGS = {'assay_ref': 'reference', 'assayed_subject_ref': 'reference', 'organism_ref': 'reference',
    'genotype_ref': 'reference', 'construct_ref': 'reference', 'preparation_ref': 'reference',
    'condition_ref': 'context', 'intended_variable_ref': 'reference', 'endpoint_ref': 'term', 'arrangement_ref': 'term',
    'covariance_source_ref': 'source', 'experimental_system_ref': 'reference',
    'expression_host_ref': 'reference', 'measured_entity_ref': 'reference',
    'asserted_input_ref': 'reference', 'asserted_output_ref': 'reference'}
REASONS = ('endpoint_requires_different_model', 'assayed_molecule_unresolved', 'source_endpoint_unresolved', 'source_endpoint_conflicting',
    'source_measurement_unavailable', 'correction_inputs_unreported', 'numerical_model_range',
    'primitive_covariance_unreported', 'distinct_residual_variance_unreported',
    'invalid_propagated_variance', 'positive_effect_variance_required',
    'known_variance_required', 'observation_model_unspecified')
CONDITIONS = ('source_role_assignments', 'first_order_covariance_propagation',
              'known_variance', 'known_normal_nonnegative_presence')


class LiteratureAssayRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = 'literature_assay_population_record_v1'
    operations_table = 'literature_assay_operations'
    received_table = 'literature_assay_received'
    binding_fields = tuple(BINDINGS)

    def populate(self, context, arguments, operation_key):
        from .literature_assay_inputs import read_assay_inputs
        from .literature_activity_calculations import populate_corrected_activity
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        signature = canonical({'arguments': args, 'scope': plain(context.scope)})
        # Recheck all original source custody on replay without parsing the
        # inputs again. A shared/global source is never receipt authorization.
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            for ref in self.read(outcome['result']['sheet_ref'])['input_source_refs']:
                self._received_source(context, ref)
            return outcome

        def read_source(reference, representation):
            source = self._received_source(context, reference)
            artifact = source['artifact_ref'] if representation == 'original' else source.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}

        extracted = read_assay_inputs(args, read_source=read_source)
        correction = populate_corrected_activity({key: extracted[key] for key in (
            'values', 'covariance', 'variance_status', 'distinct_residual_variance', 'observation_model')})
        scope_reason = ('assayed_molecule_unresolved' if extracted['assay']['molecule'] is None
            else 'source_endpoint_unresolved' if extracted['assay']['endpoint']['value'] == 'unknown'
            else 'source_endpoint_conflicting' if extracted['assay']['endpoint']['value'] == 'conflicting' else None)
        if scope_reason:
            for name in ('source_profile_log_ratio', 'source_presence_index'):
                correction['cells'][name].update(value=None, status='unavailable', unavailable_reason=scope_reason)
        # This correction is a concentration-rate/molecule-normalization model.
        # A phenotype, static abundance or affinity readout is a different model,
        # even if a caller nominates source numbers with compatible spelling.
        if extracted['assay']['endpoint']['value'] in {
                'growth', 'abundance', 'ligand_binding', 'other_measured_endpoint'}:
            for numeric_cell in correction['cells'].values():
                numeric_cell.update(value=None, status='unavailable',
                                    unavailable_reason='endpoint_requires_different_model')
        source = self._received_source(context, args['source_ref'])
        origin = {'synthetic_fixture': 'synthetic', 'graph_extraction': 'graph_derived',
                  'retained_extraction': 'derived'}.get(
            extracted['source_kind'], 'reported')
        def cell(value, unit, formula, *, reason=None, value_origin='derived'):
            if value is not None and not math.isfinite(value):
                value, reason = None, 'numerical_model_range'
            return {'value': value, 'unit': unit, 'formula': formula,
                'status': 'populated' if value is not None else 'unavailable',
                'origin': value_origin, 'unavailable_reason': reason,
                'conditional_on': ['source_role_assignments']}
        values = extracted['values']
        cells = {name: cell(values[role], unit, 'source_operand_' + role,
            reason='source_measurement_unavailable' if values[role] is None else None,
            value_origin=origin) for role, (name, unit) in PRIMITIVE_CELLS.items()}
        available = lambda *roles: all(values[role] is not None for role in roles)
        cells['attributed_rate'] = cell(values['q']-values['g'] if available('q','g') else None,
            'uM/min', 'q-g', reason=None if available('q','g') else 'correction_inputs_unreported')
        response = values['u']/values['v'] if available('u','v') else None
        response_reason = None if available('u','v') else 'correction_inputs_unreported'
        if response == 0:
            response, response_reason = None, 'numerical_model_range'
        cells['condition_response'] = cell(response, 'dimensionless', 'u/v', reason=response_reason)
        for name, row in correction['cells'].items():
            row['conditional_on'] = ['source_role_assignments', *row['conditional_on']]
            cells[name] = row
        payload = {'version': self.record_version, 'input_source_ref': args['source_ref'],
            'input_source_refs': extracted['source_refs'], 'input_artifact_ref': source['artifact_ref'],
            'interpretation_kind': 'episode_source_interpretation',
            'sheet': {'axis': 'A105', 'scope': 'interpreted_source_endpoint', 'extraction': extracted,
                'cells': cells, 'correction': correction, 'annotation_credit': None,
                'interpretation_limits': ['source_witness_validation_is_not_scientific_attribution_proof',
                    'source_endpoint_score_is_not_annotation_probability',
                    'condition_controls_exclude_the_deliberately_tested_variable',
                    'source_kind_is_a_declared_provenance_basis_not_verified_experimental_validity']}}
        with self.store.transaction():
            newly_created = []
            def publish(kind, record):
                candidate = identity(kind, {'origin': 'tool', 'record': record})
                existed = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (candidate,)).fetchone()
                row = self.store.put(kind, record, origin='tool', scope=plain(context.scope))
                if existed is None:
                    newly_created.append(row['id'])
                return row['id']
            def reference(field, literal):
                if literal is None:
                    return None
                return publish('reference', {'reference_type': 'literature_result',
                    'source_ref': literal['witness']['source_ref'],
                    'accession': identity('assay_literal', {'field': field, 'literal': literal}),
                    'label': literal['value'], 'sequence_ref': None, 'molecule': None,
                    'length': None, 'term_refs': [], 'context_refs': []})
            assay = extracted['assay']
            bindings = {field + '_ref': reference(field, assay[field]) for field in
                ('organism','genotype','construct','preparation','intended_variable','experimental_system',
                 'expression_host','measured_entity','asserted_input','asserted_output')}
            bindings['assayed_subject_ref'] = reference('molecule', assay['molecule'])
            bindings['assay_ref'] = publish('reference', {'reference_type': 'assay',
                'source_ref': args['source_ref'], 'accession': identity('interpreted_assay', {
                    'source': args['source_ref'], 'assay': assay}),
                'label': 'Source assay interpretation', 'sequence_ref': None, 'molecule': None,
                'length': None, 'term_refs': [], 'context_refs': []})
            condition = assay['condition']
            bindings['condition_ref'] = publish('context', {'context_type': 'assay_condition',
                'name': condition['value'], 'source_ref': condition['witness']['source_ref'],
                'attributes': [], 'related_refs': [bindings['assay_ref']]}) if condition else None
            for field in ('endpoint','arrangement'):
                value = assay[field]['value']
                bindings[field + '_ref'] = publish('term', {'namespace': 'literature_assay_' + field,
                    'accession': identity('assay_' + field, {'source': args['source_ref'], 'interpretation': assay[field]}),
                    'label': value, 'term_type': 'other', 'source_ref': args['source_ref'], 'anchor': None})
            bindings['covariance_source_ref'] = args['covariance_source_ref']
            measurement_bindings = {}
            for role, observation in {**extracted['primitive_observations'],
                    'distinct_residual_variance': extracted['distinct_residual_observation']}.items():
                if observation is None:
                    measurement_bindings[role] = None
                    continue
                witness = observation['witness']
                quote = witness['quote']
                start = witness['start'] + len(quote[:observation['number_start']].encode('utf-8'))
                end = witness['start'] + len(quote[:observation['number_end']].encode('utf-8'))
                measurement_bindings[role] = publish('reference', {'reference_type': 'literature_result',
                    'source_ref': witness['source_ref'], 'accession': observation['measurement_key'],
                    'label': observation['raw_number'], 'sequence_ref': None, 'molecule': None,
                    'length': None, 'term_refs': [], 'context_refs': [], 'anchor': {
                        'source_ref': witness['source_ref'], 'artifact_ref': witness['artifact_ref'],
                        'start': start, 'end': end, 'quote': observation['raw_number']}})
            payload['measurement_bindings'] = measurement_bindings
            payload['experimental_bindings'] = bindings
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request = self.store.artifact(canonical({'run_id': self.run_id, 'episode_id': context.episode_id,
                'operation_key': operation_key, 'arguments': args}), 'application/json')
            sheet_ref = publish('source', {'provider': self.provider, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
                'version': self.record_version, 'retrieved_at': None,
                'parent_source_refs': extracted['source_refs']})
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {
                'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}),
                'record_refs': [sheet_ref, *dict.fromkeys(ref for ref in (*bindings.values(), *measurement_bindings.values()) if ref)],
                'changed_record_refs': newly_created, 'result': {'sheet_ref': sheet_ref, 'cells': cells,
                    'assay_interpretation': assay, 'source_kind': extracted['source_kind'],
                    'interpretation_kind': payload['interpretation_kind'],
                    'primitive_observations': extracted['primitive_observations'],
                    'model_assumptions': {'variance_status': extracted['variance_status'],
                        'observation_model': extracted['observation_model'],
                        'covariance_origin': extracted.get('covariance_origin')}}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _received_source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError('literature_source_not_received')
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError('literature_source_outside_scope')
        row = self.store.get(reference)
        if row['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return row

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        rows = super().project_cells(sheet_refs, permitted_record_refs=permitted_record_refs, components=components)
        for row in rows:
            saved = self.read(row['sheet_ref'])
            extracted = saved['sheet']['extraction']
            dependency_roles = {'attributed_rate': ('q','g'), 'condition_response': ('u','v')}
            dependency_roles.update({name:(role,) for role,(name,_) in PRIMITIVE_CELLS.items()})
            roles = dependency_roles.get(row['component'], tuple(PRIMITIVE_CELLS))
            if row['component'] in {'effect_variance', 'effect_standard_uncertainty', 'effect_precision',
                    'source_profile_log_ratio', 'source_presence_index'}:
                roles = (*roles, 'distinct_residual_variance')
            row['input_measurement_refs'] = list(dict.fromkeys(saved['measurement_bindings'][role]
                for role in roles if saved['measurement_bindings'][role] is not None))
            row['interpretation_kind'] = 'episode_source_interpretation'
            row['evaluated_scope'] = 'interpreted_source_endpoint'
            row['endpoint_kind'] = extracted['assay']['endpoint']['value']
            row['arrangement_kind'] = extracted['assay']['arrangement']['value']
            row['operand_source_kind'] = extracted['source_kind']
            row['covariance_origin'] = extracted.get('covariance_origin')
        return rows


def assay_cells_schema():
    from .domain import obj
    from .literature_assay_inputs import ENDPOINTS, ARRANGEMENTS, SOURCE_KINDS
    reference = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    properties = {'sheet_ref': dict(reference), 'evidence_source_ref': dict(reference),
        'component': {'type': 'string', 'enum': list(COMPONENTS)},
        'value': {'type': ['number','null']},
        'input_measurement_refs': {'type':'array','uniqueItems':True,'items':{
            'type':'string','format':'reference','x-reference-namespace':'reference'}},
        'unit': {'type': 'string', 'enum': ['uM/min','uM','dimensionless','per_min','per_min_squared','min_squared']},
        'status': {'type': 'string', 'enum': ['populated','unavailable']},
        'origin': {'type': 'string', 'enum': ['reported','graph_derived','synthetic','derived','proposed']},
        'unavailable_reason': {'type': ['string','null'], 'enum': [None,*REASONS]},
        'conditional_on': {'type': 'array', 'uniqueItems': True, 'items': {'type':'string','enum':list(CONDITIONS)}},
        'interpretation_kind': {'type':'string','enum':['episode_source_interpretation']},
        'evaluated_scope': {'type':'string','enum':['interpreted_source_endpoint']},
        'endpoint_kind': {'type':'string','enum':list(ENDPOINTS)},
        'arrangement_kind': {'type':'string','enum':list(ARRANGEMENTS)},
        'operand_source_kind': {'type':'string','enum':list(SOURCE_KINDS)},
        'covariance_origin': {'type':['string','null'],'enum':[None,'reported','derived','synthetic']}}
    for name, namespace in BINDINGS.items():
        properties[name] = {'type':['string','null'], 'format':'reference','x-reference-namespace':namespace}
    return {'type':'array','items':obj(properties),'x-source':'literature_assay_cells'}
