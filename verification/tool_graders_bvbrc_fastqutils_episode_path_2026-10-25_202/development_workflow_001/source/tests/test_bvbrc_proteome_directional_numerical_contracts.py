"""Source-bound numerical validation, using native and labelled synthetic data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.bvbrc_proteome_directional_numerical_contracts import (
    DirectionalNumericalContractError, canonical_sheet_sha256,
    directional_numerical_schema, validate_directional_numerical,
)
from gene_annotation_episode.bvbrc_proteome_directional_calculators import calculate_directional_components
from gene_annotation_episode.bvbrc_proteome_directional_geometry import calculate_protein_block
from test_bvbrc_proteome_directional_sheet import (
    PARAMETERS, native_sheet, synthetic_sheet, parse_bytes, native_bytes,
)


def computed(sheet, parameters=None):
    return calculate_directional_components(sheet,parameters=parameters or PARAMETERS)['components']


def first_hsp(components):
    return components['reports'][0]['queries'][0]['subjects'][0]['hsps'][0]


def first_subject(components):
    return components['reports'][0]['queries'][0]['subjects'][0]


NAMES = ('DirectionalSheet','DirectionalSheetResult','DirectionalCalculationParameters',
    'BlockComponents','HspComponents','CorrespondenceGraph','DirectionalComponents',
    'DirectionalComponentsResult','DirectionalScoringSheet')


@pytest.mark.parametrize('name',NAMES)
def test_all_nine_exported_schemas_are_closed_and_valid(name):
    schema = directional_numerical_schema(name)
    Draft202012Validator.check_schema(schema)
    def walk(x):
        if isinstance(x,dict):
            if x.get('type') == 'object':
                assert x['additionalProperties'] is False
                assert set(x['required']) == set(x['properties'])
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(schema)
    schema['$defs'].clear()
    assert directional_numerical_schema(name)['$defs']


@pytest.mark.parametrize('name',['Issue','CountCell','ReaderResult','no-such-schema',None])
def test_private_or_unknown_schema_names_rejected(name):
    with pytest.raises(DirectionalNumericalContractError) as caught: directional_numerical_schema(name)
    assert caught.value.pointer == '/name'


@pytest.mark.parametrize('field,value',[
    ('ratio_decimal_places',True),('ratio_decimal_places',-1),('ratio_decimal_places',31),
    ('ratio_decimal_places',18.0),('rounding','half_up'),('amino_acid_alphabet','all'),
    ('formula_version','alternate'),('extra','hidden'),
])
def test_parameters_reject_bool_float_hidden_defaults_and_unknown_versions(field,value):
    p = {**PARAMETERS,field:value}
    with pytest.raises(DirectionalNumericalContractError): validate_directional_numerical('DirectionalCalculationParameters',p)


def test_all_explicit_parameters_required_and_copied():
    for field in PARAMETERS:
        p = deepcopy(PARAMETERS)
        del p[field]
        with pytest.raises(DirectionalNumericalContractError): validate_directional_numerical('DirectionalCalculationParameters',p)
    p = validate_directional_numerical('DirectionalCalculationParameters',PARAMETERS)
    p['ratio_decimal_places'] = 0
    assert PARAMETERS['ratio_decimal_places'] == 18


def test_canonical_hash_exact_utf8_encoding_and_no_mutation():
    s = synthetic_sheet()
    expected = hashlib.sha256(json.dumps(s,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    assert canonical_sheet_sha256(s) == expected
    assert canonical_sheet_sha256(json.loads(json.dumps(s))) == expected
    assert canonical_sheet_sha256({'native_label':'α'}) == hashlib.sha256('{"native_label":"α"}'.encode()).hexdigest()
    with pytest.raises(DirectionalNumericalContractError): canonical_sheet_sha256({'bad':float('nan')})


def test_semantic_context_is_required_not_shape_only():
    sheet = synthetic_sheet()
    result = computed(sheet)
    hsp = first_hsp(result)
    graph = first_subject(result)['correspondence']
    for name,value in [('BlockComponents',hsp['blocks'][0]),('HspComponents',hsp),('CorrespondenceGraph',graph),('DirectionalComponents',result)]:
        with pytest.raises(DirectionalNumericalContractError) as caught:
            validate_directional_numerical(name,value)
        assert caught.value.code == 'semantic_context_missing'
        assert caught.value.pointer == '/sheet'
    with pytest.raises(DirectionalNumericalContractError) as caught:
        validate_directional_numerical('BlockComponents',hsp['blocks'][0],sheet=sheet)
    assert caught.value.pointer == '/parameters'


def test_embedded_and_external_context_must_agree():
    sheet = synthetic_sheet()
    components = computed(sheet)
    wrong = deepcopy(sheet)
    wrong['reader_results'] = []
    with pytest.raises(DirectionalNumericalContractError) as caught:
        validate_directional_numerical('DirectionalSheet',sheet,sheet=wrong)
    assert caught.value.code == 'semantic_context_conflict'
    with pytest.raises(DirectionalNumericalContractError) as caught:
        validate_directional_numerical('DirectionalComponents',components,sheet=sheet,
            parameters={**PARAMETERS,'ratio_decimal_places':5})
    assert caught.value.code == 'semantic_context_conflict'


@pytest.mark.parametrize('target,change',[
    ('reported',lambda h:h['reported']['reported_identity_fraction']['value'].update(numerator=3)),
    ('ratio_rendering',lambda h:h['reported']['reported_identity_fraction']['value'].update(decimal='0.999999999999999999')),
    ('copied_score',lambda h:h['native_scores']['bit_score'].update(value='21',native_text='21')),
    ('trace_count',lambda h:h['trace_counts']['paired_columns'].update(value=3)),
    ('class_count',lambda h:h['trace_counts']['resolved_amino_acid_substituted_pairs'].update(value=1)),
    ('false_support',lambda h:h['strings_support'].update(complete_for_displayed_blocks=False)),
    ('source_operand',lambda h:h['reported']['reported_identity_fraction']['inputs'][0].update(pointer='/queries/0/length')),
    ('native_extent',lambda h:h.update(native_denominator_extent='unknown')),
    ('wrong_unit',lambda h:h['trace_counts']['paired_columns'].update(unit='alignment_column')),
    ('interval',lambda h:h['coverage']['query_trace_paired_union']['intervals'][0].__setitem__(1,3)),
    ('column_position',lambda h:h['blocks'][0]['columns'][0]['query_position'].update(value=1)),
    ('column_symbol',lambda h:h['blocks'][0]['columns'][0].update(query_symbol='X')),
])
def test_synthetic_hsp_numeric_source_and_geometry_tampering_rejects(target,change):
    sheet = synthetic_sheet()
    hsp = first_hsp(computed(sheet))
    change(hsp)
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('HspComponents',hsp,sheet=sheet,parameters=PARAMETERS)


@pytest.mark.parametrize('change',[
    lambda s:s['displayed_hsp_count'].update(value=2),
    lambda s:s['compatible_pair_counts']['identical_symbol_pairs'].update(value=3),
    lambda s:s['compatible_unique_pair_symbol_identity']['value'].update(denominator=5),
    lambda s:s['maximum_reported_hsp_bit_score']['selected_field'].update(pointer='/queries/0/subjects/0/hsps/0/expect'),
    lambda s:s['nonoverlapping_hsp_reported_identity_count'].update(value=3),
    lambda s:s['correspondence']['edges'][0]['supports'][0].update(column_ordinal=1),
    lambda s:s['correspondence']['repeated_pair_occurrence_count'].update(value=1),
])
def test_synthetic_subject_aggregate_and_extremum_tampering_rejects(change):
    sheet = synthetic_sheet()
    components = computed(sheet)
    change(first_subject(components))
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('DirectionalComponents',components,sheet=sheet)


def test_swapping_equal_id_occurrences_is_not_a_valid_source_reference():
    sheet = synthetic_sheet(hsps=[dict(q='ACDE',s='ACDE',qs=1,qe=4,ss=1,se=4,i=4,d=4),
                                  dict(q='ACDE',s='ACDE',qs=1,qe=4,ss=1,se=4,i=4,d=4)])
    components = computed(sheet)
    hsp = first_hsp(components)
    hsp['reported']['reported_identity_fraction']['inputs'][0]['pointer'] = '/queries/0/subjects/0/hsps/1/identity_count'
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('HspComponents',hsp,sheet=sheet,parameters=PARAMETERS)


def test_graph_does_not_depend_on_alphabet_or_ratio_precision():
    sheet = synthetic_sheet(hsps=[dict(q='UX*A',s='UX*A',qs=1,qe=4,ss=1,se=4,i=4,d=4)])
    first = computed(sheet)
    second = computed(sheet,{**PARAMETERS,'amino_acid_alphabet':'standard20_plus_uo','ratio_decimal_places':0})
    graph = first_subject(first)['correspondence']
    assert graph == first_subject(second)['correspondence']
    assert first_hsp(first)['trace_counts']['resolved_amino_acid_pairs']['value'] == 1
    assert first_hsp(second)['trace_counts']['resolved_amino_acid_pairs']['value'] == 2
    assert validate_directional_numerical('CorrespondenceGraph',graph,sheet=sheet) == graph


@pytest.mark.parametrize('name',['2011','2202','2221'])
def test_complete_original_native_scoring_sheet_validates_with_all_occurrences(name):
    sheet = native_sheet(name)
    components = computed(sheet)
    saved = {'version':'bvbrc_proteome_directional_scoring_sheet_v1','observed':sheet,'calculated':components}
    assert validate_directional_numerical('DirectionalScoringSheet',saved) == saved
    assert components['reports'][0]['displayed_query_count']['value'] == len(sheet['reports'][0]['query_rows'])
    if name == '2221':
        subject = components['reports'][0]['queries'][1]['subjects'][0]
        assert subject['coverage']['query_trace_paired_union']['coverage']['value'] == {
            'numerator':529,'denominator':600,'decimal':'0.881666666666666667'}
        assert subject['compatible_unique_pair_symbol_identity']['value'] == {
            'numerator':468,'denominator':529,'decimal':'0.884688090737240076'}
        assert subject['compatible_pair_counts']['unresolved_pairs']['value'] == 61
    elif name == '2202':
        subject = components['reports'][0]['queries'][1]['subjects'][0]
        assert subject['coverage']['subject_trace_paired_union']['count']['value'] == 223
        codes = {c['code'] for c in subject['correspondence']['conflicts']}
        assert {'alternative_subject_mapping','subject_gap_versus_pair_conflict'} <= codes
    else:
        query = components['reports'][0]['queries'][0]
        assert query['subjects'] == []
        assert query['any_displayed_subject_query_paired_union']['coverage']['value']['numerator'] == 0
        assert query['any_displayed_subject_query_paired_union']['coverage']['value']['denominator'] == 102


def test_saved_sheet_recalculation_validation_no_parser_network_process_or_files(monkeypatch):
    sheet = synthetic_sheet(hsps=[dict(q='AUX',s='AUX',qs=1,qe=3,ss=1,se=3,i=3,d=3)])
    saved = json.loads(json.dumps(sheet))
    def forbidden(*args,**kwargs): raise AssertionError('unexpected acquisition or parsing')
    monkeypatch.setattr('builtins.open',forbidden)
    monkeypatch.setattr(Path,'open',forbidden)
    monkeypatch.setattr('socket.socket',forbidden)
    monkeypatch.setattr('subprocess.Popen',forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_proteome_directional.parse_genome_comparison_directional_report',forbidden)
    a = computed(saved)
    b = computed(saved,{**PARAMETERS,'ratio_decimal_places':3,'amino_acid_alphabet':'standard20_plus_uo'})
    assert a['sheet_sha256'] == b['sheet_sha256'] == canonical_sheet_sha256(sheet)
    assert first_hsp(a)['trace_counts']['resolved_amino_acid_pairs']['value'] == 1
    assert first_hsp(b)['trace_counts']['resolved_amino_acid_pairs']['value'] == 2
    assert first_hsp(b)['trace_fractions']['trace_resolved_pair_fraction']['value']['decimal'] == '0.667'
    assert saved == sheet


def test_failure_result_cannot_invent_scientific_references_without_observations():
    failure = {'state':'failure','components':None,'diagnostics':[{
        'code':'invalid_input_contract','fields':[],'columns':[],'hsps':[],
        'argument_pointer':'/sheet'}]}
    assert validate_directional_numerical('DirectionalComponentsResult',failure) == failure
    failure['diagnostics'][0]['fields'] = [{'report_ordinal':0,'pointer':'/queries'}]
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('DirectionalComponentsResult',failure)


def hsp_spec(q, s, qs=1, ss=1, **extra):
    paired = [(a,b) for a,b in zip(q,s) if a != '-' and b != '-']
    return dict(q=q,s=s,qs=qs,qe=qs + len(q.replace('-','')) - 1,
                ss=ss,se=ss + len(s.replace('-','')) - 1,
                i=sum(a.upper()==b.upper() for a,b in paired),d=len(q),**extra)


@pytest.mark.parametrize('specs,distinct,repeated,qcount,scount,conflict',[
    ([hsp_spec('ACDE','ACDE'),hsp_spec('ACDE','ACDE'),hsp_spec('DEFG','DEFG',3,3)],6,6,6,6,None),
    ([hsp_spec('ACDE','ACDE'),hsp_spec('ACDE','ACDE',1,2)],8,0,4,5,'alternative_query_mapping'),
    ([hsp_spec('ACDE','ACDE'),hsp_spec('ACDE','ACDF')],4,4,4,4,'subject_symbol_conflict'),
    ([hsp_spec('ACDE','ACDE'),hsp_spec('AC-D','ACTD')],5,2,4,4,'subject_gap_versus_pair_conflict'),
    ([hsp_spec('AC','AC',1,5),hsp_spec('FG','FG',5,1)],4,0,4,4,'noncollinear_pair_order'),
])
def test_177_independent_synthetic_graph_answers(specs,distinct,repeated,qcount,scount,conflict):
    sheet = synthetic_sheet(hsps=specs)
    components = computed(sheet)
    subject = first_subject(components)
    graph = subject['correspondence']
    assert graph['distinct_pair_count']['value'] == distinct
    assert graph['repeated_pair_occurrence_count']['value'] == repeated
    assert subject['coverage']['query_trace_paired_union']['count']['value'] == qcount
    assert subject['coverage']['subject_trace_paired_union']['count']['value'] == scount
    if conflict:
        assert conflict in {c['code'] for c in graph['conflicts']}
        assert subject['compatible_unique_pair_symbol_identity']['state'] == 'conflict'
        altered = deepcopy(graph)
        altered['conflicts'] = [c for c in altered['conflicts'] if c['code'] != conflict]
        with pytest.raises(DirectionalNumericalContractError):
            validate_directional_numerical('CorrespondenceGraph',altered,sheet=sheet)
    else:
        assert graph['mapping_state'] == 'compatible_displayed_partial_map'
        assert subject['compatible_unique_pair_symbol_identity']['value']['numerator'] == 6
        assert subject['compatible_unique_pair_symbol_identity']['value']['denominator'] == 6


@pytest.mark.parametrize('query,subject,expected',[
    ('AXBC*U','AYDC*U',dict(alignment_columns=6,paired_columns=6,
        displayed_symbol_identical_pairs=4,resolved_amino_acid_pairs=2,
        resolved_amino_acid_substituted_pairs=0,unresolved_symbol_pairs=3,stop_containing_pairs=1)),
    ('ACD-EFG','ACTVE-G',dict(alignment_columns=7,paired_columns=5,
        displayed_symbol_identical_pairs=4,resolved_amino_acid_pairs=5,
        resolved_amino_acid_substituted_pairs=1,query_gap_columns=1,subject_gap_columns=1)),
])
def test_177_independent_synthetic_symbol_counts(query,subject,expected):
    sheet = synthetic_sheet(hsps=[hsp_spec(query,subject)])
    hsp = first_hsp(computed(sheet))
    assert {k:hsp['trace_counts'][k]['value'] for k in expected} == expected
    assert validate_directional_numerical('HspComponents',hsp,sheet=sheet,parameters=PARAMETERS) == hsp


@pytest.mark.parametrize('kwargs,expected_state',[
    (dict(hsps=[dict(i=6,d=10,g=2,gd=10,blocks=[])]),'missing'),
    (dict(hsps=[dict(q='ACDE',s='ACDE',qs=1,qe=9,ss=1,se=4,i=4,d=4)]),'conflict'),
    (dict(hsps=[dict(q='A?',s='AC',qs=1,qe=2,ss=1,se=2,i=2,d=2)]),'invalid'),
])
def test_missing_and_invalid_geometry_does_not_become_compatible_identity(kwargs,expected_state):
    sheet = synthetic_sheet(**kwargs)
    components = computed(sheet)
    subject = first_subject(components)
    assert subject['correspondence']['mapping_state'] == 'incomplete_geometry'
    assert subject['compatible_unique_pair_symbol_identity']['state'] == 'missing'
    assert subject['compatible_unique_pair_resolved_fraction']['state'] == 'missing'
    assert subject['nonoverlapping_hsp_reported_identity_count']['state'] == expected_state
    if expected_state == 'conflict':
        assert subject['coverage']['subject_trace_paired_union']['coverage']['value']['numerator'] == 4
        assert subject['coverage']['query_reported_interval_union']['count']['value'] == 9
        assert first_hsp(components)['trace_counts']['paired_columns']['value'] == 4


@pytest.mark.parametrize('first,second',[
    (dict(q='ACDE',s='ACDE',qs=1,qe=4,ss=1,se=4),dict(q='A?',s='AC',qs=5,qe=6,ss=5,se=6)),
    (dict(q='ACDE',s='ACDE',qs=0,qe=3,ss=1,se=4),dict(q='ACDE',s='ACDE',qs=4,qe=7,ss=5,se=8)),
])
def test_multiple_block_gap_run_prerequisites_preserve_invalid_causes(first,second):
    sheet = synthetic_sheet(hsps=[dict(i=4,d=4,blocks=[first,second])])
    hsp = first_hsp(computed(sheet))
    assert hsp['trace_counts']['paired_columns']['state'] == 'value'
    for axis in ('query','subject'):
        assert hsp['trace_counts'][axis + '_gap_runs']['state'] == 'invalid'
        assert hsp['trace_counts'][axis + '_gap_runs']['value'] is None


def test_missing_native_gaps_never_replaced_with_observed_trace_zero():
    missing = first_hsp(computed(synthetic_sheet(hsps=[hsp_spec('ACDE','ACDE')])))
    zero = first_hsp(computed(synthetic_sheet(hsps=[hsp_spec('ACDE','ACDE',g=0,gd=4)])))
    assert missing['reported']['reported_paired_column_count']['state'] == 'missing'
    assert zero['reported']['reported_paired_column_count']['value'] == 4
    assert missing['trace_counts']['query_gap_columns']['value'] == zero['trace_counts']['query_gap_columns']['value'] == 0


def test_native_zero_and_positive_extreme_expectations_remain_distinct():
    sheet = synthetic_sheet(hsps=[hsp_spec('ACDE','ACDE',expect='0.0'),hsp_spec('ACDE','ACDE',expect='e-900')])
    components = computed(sheet)
    subject = first_subject(components)
    assert subject['hsps'][0]['native_scores']['expectation_display'] == 'printed_zero_precision_unknown'
    assert subject['hsps'][1]['native_scores']['expect']['native_text'] == 'e-900'
    assert subject['hsps'][1]['native_scores']['expect']['value'] == '1e-900'
    assert subject['minimum_reported_hsp_expectation']['tied_hsps'] == [subject['hsps'][0]['key']]


def test_zero_pair_population_and_zero_resolved_population_are_undefined():
    sheet = synthetic_sheet(hsps=[hsp_spec('A-','-A',g=2,gd=2)])
    subject = first_subject(computed(sheet))
    assert subject['correspondence']['distinct_pair_count']['value'] == 0
    assert subject['compatible_unique_pair_symbol_identity']['state'] == 'undefined'
    sheet = synthetic_sheet(hsps=[hsp_spec('XX','XX')])
    subject = first_subject(computed(sheet))
    assert subject['compatible_unique_pair_symbol_identity']['value']['numerator'] == 2
    assert subject['compatible_unique_pair_resolved_identity']['state'] == 'undefined'


def test_diagnostic_cannot_lie_about_another_occurrence_or_unobserved_condition():
    sheet = synthetic_sheet(hsps=[hsp_spec('ACDE','ACDE',expect='0.0'),hsp_spec('ACDE','ACDE',expect='1e-10')])
    components = computed(sheet)
    hsp = first_hsp(components)
    issue = next(i for i in hsp['diagnostics'] if i['code'] == 'printed_zero_expectation')
    issue['fields'][0]['pointer'] = '/queries/0/subjects/0/hsps/1/expect'
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('HspComponents',hsp,sheet=sheet,parameters=PARAMETERS)


def test_bool_is_not_equal_external_context_and_nohit_partial_is_not_available():
    sheet = synthetic_sheet(nohit=True)
    p = {**PARAMETERS,'ratio_decimal_places':1}
    components = computed(sheet,p)
    with pytest.raises(DirectionalNumericalContractError) as caught:
        validate_directional_numerical('DirectionalComponents',components,sheet=sheet,parameters={**p,'ratio_decimal_places':True})
    assert caught.value.code == 'semantic_context_conflict'
    result = {'state':'partial','components':components,'diagnostics':components['diagnostics']}
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('DirectionalComponentsResult',result,sheet=sheet)


@pytest.mark.parametrize('second_start,expected',[ (3,'invalid'), (4,'conflict') ])
def test_all_invalid_string_blocks_still_preserve_boundary_prerequisites(second_start,expected):
    bad = dict(q='A?',s='AC',qs=1,qe=2,ss=1,se=2)
    later = dict(q='A?',s='AC',qs=second_start,qe=second_start+1,ss=3,se=4)
    sheet = synthetic_sheet(hsps=[dict(i=2,d=4,blocks=[bad,later])])
    subject = first_subject(computed(sheet))
    hsp = subject['hsps'][0]
    assert hsp['trace_counts']['query_gap_runs']['state'] == expected
    assert 'invalid_traceback_symbols' in hsp['trace_counts']['query_gap_runs']['reasons']
    assert subject['correspondence']['mapping_state'] == 'incomplete_geometry'
    assert subject['correspondence']['conflicts'] == []
    if expected == 'conflict':
        assert hsp['contiguous_blocks'] == 'no'
        assert 'block_continuity_conflict' in {i['code'] for i in hsp['diagnostics']}
    assert validate_directional_numerical('CorrespondenceGraph',subject['correspondence'],sheet=sheet) == subject['correspondence']


def test_unknown_or_spurious_failure_reason_is_not_valid_numerical_metadata():
    sheet = synthetic_sheet()
    components = computed(sheet)
    hsp = first_hsp(components)
    hsp['trace_counts']['paired_columns']['reasons'] = ['zero_native_denominator']
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('HspComponents',hsp,sheet=sheet,parameters=PARAMETERS)


def test_removing_required_conflict_diagnostic_fails_even_with_correct_numbers():
    sheet = synthetic_sheet(hsps=[dict(q='ACDE',s='ACDE',qs=1,qe=4,ss=1,se=4,i=2,d=4)])
    components = computed(sheet)
    hsp = first_hsp(components)
    assert hsp['reported']['reported_identity_fraction']['value']['numerator'] == 2
    assert hsp['trace_fractions']['trace_symbol_identity_over_columns']['value']['numerator'] == 4
    hsp['diagnostics'] = [i for i in hsp['diagnostics'] if i['code'] != 'reported_count_traceback_conflict']
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('HspComponents',hsp,sheet=sheet,parameters=PARAMETERS)
