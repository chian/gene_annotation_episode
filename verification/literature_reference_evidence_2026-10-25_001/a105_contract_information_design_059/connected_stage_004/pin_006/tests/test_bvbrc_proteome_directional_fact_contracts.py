"""Finite selector/form semantics and exact nonfloating numeric transport."""
from copy import deepcopy
from decimal import localcontext, Inexact, Rounded, ROUND_DOWN
import ast
from pathlib import Path

import pytest

from gene_annotation_episode import bvbrc_proteome_directional_fact_contracts as c
from gene_annotation_episode import bvbrc_proteome_fact_contracts as legacy
from gene_annotation_episode.bvbrc_proteome_returns import proteome_fact_sources
from gene_annotation_episode.communication import validate_closed_schema


def all_selections():
    selections = {}
    for kind, schema in c.SELECTORS.items():
        for branch in schema.get('oneOf', [schema]):
            props = branch['properties']
            varying = 'metric' if 'metric' in props else 'collection' if 'collection' in props else None
            for metric in props[varying]['enum'] if varying else [None]:
                for member in props['member']['enum'] if 'member' in props else [None]:
                    value = {}
                    for name, node in props.items():
                        if 'const' in node: value[name] = node['const']
                        elif name == varying: value[name] = metric
                        elif name == 'member': value[name] = member
                        elif 'enum' in node: value[name] = node['enum'][0]
                        else: value[name] = {'document_id': 'd', 'query_ordinal': 1, 'hsp_ordinal': 1, 'limit': 2}.get(name, 0)
                    key = '_'.join(str(value[k]) for k in ('kind', 'scope', 'metric', 'collection', 'member', 'layer') if k in value)
                    selections[key] = value
                    if kind == 'directional_issues':
                        selections[key + '_numerical'] = {**value, 'layer': 'numerical'}
    return selections


@pytest.mark.parametrize('selection', list(all_selections().values()))
def test_every_finite_variant_and_metric_is_canonical(selection):
    assert c.validate_directional_selector(selection) == selection
    form = c.requested_form_schema_v2({'selected': selection})
    assert c.validate_requested_form_v2(form) == form
    loose = deepcopy(form)
    loose['properties']['selected']['additionalProperties'] = True
    with pytest.raises(ValueError): c.validate_requested_form_v2(loose)


@pytest.mark.parametrize('extra', [{'report_ordinal': 0}, {'pointer': '/queries/1'}, {'subject_id': 'P0AAW1'},
    {'metric': 'unknown'}, {'document_id': ' '}, {'query_ordinal': True}, {'hsp_ordinal': -1}])
def test_selector_cannot_choose_arbitrary_json_or_ambiguous_identity(extra):
    value = dict(kind='directional_native_decimal', scope='hsp', document_id='d',
        query_ordinal=1, subject_ordinal=0, hsp_ordinal=1, metric='expect')
    with pytest.raises(ValueError): c.validate_directional_selector({**value, **extra})


@pytest.mark.parametrize('offset,limit', [(-1, 1), (0, 0), (0, -1), (True, 1), (0, True)])
def test_page_requires_explicit_nonnegative_offset_positive_limit(offset, limit):
    with pytest.raises(ValueError): c.validate_directional_selector(dict(kind='directional_columns', scope='block',
        document_id='d', query_ordinal=0, subject_ordinal=0, hsp_ordinal=0, block_ordinal=0, offset=offset, limit=limit))


@pytest.mark.parametrize('text,expected', [
    ('1e-900', (0, [1], -900)), ('2e-66', (0, [2], -66)), ('0.0', (0, [0], 0)),
    ('-0.000', (0, [0], 0)), ('+001.2300e-4', (0, [1, 2, 3], -6)), ('-12.50', (1, [1, 2, 5], -1)),
    ('0.881666666666666667', (0, [int(v) for v in '881666666666666667'], -18))])
def test_exact_decimals_ignore_caller_precision_exponents_and_traps(text, expected):
    answer = dict(zip(('sign', 'digits', 'exponent'), expected))
    with localcontext() as ctx:
        ctx.prec, ctx.Emin, ctx.Emax, ctx.rounding = 2, -9, 9, ROUND_DOWN
        ctx.traps[Inexact] = ctx.traps[Rounded] = True
        assert c.exact_decimal(text) == answer


