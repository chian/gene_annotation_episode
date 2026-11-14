"""Original product-coupling schemas and scoped saved-value projection."""
from copy import deepcopy
import re
from gene_annotation_episode.domain import ContractError, obj
from .literature_product_coupling_inputs import (
    CONTEXT_FIELDS, QUANTITY_MEANINGS, RELATIONSHIPS, NU_STATUSES, ORIGINS,
    product_coupling_extraction_schema,
)
from .literature_product_coupling_calculations import (
    COMPONENTS, QUALIFICATIONS, product_coupling_cell_schema,
)

PROVIDER = 'literature.a105.product_coupling'
VERSION = 'literature_product_coupling_record_v1'
NAMESPACE = 'literature_product_coupling_cells'
from gene_annotation_episode.episodic_workflow.root.library.literature_product_coupling_metadata import REQUESTED
VIEW = 'product_coupling_components'
from gene_annotation_episode.episodic_workflow.root.library.literature_product_coupling_metadata import SCOPE
PROJECTION_VERSION = 'product_coupling_projection_v2'
MODEL_COMPONENTS = frozenset(('productive_fraction', 'calculated_coupling_percent',
    'displayed_coupling_difference_pp', 'productive_fraction_variance',
    'productive_fraction_standard_uncertainty'))
UNCERTAINTY_COMPONENTS = frozenset(('product_per_cofactor_variance',
    'productive_fraction_variance', 'productive_fraction_standard_uncertainty'))
def _array(schema):
    return {'type': 'array', 'items': deepcopy(schema)}


def _ref(nullable=False, namespace='source'):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference',
        'x-reference-namespace': namespace}


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': r'^-?[0-9]+$'},
        'denominator': {'type': 'string', 'pattern': r'^[1-9][0-9]*$'}})


def _location_schema():
    return obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'),
        'representation': {'enum': ['original', 'text']},
        'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})


def _meaning_schema():
    return _nullable(obj({**_location_schema()['properties'],
        'display_text': {'type': 'string', 'minLength': 1},
        'status': {'enum': ['selected', 'unrequested_numbers_withheld', 'numerical_scope_unresolved']},
        'unavailable_reason': {'enum': ['unrequested_numerical_scope_unresolved', None]}}))


def product_coupling_cells_schema():
    interpreted = lambda values: obj({'value': {'enum': list(values)}, 'support': _array(_meaning_schema())})
    quantity = _nullable(obj({'label': _meaning_schema(), 'unit': _meaning_schema(),
        **{name: interpreted(values) for name, values in QUANTITY_MEANINGS.items()},
        'measurement_key': {'type': ['string', 'null']},
        'physical_identity_key': {'type': ['string', 'null']},
        'physical_identity': _meaning_schema(), 'dependency_support': _array(_meaning_schema())}))
    model = _nullable(obj({'kind': {'const': 'interpreted_reaction_account'},
        'direction': {'const': 'cofactor_per_product'}, 'status': {'enum': list(NU_STATUSES)},
        'exact_value': _nullable(_exact_schema()), 'model_key': {'type': ['string', 'null']},
        'support': _array(_meaning_schema())}))
    covariance_fields = product_coupling_extraction_schema()['properties']['covariance']['properties']
    covariance = _nullable(obj({name: deepcopy(value) for name, value in covariance_fields.items()
        if name != 'matrix_exact'}))
    row = obj({**product_coupling_cell_schema()['properties'],
        'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'const': SCOPE},
        'component': {'enum': list(COMPONENTS)}, 'source_kind': {'enum': list(ORIGINS)},
        'source_meanings': obj({name: _meaning_schema() for name in CONTEXT_FIELDS}),
        'quantity_meanings': obj({role: quantity for role in ('product', 'cofactor', 'reported_coupling')}),
        'relationships': obj({name: interpreted(values) for name, values in RELATIONSHIPS.items()}),
        'reaction_account': model, 'covariance': covariance,
        'source_scope': _array(_ref()), 'withheld_locations': _array(_location_schema()),
        'model_support_locations': _array(_location_schema()),
        'qualifications': {'const': list(QUALIFICATIONS)}})
    return {'type': 'array', 'items': row, 'x-source': NAMESPACE}


def _locations(extraction):
    return [{**{name: item['number']['selector']['witness'][name]
                for name in ('source_ref', 'artifact_ref', 'representation')},
             'start': item['number']['number_start_bytes'], 'end': item['number']['number_end_bytes']}
        for role in ('product', 'cofactor', 'reported_coupling')
        if (item := extraction['quantities'][role]) is not None and item['number'] is not None]


_VISIBLE_NUMBER = re.compile(r'(?<![A-Za-z0-9_.])[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'
    r'(?:[eE][+−-]?[0-9]+)?(?![A-Za-z0-9_.])')
