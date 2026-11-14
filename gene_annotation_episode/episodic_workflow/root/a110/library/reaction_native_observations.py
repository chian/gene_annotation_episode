"""Independently requested native A110 observations over one saved sheet.

Native observations are source operands, not scoring components. Aggregate-only
forms never acquire them. Saved projection reads no scientific source bytes.
"""
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population_contracts import BINDINGS
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_native_inputs import RATIO_BASES, COUNT_BASES, UNCERTAINTY_KINDS, TRACE_VERSION
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_meanings import _witness_label
NAMESPACE = 'literature_reaction_native_observations'
POSITIONS_FIELD = 'requested_reaction_native_positions'

def positions_schema():
    return {'type': 'array', 'uniqueItems': True, 'items': {'anyOf': [{'type': 'integer', 'minimum': 0}, {'type': 'string', 'const': 'all'}]}}

def native_observations_schema():

    def ref(kind, nullable=False):
        return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': kind}
    number = {'type': ['number', 'null']}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj({**{name: ref('source') for name in ('sheet_ref', 'evidence_source_ref', 'data_source_ref')}, **{field: ref(kind, True) for field, (_, kind) in BINDINGS.items()}, 'observation_position': {'type': 'integer', 'minimum': 0}, 'measurement_ref': ref('reference'), 'resource_ref': ref('reference', True), 'source_number_refs': {'type': 'array', 'items': ref('reference')}, 'basis_refs': {'type': 'array', 'items': ref('reference')}, 'count_basis_refs': {'type': 'array', 'items': ref('reference')}, 'uncertainty_basis_refs': {'type': 'array', 'items': ref('reference')}, 'count_number_ref': ref('reference', True), 'uncertainty_number_ref': ref('reference', True), 'source_unit_ref': ref('reference', True), 'operand_role': {'type': 'string', 'enum': ['ratio_summary', 'ratio_observation', 'resource_value', 'resource_lower', 'resource_upper']}, 'value': dict(number), 'reported_value': dict(number), 'numerator_value': dict(number), 'denominator_value': dict(number), 'unit': {'type': 'string', 'enum': ['mol_per_mol', 'signal_per_signal', 'umol', 'uM', 'umol_per_min', 'uM_per_min']}, 'source_unit': {'type': ['string', 'null'], 'enum': [None, 'pmol', 'nmol', 'umol', 'mmol', 'nM', 'uM', 'mM', *[u + '/' + t for u in ('pmol', 'nmol', 'umol', 'mmol', 'nM', 'uM', 'mM') for t in ('s', 'min')]]}, 'ratio_kind': {'type': ['string', 'null'], 'enum': [None, 'product_pair', 'formed_per_consumed', 'formed_per_supplied', 'signal_ratio']}, 'ratio_form': {'type': 'string', 'enum': ['reported_point', 'normalized_reported_pair', 'not_extracted', 'not_ratio']}, 'measurement_basis': {'type': ['string', 'null'], 'enum': [None, *RATIO_BASES]}, 'reported_count': {'type': ['integer', 'null'], 'minimum': 1}, 'count_basis': {'type': 'string', 'enum': list(COUNT_BASES)}, 'independent_n': {'type': ['integer', 'null'], 'minimum': 1}, 'uncertainty_kind': {'type': 'string', 'enum': list(UNCERTAINTY_KINDS)}, 'uncertainty_value': {**number, 'minimum': 0}, 'transformation': {'type': 'string', 'enum': ['identity', 'normalize_reported_pair', 'unit_conversion', 'not_extracted']}, 'evaluation_scope': {'type': 'string', 'const': 'native_reference_reaction_operands'}, 'measurement_corrections': {'type': 'string', 'const': 'not_applied'}, 'origin': {'type': 'string', 'enum': ['reported', 'graph_derived', 'synthetic']}})}

