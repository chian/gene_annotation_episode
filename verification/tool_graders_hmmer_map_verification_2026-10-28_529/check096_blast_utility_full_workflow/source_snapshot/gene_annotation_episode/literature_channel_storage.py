"""Selected electrical components, exact requested returns and saved custody.

Scientific source reading and arithmetic occur once at selected population.
Saved reads authenticate the original request, result and source associations;
they neither reopen scientific artifacts nor rerun their numerical conversion.
"""
from copy import deepcopy
import hashlib
import json
import re

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_channel_inputs import (
    VERSION as EXTRACTION_VERSION, SOURCE_KINDS, LITERAL_FIELDS, ARRANGEMENT_KINDS,
    SPREAD_KINDS, channel_population_schema, channel_extraction_schema,
    read_channel_inputs, channel_calculation_inputs,
)
from .literature_channel_calculations import (
    VERSION as SHEET_VERSION, PRIMITIVE_ORDER, QUANTITIES, CURRENT_KINDS,
    ARRANGEMENT_RELATIONS, COMPONENTS, UNITS, MEANINGS, SECTIONS,
    populate_channel_components,
)
from .literature_rate_storage import LiteratureRateRepository


PROVIDER = 'literature.a105.channel'
VERSION = 'literature_channel_record_v1'
NAMESPACE = 'literature_channel_cells'
REQUESTED = 'requested_channel_components'
VIEW = 'channel_components'
FORMULAS = {name: name for name in QUANTITIES}
FORMULAS.update(
    absolute_driving_voltage='abs(applied_voltage-reversal_voltage)',
    chord_conductance='1000*abs(current)/(abs(applied_voltage-reversal_voltage))',
    charge_equivalent_rate='abs(current)*1e-12/1.602176634e-19',
    chord_conductance_variance='J*covariance*J_transpose; J=[1000*sign(I)/abs(D),-1000*abs(I)*sign(D)/D^2,1000*abs(I)*sign(D)/D^2]; D=V-E',
    chord_conductance_standard_uncertainty='sqrt(chord_conductance_variance)',
)
COMPONENT_ROLES = {name: (name,) for name in QUANTITIES}
COMPONENT_ROLES.update(absolute_driving_voltage=PRIMITIVE_ORDER[1:],
    chord_conductance=PRIMITIVE_ORDER, charge_equivalent_rate=('current',),
    chord_conductance_variance=PRIMITIVE_ORDER,
    chord_conductance_standard_uncertainty=PRIMITIVE_ORDER)
CONDITIONS = ('reversal_condition_applicable_to_current_voltage',
    'defined_chord_not_differential_conductance', 'electrical_charge_equivalents_only',
    'first_order_covariance_propagation')
CELL_CONDITIONS = {name: [] for name in QUANTITIES}
CELL_CONDITIONS.update(absolute_driving_voltage=list(CONDITIONS[:1]),
    chord_conductance=list(CONDITIONS[:2]), charge_equivalent_rate=[CONDITIONS[2]],
    chord_conductance_variance=[*CONDITIONS[:2], CONDITIONS[3]],
    chord_conductance_standard_uncertainty=[*CONDITIONS[:2], CONDITIONS[3]])
REASONS = ('electrical_measurement_not_supplied', 'electrical_inputs_not_supplied',
    'numerical_model_range', 'different_electrical_arrangements',
    'reversal_condition_applicability_not_supplied', 'reversal_condition_applicability_conflicting',
    'current_kind_not_supplied', 'current_kind_conflicting', 'zero_driving_voltage',
    'absolute_current_not_differentiable_at_zero', 'primitive_covariance_not_supplied',
    'primitive_measurement_identity_not_supplied', 'primitive_variance_status_unknown')
INPUT_LIMITS = ('literal_custody_does_not_prove_applicability',
    'matching_conditions_do_not_merge_measurements', 'reported_spreads_are_not_covariance',
    'charge_equivalents_are_not_ion_flux', 'no_pore_normalization', 'no_replication_inference')
SHEET_LIMITS = ('no_ion_flux_attribution', 'no_pore_or_polypeptide_normalization',
    'no_independent_preparation_count', 'no_overall_reliability_grade', 'no_annotation_credit')