# A narrow literal condition can keep its actual numeric setting. This is a
# presentation grammar, not a claim to identify arbitrary numbers in prose.
_SETTING_NUMBER = r'[0-9]+(?:\.[0-9]+)?'
_SETTING = (r'(?:pH\s*'+_SETTING_NUMBER+r'|(?:at\s*|temperature\s*)?'+_SETTING_NUMBER
    +r'\s*(?:°?C|K)|(?:in\s*)?(?:buffer\s*)?'+_SETTING_NUMBER
    +r'\s*(?:mM|µM|μM|uM|nM|M)(?:\s+[A-Za-z][A-Za-z0-9()-]*)?)')
_CONDITION = re.compile(r'\s*'+_SETTING+r'(?:\s*(?:at|and|,|;)\s*'+_SETTING+r')*\s*[.]?\s*', re.I)
_STATISTICAL_PREFIX = re.compile(r'\b(?:SD|SEM|SE|mean|CV|variance|uncertainty|CI|activity|rate|turnover|coupling)\b', re.I)


def _meaning_v1(witness, locations, *, unit=False, condition=False):
    """Exact markerless saved-display policy from the immutable218pin001."""
    if witness is None:
        return None
    raw = witness['quote'].encode(); flags = [False] * len(raw)
    for location in locations:
        if (location['artifact_ref'] == witness['artifact_ref']
                and witness['start'] < location['end'] and location['start'] < witness['end']):
            a = max(witness['start'], location['start']) - witness['start']
            b = min(witness['end'], location['end']) - witness['start']
            flags[a:b] = [True] * (b-a)
    chunks, start = [], 0
    while start < len(raw):
        end = start+1
        while end < len(raw) and flags[end] == flags[start]:
            end += 1
        chunks.append('[unrequested numerical operand]' if flags[start] else raw[start:end].decode())
        start = end
    shown = ''.join(chunks)
    visible = re.sub(r'<[^>]+>', ' ', shown)
    numeric = bool(_VISIBLE_NUMBER.search(visible))
    # Known operand coordinates are masked even inside same-artifact aliases.
    # Unknown table/prose statistics are withheld as a partial projection. Only
    # separately selected bounded literal conditions and units bypass this.
    safe_literal = unit or bool(condition and not _STATISTICAL_PREFIX.search(visible)
        and _CONDITION.fullmatch(visible))
    unresolved = numeric and not safe_literal
    if re.search(r'<(?:table|tr|td|th)\b', witness['quote'], re.I) and numeric:
        unresolved = True
    # Preserve molecule/product definitions and nonnumeric qualifications even
    # when the broad witness cannot classify its remaining numbers. This is a
    # redacted display, not invented source positions or a reconstructed quote.
    partial = ('[Mixed numerical source context retained; requested operand scope unresolved.] '
        + _VISIBLE_NUMBER.sub('[unclassified numerical context withheld]', visible))
    return {**{name: witness[name] for name in ('source_ref', 'artifact_ref', 'representation', 'start', 'end')},
        'display_text': partial if unresolved else shown,
        'status': 'numerical_scope_unresolved' if unresolved else 'unrequested_numbers_withheld' if any(flags) else 'selected',
        'unavailable_reason': 'unrequested_numerical_scope_unresolved' if unresolved else None}


# A bounded chemical identifier is not an assay value. This increment supports
# the position/stereochemical camphor-product names in the retained207case;
# neither arbitrary digit-prefixed prose nor numerical ranges qualify.
_CHEMICAL_NAME = re.compile(r'(?<![A-Za-z0-9_])[0-9]+(?:,[0-9]+)*-'
    r'(?:(?:exo|endo|cis|trans|R|S)-)?(?:hydroxy|oxo|amino|deoxy)camphor(?![A-Za-z0-9_])', re.I)
_STATISTIC_NUMBER = re.compile(r'(\b(?:SD|SEM|SE|mean|CV|variance|uncertainty|CI|activity|rate|turnover|coupling)'
    r'\s*[:=]?\s*)([+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?)', re.I)
_UNIT_ADJACENT_NUMBER = re.compile(r'(?<![A-Za-z0-9_.])[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'
    r'(?:[eE][+−-]?[0-9]+)?(?=(?:mM|µM|μM|uM|nM|M|percent|%)(?![A-Za-z0-9_]))', re.I)


