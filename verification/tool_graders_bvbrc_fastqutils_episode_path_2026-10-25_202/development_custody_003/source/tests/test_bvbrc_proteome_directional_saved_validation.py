"""Immutable saved-data checks prohibit scientific reconstruction explicitly."""
from copy import deepcopy
from decimal import localcontext, Inexact, Rounded, ROUND_UP
import importlib
import json

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_v2_contracts as c
from gene_annotation_episode.bvbrc_proteome_bundle_v2_resolution import _construct_bundle
from gene_annotation_episode.bvbrc_proteome_directional_calculators import calculate_directional_components
from test_bvbrc_proteome_bundle_v2_resolution import fixture


@pytest.fixture(scope='module')
def saved():
    case=fixture('2221')
    return case,_construct_bundle(**case)


def check(case,result):
    return c.validate_saved_provider_v2(result['sheet'],result['components'],parameters=case['parameters'],
        requested_form=case['requested_form'],original_task=case['bundle']['original_task'],bundle_sha256=c.digest(case['bundle']),bundle=case['bundle'])


def forbidden(*args,**kwargs):
    raise AssertionError('saved validation called scientific parsing/building/calculation or transport')


def forbid_producers(monkeypatch, *, calculator=True):
    names={'bvbrc_proteome_directional':['parse_genome_comparison_directional_report'],
        'bvbrc_proteome_directional_sheet':['build_directional_sheet'],
        'bvbrc_proteome_directional_geometry':['calculate_protein_block','inspect_protein_correspondence','union_position_intervals'],
        'bvbrc_proteome_directional_numerical_contracts':['_validate_components','_validate_block','_validate_graph'],
        'bvbrc_proteome_bundle_v2_resolution':['parse_genome_comparison_directional_report','build_directional_sheet','calculate_directional_components']}
    if calculator:names['bvbrc_proteome_directional_calculators']=['calculate_directional_components']
    for module,functions in names.items():
        for fn in functions:monkeypatch.setattr(importlib.import_module('gene_annotation_episode.'+module),fn,forbidden)
    monkeypatch.setattr('socket.socket',forbidden)
    monkeypatch.setattr('subprocess.run',forbidden)


def test_saved_native_answers_replay_without_producers_and_are_detached(saved,monkeypatch):
    case,result=saved;forbid_producers(monkeypatch)
    sheet,components=check(case,result)
    subject=components['directional']['components']['reports'][0]['queries'][1]['subjects'][0]
    assert subject['coverage']['query_trace_paired_union']['coverage']['value']==dict(numerator=529,denominator=600,decimal='0.881666666666666667')
    assert subject['compatible_unique_pair_symbol_identity']['value']==dict(numerator=468,denominator=529,decimal='0.884688090737240076')
    assert subject['compatible_unique_pair_resolved_identity']['value']==dict(numerator=468,denominator=468,decimal='1.000000000000000000')
    assert subject['compatible_pair_counts']['unresolved_pairs']['value']==61
    assert subject['hsps'][1]['native_scores']['expect']['value']=='2e-66'
    assert subject['hsps'][1]['reported']['reported_gap_fraction']['state']=='missing'
    assert subject['hsps'][1]['trace_counts']['query_gap_columns']['value']==0
    sheet['analysis_id']='caller-edit';assert result['sheet']['analysis_id']!='caller-edit'


@pytest.mark.parametrize('mutation',[
    'ratio_numerator','ratio_denominator','ratio_decimal','interval_count','interval_overlap','length',
    'length_reference','native_score','partition','edge_support','edge_position','block_key','resolution_index',
    'observed_copy','parameters','provider_hash','support_partition','extremum_operand','diagnostic_cross_report'])
