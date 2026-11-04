"""Real native-reader/A/C composition using retained public bytes, synthetic custody."""
from copy import deepcopy
import importlib

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode import bvbrc_proteome_bundle_v2_contracts as c
from gene_annotation_episode import bvbrc_proteome_bundle_v2_resolution as provider
from gene_annotation_episode.bvbrc_proteome_directional_fact_contracts import requested_form_schema_v2
from test_bvbrc_proteome_bundle_resolution import fixture as legacy_fixture, member
from test_bvbrc_proteome_directional import native
from test_bvbrc_proteome_directional_calculators import PARAMETERS


def fixture(key='2011', *, mixed=False, exact=False, supplementary=False):
    case=legacy_fixture(supplementary=supplementary)
    raw=native(key)
    artifact=member(raw,name='directional',role='proteome_directional_report',fmt='ncbi_blastall_blastp_pairwise_text_v1')
    artifact['declared_format'].update(version={'2011':'2.0.11','2202':'2.2.2','2221':'2.2.21'}[key],mode='protein_database_search_pairwise_display')
    artifact['requirement_ids']=['directional']
    case['bundle']['artifacts'] = case['bundle']['artifacts'] + [artifact] if mixed else [artifact]
    case['bundle']['acquisition_receipt_refs']=[a['transfer']['receipt_ref'] for a in case['bundle']['artifacts']]
    case['artifact_bytes']['directional']=raw
    selected=dict(document_id='d',report_key='logical-report',role=artifact['role'],declared_format=deepcopy(artifact['declared_format']))
    selected.update(source_ref='directional',raw_artifact_ref='directional') if exact else selected.update(requirement_id='directional')
    case['parameters'].update(version='bvbrc_proteome_bundle_parameters_v2',directional_documents=[selected],directional_calculation_parameters=deepcopy(PARAMETERS))
    if not mixed: case['parameters'].update(native_documents=[],primary_document_id=None,calculation_parameters=None)
    case['requested_form']=requested_form_schema_v2({'count':dict(kind='directional_count',scope='report',document_id='d',metric='displayed_query_count')})
    return case


def selector(case):
    p=case['parameters']
    return dict(version='bvbrc_appservice_result_selector_v1',endpoint='requested_projection',
        requirements=[dict(requirement_id=s['requirement_id'],role=s['role'],required=True,declared_format=deepcopy(s['declared_format']),
            producer_rule_evidence=None,exact_object=None) for s in p['native_documents']+p['directional_documents'] if 'requirement_id' in s],
        adapter=dict(adapter_id='bvbrc_proteome',adapter_version='2',parameters=deepcopy(p)),requested_schema=deepcopy(case['requested_form']),
        supplied_metadata=[],supplied_contents=[],supplied_capabilities=[])


def append_document(case, *, document_id='second', raw=None):
    """A distinct synthetic source occurrence, never inferred from byte equality."""
    raw = case['artifact_bytes']['directional'] if raw is None else raw
    first = case['parameters']['directional_documents'][0]
    artifact = member(raw, name=document_id, role=first['role'])
    artifact['declared_format'] = deepcopy(first['declared_format'])
    artifact['requirement_ids'] = [document_id]
    case['bundle']['artifacts'].append(artifact)
    case['bundle']['acquisition_receipt_refs'].append(artifact['transfer']['receipt_ref'])
    case['artifact_bytes'][document_id] = raw
    case['parameters']['directional_documents'].append(dict(document_id=document_id, report_key=document_id,
        requirement_id=document_id, role=first['role'], declared_format=deepcopy(first['declared_format'])))