ORIGINS = ('reported', 'derived', 'graph_derived', 'synthetic')
_SOURCE_ORIGINS = dict(primary_source='reported', retained_extraction='derived',
    graph_extraction='graph_derived', synthetic_fixture='synthetic')
# A selected quotation can mention another electrical result that is not one
# of this selection's four operands (for example both reversal arrangements).
# These lexical locations mask display only; they supply no scientific value.
_ELECTRICAL_DISPLAY_TOKENS = re.compile(
    r'(?<![A-Za-z0-9_.])(?P<point>[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?)'
    r'(?:\s*±\s*(?P<spread>[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?))?'
    r'\s*(?:pA|nA|A|mV|V|pS|nS|S)(?![A-Za-z])')


def _enum(values, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string',
            'enum': [*values, None] if nullable else list(values)}


def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}


def _reference(namespace, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference',
            'x-reference-namespace': namespace}


def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}


def _witness_schema():
    return obj({'source_ref': _reference('source'), 'artifact_ref': _reference('artifact'),
        'representation': _enum(('original', 'text')), 'start': {'type': 'integer', 'minimum': 0},
        'end': {'type': 'integer', 'minimum': 1}, 'quote': {'type': 'string', 'minLength': 1}})


def _meaning_schema():
    return obj({'status': _enum(('selected', 'not_selected', 'withheld_electrical_operand')),
                'witness': _nullable(_witness_schema())})


def _interpretation_schema(values):
    return obj({'value': _enum(values), 'support': _array(_meaning_schema())})


def _reading_schema():
    return _nullable(obj({'number': _witness_schema(),
        'native_value': {'type': 'number'}, 'native_unit': {'type': 'string', 'minLength': 1},
        'canonical_unit': _enum(('pA', 'mV', 'pS')), 'origin': _enum(ORIGINS),
        'conversion_origin': _enum(ORIGINS)}))


def _cell_schema(component=None):
    def specified(mapping):
        return {'type': 'string', 'const': mapping[component]} if component else _enum(tuple(dict.fromkeys(mapping.values())))
    return obj({'value': {'type': ['number', 'null']}, 'unit': specified(UNITS),
        'status': _enum(('populated', 'unavailable')), 'formula': specified(FORMULAS),
        'origin': _enum(ORIGINS), 'unavailable_reason': _enum(REASONS, True),
        'section': specified(SECTIONS), 'meaning': specified(MEANINGS),
        'conditional_on': {'const': CELL_CONDITIONS[component]} if component else _array(_enum(CONDITIONS), True),
        'operand_roles': {'const': list(COMPONENT_ROLES[component])} if component else _array(_enum(QUANTITIES), True),
        'measurement_keys': _array({'type': 'string', 'minLength': 1}, True)})


def channel_cells_schema():
    operand = obj({'role': _enum(QUANTITIES), 'context': _meaning_schema(),
        'reading': _reading_schema(), 'spread_reading': _reading_schema(),
        'spread_kind': _interpretation_schema(SPREAD_KINDS),
        'measurement_key': {'type': ['string', 'null']}})
    return {**_array(obj({'sheet_ref': _reference('source'),
        'evidence_source_ref': _reference('source'),
        'evaluation_scope': {'type': 'string', 'const': 'source_electrical_activity'},
        'component': _enum(COMPONENTS), **_cell_schema()['properties'],
        'source_kind': _enum(SOURCE_KINDS),
        'source_meanings': obj({name: _meaning_schema() for name in LITERAL_FIELDS}),
        'arrangement_kind': _interpretation_schema(ARRANGEMENT_KINDS),
        'current_kind': _interpretation_schema(CURRENT_KINDS),
        'arrangement_relation': _interpretation_schema(ARRANGEMENT_RELATIONS),
        'operands': _array(operand), 'variance_status': _enum(('known', 'estimated', 'unknown')),
        'covariance_origin': _enum(('reported', 'derived', 'synthetic'), True),
        'covariance_source_ref': _reference('source', True),
        'replication_status': {'type': 'string', 'const': 'not_evaluated_by_this_component'},
        'interpretation_limits': {'const': [*INPUT_LIMITS, *SHEET_LIMITS]},
        'annotation_credit': {'type': 'null'}})), 'x-source': NAMESPACE}