def _meaning(witness, locations, *, unit=False, condition=False):
    """New projection policy; preserve bounded chemical names, redact statistics."""
    if witness is None:
        return None
    # Coordinate masking follows the original artifact/span policy. Classify
    # that display afresh; the v1 helper's already redacted display cannot be
    # used here because chemical locants must still be available.
    raw = witness['quote'].encode(); flags = [False] * len(raw)
    for location in locations:
        if (location['artifact_ref'] == witness['artifact_ref']
                and witness['start'] < location['end'] and location['start'] < witness['end']):
            a = max(witness['start'], location['start']) - witness['start']
            b = min(witness['end'], location['end']) - witness['start']
            flags[a:b] = [True] * (b-a)
    chunks, start = [], 0
    while start < len(raw):
        end = start+1
        while end < len(raw) and flags[end] == flags[start]:
            end += 1
        chunks.append('[unrequested numerical operand]' if flags[start] else raw[start:end].decode())
        start = end
    shown = ''.join(chunks); visible = re.sub(r'<[^>]+>', ' ', shown)
    chemical = []
    def protect(match):
        # Alphabet-only placeholder cannot masquerade as a statistic or model
        # value. It is restored solely to this exact matched source substring.
        token = 'CHEMICALLOCANT' + chr(0xE000+len(chemical))
        chemical.append((token, match.group()))
        return token
    protected = _CHEMICAL_NAME.sub(protect, visible)
    numeric = bool(_VISIBLE_NUMBER.search(protected) or _STATISTIC_NUMBER.search(protected)
        or _UNIT_ADJACENT_NUMBER.search(protected))
    safe_literal = unit or bool(condition and not _STATISTICAL_PREFIX.search(visible)
        and _CONDITION.fullmatch(visible))
    unresolved = numeric and not safe_literal
    if re.search(r'<(?:table|tr|td|th)\b', witness['quote'], re.I) and numeric:
        unresolved = True
    display = shown
    if unresolved:
        redacted = _STATISTIC_NUMBER.sub(lambda match: match.group(1)+'[unclassified numerical context withheld]', protected)
        redacted = _UNIT_ADJACENT_NUMBER.sub('[unclassified numerical context withheld]', redacted)
        redacted = _VISIBLE_NUMBER.sub('[unclassified numerical context withheld]', redacted)
        for token, original in chemical:
            redacted = redacted.replace(token, original)
        display = '[Mixed numerical source context retained; requested operand scope unresolved.] ' + redacted
    return {**{name: witness[name] for name in ('source_ref', 'artifact_ref', 'representation', 'start', 'end')},
        'display_text': display, 'status': 'numerical_scope_unresolved' if unresolved else
            'unrequested_numbers_withheld' if any(flags) else 'selected',
        'unavailable_reason': 'unrequested_numerical_scope_unresolved' if unresolved else None}


def _projection_policy(saved):
    if 'projection_version' not in saved:
        return _meaning_v1
    if saved['projection_version'] != PROJECTION_VERSION:
        raise ContractError('product_coupling_saved_projection_version_unsupported')
    return _meaning


def _project_saved(saved, reference, components):
    data = saved['extraction']; locations = saved['numerical_scope_locations']
    policy = _projection_policy(saved)
    meaning = lambda w: policy(w, locations)
    interpreted = lambda v: {'value': v['value'], 'support': [meaning(w) for w in v['witnesses']]}
    quantities = {}
    for role, item in data['quantities'].items():
        quantities[role] = None if item is None else {
            'label': meaning(item['quantity_label']),
            'unit': None if item['unit'] is None else policy(item['unit']['witness'], locations,
                unit=item['unit']['canonical_unit'] is not None),
            **{name: interpreted(item[name]) for name in QUANTITY_MEANINGS},
            'measurement_key': None if item['number'] is None else item['number']['measurement_key'],
            'physical_identity_key': item['physical_identity_key'],
            'physical_identity': meaning(item['physical_identity']),
            'dependency_support': [meaning(w) for w in item['dependency_witnesses']]}
    metadata = {'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'],
        'evaluation_scope': SCOPE, 'source_kind': data['source_kind'],
        'source_meanings': {name: None if value is None else policy(value['witness'], locations,
            condition=name in ('product_conditions', 'cofactor_conditions'))
            for name, value in data['context'].items()},
        'quantity_meanings': quantities,
        'relationships': {name: interpreted(value) for name, value in data['relationships'].items()},
        'source_scope': deepcopy(saved['input_source_refs']), 'withheld_locations': deepcopy(locations),
        'model_support_locations': [{name: w[name] for name in
            ('source_ref', 'artifact_ref', 'representation', 'start', 'end')}
            for w in data['nu_cofactor_per_product']['witnesses']],
        'qualifications': list(QUALIFICATIONS)}
    rows = []
    for name in components:
        nu = data['nu_cofactor_per_product']
        model = None if name not in MODEL_COMPONENTS else {
            **{key: deepcopy(nu[key]) for key in ('kind', 'direction', 'status', 'exact_value', 'model_key')},
            'support': [meaning(w) for w in nu['witnesses']]}
        covariance = None if name not in UNCERTAINTY_COMPONENTS else {
            key: deepcopy(value) for key, value in data['covariance'].items() if key != 'matrix_exact'}
        rows.append({**deepcopy(metadata), 'component': name, **deepcopy(saved['sheet']['cells'][name]),
            'reaction_account': model, 'covariance': covariance})
    return rows


