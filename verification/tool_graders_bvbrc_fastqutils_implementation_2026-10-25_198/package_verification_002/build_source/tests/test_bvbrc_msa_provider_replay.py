"""Saved-sheet recalculation and saved-result validation with I/O disabled."""
from copy import deepcopy
import builtins
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import pytest

from gene_annotation_episode import bvbrc_msa_inputs, bvbrc_msa_grader, bvbrc_msa_provider_contracts as c
from gene_annotation_episode import bvbrc_msa_formats, phylogeny_formats, xmfa_formats, bvbrc_msa_xmfa_inputs
from gene_annotation_episode import phylogeny_calculators, bvbrc_msa_calculators, xmfa_calculators, xmfa_coordinates
from gene_annotation_episode import bvbrc_msa_calculation_contracts, xmfa_calculation_contracts
from test_bvbrc_msa_provider import (native_operands,associated_operands,xmfa_operands,tree_operands,composition_operands,reference_operands,
    gap_fill_operands,first_block_projection_operands,source_example_operands,unbound_source_operands,alignment,artifact,frequency_header,parse_msa_frequency_table,
    parameters,request,entropy_request,extract_msa_sheet,calculate_msa,operands)


def forbid(*args,**kwargs):
    raise AssertionError('saved provider operation attempted I/O, parsing or a forbidden calculation')


def block_io(monkeypatch):
    for target,names in [(builtins,['open']),(io,['open']),(Path,['open','read_text','read_bytes','write_text','write_bytes']),
        (os,['open','read','write','stat','listdir','scandir','system']),(socket,['socket','create_connection','getaddrinfo']),
        (subprocess,['run','Popen','check_output','check_call','call'])]:
        for name in names:
            monkeypatch.setattr(target,name,forbid)
    for module,names in [(bvbrc_msa_formats,['parse_msa_frequency_table']),(phylogeny_formats,['parse_aligned_fasta','parse_newick']),
        (xmfa_formats,['parse_mauve_xmfa']),(bvbrc_msa_xmfa_inputs,['verify_xmfa_source_inputs','extract_msa_xmfa_bindings','parse_aligned_fasta'])]:
        for name in names:
            monkeypatch.setattr(module,name,forbid)


def block_saved_calculations(guard):
    guard.setattr(bvbrc_msa_inputs,'extract_msa_sheet',forbid)
    guard.setattr(bvbrc_msa_grader,'calculate_msa',forbid)
    for module in (phylogeny_calculators,bvbrc_msa_calculators,xmfa_calculators,xmfa_coordinates):
        for name in module.__all__: guard.setattr(module,name,forbid)
    for module,names in [(bvbrc_msa_calculation_contracts,['validate_msa_entropy_components','validate_msa_reference_components']),
        (xmfa_calculation_contracts,['validate_xmfa_alignment_components','validate_xmfa_coverage_components','union_intervals','interval_length','multiplicity_bases','complement_intervals'])]:
        for name in names: guard.setattr(module,name,forbid)
    guard.setattr(bvbrc_msa_calculation_contracts,'format',forbid,raising=False)
    guard.setattr(math,'log2',forbid); guard.setattr(math,'fsum',forbid)


def example_operands(name):
    if name in ('dna','protein'):
        op,table=native_operands(name); return op,parameters(entropy_request(name,table))
    if name=='reference':
        op=reference_operands(); return op,parameters(request('msa_reference_differences',population_id='all',reference=op['analysis']['reference'],member_row_indices=[1],alphabet='dna',case_policy='preserve'))
    if name=='original_coverage':
        op=associated_operands('explicit_reference_identity'); return op,parameters(request('original_coverage',population_id='all'))
    if name=='concatenation': return gap_fill_operands(),parameters(entropy_request('protein'),request('original_coverage',population_id='all'))
    if name=='trees': return tree_operands(True)
    if name=='unknown_tree_units': return tree_operands(False)
    if name=='composition': return composition_operands()
    if name=='xmfa': return xmfa_operands()
    if name=='xmfa_missing_sources': return xmfa_operands(with_sources=False)
    if name in ('unbound_GenBank','unbound_DNAstar'): return unbound_source_operands(name[len('unbound_'):])
    if name.startswith('source_'): return source_example_operands(name[len('source_'):])
    if name=='mauve_first_block_projection': return first_block_projection_operands()
    if name=='segment_alignment':
        op=associated_operands('reverse_translation_concatenation','segment_alignment')
        return op,parameters(entropy_request('protein'),request('original_coverage',population_id='all'))
    if name=='full_row_mask_subset':
        op=operands(alignment(b'>a\nA--C\n>b\nA--C\n>c\nATGC\n>d\n---C\n')); op['populations']['alignments'][0]['columns_0based']=[1]
        return op,parameters(entropy_request())
    if name in ('blank','unknown','duplicate','native_na'):
        if name=='unknown':
            data=('\t'.join(frequency_header('protein','current_without_reference'))+'\n1\t0\tFoo\tFoo=2\t2\n').encode(); alpha='protein'
        else:
            line='1\t0\tA\t2\t0\t0\t0\t0\t2\n'
            if name=='blank': line=line.replace('\t2\t0','\t2\t',1)
            if name=='native_na': line=line.replace('\t0\tA','\tNA\tA')
            data=('\t'.join(frequency_header('dna','current_without_reference'))+'\n'+line+(line if name=='duplicate' else '')).encode(); alpha='dna'
        table=parse_msa_frequency_table(data,artifact=artifact(data,'partial'),alphabet=alpha,layout='current_without_reference',encoding='ascii')['value']
        return operands(alignment(b'>a\nA\n>b\nA\n'),table),parameters(entropy_request(alpha,table))
    if name in ('reference_bare','reference_duplicate','reference_different'):
        text={'reference_bare':'AC','reference_duplicate':'>a\nAC\n>a\nAC\n','reference_different':'>a\nTT\n'}[name]
        op=reference_operands(text)
        return op,parameters(request('msa_reference_differences',population_id='all',reference=op['analysis']['reference'],member_row_indices=[1],alphabet='dna',case_policy='preserve'))
    if name in ('duplicate_physical_headers','identical_sequences_ambiguous'):
        return associated_operands(name),parameters(request('original_coverage',population_id='all'),entropy_request())
    if name=='incomplete_original_map':
        op=associated_operands('explicit_reference_identity'); op['associations']['correspondences']=op['associations']['correspondences'][:-1]
        return op,parameters(request('original_coverage',population_id='all'))
    if name=='empty_population':
        op=operands(); op['populations']['alignments'][0]['row_indices']=[]
        return op,parameters(entropy_request(),request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[]))
    if name=='ragged_alignment':
        return operands(alignment(b'>a\nACT\n>b\nA\n')),parameters(entropy_request(),request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,1]]))
    if name=='missing_originals':
        op=operands()
        return op,parameters(request('original_coverage',population_id='all'),request('ungapped_map',alignment_id=op['analysis']['alignment_id'],row_indices=[0,1]),entropy_request())
    if name=='independent_failure':
        return operands(),parameters(entropy_request(),request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,99]]))
    if name=='missing_table': return operands(),parameters(entropy_request()|{'observed_table_id':'missing-table'})
    op=operands(mode=name)
    return op,parameters(entropy_request(),request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,1]]))


