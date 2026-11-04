"""Source-executed native2.5.0 bytes; mutation cases are explicitly synthetic."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError, validate_native_document
from gene_annotation_episode.bvbrc_fastqutils_identity import native_ref
from gene_annotation_episode.bvbrc_fastqutils_native import parse_fastqutils_artifact
from gene_annotation_episode.bvbrc_fastqutils_samstat_svg import parse_samstat_html_2_5_0, parse_samstat_bvbrc_error_html

FIXTURES=Path(__file__).parent/'fixtures/bvbrc_fastqutils_samstat_svg'


def context(raw, *, version=None, fmt='samstat_html', scope='complete', identity='source_executed_synthetic'):
    return dict(analysis_id='samstat_current',document_id='report',task_ref='task:synthetic',
        content=dict(source_ref='source:synthetic',artifact_field='artifact_ref',artifact_ref='content:synthetic',
                     sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw)),
        native_name=None,declared_format=fmt,producer_version=version,transfer_scope=scope,identity=identity)


def read(name):
    return (FIXTURES/('2_5_0/'+name if not name.startswith('caller_') else name)).read_bytes()


def parse(raw,**kwargs):
    return parse_fastqutils_artifact(raw,context=context(raw,**kwargs))


def cells(doc,metric):
    return [c for c in doc['cells'] if c['metric']==metric]


def one(doc,metric):
    found=cells(doc,metric)
    assert len(found)==1
    return found[0]


def bins(doc,ordinal):
    pop=next(p for p in doc['populations'] if p['population_key']=='samstat_report_records' and p['population_ordinal']==ordinal)
    return [c for c in cells(doc,'samstat_alignment_bin_count') if c['population_ref']==pop['id']]


@pytest.mark.parametrize('name',[str(p.relative_to(FIXTURES)) for p in sorted(FIXTURES.rglob('*.html'))])
def test_all_retained_native_artifacts_parse_closed_and_keep_exact_locations(name):
    raw=(FIXTURES/name).read_bytes();doc=parse(raw)
    validate_native_document(doc)
    assert doc['parse_scope']=='complete'
    assert doc['artifact']['sha256']==hashlib.sha256(raw).hexdigest()
    assert doc['artifact']['identity']=='source_executed_synthetic'
    assert not doc['alignment_records'] and not doc['sequence_records'] and not doc['categories']
    assert all(p['scope'] in ('unknown','partial') and p['quality_encoding']=='unknown' for p in doc['populations'])
    starts=[]
    for i,cell in enumerate(doc['cells']):
        assert cell['id']==native_ref('cell',context(raw),i)
        loc=cell['locator'];starts.append(loc['byte_start'])
        assert 0<=loc['byte_start']<=loc['byte_end']<=len(raw)
        if cell['native_token'] is not None:
            assert raw[loc['byte_start']:loc['byte_end']].decode()==cell['native_token']
    assert starts==sorted(starts)


@pytest.mark.parametrize('name',['mixed.sam.samstat.html','mixed.bam.samstat.html'])
def test_mixed_native_counts_mate_strata_exclusions_and_quality(name):
    doc=parse(read(name))
    assert one(doc,'samstat_alignment_total_count')['value']==10
    assert one(doc,'samstat_total_base_count')['value']==50
    assert [c['value'] for c in bins(doc,0)]==[4,3,2,1]
    assert [c['value'] for c in bins(doc,1)]==[4,2,2,1]
    assert [c['value'] for c in bins(doc,2)]==[0,1,0,0]
    assert bins(doc,0)[0]['axis']==dict(kind='mapq',label='MAPQ >= 30',lower=30,upper=255)
    assert 'samstat_mapq255_merged' in bins(doc,0)[0]['diagnostic_codes']
    assert one(doc,'samstat_secondary_excluded_count')['value']==1
    assert one(doc,'samstat_supplementary_excluded_count')['value']==1
    assert one(doc,'samstat_error_probability_mean_phred')['native_token']=='16.2'
    assert one(doc,'samstat_error_probability_mean_phred')['value']==16.2
    assert one(doc,'samstat_reported_mapped_percent')['value']==90.0
    assert one(doc,'samstat_gap_compressed_median_identity_percent')['state']=='not_measured'
    pops={p['population_ordinal']:p for p in doc['populations'] if p['population_key']=='samstat_report_records'}
    assert pops[1]['disjoint_from_refs']==[pops[2]['id']]
    assert pops[1]['parent_population_refs']==[pops[0]['id']]
    assert not pops[0]['disjoint_from_refs']


def test_quality_mean_is_native_error_probability_mean_and_not_optional_json():
    doc=parse(read('boundaries/quality_pair.sam.samstat.html'))
    assert one(doc,'samstat_error_probability_mean_phred')['value']==3.0
    assert not cells(doc,'samstat_legacy_mean_phred')


def test_exact_si_sublabel_is_arithmetic_value_and_display_retained():
    doc=parse(read('precision/peek10001.sam.samstat.html'))
    for metric in ('samstat_alignment_total_count','samstat_total_base_count'):
        cell=one(doc,metric)
        assert (cell['value'],cell['native_token'],cell['precision'])==(10001,'10,001','exact_for_retained_population')
    assert {'10.0 k','10.0 kb'}<={r['value'] for r in doc['labels']}


def test_large_lengths_retain_native_unit_and_rounding():
    doc=parse(read('precision/long_lengths.fastq.samstat.html'))
    assert (one(doc,'samstat_median_length')['value'],one(doc,'samstat_n50_length')['value'])==(10.1,11.0)
    assert one(doc,'samstat_median_length')['unit']=='kbp'
    assert one(doc,'samstat_median_length')['precision']=='native_rounded'
    assert one(doc,'samstat_total_base_count')['value']==21110
    assert not any(c['value'] in (10123,10987) for c in doc['cells'])


def test_empty_known_alignment_and_unknown_input_kind_remain_distinct():
    sam=parse(read('empty.sam.samstat.html'))
    assert one(sam,'samstat_alignment_total_count')['value']==0
    assert not cells(sam,'samstat_alignment_bin_count')
    unknown=parse(read('empty.fastq.samstat.html'))
    cell=one(unknown,'samstat_reported_item_count')
    assert (cell['value'],cell['state'],cell['unit'],cell['population_ref'])==(0,'available','native_count',None)
    assert not unknown['populations']
    assert any(r['code']=='source_row_absent' and r['required_data']=='native_execution_evidence' for r in unknown['requirements'])


def test_missing_sequence_and_quality_are_not_zero_measurements():
    doc=parse(read('missing_sequence.sam.samstat.html'))
    assert (one(doc,'samstat_total_base_count')['state'],one(doc,'samstat_total_base_count')['value'])==('not_measured',None)
    assert not cells(doc,'samstat_error_probability_mean_phred')
    missing=parse(read('missing_quality.sam.samstat.html'))
    assert not cells(missing,'samstat_error_probability_mean_phred')
    assert not cells(missing,'samstat_min_read_quality_bin')


def test_native_clipping_identity_and_conditional_notes():
    doc=parse(read('errors.sam.samstat.html'))
    assert one(doc,'samstat_soft_clipped_base_percent')['value']==15.4
    assert one(doc,'samstat_mismatch_unavailable_record_count')['value']==1
    assert one(doc,'samstat_identity_unavailable_record_count')['value']==5
    assert [c['value'] for c in cells(doc,'samstat_mapped_note_record_count')]==[5,5]
    known=parse(read('boundaries/known_identity.sam.samstat.html'))
    assert one(known,'samstat_gap_compressed_median_identity_percent')['value']==80.0
    assert one(known,'samstat_gap_compressed_median_identity_percent')['precision']=='native_estimator'
    assert not cells(known,'samstat_identity_unavailable_record_count')


def test_repeated_mate_figure_extrema_have_global_scope_and_distinct_occurrences():
    doc=parse(read('mixed60.sam.samstat.html'))
    pop0=next(p['id'] for p in doc['populations'] if p['population_key']=='samstat_report_records' and p['population_ordinal']==0)
    for metric,answer in [('samstat_min_length',4),('samstat_max_length',8),('samstat_min_read_quality_bin',5),('samstat_max_read_quality_bin',40)]:
        repeated=cells(doc,metric)
        assert len(repeated)==2
        assert all(c['value']==answer and c['population_ref']==pop0 for c in repeated)
        assert len({c['section_ordinal'] for c in repeated})==2
    assert any(r['code']=='samstat_svg_values_not_retained' and r['required_data']=='requested_measurement' for r in doc['requirements'])
    assert not cells(doc,'samstat_base_A_count') and not cells(doc,'samstat_length_density')


def test_prefix_available_literal_values_partial_population_not_full_input():
    doc=parse(read('boundaries/peek10001.sam.samstat.html'))
    assert doc['parse_scope']=='complete'
    assert all(p['scope']=='partial' for p in doc['populations'])
    assert one(doc,'samstat_alignment_total_count')['value']==10
    assert all(c['state']=='available' for c in bins(doc,0))
    assert any(d['code']=='samstat_native_prefix' for d in doc['diagnostics'])


def test_truncated_mapping_retains_summary_and_complete_rows():
    raw=read('mixed.sam.samstat.html');raw=raw[:raw.index(b'<th scope="row">Unmapped')]
    doc=parse(raw,identity='handcrafted_synthetic',scope='partial')
    assert doc['parse_scope']=='partial'
    assert one(doc,'samstat_alignment_total_count')['value']==10
    assert [c['value'] for c in bins(doc,0)]==[4,3,2]
    assert any(r['required_data']=='complete_native_bytes' for r in doc['requirements'])


@pytest.mark.parametrize('mutation', ['count','column','duplicate_row','malformed_row','duplicate_card','missing_exact'])
def test_conflicting_and_malformed_sections_preserve_independent_values(mutation):
    raw=read('mixed.sam.samstat.html')
    if mutation=='count': raw=raw.replace(b'<td class="num">4</td>',b'<td class="num">8</td>',1)
    elif mutation=='column': raw=raw.replace(b'>Read 1</th>',b'>Unknown</th>',1)
    elif mutation=='duplicate_row':
        row=re.search(rb'<tbody>\s*(<tr>.*?</tr>)',raw,re.S)[1];raw=raw.replace(b'</tbody>',row+b'</tbody>',1)
    elif mutation=='malformed_row': raw=raw.replace(b'<td class="num">4</td>',b'<td class="num">-4</td>',1)
    elif mutation=='duplicate_card': raw=raw.replace(b'</dl>',b'<div><dt>Reads (R1+R2)</dt><dd>12</dd></div></dl>',1)
    elif mutation=='missing_exact':
        raw=read('precision/peek10001.sam.samstat.html').replace(b'<span class="sub">10,001</span>',b'',1)
    doc=parse(raw,identity='handcrafted_synthetic')
    assert doc['parse_scope']=='partial'
    assert one(doc,'samstat_error_probability_mean_phred')['state']=='available'
    assert any(c['state'] in ('incompatible','malformed') for c in doc['cells']) or mutation=='column'


@pytest.mark.parametrize('version',['2.2.3','2.6.0'])
def test_supplied_version_conflicts_are_typed_and_not_numeric(version):
    doc=parse(read('mixed.sam.samstat.html'),version=version)
    assert doc['parse_scope']=='unsupported' and not doc['cells']
    assert {version,'2.5.0'}<={r['value'] for r in doc['labels']}
    assert any(r['code']=='native_header_conflict' for r in doc['diagnostics'])


def test_unknown_native_version_and_conflicting_footer_preserve_bytes():
    raw=read('mixed.sam.samstat.html')
    for changed in (raw.replace(b'SAMStat 2.5.0',b'SAMStat 2.6.0'), raw.replace(b'made by SAMStat 2.5.0',b'made by SAMStat 2.6.0')):
        doc=parse(changed,identity='handcrafted_synthetic')
        assert doc['parse_scope']=='unsupported' and not doc['cells']
        assert doc['raw_blocks'] and doc['artifact']['sha256']==hashlib.sha256(changed).hexdigest()


def test_byte_locations_handle_utf8_and_html_entities():
    raw=read('mixed.sam.samstat.html').replace(b'mixed.sam', 'α&amp;β.sam'.encode())
    doc=parse(raw,identity='handcrafted_synthetic')
    assert any(l['value']=='α&β.sam' for l in doc['labels'])
    for cell in doc['cells']:
        a,b=cell['locator']['byte_start'],cell['locator']['byte_end']
        assert raw[a:b].decode()==cell['native_token']


def test_source_established_strict_upper_bound_and_estimated_length_tokens():
    raw=read('mixed.sam.samstat.html').replace(b'</ul>',b'<li>&lt;0.1% of bases lie beyond position 1000 and are not in plots 3-5.</li></ul>',1)
    raw=raw.replace(b'median 4 bp',b'median ~1,050 bp')
    doc=parse(raw,identity='handcrafted_synthetic')
    bound=one(doc,'samstat_beyond_axis_percent_upper_bound')
    assert (bound['value'],bound['native_token'])==(0.1,'&lt;0.1')
    estimate=one(doc,'samstat_median_length')
    assert (estimate['value'],estimate['precision'])==(1050,'native_estimator')


def test_scripts_and_svg_geometry_cannot_supply_measurements(monkeypatch):
    raw=read('mixed.sam.samstat.html')
    script=b'<script>throw new Error("execute"); var data=[99999]; document.write("SAMStat 9.9.9");</script>'
    raw=raw.replace(b'</head>',script+b'</head>').replace(b'<path ',b'<path data-numeric="99999" ')
    def forbidden(*a,**k): raise AssertionError('parser attempted external work')
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(subprocess,'run',forbidden)
    doc=parse(raw,identity='handcrafted_synthetic')
    assert doc['artifact']['producer_version']=='2.5.0'
    assert one(doc,'samstat_alignment_total_count')['value']==10
    assert not any(c['value']==99999 for c in doc['cells'])
    assert any(r['native_name']=='script' for r in doc['raw_blocks'])


def test_caller_failure_is_fixed_failed_sentinel_with_no_populations():
    raw=read('caller_error_stub.all.bam.samstat.html')
    doc=parse(raw,version='2.5.0')
    assert doc['artifact']['actual_format']=='samstat_bvbrc_error_html'
    assert doc['artifact']['producer_name']=='FastqUtils' and doc['artifact']['producer_version'] is None
    assert len(doc['cells'])==1 and not doc['populations'] and not doc['native_lineage']
    cell=doc['cells'][0]
    assert (cell['metric'],cell['state'],cell['value'],cell['native_token'],cell['precision'])==('samstat_alignment_total_count','failed',None,None,'not_reported')
    assert cell['population_ref'] is None and cell['axis']['kind']=='none'
    assert {'return code: 1',"command: ['/bin/false']",'output: None','stdout: None','stderr: None','2.5.0'}<={l['value'] for l in doc['labels']}
    assert doc['raw_blocks'][0]['kind']=='error_report'
    assert any(r['code']=='samstat_caller_failure' and r['required_data']=='native_execution_evidence' for r in doc['requirements'])


def test_contract_violations_raise_but_bad_native_bytes_return_typed():
    raw=read('mixed.sam.samstat.html');ctx=context(raw)
    wrong=deepcopy(ctx);wrong['content']['sha256']='0'*64
    with pytest.raises(FastqUtilsContractError): parse_samstat_html_2_5_0(raw,context=wrong)
    with pytest.raises(FastqUtilsContractError): parse_samstat_html_2_5_0(raw.decode(),context=ctx)
    invalid=b'\xff';doc=parse(invalid,identity='handcrafted_synthetic')
    assert doc['parse_scope']=='malformed' and not doc['cells']
    doc=parse_samstat_bvbrc_error_html(b'<html>broken</html>',context=context(b'<html>broken</html>'))
    assert doc['parse_scope']=='malformed' and not doc['cells']
