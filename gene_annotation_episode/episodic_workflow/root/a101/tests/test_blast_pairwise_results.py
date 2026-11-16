"""Native numerical examples and synthetic missing/custody counterexamples."""
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_results import populate_blast_pairwise_sheet, calculate_blast_pairwise_components

ROOT=Path(__file__).resolve().parents[5]


def components(sheet):return calculate_blast_pairwise_components(sheet)['components']


@pytest.mark.parametrize('filename,fmt',[('native_pair_result.json','json15'),('native_pair_result.tsv','tabular7')])
def test_existing_253_column_fixture_retains_its_original_meaning(filename,fmt):
    descriptors={axis:{'subject_ref':axis,'length':length,'molecule':'protein','artifact_key':axis,
        'native_id':identifier,'selected_interval':None} for axis,length,identifier in [
            ('query',253,'public_ybhP_pair_test'),('reference',243,'synthetic_deletion_and_substitutions')]}
    operands=[{'role':'query' if axis=='query' else 'subject',**row,'record_ordinal':0,
        'native_title':row['native_id'],'identity':None} for axis,row in descriptors.items()]
    invocation={'execution_program':'blastp','scientific_mode':'pairwise','resource_kind':'local','query_kind':'sequence','reference_kind':'sequence',
        'request':{},'effective_options':{},'operands':operands,'completion':{'native_returncode':0,'producer_complete':True}}
    raw=(ROOT/'gene_annotation_episode/episodic_workflow/root/a101/tests/fixtures/blast_grading_inputs'/filename).read_bytes()
    collection=parse_blast_report_collection({'original':raw},artifacts=[{'artifact_key':'original','role':'primary_report',
        'format':fmt,'fields':None,'delimiter':None if fmt=='json15' else '\t'}],invocation=invocation)
    result=components(populate_blast_pairwise_sheet(collection['searches'][0],operand_bindings=descriptors))
    hsp=result['hsps'][0]['components']
    assert hsp['counts']['alignment_columns']==253 and hsp['counts']['paired_columns']==243
    assert hsp['counts']['identical_pairs']==238 and hsp['counts']['reference_gap_columns']==10
    assert hsp['fractions']['query_paired_coverage']==pytest.approx(243/253)
    assert hsp['fractions']['reference_paired_coverage']==1