CASES=['dna','protein','reference','original_coverage','concatenation','trees','unknown_tree_units','composition','xmfa','xmfa_missing_sources',
    'ordinary_prealigned','segment_alignment','mauve_first_block_projection','full_row_mask_subset','blank','unknown','duplicate','native_na',
    'reference_bare','reference_duplicate','reference_different','duplicate_physical_headers','identical_sequences_ambiguous',
    'incomplete_original_map','empty_population','ragged_alignment','missing_originals','independent_failure','missing_table','unbound_GenBank','unbound_DNAstar',
    *['source_'+name for name in ['separate_native','one_missing_source','contradictory_json_sequence','missing_reader','partial_record_population','distinct_original_occurrences']]]


@pytest.mark.parametrize('name',CASES)
def test_complete_saved_recalculation_without_parsing_or_io(name,monkeypatch):
    op,p=example_operands(name); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=json.loads(json.dumps(parsed['value'])); initial=calculate_msa(sheet,p)
    saved=json.loads(json.dumps({'sheet':sheet,'parameters':p,'components':initial}))
    with monkeypatch.context() as guard:
        block_io(guard)
        result=calculate_msa(saved['sheet'],saved['parameters'])
        assert result==saved['components']
        assert c.validate_msa_sheet(saved['sheet'])==saved['sheet']
        assert c.validate_msa_components(saved['components'],sheet=saved['sheet'])==saved['components']
    assert saved['sheet']==sheet


@pytest.mark.parametrize('name',CASES)
def test_saved_validation_does_not_call_any_calculator_or_extractor(name,monkeypatch):
    op,p=example_operands(name); sheet=extract_msa_sheet(**op)['value']; result=calculate_msa(sheet,p)
    with monkeypatch.context() as guard:
        block_io(guard)
        block_saved_calculations(guard)
        assert c.validate_msa_components(result,sheet=sheet)==result


def test_changed_parameters_recalculate_without_mutating_native_data(monkeypatch):
    op,table=native_operands(); sheet=extract_msa_sheet(**op)['value']; saved=deepcopy(sheet)
    original=parameters(entropy_request(table=table)); changed=deepcopy(original); changed['requests'][0]['native_rounding']=None
    with monkeypatch.context() as guard:
        block_io(guard)
        before=calculate_msa(sheet,original); after=calculate_msa(sheet,changed)
    a,b=before['results'][0]['value'],after['results'][0]['value']
    assert a['sites'][1]['native_score_recalculated']['value']==92
    assert b['sites'][1]['native_score_recalculated']['state']=='not_measured'
    assert a['sites'][1]['literal_entropy_bits']==b['sites'][1]['literal_entropy_bits']
    assert sheet==saved


def test_xmfa_changed_selection_and_case_are_recalculated_from_saved_data(monkeypatch):
    op,p=xmfa_operands(); sheet=extract_msa_sheet(**op)['value']; changed=deepcopy(p)
    changed['requests']=[changed['requests'][0]]; changed['requests'][0]['case_policy']='preserve'; changed['requests'][0]['selection']['block_columns']=[{'block_index':0,'columns_0based':[0,28,48]}]
    with monkeypatch.context() as guard:
        block_io(guard); result=calculate_msa(sheet,changed)
    assert result['results'][0]['value']['blocks'][0]['selected_column_count']['value']==3
