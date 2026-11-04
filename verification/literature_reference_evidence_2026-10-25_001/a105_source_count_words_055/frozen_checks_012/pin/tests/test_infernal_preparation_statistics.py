from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.infernal_preparation_models import extract_infernal_models
from gene_annotation_episode.infernal_preparation_schema import locator, record_key, value, validate_common_sheet
from gene_annotation_episode.infernal_preparation_statistics import (
    CM_ALGORITHMS, parse_cmbuild_summary, parse_cmcalibrate_output, parse_cmcalibrate_sidecar,
    parse_cmstat_output, populate_infernal_statistics_sheet,
)

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT/'verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native'
NEW = ROOT/'verification/tool_graders_infernal_preparation_statistics_2026-10-26_249/native'


def operation(program, mode, **settings):
    return dict(program=program, mode=mode, engine_version='1.1.5', settings=settings)


def payload(content, role, format, ref=None, completeness='complete'):
    data = content.encode() if isinstance(content, str) else content
    artifact = dict(role=role, format=format, artifact_ref=ref or role, sha256=hashlib.sha256(data).hexdigest(),
                    size_bytes=len(data), completeness=completeness)
    return dict(artifact=artifact, content=content)


def retained(case, filename, role, format, *, new=False, ref=None):
    return payload(((NEW if new else OLD)/case/filename).read_bytes(), role, format, ref)


def populate(op, inputs, outputs):
    artifacts = [p['artifact'] for mapping in (inputs, outputs) for items in mapping.values() for p in items]
    return populate_infernal_statistics_sheet(operation=op, artifacts=artifacts, inputs=inputs, outputs=outputs)


def model_fixture():
    """Explicit frozen A→B contract fixture, independent of A's parser."""
    loc = locator('model-input', 0, line_start=1, line_end=12)
    fields = {k: value(basis='model_header', unit=u) for k, u in
              dict(CLEN='nt', W='nt', NSEQ='count', EFFN='count', STATES='count', NODES='count', CKSUM='dimensionless', GA='bit', TC='bit', NC='bit').items()}
    for k, number in dict(CLEN=12, W=25, NSEQ=3, EFFN=3.0, STATES=40, NODES=10, CKSUM=1727146044).items():
        fields[k]['value'], fields[k]['state'] = number, 'present'
    return dict(kind='model', record_key=record_key('model-input', 'model', 0), locator=loc,
        format='infernal_cm_ascii', writer_version='1.1.5 | Sep 2023', model_type='cm', name='fixture246', accession='TEST246',
        description=None, alphabet='RNA', content_validation='parsed_headers_and_boundaries', fields=fields,
        flags=dict(RF='yes', CONS='yes', MAP='yes'), null_background=[], calibration=dict(ECMLC=None, ECMGC=None, ECMLI=None, ECMGI=None),
        efp7gf=None, filter_hmm=None,
        topology={k: value(n, basis='model_header') for k, n in dict(base_pair_nodes=4, bifurcation_nodes=0, total_nodes=10, total_states=40).items()},
        source_fields=dict(date=[], commands=[], other_headers=[]))


def actual_models():
    p = retained('cmbuild_hand', 'built.cm', 'models', 'infernal_cm_ascii', ref='model-input')
    return extract_infernal_models(p['content'], artifact=p['artifact'], format=p['artifact']['format'], engine_version='1.1.5')


def native_stat(case='cmstat_E', mode='scores_at_evalue', *, new=False, **settings):
    return populate(operation('cmstat', mode, **settings),
        {'models': [retained(case, 'model.cm', 'models', 'infernal_cm_ascii', new=new)]},
        {'stdout': [retained(case, 'stdout.txt', 'stdout', 'infernal_stdout', new=new)]})