def test_directional_only_calls_real_producers_once_and_never_legacy_projection(monkeypatch):
    case=fixture(); before=deepcopy(case); calls={}
    from gene_annotation_episode import bvbrc_proteome_directional_numerical_contracts as numerical
    full_validation = numerical._validate_components
    def counted_validation(*args, **kwargs):
        calls['full_producer_validation'] = calls.get('full_producer_validation', 0) + 1
        return full_validation(*args, **kwargs)
    monkeypatch.setattr(numerical, '_validate_components', counted_validation)
    for name in ('parse_genome_comparison_directional_report','build_directional_sheet','calculate_directional_components'):
        fn=getattr(provider,name)
        def counted(*args,_name=name,_fn=fn,**kwargs):
            calls[_name]=calls.get(_name,0)+1
            return _fn(*args,**kwargs)
        monkeypatch.setattr(provider,name,counted)
    def fail(*a,**k):raise AssertionError('legacy consume_bundle is not v2 construction')
    monkeypatch.setattr(provider.legacy,'consume_bundle',fail)
    result=adapter.consume_bundle(**case)
    assert result['facts']['count']['cell']['value']==1
    assert case==before
    assert len(calls) == 4 and set(calls.values()) == {1}
    assert result['components']['legacy'] is None
    assert result['sheet']['numerical_sheet']['directional_operand_binding']=='unbound'


@pytest.mark.parametrize('exact',[False,True])
def test_retained_native_no_hit_zero_is_explicit(exact):
    result=adapter.consume_bundle(**fixture(exact=exact))
    query=result['components']['directional']['components']['reports'][0]['queries'][0]
    assert query['any_displayed_subject_query_paired_union']['coverage']['value']==dict(numerator=0,denominator=102,decimal='0.000000000000000000')
    assert query['display_state']=='native_no_hit_claim'


def test_wrong_original_task_retains_precise_global_failure_before_parsing(monkeypatch):
    case = fixture()
    case['bundle']['artifacts'][0]['task_association']['task_id'] = 'foreign-task'
    def forbidden(*args, **kwargs): raise AssertionError('wrong-task artifact reached native parser')
    monkeypatch.setattr(provider, 'parse_genome_comparison_directional_report', forbidden)
    with pytest.raises(c.ProteomeBundleV2Error, match='proteome_original_task_conflict') as failure:
        adapter.consume_bundle(**case)
    assert failure.value.path == ''  # The host's cross-task diagnostic is global.


@pytest.mark.parametrize('mode,code',[('missing','document_missing'),('ambiguous','document_ambiguous'),('digest','artifact_digest_mismatch'),
    ('role','artifact_binding_conflict'),('format','format_incompatible'),('range','nonzero_range_unsupported'),('request_range','nonzero_range_unsupported'),('near','artifact_binding_conflict')])
def test_scoped_document_failures_preserve_selected_empty_sheet(mode,code):
    case=fixture(exact=mode=='near'); a=case['bundle']['artifacts'][0]
    if mode=='missing':case['bundle']['artifacts']=[]
    elif mode=='ambiguous':case['bundle']['artifacts'].append(deepcopy(a))
    elif mode=='digest':case['artifact_bytes']['directional']=b'wrong bytes'
    elif mode=='role':a['role']='unrelated'
    elif mode=='format':a['declared_format']['producer_source_ref']='other-source'
    elif mode=='range':a['transfer'].update(object_complete='no',observed_range=dict(start=1,end_inclusive=a['byte_count'],total_size=a['byte_count']+1),total_size=a['byte_count']+1)
    elif mode=='request_range':a['transfer'].update(object_complete='unknown',requested_range=[1,None])
    elif mode=='near':a['raw_artifact_ref']='different-artifact'
    result=adapter.consume_bundle(**case)
    assert result['sheet']['input_resolution'][0]['result_index'] is None
    assert 'proteome_directional_'+code in {r['reason_code'] for r in result['missing_requirements']}
    assert result['sheet']['directional_sheet_result']['sheet']['reader_results']==[]
    assert result['facts']['count']['availability']=='unavailable'


def test_joint_duplicate_selection_is_rejected_before_either_reader(monkeypatch):
    case=fixture(mixed=True)
    case['parameters']['native_documents'][0].update(source_ref='directional',raw_artifact_ref='directional')
    def fail(*a,**k):raise AssertionError('duplicate source was parsed')
    monkeypatch.setattr(provider,'parse_genome_comparison_directional_report',fail)
    monkeypatch.setattr(provider.legacy,'parse_genome_comparison',fail)
    result=adapter.consume_bundle(**case)
    assert all(r['result_index'] is None and r['state']=='invalid' for r in result['sheet']['input_resolution'])