def publish_native_observations(extraction, scientific_bindings, semantic_bindings, publish):
    """Publish exact source anchors and declared operand roles, without inference."""
    trace = extraction['native_evidence']
    inputs = extraction['calculation_inputs']
    data_ref = extraction['arguments']['data_source_ref']
    rows = []

    def reference(witness, role, fallback=None):
        if witness is None and fallback is None:
            return None
        anchor = None if witness is None else {key: witness[key] for key in ('source_ref', 'artifact_ref', 'start', 'end', 'quote')}
        return publish('reference', {'reference_type': 'literature_result', 'source_ref': data_ref if witness is None else witness['source_ref'], 'accession': identity('reaction_literal', {'native_role': role, 'anchor': anchor, 'fallback': fallback if witness is None else None}), 'label': 'Not extracted ' + role if witness is None else _witness_label(witness['quote']), 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [], 'anchor': anchor})

    def number_witness(number):
        selector = number['selector']
        witness = selector['witness']
        start = witness['start'] + len(witness['quote'][:selector['number_start']].encode())
        return {**witness, 'start': start, 'end': start + len(number['raw_number'].encode()), 'quote': number['raw_number']}

    def number_ref(number, role):
        return None if number is None else reference(number_witness(number), role)

    def measurement_witness(numbers):
        if not numbers:
            return None
        first, last = (number_witness(numbers[0]), number_witness(numbers[-1]))
        if len(numbers) == 1:
            return first
        outer = numbers[0]['selector']['witness']
        raw = outer['quote'].encode()
        return {**outer, 'start': first['start'], 'end': last['end'], 'quote': raw[first['start'] - outer['start']:last['end'] - outer['start']].decode()}

    def witnesses(values, role):
        return list(dict.fromkeys((reference(value, role) for value in values)))

    def base(role, measurement, value, unit):
        return {'evidence_source_ref': extraction['arguments']['source_ref'], 'data_source_ref': data_ref, **deepcopy(scientific_bindings), 'observation_position': len(rows), 'measurement_ref': measurement, 'resource_ref': None, 'source_number_refs': [], 'basis_refs': [], 'count_basis_refs': [], 'uncertainty_basis_refs': [], 'count_number_ref': None, 'uncertainty_number_ref': None, 'source_unit_ref': None, 'operand_role': role, 'value': value, 'reported_value': None, 'numerator_value': None, 'denominator_value': None, 'unit': unit, 'source_unit': None, 'ratio_kind': None, 'ratio_form': 'not_ratio', 'measurement_basis': None, 'reported_count': None, 'count_basis': 'unknown', 'independent_n': None, 'uncertainty_kind': 'unreported', 'uncertainty_value': None, 'transformation': 'not_extracted', 'evaluation_scope': 'native_reference_reaction_operands', 'measurement_corrections': 'not_applied', 'origin': inputs['ratio']['origin'] if role.startswith('ratio') else inputs['budget']['origin']}
    ratio = trace['ratio']
    if ratio is not None:
        items = [('ratio_summary', ratio['summary']['ratio'], ratio['summary'], [])] if ratio['summary'] is not None else [('ratio_observation', item['ratio'], None, item['basis_witnesses']) for item in ratio['observations']]
        for role, expression, summary, design in items:
            numbers = [] if expression is None else [expression['number']] if expression['number'] is not None else [expression['numerator'], expression['denominator']]
            witness = measurement_witness(numbers)
            row = base(role, reference(witness, 'reported reaction measurement', len(rows)), None if expression is None else expression['value'], inputs['ratio']['unit'])
            row.update(ratio_kind=inputs['ratio']['ratio_kind'], measurement_basis=ratio['measurement_basis'], basis_refs=witnesses([*ratio['basis_witnesses'], *design], 'ratio interpretation basis'), source_number_refs=[number_ref(number, 'reported ratio operand') for number in numbers], ratio_form='not_extracted' if expression is None else expression['form'])
            if expression is not None:
                paired = expression['form'] == 'normalized_reported_pair'
                row.update(reported_value=None if paired else expression['number']['value'], numerator_value=expression['numerator']['value'] if paired else None, denominator_value=expression['denominator']['value'] if paired else None, transformation='normalize_reported_pair' if paired else 'identity')
            if summary is not None:
                spread, count = (summary['uncertainty'], summary['count'])
                row.update(reported_count=count['reported_n'], count_basis=count['basis'], independent_n=inputs['ratio']['independent_n'], uncertainty_kind=spread['kind'], uncertainty_value=None if spread['number'] is None else spread['number']['value'], count_number_ref=number_ref(count['number'], 'reported repetition count'), uncertainty_number_ref=number_ref(spread['number'], 'reported ratio uncertainty'), count_basis_refs=witnesses(count['basis_witnesses'], 'repetition interpretation basis'), uncertainty_basis_refs=witnesses(spread['basis_witnesses'], 'uncertainty interpretation basis'))
            rows.append(row)
    if trace['budget'] is not None:
        resource_refs = {raw['resource_key']: meaning['resource_ref'] for raw, meaning in zip(extraction['observations']['budget']['resources'], semantic_bindings['resources'])}
        for resource in trace['budget']['resources']:
            for role in ('value', 'lower', 'upper'):
                quantity = resource[role]
                if quantity is None:
                    continue
                number, unit = (quantity['number'], quantity['unit'])
                row = base('resource_' + role, reference(number_witness(number), 'reported resource measurement'), quantity['value'], unit['canonical_unit'])
                raw_unit = unit['native_unit']
                row.update(resource_ref=resource_refs[resource['resource_key']], reported_value=number['value'], source_number_refs=[number_ref(number, 'reported resource operand')], source_unit_ref=reference(unit['witness'], 'reported resource unit'), source_unit=raw_unit, transformation='identity' if unit['multiplier'] == 1 else 'unit_conversion')
                rows.append(row)
    return rows

def native_row_references(rows):
    result = []
    for row in rows:
        for key, value in row.items():
            if key.endswith('_ref') and value is not None:
                result.append(value)
            elif key.endswith('_refs'):
                result.extend(value)
    return list(dict.fromkeys(result))