@pytest.mark.parametrize('case', ['cmbuild_default', 'cmbuild_hand', 'cmbuild_noss'])
def test_build_native_rows_and_actual_model_and_alignment_bindings(case):
    settings = {'--noss': True} if case.endswith('noss') else {'--hand': True} if case.endswith('hand') else {}
    sheet = populate(operation('cmbuild', 'build', **settings),
        {'alignment': [retained(case, 'seed.sto', 'alignment', 'stockholm')]},
        {'built_models': [retained(case, 'built.cm', 'built_models', 'infernal_cm_ascii')],
         'stdout': [retained(case, 'stdout.txt', 'stdout', 'infernal_stdout')]})
    row = next(r for r in sheet['native_rows'] if r['kind'] == 'build')
    assert row['values']['nseq']['value'] == 3
    assert row['values']['consensus_length']['value'] == 12
    assert row['values']['base_pairs']['value'] == (0 if case.endswith('noss') else 4)
    assert row['values']['eff_nseq']['native_token'] == '3.00'
    assert row['model_keys'] == ['built_models#model/0']
    assert next(a for a in sheet['associations'] if a['relation'] == 'built_from')['status'] == 'validated'
    assert sheet['input_records'][0]['values']['checksum']['value'] == 1727146044
    assert not [i for i in sheet['issues'] if i['severity'] == 'error']
    validate_common_sheet(sheet)


def test_refine_iterations_are_native_optimization_rows():
    sheet = populate(operation('cmbuild', 'refine'),
        {'alignment': [retained('cmbuild_refine', 'seed.sto', 'alignment', 'stockholm', new=True)]},
        {'built_models': [retained('cmbuild_refine', 'built.cm', 'built_models', 'infernal_cm_ascii', new=True)],
         'stdout': [retained('cmbuild_refine', 'stdout.txt', 'stdout', 'infernal_stdout', new=True)],
         'processed_alignment': [retained('cmbuild_refine', 'processed.sto', 'processed_alignment', 'stockholm', new=True)],
         'refined_alignment': [retained('cmbuild_refine', 'refined.sto', 'refined_alignment', 'stockholm', new=True)]})
    iterations = [r for r in sheet['native_rows'] if r['kind'] == 'build_refinement']
    assert [r['identity']['iteration'] for r in iterations] == [1, 2]
    assert [r['values']['bit_score_sum']['value'] for r in iterations] == [41.11, 41.11]
    assert iterations[0]['values']['fractional_difference']['state'] == 'missing'
    assert iterations[1]['values']['fractional_difference']['value'] == 0
    assert len([r for r in sheet['output_records'] if r['kind'] == 'training_alignment']) == 2
    assert any(a['relation'] == 'built_from' and a['input_keys'] == ['refined_alignment#training_alignment/0'] for a in sheet['associations'])


@pytest.mark.parametrize('case,mode', [('cmcalibrate_tiny','calibrate'), ('cmcalibrate_merge','merge_scores'),
    ('cmcalibrate_forecast','forecast'), ('cmcalibrate_memreq_without_cpu_env','memory_estimate'),
    ('cmcalibrate_split','split_commands'), ('cmcalibrate_partition_1','partition_scores')])
def test_all_six_native_calibration_output_modes(case, mode):
    p = retained(case, 'stdout.txt', 'stdout', 'infernal_stdout')
    result = parse_cmcalibrate_output(p['content'], operation=operation('cmcalibrate', mode), artifact=p['artifact'])
    assert result['rows']
    assert not result['issues']
    if mode == 'calibrate':
        fits = [r for r in result['rows'] if r['kind'] == 'calibration']
        assert [r['identity']['algorithm'] for r in fits] == list(CM_ALGORITHMS)
        assert [r['values']['random_hit_count']['value'] for r in fits] == [3149, 3035, 4409, 3812]
        assert fits[2]['values']['mu_orig']['native_token'] == '-2.54'
        assert fits[2]['values']['mu_extrap']['state'] == 'not_measured'
    if mode == 'forecast':
        assert result['rows'][0]['values']['predicted_seconds']['value'] == 0
        assert result['rows'][0]['values']['predicted_seconds']['basis'] == 'native_prediction'
    if mode == 'memory_estimate':
        assert [r['values']['predicted_mb']['value'] for r in result['rows']] == [72.1, 288.4]
        assert [r['values']['cpu_count']['value'] for r in result['rows']] == [1, 4]


@pytest.mark.parametrize('kind,filename,nseries', [('hfile','hist.dat',8), ('sfile','survival.dat',12),
    ('qqfile','qq.dat',8), ('xfile','tail.dat',4)])