def test_missing_first_document_does_not_shift_logical_target():
    case=fixture(); first=deepcopy(case['parameters']['directional_documents'][0]); first.update(document_id='missing',report_key='missing',requirement_id='absent')
    case['parameters']['directional_documents'].insert(0,first)
    result=adapter.consume_bundle(**case)
    assert [r['result_index'] for r in result['sheet']['input_resolution']]==[None,0]
    assert result['facts']['count']['context']['target']['report_ordinal']==0
    assert result['sheet']['directional_results'][0]['report_key']=='logical-report'


def test_version_conflict_preserves_native_observation_and_arithmetic():
    case=fixture(); case['parameters']['directional_documents'][0]['declared_format']['version']='2.2.2'
    case['bundle']['artifacts'][0]['declared_format']['version']='2.2.2'
    result=adapter.consume_bundle(**case)
    assert result['sheet']['input_resolution'][0]['state']=='incompatible'
    assert result['components']['directional']['components']['reports'][0]['displayed_query_count']['value']==1
    assert result['facts']['count']['availability']=='incompatible'


def test_zero_origin_partial_bytes_keep_exact_completeness():
    case=fixture();case['bundle']['artifacts'][0]['transfer'].update(body_complete=False,object_complete='no')
    result=adapter.consume_bundle(**case)
    assert result['sheet']['directional_results'][0]['source']['body_complete'] is False
    assert result['sheet']['input_resolution'][0]['state']=='partial'
    assert result['facts']['count']['cell']['value']==1


@pytest.mark.parametrize('corrupt',[False,True])
def test_malformed_native_result_retained_but_corrupt_reader_object_isolated(monkeypatch,corrupt):
    case=fixture()
    if corrupt:
        monkeypatch.setattr(provider,'parse_genome_comparison_directional_report',lambda *a,**k:{'parse_state':'ok'})
    else:
        raw=b'<html>this is not BLAST</html>'
        a=member(raw,name='directional',role='proteome_directional_report')
        a['declared_format']=case['bundle']['artifacts'][0]['declared_format'];a['requirement_ids']=['directional']
        case['bundle']['artifacts']=[a];case['artifact_bytes']['directional']=raw
    result=adapter.consume_bundle(**case)
    assert len(result['sheet']['directional_results'])==(0 if corrupt else 1)
    if not corrupt:assert result['sheet']['directional_results'][0]['parse_state']=='failure'


def test_mixed_native_and_directional_preserve_separate_meanings():
    result=adapter.consume_bundle(**fixture(mixed=True,supplementary=True))
    assert result['components']['legacy']['value']['tracks'][0]['first_hsp_identity_summary']['mean']['value']==.4375
    assert result['sheet']['numerical_sheet']['legacy_sheet']['directional_attachment'] is None
    assert result['components']['directional']['components']['reports'][0]['displayed_query_count']['value']==1


def test_native_only_v2_keeps_directional_wrappers_null_and_calls_no_directional_producer(monkeypatch):
    case = fixture(mixed=True, supplementary=True)
    case['parameters'].update(directional_documents=[], directional_calculation_parameters=None)
    case['requested_form'] = requested_form_schema_v2({'mean': {'kind': 'measurement', 'target': 'summary',
        'track_key': 'comp_genome_2', 'summary': 'first_hsp_identity_summary', 'metric': 'mean'}})
    def forbidden(*args, **kwargs): raise AssertionError('unselected directional producer ran')
    for name in ('parse_genome_comparison_directional_report', 'build_directional_sheet', 'calculate_directional_components'):
        monkeypatch.setattr(provider, name, forbidden)
    result = adapter.consume_bundle(**case)
    assert result['facts']['mean']['cell']['value'] == .4375
    assert result['sheet']['directional_results'] == []
    assert result['sheet']['directional_sheet_result'] is result['components']['directional'] is None
    assert result['sheet']['numerical_sheet']['directional_sheet'] is None