def _location(number):
    selector = number['selector']; witness = selector['witness']
    return {'source_ref': witness['source_ref'], 'artifact_ref': witness['artifact_ref'],
        'representation': witness['representation'],
        'start': number['number_start_bytes'], 'end': number['number_end_bytes'],
        'quote': number['raw_number']}


def _project_saved(saved, reference, components):
    data = saved['extraction']; result = []
    for component in components:
        exposed = {component} if component in QUANTITIES else set()
        withheld = [_location(number) for role, item in data['measurements'].items()
            if role not in exposed and item is not None
            for number in (item['number'], item['spread']) if number is not None]
        allowed = [_location(number) for role, item in data['measurements'].items()
            if role in exposed and item is not None
            for number in (item['number'], item['spread']) if number is not None]
        def meaning(witness):
            if witness is None:
                return {'status': 'not_selected', 'witness': None}
            overlap = any(witness['artifact_ref'] == point['artifact_ref']
                and witness['start'] < point['end'] and witness['end'] > point['start'] for point in withheld)
            for match in _ELECTRICAL_DISPLAY_TOKENS.finditer(witness['quote']):
                for field in ('point', 'spread'):
                    if match.group(field) is None:
                        continue
                    start = witness['start'] + len(witness['quote'][:match.start(field)].encode('utf8'))
                    end = witness['start'] + len(witness['quote'][:match.end(field)].encode('utf8'))
                    if not any(point['artifact_ref'] == witness['artifact_ref'] and point['start'] == start
                            and point['end'] == end for point in allowed):
                        overlap = True
            return {'status': 'withheld_electrical_operand' if overlap else 'selected',
                    'witness': None if overlap else deepcopy(witness)}
        def interpreted(value):
            return {'value': value['value'], 'support': [meaning(w) for w in value['witnesses']]}
        def reading(number, item, role):
            if role not in exposed or number is None:
                return None
            multiplier = item['unit']['multiplier']
            return {'number': _location(number), 'native_value': number['native_value'],
                'native_unit': item['unit']['raw_unit'], 'canonical_unit': number['unit'],
                'origin': number['origin'], 'conversion_origin': number['origin']
                    if multiplier['numerator'] == multiplier['denominator'] else 'derived'}
        operands = []
        for role in COMPONENT_ROLES[component]:
            item = data['measurements'][role]
            operands.append({'role': role, 'context': meaning(item['context'] if item else None),
                'reading': reading(item['number'], item, role) if item else None,
                'spread_reading': reading(item['spread'], item, role) if item else None,
                'spread_kind': interpreted(item['spread_kind']) if item else {'value': 'unknown', 'support': []},
                'measurement_key': item['number']['measurement_key'] if item else None})
        result.append({'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'],
            'evaluation_scope': 'source_electrical_activity', 'component': component,
            **deepcopy(saved['sheet']['cells'][component]), 'source_kind': data['source_kind'],
            'source_meanings': {name: meaning(value['witness'] if value else None)
                                for name, value in data['literals'].items()},
            **{name: interpreted(data[name]) for name in ('arrangement_kind', 'current_kind', 'arrangement_relation')},
            'operands': operands, 'variance_status': data['variance_status'],
            'covariance_origin': data['covariance_origin'], 'covariance_source_ref': data['covariance_source_ref'],
            'replication_status': 'not_evaluated_by_this_component',
            'interpretation_limits': [*INPUT_LIMITS, *SHEET_LIMITS], 'annotation_credit': None})
    return result