def test_complete_sidecar_arrays_native_and_explicit_model_fixture(kind, filename, nseries):
    p = retained('cmcalibrate_tiny', filename, kind, 'infernal_calibration_'+kind)
    for models in ([model_fixture()], actual_models()['records']):
        result = parse_cmcalibrate_sidecar(p['content'], kind=kind, operation=operation('cmcalibrate','calibrate'),
                                           artifact=p['artifact'], model_order=models)
        assert not result['issues']
        assert len(result['rows']) == nseries
        assert all(r['model_keys'] == ['model-input#model/0'] for r in result['rows'])
        assert sum(len(r['series']) for r in result['rows']) == len(p['content'].splitlines())-nseries
        if kind == 'hfile':
            assert sum(point['y']['value'] for point in result['rows'][0]['series']) == 3149
            assert result['rows'][0]['identity']['series_kind'] == 'observed_bin_count'
            assert result['rows'][1]['identity']['series_kind'] == 'fitted_expected_bin_count'
            assert result['rows'][0]['series'][0]['x']['native_token'] == '-15.200000'
        if kind == 'sfile':
            assert result['rows'][0]['series'][0]['y']['value'] == pytest.approx(1/3149, abs=5e-10)
            assert result['rows'][2]['identity']['series_kind'] == 'comparison_exponential_survival'
        if kind == 'qqfile':
            assert len(result['rows'][1]['series']) == 2
            assert result['rows'][1]['identity']['series_kind'] == 'identity_reference'


def test_fit_grid_missing_fits_stay_missing_and_not_chosen_calibration():
    p = retained('cmcalibrate_tiny', 'fits.dat', 'ffile', 'infernal_calibration_ffile')
    result = parse_cmcalibrate_sidecar(p['content'], kind='ffile', operation=operation('cmcalibrate','calibrate'),
                                       artifact=p['artifact'], model_order=actual_models()['records'])
    assert not result['issues']
    assert len(result['rows']) == 164
    assert {r['identity']['series_kind'] for r in result['rows']} == {'fit_grid'}
    assert result['rows'][0]['values']['tail_hit_count']['value'] == 3149
    assert result['rows'][-1]['values']['tail_hit_count']['value'] == 0
    assert result['rows'][-1]['values']['lambda']['native_token'] == 'N/A'
    assert result['rows'][-1]['values']['lambda']['state'] == 'missing'


def test_missing_unnamed_series_never_shifts_model_or_algorithm_join():
    p = retained('cmcalibrate_tiny', 'qq.dat', 'qqfile', 'infernal_calibration_qqfile')
    text = p['content'].decode().split('&\n',1)[1]
    q = payload(text, 'qqfile', 'infernal_calibration_qqfile')
    result = parse_cmcalibrate_sidecar(text, kind='qqfile', operation=operation('cmcalibrate','calibrate'),
                                      artifact=q['artifact'], model_order=[model_fixture()])
    assert len(result['rows']) == 7
    assert all(not r['model_keys'] and r['identity']['algorithm'] is None for r in result['rows'])
    assert any(i['code'].endswith('series_count_mismatch') for i in result['issues'])


def test_partition_arrays_counts_and_inert_commands():
    p = retained('cmcalibrate_partition_1', 'scores.dat', 'partition_scores', 'infernal_partition_scores')
    result = parse_cmcalibrate_sidecar(p['content'], kind='partition_scores', operation=operation('cmcalibrate','partition_scores', **{'--part':1,'--ptot':2}),
                                      artifact=p['artifact'], model_order=actual_models()['records'])
    assert not result['issues']
    assert [r['values']['score_count']['value'] for r in result['rows']] == [3149,3035,4409,3812]
    assert [len(r['series']) for r in result['rows']] == [3149,3035,4409,3812]
    assert result['rows'][0]['values']['requested_megabases']['value'] == .02
    assert result['rows'][0]['values']['requested_megabases']['unit'] == 'Mnt'
    bad = p['content'].replace(b'3149 ',b'3150 ',1)
    p = payload(bad,'partition_scores','infernal_partition_scores')
    result = parse_cmcalibrate_sidecar(bad, kind='partition_scores', operation=operation('cmcalibrate','partition_scores'), artifact=p['artifact'], model_order=[model_fixture()])
    assert len(result['rows'][0]['series']) == 3149
    assert any(i['code'].endswith('partition_count_mismatch') for i in result['issues'])
    commands = payload('cmcalibrate --part 1 --ptot 2 -L .02 model.cm\ncmcalibrate --part 2 --ptot 2 -L .02 model.cm\n', 'commands','infernal_commands')
    result = parse_cmcalibrate_sidecar(commands['content'],kind='commands',operation=operation('cmcalibrate','split_commands'),artifact=commands['artifact'],model_order=[])
    assert result['rows'][0]['values']['command_count']['value'] == 2