def test_exact_and_requirement_duplicate_rejected_before_reading(monkeypatch):
    case = fixture()
    second = deepcopy(case['parameters']['directional_documents'][0])
    second.pop('requirement_id')
    second.update(document_id='other-label', report_key='other-label', source_ref='directional', raw_artifact_ref='directional')
    case['parameters']['directional_documents'].append(second)
    def forbidden(*args, **kwargs): raise AssertionError('duplicate selections reached parser')
    monkeypatch.setattr(provider, 'parse_genome_comparison_directional_report', forbidden)
    result = adapter.consume_bundle(**case)
    assert all(row['state'] == 'invalid' and row['result_index'] is None for row in result['sheet']['input_resolution'])
    assert {r['reason_code'] for r in result['missing_requirements']} >= {'proteome_directional_duplicate_document_selection'}


def test_equal_bytes_in_distinct_source_occurrences_are_retained_without_deduplication():
    case = fixture()
    append_document(case)
    result = adapter.consume_bundle(**case)
    assert [r['result_index'] for r in result['sheet']['input_resolution']] == [0, 1]
    readers = result['sheet']['directional_results']
    assert readers[0]['source']['content']['sha256'] == readers[1]['source']['content']['sha256']
    assert readers[0]['source']['content']['source_ref'] != readers[1]['source']['content']['source_ref']
    assert result['sheet']['numerical_sheet']['directional_operand_binding'] == 'unbound'


@pytest.mark.parametrize('failure', ['missing', 'ambiguous', 'digest', 'malformed'])
def test_bad_document_does_not_erase_valid_neighbor(failure):
    case = fixture()
    append_document(case)
    if failure == 'missing': case['bundle']['artifacts'].pop(0)
    elif failure == 'ambiguous': case['bundle']['artifacts'].append(deepcopy(case['bundle']['artifacts'][0]))
    elif failure == 'digest': case['artifact_bytes']['directional'] = b'changed'
    else:
        raw = b'BLASTN 2.2.2\nunsupported selected protein mode\n'
        a = member(raw, name='directional', role='proteome_directional_report')
        a['declared_format'] = case['bundle']['artifacts'][0]['declared_format']
        a['requirement_ids'] = ['directional']
        case['bundle']['artifacts'][0] = a
        case['artifact_bytes']['directional'] = raw
    result = adapter.consume_bundle(**case)
    rows = result['sheet']['input_resolution']
    assert rows[1]['state'] == 'resolved'
    report = result['components']['directional']['components']['reports'][rows[1]['result_index']]
    assert report['displayed_query_count']['value'] == 1
    assert result['sheet']['directional_results'][rows[1]['result_index']]['report_key'] == 'second'


@pytest.mark.parametrize('second', ['Query: 5 FGHI 8\n', 'Query: 5 F?HI 8\nSbjct: 5 FGHI 8\n',
    'Query: 5 FGHI 9\nSbjct: 5 FGHI 8\n'])
def test_valid_subset_and_precise_geometry_failures_survive_provider_and_saved_checks(second, monkeypatch):
    case = fixture()
    raw = ('BLASTP 2.2.2\nQuery= q\n (10 letters)\n> s\n Length = 10\n'
        ' Score = 20 bits (40), Expect = e-30\n Identities = 8/8 (100%)\n'
        'Query: 1 ACDE 4\nSbjct: 1 ACDE 4\n' + second + 'S2: 40 (20 bits)\n').encode()
    a = member(raw, name='directional', role='proteome_directional_report')
    declaration = deepcopy(case['parameters']['directional_documents'][0]['declared_format'])
    declaration['version'] = '2.2.2'
    a.update(declared_format=declaration, requirement_ids=['directional'])
    case['bundle']['artifacts'] = [a]
    case['artifact_bytes']['directional'] = raw
    case['parameters']['directional_documents'][0]['declared_format'] = declaration
    result = adapter.consume_bundle(**case)
    subject = result['components']['directional']['components']['reports'][0]['queries'][0]['subjects'][0]
    support = subject['coverage']['query_trace_paired_union']['support']
    assert len(support['included_blocks']) == len(support['excluded_blocks']) == 1
    assert not support['complete_for_displayed_blocks']
    assert subject['coverage']['query_trace_paired_union']['count']['value'] == 4
    assert subject['compatible_unique_pair_symbol_identity']['state'] == 'missing'
    from test_bvbrc_proteome_directional_saved_validation import check, forbid_producers
    forbid_producers(monkeypatch)
    assert check(case, result) == (result['sheet'], result['components'])
