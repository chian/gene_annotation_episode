"""218 fixture selection and evidence checks; no scientific implementation."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import uuid

import test_bvbrc_fastqutils_episode_flow as host
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_parameters
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_episodes import ExecutionEpisodes

HERE = Path(__file__).resolve().parent
NAMES = ('report',)
METRICS = ('samstat_report_mapped_record_fraction', 'samstat_report_ge30_record_fraction')
EXPECTED = {'current': ((9, 10), (4, 10)), 'legacy': ((10, 11), (5, 11))}
VERSIONS = {'current': '2.5.0', 'legacy': '2.2.3'}
HASHES = {'current': 'e7cdccbe6c1225fe02f13d1a51297ab8e794ab31599b1d23039441aad19c4d19',
          'legacy': '626fe9b5441283df466c41f5bc119e165b4b4bd0e371154149b223dfcaedad74'}
OUTPUTS = {'report': ('/fixture/output/mixed.sam.samstat.html', str(uuid.uuid5(
    uuid.NAMESPACE_URL, 'controlled-samstat-host218:report')))}
QUALIFICATIONS = {'samstat_input_scope_unproven', 'samstat_report_population_only', 'samstat_mapq255_merged'}

def save(case, name, value):
    directory = Path(os.environ['SAMSTAT_EVIDENCE']) / case
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + '.json')
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return path

def declarations(family):
    ordinals = (0,) if family == 'current' else (1, 2)
    fields = [dict(field=name, selection=dict(target=dict(kind='component', selector=dict(
        selection='semantic', calculation_id='mapping', metric=metric, threshold=None)),
        cardinality='one_target', expected_cardinality=1, availability_requirement='available_value'))
        for name, metric in zip(('mapped', 'high'), METRICS)]
    fields.append(dict(field='requirements', selection=dict(target=dict(kind='requirements'),
        cardinality='one_target', expected_cardinality=1, availability_requirement='typed_state')))
    parameters = validate_parameters(dict(version='fastqutils_provider_v2', analysis_id='samstat218' + family,
        documents=[dict(document_id='report', selection=dict(kind='output_requirement', requirement_id='selected_report'),
                        format='samstat_html', producer_version=None)], metadata_bindings=[],
        calculation_requests=[dict(calculation_id='mapping', method='samstat_report_mapping_v1',
            populations=[dict(selection='semantic', document_id='report',
                population_key='samstat_report_records', population_ordinal=n) for n in ordinals])]))
    return dict(parameters=parameters, requested_form=dict(version='fastqutils_projection_v2', fields=fields),
        declarations=dict(declarations=[]), submitted_parameters=dict(
            paired_end_libs=[], single_end_libs=[dict(read='/fixture/input/mixed.fastq', platform='illumina')],
            srr_libs=[], reference_genome_id='83333.1', recipe=['ALIGN'],
            output_path='/fixture/output', output_file='selected'))

def configure(monkeypatch, family):
    fixture_map = declarations(family)
    native = (HERE / 'native_inputs' / family / 'mixed.sam.samstat.html').read_bytes()
    assert hashlib.sha256(native).hexdigest() == HASHES[family]
    monkeypatch.setattr(host, 'fixture', lambda name: deepcopy(fixture_map[name]))
    monkeypatch.setattr(host, 'raw', lambda name: native)
    monkeypatch.setattr(host, 'NAMES', NAMES)
    monkeypatch.setattr(host, 'OUTPUTS', OUTPUTS)
    return fixture_map, native

def action_rows(store):
    return [dict(row) for row in store.db.execute(
        'SELECT * FROM runtime_actions ORDER BY run_id,episode_id,decision_index')]

def check_values(values, family):
    assert set(values) == {'mapped', 'high', 'requirements'}
    for name, metric, (numerator, denominator) in zip(('mapped', 'high'), METRICS, EXPECTED[family]):
        selected = values[name]
        assert selected['state'] == 'satisfied' and selected['satisfied']
        assert selected['matched_count'] == len(selected['records']) == 1
        row = selected['records'][0]
        payload = row['payload']
        assert payload['quantity'] == metric and payload['method'] == 'samstat_report_mapping_v1'
        assert (payload['numerator'], payload['denominator'], payload['value']) == (
            numerator, denominator, numerator / denominator)
        assert payload['state'] == 'available' and payload['unit'] == 'fraction'
        assert payload['meaning'] == 'native_report_derived' and payload['uncertainty'] == 'not_estimated'
        assert payload['encoding_basis'] is payload['lineage_basis'] is payload['threshold'] is None
        assert QUALIFICATIONS <= set(row['diagnostic_codes'])
        assert row['source_refs'] and payload['population_refs'] and payload['operand_measurement_refs']
    assert values['requirements']['satisfied']
    return values

def check_sheet(sheet, components, family, native):
    doc, = sheet['documents']
    assert doc['artifact']['actual_format'] == 'samstat_html_' + VERSIONS[family].replace('.', '_')
    assert doc['artifact']['producer_version'] == VERSIONS[family]
    assert doc['artifact']['sha256'] == HASHES[family] and doc['parse_scope'] == 'complete'
    assert not doc['sequence_records'] and not doc['alignment_records'] and not doc['reference_dictionary']
    assert all(p['scope'] == 'unknown' for p in doc['populations'])
    assert not sheet['associations'] and not sheet['native_lineage'] and not sheet['supplied_metadata']
    assert [s['requested_token'] for s in sheet['stages']] == ['ALIGN']
    assert all(s['observed_state'] == 'unknown' for s in sheet['stages'])
    job, = components['calculations']['parameters']['calculations']
    rows = {r['id']: r for r in sheet['measurements']}
    expected_bins = [4, 3, 2, 1, 10] if family == 'current' else [5, 2, 2, 1, 10, 0, 1, 0, 0, 1]
    assert [rows[r]['value'] for r in job['operand_measurement_refs']] == expected_bins
    populations = {p['id']: p for p in sheet['populations']}
    assert [populations[r]['population_ordinal'] for r in job['population_refs']] == ([0] if family == 'current' else [1, 2])
    if family == 'legacy':
        p, q = [populations[r] for r in job['population_refs']]
        assert p['id'] in q['disjoint_from_refs'] and q['id'] in p['disjoint_from_refs']
    for cell in [rows[r] for r in job['operand_measurement_refs']]:
        loc = cell['locator']
        assert native[loc['byte_start']:loc['byte_end']].decode() == cell['native_token']
    for component, metric, (numerator, denominator) in zip(components['calculations']['components'], METRICS, EXPECTED[family]):
        assert (component['metric'], component['numerator'], component['denominator'], component['value']) == (
            metric, numerator, denominator, numerator / denominator)
        assert component['population_refs'] == job['population_refs']
        assert component['operand_measurement_refs'] == job['operand_measurement_refs']
        assert QUALIFICATIONS <= set(component['diagnostic_codes'])
    return dict(native_bins=expected_bins, selected_population_ordinals=[populations[r]['population_ordinal']
        for r in job['population_refs']], calculation=job)

def checkpoint(driver, directory, body, case):
    values = {name: deepcopy(getattr(driver, name)) for name in (
        'config', 'schema', 'selected', 'frozen_assignment', 'material', 'declarations',
        'query', 'handoff', 'manifest', 'native_args', 'last_outcome')}
    values.update(version='samstat_host218_checkpoint_v1', directory=str(directory),
        state_path=str(driver.store.path), run_id=driver.saved.run_id,
        phase='scientific_acquisition_complete_before_assertions',
        episode_ids={name: getattr(driver, name).episode_id for name in ('parent', 'grandparent', 'context', 'launch')},
        body=body, sheet=driver.sheet, components=driver.components, calls=driver.client.calls,
        actions=action_rows(driver.store))
    return save(case, 'acquired_checkpoint', values)

def reconstruct(store, saved):
    d = host.FastqDriver.__new__(host.FastqDriver)
    d.store, d.config = store, deepcopy(saved['config'])
    d.saved = SimpleNamespace(run_id=saved['run_id'], journal=Journal(store, saved['run_id']),
                              receipts=EpisodeReceipts(store, saved['run_id']))
    d.family = ExecutionEpisodes(None, store=store, directory=Path(saved['directory']),
        run_id=saved['run_id'], resources={'selected-api': d.config}, initial_information={},
        tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))
    d.api, d.client = d.family.api_execution, host.ControlledClient()
    d.service = d.api.services['selected-api']; d.service.client = d.client
    d.records, d.custody = d.api.appservice.records, d.api.appservice.custody
    for name, ident in saved['episode_ids'].items():
        setattr(d, name, d.custody.context(ident))
    d.saved.root = d.parent
    for name in ('schema', 'selected', 'frozen_assignment', 'material', 'declarations',
                 'query', 'handoff', 'manifest', 'native_args', 'last_outcome'):
        setattr(d, name, deepcopy(saved[name]))
    return d

def disable_reexecution(monkeypatch):
    attempts, patched = [], []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('saved218 verification attempted parsing, calculation, acquisition or subprocess')
    for suffix in ('bundle_adapter', 'native', 'samstat_native', 'samstat_svg', 'samstat_legacy',
                   'samstat_mapping', 'metadata', 'sheet', 'calculators', 'resolution'):
        module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
        for name, function in list(vars(module).items()):
            if callable(function) and (name.startswith(('parse_', 'populate_', 'extract_', 'calculate_'))
                                       or name in ('consume_bundle', 'resolve_calculation_inputs')):
                monkeypatch.setattr(module, name, forbidden)
                patched.append(module.__name__ + '.' + name)
    monkeypatch.setattr(adapter.FastqUtilsBundleAdapter, 'consume_bundle', forbidden)
    patched.append(adapter.__name__ + '.FastqUtilsBundleAdapter.consume_bundle')
    for target in ('gene_annotation_episode.bvbrc_appservice_publication.AppServicePublications._grade',
        'gene_annotation_episode.api_service_execution.APIServiceExecution.execute',
        'socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex',
        'urllib.request.OpenerDirector.open', 'subprocess.Popen'):
        monkeypatch.setattr(target, forbidden); patched.append(target)
    for cls in (host.ControlledClient, host.NativeClient):
        for name in ('rpc', 'task_info', 'download', 'upload'):
            monkeypatch.setattr(cls, name, forbidden); patched.append(cls.__name__ + '.' + name)
    return attempts, patched