@pytest.mark.parametrize('case,mode', [('cmstat_summary','summary'),('cmstat_E','scores_at_evalue'),('cmstat_P','scores_at_pvalue'),
    ('cmstat_T','evalues_at_score'),('cmstat_GA','evalues_at_ga'),('cmstat_NC','evalues_at_nc'),('cmstat_TC','evalues_at_tc')])
def test_all_seven_cmstat_native_modes(case, mode):
    sheet = native_stat(case, mode)
    assert not sheet['issues']
    assert len(sheet['native_rows']) == (1 if mode == 'summary' else 4)
    assert all(r['model_keys'] == ['models#model/0'] for r in sheet['native_rows'])
    if mode == 'scores_at_evalue':
        assert [r['values']['threshold_bits']['value'] for r in sheet['native_rows']] == [45.32,36.71,41.88,42.23]
    if mode == 'scores_at_pvalue':
        assert [r['values']['threshold_bits']['value'] for r in sheet['native_rows']] == [4.14,2.60,2.66,2.18]
    if mode.startswith('evalues_at_') and mode != 'evalues_at_score':
        assert all(r['values']['threshold_bits']['native_token'] == '<not-set>' for r in sheet['native_rows'])


def test_actual_hmm_and_key_mode_associations():
    sheet = native_stat('cmstat_hmm_P','scores_at_pvalue',new=True, **{'--hmmonly':True,'-P':.01})
    assert [r['values']['threshold_bits']['value'] for r in sheet['native_rows']] == [3.77,-1.26,3.46,None]
    assert sheet['native_rows'][-1]['values']['threshold_bits']['state'] == 'incompatible'
    assert sheet['native_rows'][2]['identity']['algorithm'] == 'hmm_glocal_forward'
    sheet = native_stat('cmstat_key','scores_at_evalue',new=True, **{'--key':'SECOND249'})
    assert all(r['model_keys'] == ['models#model/1'] and r['identity']['native_index'] == 1 for r in sheet['native_rows'])
    sheet = native_stat('cmstat_noss_summary','summary')
    assert sheet['native_rows'][0]['identity']['model_family'] == 'hmm'
    assert sheet['native_rows'][0]['values']['cm_relative_entropy']['state'] == 'incompatible'


def test_invalid_native_numbers_and_partial_rows_preserve_useful_siblings():
    p = retained('cmstat_E','stdout.txt','stdout','infernal_stdout')
    bad = p['content'].replace(b'45.32',b'nan')
    q = payload(bad,'stdout','infernal_stdout',completeness='partial')
    result = parse_cmstat_output(bad,operation=operation('cmstat','scores_at_evalue'),artifact=q['artifact'])
    assert result['rows'][0]['values']['threshold_bits']['state'] == 'invalid'
    assert result['rows'][1]['values']['threshold_bits']['value'] == 36.71
    assert any(i['code'].endswith('capture_incomplete') for i in result['issues'])
    json.dumps(result,allow_nan=False)


def test_actual_calibration_header_kept_separate_from_stdout_precision():
    sheet = populate(operation('cmcalibrate','calibrate', **{'-L':.01}),
        {'models':[retained('cmcalibrate_tiny','original.cm','models','infernal_cm_ascii')]},
        {'calibrated_models':[retained('cmcalibrate_tiny','model.cm','calibrated_models','infernal_cm_ascii')],
         'stdout':[retained('cmcalibrate_tiny','stdout.txt','stdout','infernal_stdout')]})
    fits = [r for r in sheet['native_rows'] if r['kind'] == 'calibration' and r['identity']['algorithm'] == 'cm_local_cyk']
    assert [r['values']['lambda']['native_token'] for r in fits] == ['0.449','0.44855']
    assert [r['values']['mu_orig']['native_token'] for r in fits] == ['-2.54','-2.53576']
    assert any(a['relation'] == 'calibrated_from' and a['status'] == 'validated' for a in sheet['associations'])