class LiteratureChannelRepository(LiteratureRateRepository):
    provider, record_version, components = PROVIDER, VERSION, COMPONENTS
    operations_table = 'literature_channel_operations'
    received_table = 'literature_channel_received'
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
        if (not isinstance(values, (list, tuple)) or any(type(value) is not str or value not in COMPONENTS for value in values)
                or len(set(values)) != len(values)):
            raise ContractError('literature_channel_component_selection_invalid')
        return list(values)

    def _ancestors(self, scope, references):
        result = list(dict.fromkeys(references))
        for ref in result:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in result:
                    result.append(parent)
        return result

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments); validate_schema(args, channel_population_schema())
        requested = self._components(plain(context.assignment.get(REQUESTED, [])))
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key,
                   'scope': plain(context.scope), 'arguments': args, 'components': requested}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome']); saved = self.read(outcome['result']['sheet_ref'])
            for ref in saved['direct_input_source_refs']:
                self._native_source(context, ref)
            return outcome
        source = self._native_source(context, args['source_ref'])
        def read_source(ref, representation):
            row = self._native_source(context, ref)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
        extraction = read_channel_inputs(args, read_source=read_source)
        sheet = populate_channel_components(channel_calculation_inputs(extraction))
        direct = extraction['source_refs']; parents = self._ancestors(context.scope, direct)
        payload = {'version': VERSION, 'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'],
            'direct_input_source_refs': direct, 'input_source_refs': parents, 'selection': args,
            'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': req_ref, 'version': VERSION, 'retrieved_at': None,
                'parent_source_refs': parents}
            reference = identity('source', {'origin': 'tool', 'record': value})
            existed = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (reference,)).fetchone()
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            rows = _project_saved(payload, reference, requested); validate_schema(rows, channel_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [reference],
                'changed_record_refs': [] if existed else [reference],
                'result': {'sheet_ref': reference, 'view': VIEW, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if 'artifact_' + hashlib.sha256(raw).hexdigest() != reference:
            raise ContractError('channel_saved_artifact_hash_mismatch')
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, TypeError, ValueError) as error:
            raise ContractError('channel_saved_json_invalid') from error
        if not isinstance(value, dict):
            raise ContractError('channel_saved_object_required')
        return value

    def _validate_bindings(self, saved, request):
        args, data = request['arguments'], saved['extraction']
        validate_schema(data, channel_extraction_schema())
        if (data['version'] != EXTRACTION_VERSION or data['source_ref'] != saved['input_source_ref']
                or data['artifact_ref'] != saved['input_artifact_ref'] or data['source_kind'] != args['source_kind']
                or data['source_refs'] != saved['direct_input_source_refs']
                or data['interpretation_limits'] != list(INPUT_LIMITS)):
            raise ContractError('channel_saved_extraction_mismatch')
        def witness(selected):
            source = self._native_provenance(request['scope'], selected['source_ref'])
            artifact = source['artifact_ref'] if selected['representation'] == 'original' else source.get('text_ref')
            if (artifact is None or selected['source_ref'] not in data['source_refs']
                    or selected['end'] - selected['start'] != len(selected['quote'].encode('utf8'))):
                raise ContractError('channel_saved_source_binding_mismatch')
            return {**deepcopy(selected), 'artifact_ref': artifact}
        def interpreted(selected):
            result = {'kind': 'source_interpretation', 'value': selected['value'],
                      'witnesses': [witness(w) for w in selected['witnesses']]}
            unique = {(w['source_ref'], w['artifact_ref'], w['representation'], w['start'], w['end']) for w in result['witnesses']}
            if len(unique) < (2 if result['value'] == 'conflicting' else 0 if result['value'] == 'unknown' else 1):
                raise ContractError('channel_saved_interpretation_mismatch')
            return result
        for name in LITERAL_FIELDS:
            expected = None if args['literals'][name] is None else {'value': args['literals'][name]['quote'],
                'witness': witness(args['literals'][name])}
            if data['literals'][name] != expected:
                raise ContractError('channel_saved_literal_mismatch')
        for name in ('arrangement_kind', 'current_kind', 'arrangement_relation'):
            if data[name] != interpreted(args[name]):
                raise ContractError('channel_saved_interpretation_mismatch')
        for role in QUANTITIES:
            selected, item = args['measurements'][role], data['measurements'][role]
            if (selected is None) != (item is None):
                raise ContractError('channel_saved_measurement_mismatch')
            if selected is None:
                if any(data[field][role] is not None for field in ('values', 'exact_values', 'measurement_keys')):
                    raise ContractError('channel_saved_measurement_mismatch')
                continue
            if (item['unit']['witness'] != witness(selected['unit'])
                    or item['unit']['raw_unit'] != selected['unit']['quote']
                    or item['unit']['unit'] != UNITS[role]
                    or item['context'] != (witness(selected['context']) if selected['context'] else None)
                    or item['spread_kind'] != interpreted(selected['spread_kind'])):
                raise ContractError('channel_saved_measurement_mismatch')
            for name in ('number', 'spread'):
                number, chosen = item[name], selected[name]
                if (number is None) != (chosen is None):
                    raise ContractError('channel_saved_number_mismatch')
                if chosen is None:
                    continue
                enriched = {**deepcopy(chosen), 'witness': witness(chosen['witness'])}
                w = enriched['witness']; start, end = enriched['number_start'], enriched['number_end']
                begin = w['start'] + len(w['quote'][:start].encode('utf8'))
                finish = w['start'] + len(w['quote'][:end].encode('utf8'))
                key = identity('literature_measurement', {'artifact_ref': w['artifact_ref'], 'number_start': begin, 'number_end': finish})
                if (number['selector'] != enriched or not 0 <= start < end <= len(w['quote'])
                        or w['quote'][start:end] != number['raw_number'] or number['number_start_bytes'] != begin
                        or number['number_end_bytes'] != finish or number['measurement_key'] != key
                        or number['unit'] != UNITS[role] or number['origin'] != _SOURCE_ORIGINS[data['source_kind']]):
                    raise ContractError('channel_saved_number_mismatch')
            if any(data[field][role] != item['number'][source_field] for field, source_field in (
                    ('values', 'value'), ('exact_values', 'exact_value'), ('measurement_keys', 'measurement_key'))):
                raise ContractError('channel_saved_measurement_mismatch')
        if (data['variance_status'] != args['variance_status']
                or data['variance_witnesses'] != [witness(w) for w in args['variance_witnesses']]
                or data['covariance_source_ref'] != args['covariance_source_ref']):
            raise ContractError('channel_saved_covariance_binding_mismatch')
        if data['covariance_source_ref'] is None:
            if data['covariance'] is not None or data['covariance_origin'] is not None:
                raise ContractError('channel_saved_covariance_binding_mismatch')
        elif data['covariance_source_ref'] not in data['source_refs']:
            raise ContractError('channel_saved_covariance_binding_mismatch')
        inputs = {name: deepcopy(data[name]) for name in ('values', 'exact_values', 'measurement_keys', 'covariance', 'variance_status')}
        inputs.update(current_kind=data['current_kind']['value'], arrangement_relation=data['arrangement_relation']['value'],
                      origin=_SOURCE_ORIGINS[data['source_kind']])
        sheet = saved['sheet']
        if (set(sheet) != {'version', 'primitive_order', 'inputs', 'cells', 'interpretation_limits'}
                or sheet['version'] != SHEET_VERSION or sheet['primitive_order'] != list(PRIMITIVE_ORDER)
                or sheet['inputs'] != inputs or sheet['interpretation_limits'] != list(SHEET_LIMITS)
                or set(sheet['cells']) != set(COMPONENTS)):
            raise ContractError('channel_saved_sheet_mismatch')
        for component, cell in sheet['cells'].items():
            validate_schema(cell, _cell_schema(component))
            expected_keys = list(dict.fromkeys(data['measurement_keys'][role] for role in COMPONENT_ROLES[component]
                if data['measurement_keys'][role] is not None))
            if ((cell['value'] is None) != (cell['status'] == 'unavailable')
                    or (cell['unavailable_reason'] is None) != (cell['status'] == 'populated')
                    or cell['measurement_keys'] != expected_keys):
                raise ContractError('channel_saved_cell_mismatch')
            if component in QUANTITIES:
                if cell['value'] != data['values'][component] or cell['origin'] != _SOURCE_ORIGINS[data['source_kind']]:
                    raise ContractError('channel_saved_native_value_mismatch')
            elif cell['origin'] != 'derived':
                raise ContractError('channel_saved_cell_origin_mismatch')
            if component in ('chord_conductance_variance', 'chord_conductance_standard_uncertainty') and cell['value'] is not None:
                if cell['value'] < 0 or data['covariance'] is None or data['variance_status'] == 'unknown':
                    raise ContractError('channel_saved_uncertainty_mismatch')

    def read(self, reference):
        source = self.store.get(reference)
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool'
                or source.get('provider') != PROVIDER or source.get('version') != VERSION
                or identity('source', {'origin': 'tool', 'record': value}) != reference):
            raise ContractError('literature_channel_sheet_required')
        request = self._json(source['request_ref'])
        if (set(request) != {'run_id', 'episode_id', 'operation_key', 'scope', 'arguments', 'components'}
                or request['run_id'] != self.run_id):
            raise ContractError('channel_saved_request_mismatch')
        validate_schema(request['arguments'], channel_population_schema()); self._components(request['components'])
        if any(type(request[field]) is not str or not request[field] for field in ('episode_id', 'operation_key')):
            raise ContractError('channel_saved_request_mismatch')
        self._native_provenance(request['scope'], reference)
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('literature_sheet_not_selected_output')
        saved = self._json(source['artifact_ref'])
        if (set(saved) != {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs',
                'input_source_refs', 'selection', 'extraction', 'sheet'}
                or saved['version'] != VERSION or saved['selection'] != request['arguments']
                or saved['input_source_ref'] != request['arguments']['source_ref']
                or saved['input_source_refs'] != source.get('parent_source_refs')
                or source.get('text_ref') != source['artifact_ref']
                or self._ancestors(request['scope'], saved['direct_input_source_refs']) != saved['input_source_refs']
                or self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']):
            raise ContractError('channel_saved_source_mismatch')
        self._validate_bindings(saved, request)
        rows = _project_saved(saved, reference, request['components']); validate_schema(rows, channel_cells_schema())
        outcome = json.loads(operation['outcome'])
        if (outcome.get('status') != 'completed' or outcome.get('record_refs') != [reference]
                or outcome.get('feedback') is not None
                or canonical(outcome.get('result')) != canonical({'sheet_ref': reference, 'view': VIEW, 'cells': rows})
                or outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id,
                    'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('channel_saved_outcome_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = None if components is None else self._components(components)
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(ref)
            requested = self._json(self.store.get(ref)['request_ref'])['components']
            if selected is not None and any(name not in requested for name in selected):
                raise ContractError('literature_channel_component_not_selected')
            rows.extend(_project_saved(saved, ref, requested if selected is None else selected))
        return rows

    def fact_cells(self, context, sheet_refs, *, components):
        refs = list(dict.fromkeys(sheet_refs))
        selected = self._components(components)
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if self.store.reference_subset(refs, plain(context.scope)) != refs:
            raise ContractError('literature_source_outside_scope')
        received = None
        result = []
        for ref in refs:
            if ref not in context.received_record_refs:
                raise ContractError('literature_sheet_not_received')
            owner = self._sheet_owner(ref)
            if owner == context.episode_id:
                requested = self._json(self.store.get(ref)['request_ref'])['components']
                result.extend(self.project_cells([ref], permitted_record_refs=context.received_record_refs,
                    components=[name for name in selected if name in requested]))
            else:
                if received is None:
                    received = {(row['sheet_ref'], row['component']): row for row in self.received_cells(context)}
                result.extend(deepcopy(received[(ref, name)]) for name in selected if (ref, name) in received)
        return result

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install(); return super().receive_cells(context, cells, operation_key)

    def selected_sheet_refs(self, context):
        """Host receipt roster used to refresh a stale reporting context."""
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        refs = list(dict.fromkeys(json.loads(row['outcome'])['result']['sheet_ref'] for row in self.store.db.execute(
            f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid',
            (self.run_id, context.episode_id))))
        for ref in refs:
            self.read(ref)
        return refs

    def owned_sheet_refs(self, context):
        return [ref for ref in self.selected_sheet_refs(context) if ref in context.received_record_refs]

    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*self.owned_sheet_refs(context),
            *(row['sheet_ref'] for row in self.received_cells(context) if row['sheet_ref'] in context.received_record_refs)]))

    def has_work(self, context):
        return bool(self.available_sheet_refs(context))

    @staticmethod
    def cell_record_refs(cells):
        result = []
        def witnesses(value):
            if isinstance(value, dict):
                if set(value) == {'source_ref', 'artifact_ref', 'representation', 'start', 'end', 'quote'}:
                    result.extend((value['source_ref'], value['artifact_ref']))
                else:
                    for child in value.values():
                        witnesses(child)
            elif isinstance(value, list):
                for child in value:
                    witnesses(child)
        for row in cells:
            result.extend((row['sheet_ref'], row['evidence_source_ref']))
            if row['covariance_source_ref'] is not None:
                result.append(row['covariance_source_ref'])
            witnesses(row)
        return list(dict.fromkeys(result))


__all__ = ['LiteratureChannelRepository', 'channel_cells_schema', 'PROVIDER', 'VERSION',
    'NAMESPACE', 'REQUESTED', 'VIEW', 'COMPONENTS']