@pytest.mark.parametrize('text', ['', 'nan', 'inf', 'e-179', '1,000', '1e', '.', ' 1', True, 1.0])
def test_conversion_never_reinterprets_invalid_or_native_unparsed_text(text):
    with pytest.raises(ValueError): c.exact_decimal(text)


def test_all_new_parent_schemas_use_existing_closed_grammar_and_legacy_schemas_stay_exact():
    sources = proteome_fact_sources()
    assert len(sources) == 22
    for value in sources.values(): validate_closed_schema(legacy.obj(value=value['report_schema']))
    form = c.requested_form_schema_v2({'requirements': {'kind': 'requirements', 'scope': 'all'}})
    assert form == legacy.requested_form_schema({'requirements': {'kind': 'requirements', 'scope': 'all'}})
    assert set(c.FAMILIES.values()) <= {name.removeprefix('bvbrc_proteome_') for name in sources}


def test_layer_zero_has_no_provider_projection_parser_or_calculator_import():
    tree = ast.parse(Path(c.__file__).read_text())
    imports = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(any(word in name for word in ('bundle_v2', 'projection', 'returns', 'calculation', 'geometry')) for name in imports)
    from gene_annotation_episode.bvbrc_proteome_bundle_v2_contracts import DIRECTIONAL_BINDING_CODES
    assert set(c.BINDING_CODES) == set(DIRECTIONAL_BINDING_CODES)


def numerical_fact():
    context = dict(target=dict(document_id='synthetic', **{key: 0 if key in {
        'report_ordinal', 'query_ordinal', 'subject_ordinal', 'hsp_ordinal'} else None for key in c.ORDINALS}),
        native_source_ref='synthetic_source', value_ref=legacy.encode_reference('field', 'synthetic', '/value'),
        parameter_ref=None, operand_refs=[], report_parse_state='ok', body_complete=True, object_complete='yes',
        declaration_state='matching_version', operand_binding='unbound', supports=[], mapping_state=None,
        qualification_refs=[], requirement_refs=[])
    return dict(availability='available', quantity='expect', context=context,
        cell=dict(state='present', value=dict(sign=0, digits=[1], exponent=-900)), unit='expected_count',
        statistic_kind=None, expectation_display='positive_reported_decimal', expect_group_count=dict(state='missing', value=None))


@pytest.mark.parametrize('number', [dict(sign=0, digits=[0, 1], exponent=-900),
    dict(sign=0, digits=[1, 0], exponent=-901), dict(sign=1, digits=[0], exponent=0),
    dict(sign=0, digits=[0], exponent=-900), dict(sign=True, digits=[1], exponent=0),
    dict(sign=0, digits=[True], exponent=0), dict(sign=0, digits=[10], exponent=0),
    dict(sign=0, digits=[], exponent=0)])
def test_full_fact_semantics_reject_noncanonical_exact_decimal(number):
    fact = numerical_fact()
    fact['cell']['value'] = number
    with pytest.raises(ValueError): c.validate_directional_fact('directional_native_decimal', fact)


@pytest.mark.parametrize('mutation', ['unit', 'state', 'availability', 'missing_group', 'expectation_display', 'statistic_kind'])
def test_full_fact_semantics_preserve_native_quantity_meanings(mutation):
    fact = numerical_fact()
    assert c.validate_directional_fact('directional_native_decimal', fact) == fact
    if mutation == 'unit': fact['unit'] = 'bits'
    elif mutation == 'state': fact['cell']['state'] = 'missing'
    elif mutation == 'availability': fact['availability'] = 'unavailable'
    elif mutation == 'missing_group': fact['expect_group_count'] = None
    elif mutation == 'expectation_display': fact['expectation_display'] = 'printed_zero_precision_unknown'
    else: fact['statistic_kind'] = 'matrix'
    with pytest.raises(ValueError): c.validate_directional_fact('directional_native_decimal', fact)