def test_saved_numerical_and_occurrence_mutations_are_rejected(saved,monkeypatch,mutation):
    case,original=saved;result=deepcopy(original)
    s=result['components']['directional']['components']['reports'][0]['queries'][1]['subjects'][0]
    union=s['coverage']['query_trace_paired_union']; ratio=union['coverage']['value'];hsp=s['hsps'][0]
    if mutation=='ratio_numerator':ratio['numerator']+=1
    elif mutation=='ratio_denominator':ratio['denominator']+=1
    elif mutation=='ratio_decimal':ratio['decimal']='0.9'
    elif mutation=='interval_count':union['count']['value']-=1
    elif mutation=='interval_overlap':union['intervals'].append(union['intervals'][0])
    elif mutation=='length':union['reported_length']['value']-=1
    elif mutation=='length_reference':
        for ref in union['coverage']['inputs']:
            # Both native lengths are600: equality of values cannot replace
            # the selected query occurrence's own length operand.
            if ref['pointer']=='/queries/1/length':ref['pointer']='/queries/1/subjects/0/length'
    elif mutation=='native_score':hsp['native_scores']['bit_score']['value']='685'
    elif mutation=='partition':hsp['trace_counts']['paired_columns']['value']-=1
    elif mutation=='edge_support':s['correspondence']['edges'][0]['supports'].append(deepcopy(s['correspondence']['edges'][0]['supports'][0]))
    elif mutation=='edge_position':s['correspondence']['edges'][0]['query_position']+=1
    elif mutation=='block_key':hsp['blocks'][0]['key']['block_ordinal']=1
    elif mutation=='resolution_index':result['sheet']['input_resolution'][0]['result_index']=1
    elif mutation=='observed_copy':result['sheet']['directional_sheet_result']['sheet']['reports'][0]['query_rows'][1]['reported_length']['value']=599
    elif mutation=='parameters':result['components']['directional']['components']['parameters']['amino_acid_alphabet']='standard20_plus_uo'
    elif mutation=='provider_hash':result['components']['provider_sheet_sha256']='0'*64
    elif mutation=='support_partition':union['support']['included_blocks'].pop()
    elif mutation=='extremum_operand':s['minimum_reported_hsp_expectation']['selected_field']['pointer']='/queries/1/subjects/0/hsps/1/expect'
    elif mutation=='diagnostic_cross_report':
        s['diagnostics'][0]['fields'][0]['report_ordinal']=1
    forbid_producers(monkeypatch)
    with pytest.raises(ValueError):check(case,result)


@pytest.mark.parametrize('mutation',['task','membership','source','role','format','transfer','same_source_selection'])
def test_authenticated_bundle_relationship_mutations_rejected(saved,mutation):
    case,result=deepcopy(saved)
    member=case['bundle']['artifacts'][0]
    if mutation=='task':case['bundle']['original_task']['task_id']='different'
    elif mutation=='membership':member['requirement_ids']=[]
    elif mutation=='source':member['source_ref']='other'
    elif mutation=='role':member['role']='other'
    elif mutation=='format':member['declared_format']['version']=None
    elif mutation=='transfer':member['transfer']['body_complete']=False
    elif mutation=='same_source_selection':case['bundle']['artifacts'].append(deepcopy(member))
    # Even when outer hashes are consistently rewritten, the originally saved
    # selection and reader/source relationship cannot acquire another meaning.
    result['sheet']['bundle_sha256']=c.digest(case['bundle'])
    result['components']['provider_sheet_sha256']=c.digest(result['sheet'])
    with pytest.raises(ValueError):check(case,result)


def test_saved_ratio_checks_ignore_ambient_decimal_context(saved,monkeypatch):
    case,result=saved;forbid_producers(monkeypatch)
    with localcontext() as ctx:
        ctx.prec=2;ctx.Emin=-2;ctx.Emax=2;ctx.rounding=ROUND_UP
        ctx.traps[Inexact]=True;ctx.traps[Rounded]=True
        assert check(case,result)==(result['sheet'],result['components'])


def test_explicit_changed_parameter_calculation_reads_saved_observations_only(saved,monkeypatch):
    case,result=saved
    monkeypatch.setattr('gene_annotation_episode.bvbrc_proteome_directional.parse_genome_comparison_directional_report',forbidden)
    monkeypatch.setattr('socket.socket',forbidden);monkeypatch.setattr('subprocess.run',forbidden)
    before=deepcopy(result)
    options={**case['parameters']['directional_calculation_parameters'],'ratio_decimal_places':3}
    revised=calculate_directional_components(result['sheet']['directional_sheet_result']['sheet'],parameters=options)
    ratio=revised['components']['reports'][0]['queries'][1]['subjects'][0]['coverage']['query_trace_paired_union']['coverage']['value']
    assert ratio==dict(numerator=529,denominator=600,decimal='0.882')
    assert result==before


def test_retained_conflicting_correspondence_survives_check_only_saved_validation(monkeypatch):
    case = fixture('2202')
    result = _construct_bundle(**case)
    subject = result['components']['directional']['components']['reports'][0]['queries'][0]['subjects'][0]
    assert subject['correspondence']['mapping_state'] == 'observed_conflict'
    assert subject['coverage']['query_trace_paired_union']['count']['value'] == 187
    assert subject['coverage']['subject_trace_paired_union']['count']['value'] == 140
    assert subject['compatible_unique_pair_symbol_identity']['state'] == 'conflict'
    assert subject['nonoverlapping_hsp_reported_identity_over_columns']['state'] == 'conflict'
    forbid_producers(monkeypatch)
    assert check(case, result) == (result['sheet'], result['components'])