def test_pure_readers_do_not_open_paths_network_or_run_programs(monkeypatch):
    import builtins
    import socket
    import subprocess
    p = retained('cmstat_E','stdout.txt','stdout','infernal_stdout')
    def forbidden(*args, **kwargs):
        raise AssertionError('pure reader attempted I/O')
    for module, name in ((builtins,'open'),(socket,'socket'),(subprocess,'Popen')):
        monkeypatch.setattr(module,name,forbidden)
    result = parse_cmstat_output(p['content'],operation=operation('cmstat','scores_at_evalue'),artifact=p['artifact'])
    assert len(result['rows']) == 4


def test_reordered_calibration_columns_join_by_declared_algorithm():
    text = ('# Calibration summary statistics:\n'
            '# model name loc ins glc cyk loc cyk glc ins loc cyk loc ins glc ins glc cyk glc ins loc cyk glc cyk loc ins\n'
            'm -1 -2 -3 -4 .3 .1 .4 .2 40 30 20 10\n')
    p = payload(text,'stdout','infernal_stdout')
    rows = parse_cmcalibrate_output(text,operation=operation('cmcalibrate','calibrate'),artifact=p['artifact'])['rows']
    assert [r['values']['mu_orig']['value'] for r in rows] == [-2,-4,-3,-1]
    assert [r['values']['lambda']['value'] for r in rows] == [.2,.4,.3,.1]
    assert [r['values']['random_hit_count']['value'] for r in rows] == [20,40,30,10]


def test_partial_partition_population_does_not_shift_algorithm_or_model():
    p = retained('cmcalibrate_partition_1','scores.dat','partition_scores','infernal_partition_scores')
    lines = p['content'].splitlines(keepends=True)
    q = payload(b''.join(lines[:2]+lines[3:]),'partition_scores','infernal_partition_scores')
    result = parse_cmcalibrate_sidecar(q['content'],kind='partition_scores',operation=operation('cmcalibrate','partition_scores'),
                                      artifact=q['artifact'],model_order=[model_fixture()])
    assert all(r['identity']['algorithm'] is None and not r['model_keys'] for r in result['rows'])


def test_multiple_stockholm_records_duplicate_names_and_partial_later_model():
    source = retained('cmbuild_hand','seed.sto','alignment','stockholm')
    model = retained('cmbuild_hand','built.cm','built_models','infernal_cm_ascii')
    summary = retained('cmbuild_hand','stdout.txt','stdout','infernal_stdout')
    source = payload(source['content']*2,'alignment','stockholm')
    model = payload(model['content']+model['content'].split(b'HMMER3/f',1)[0],'built_models','infernal_cm_ascii',completeness='partial')
    lines = summary['content'].splitlines(keepends=True)
    native_row = next(line for line in lines if line.strip().startswith(b'1 fixture246'))
    summary = payload(summary['content']+native_row.replace(b'1 fixture246',b'2 fixture246'),'stdout','infernal_stdout')
    sheet = populate(operation('cmbuild','build'),{'alignment':[source]},{'built_models':[model],'stdout':[summary]})
    assert len(sheet['input_records']) == 2
    assert sheet['input_records'][0]['record_key'] != sheet['input_records'][1]['record_key']
    assert sheet['native_rows'][0]['model_keys'] == ['built_models#model/0']
    assert sheet['native_rows'][1]['model_keys'] == []
    assert any(i['code'].endswith('model_population_incomplete') for i in sheet['issues'])


def test_selected_mode_mismatch_is_explicit_and_absent_annotation_is_not_zero():
    p = retained('cmstat_E','stdout.txt','stdout','infernal_stdout')
    result = parse_cmstat_output(p['content'],operation=operation('cmstat','scores_at_pvalue'),artifact=p['artifact'])
    assert any(i['code'].endswith('operation_parameter_mismatch') for i in result['issues'])
    alignment = retained('cmbuild_hand','seed.sto','alignment','stockholm')
    text = '\n'.join(s for s in alignment['content'].decode().splitlines() if not s.startswith('#=GC'))+'\n'
    sheet = populate(operation('cmbuild','build',**{'--hand':True}),{'alignment':[payload(text,'alignment','stockholm')]},
        {'built_models':[retained('cmbuild_hand','built.cm','built_models','infernal_cm_ascii')],
         'stdout':[retained('cmbuild_hand','stdout.txt','stdout','infernal_stdout')]})
    assert any(i['code'].endswith('alignment_rf_missing') for i in sheet['issues'])
    assert any(i['code'].endswith('alignment_structure_missing') for i in sheet['issues'])
    assert sheet['input_records'][0]['values']['rf_column_count']['state']=='missing'
