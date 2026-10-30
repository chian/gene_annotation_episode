"""Controlled producer-to-requested-return integration, inside bounded529.

The native subprocess is replaced explicitly. These examples establish joins,
partial-result preservation and saved replay, not a new native run or scientific
measurement. Authentic format/native evidence remains in the sealed644 packet.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode import native_blast_utility_result_publication as publication
from gene_annotation_episode import blast_preparation_result_assembly as assembly
from gene_annotation_episode.blast_utility_contracts import blast_utility_result_version_for_operation
from gene_annotation_episode.native_blast_utility_materializations import preparation_path_maps
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.state import Store
from test_native_blast_preparation_649 import preparation_job, reserved_fixture
from test_native_blast_utility_publication_631 import inline_workers, prepare, publish, payload, selector


MODES = ('convert_gi_list', 'convert_seqid_list', 'inspect_seqid_list',
         'create_subset_alias', 'aggregate_databases', 'aggregate_volumes',
         'create_megablast_index', 'show_filters', 'create_profile_database')
INFO = b'Num of Ids: 1\nTitle: selected identifiers\nCreate Date: fixture date\n'
AUX = b'BLOSUM62\n11\n1\n0.000000e+00\n0.000000e+00\n0\n0\n1.000000\n320\n3.756720e-02\n'


def controlled_outputs(monkeypatch, job, *, rc=0):
    calls = []
    mode, parameters = job['operation']['mode'], job['operation']['parameters']

    def run(argv, **kwargs):
        calls.append(list(argv))
        root = Path(kwargs['cwd'])
        paths = preparation_path_maps(job, str(root))
        stdout, stderr = b'', b''
        if mode == 'inspect_seqid_list':
            stdout = INFO
        elif mode == 'convert_gi_list':
            stderr = b'Converted 3 GIs into binary GI file\n'
        elif mode == 'show_filters':
            stdout = b'\n'
        elif mode == 'create_megablast_index':
            stderr = b'Warning: -ws_hint requested is too low. Setting to the minimum value of 10\n'
        if rc:
            stderr += b'Error: explicitly failed fixture\n'
        kwargs['stdout'].write(stdout)
        kwargs['stderr'].write(stderr)
        for row in job['outputs']:
            if row['role'] in {'stdout', 'stderr'}:
                continue
            path = root / row['relative_path']
            path.parent.mkdir(parents=True, exist_ok=True)
            if row['population'] == 'file':
                path.write_bytes(b'opaque controlled bytes')
            elif row['role'] == 'index_family':
                for suffix in ('.00.idx', '.shd'):
                    Path(str(path) + suffix).write_bytes(b'controlled index member')
            elif mode == 'create_profile_database':
                for suffix in ('.aux', '.rps', '.loo', '.freq', '.phr', '.pin', '.psq'):
                    Path(str(path) + suffix).write_bytes(AUX if suffix == '.aux' else b'controlled profile member')
            else:
                keys = [parameters['source_database_key']] if mode == 'create_subset_alias' else [
                    e['database_key'] for e in (parameters['classic_list']['entries']
                        if mode == 'aggregate_databases' else parameters['volume_entries'])]
                names = [paths['database_paths'][key][0] for key in keys]
                text = 'TITLE ' + parameters['title'] + '\nDBLIST ' + ' '.join(names) + '\n'
                if mode == 'create_subset_alias':
                    text += 'SEQIDLIST ' + paths['input_paths']['ids'] + '\nNSEQ 1\nLENGTH 13\n'
                else:
                    text += 'NSEQ 3\nLENGTH 24\n'
                Path(str(path) + '.nal').write_text(text)
        return SimpleNamespace(returncode=rc)

    monkeypatch.setattr(driver.subprocess, 'run', run)
    return calls


def captured(tmp_path, monkeypatch, mode, *, rc=0, omit_original=False):
    job = preparation_job(tmp_path, mode)
    _, _, plan, target = reserved_fixture(tmp_path, monkeypatch, job=job)
    calls = controlled_outputs(monkeypatch, job, rc=rc)
    bundle = driver.run_native_blast_utility(plan)
    if omit_original:
        # The original bytes are normally acquired from their unchanged staged
        # file. Model one failed acquisition, followed by a successful capture
        # of the separately selected staged occurrence, without inventing facts.
        original = next(r for r in acquisition._selected_files(plan, bundle) if r['direction'] == 'input')
        capture_file = acquisition._capture_file
        skipped = []

        def once_missing(store, root, relative, *args, **kwargs):
            if not skipped and str(root) == original['read_root'] and relative == original['read_relative']:
                skipped.append(True)
                raise FileNotFoundError('controlled first acquisition unavailable')
            return capture_file(store, root, relative, *args, **kwargs)

        monkeypatch.setattr(acquisition, '_capture_file', once_missing)
    store = Store(tmp_path / 'store')
    capture = acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / 'capture')
    if omit_original:
        assert skipped and any(r['direction'] == 'input' for r in capture['failures'])
        assert any(r['direction'] == 'materialization' for r in capture['artifacts'])
    return job, plan, store, capture, calls, bundle


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('rc', [0, 2])
def test_all_modes_retain_results_and_publish_selected_saved_values(tmp_path, monkeypatch, mode, rc):
    job, plan, store, capture, calls, bundle = captured(tmp_path, monkeypatch, mode, rc=rc)
    workers = inline_workers(monkeypatch)
    prepared = prepare(store, capture, tmp_path)
    diagnostic = tmp_path / 'preparation/native-blast-utility-preparation/worker.stderr'
    assert prepared['worker_completed'], diagnostic.read_text()
    result = payload(store, prepared)
    assert result['version'] == blast_utility_result_version_for_operation(job['operation'])
    assert result['original_outcome']['returncode'] == rc
    assert len(calls) == 1 and len(workers) == 1
    if rc:
        assert any(r['code'] == 'native_nonzero_exit' for r in result['failures'])
    else:
        assert not any(r['code'] == 'native_nonzero_exit' for r in result['failures'])
    output_rows, _, _ = LocalPracticalOperations._utility_observed_files(
        plan, {'terminal': True}, validation={'bundle': bundle})
    assert len({r['role'] for r in output_rows}) == len(output_rows)
    fields = ['identifier_list_count'] if mode == 'inspect_seqid_list' else []
    chosen = selector(database_fields=fields, include_checks=True, saved_data=['result'],
        preparation=None if mode in {'inspect_seqid_list', 'show_filters'} else {
            'fields': ['kind', 'detail', 'materializations']})
    emitted = publish(store, prepared, chosen, tmp_path)
    assert len(workers) == 2
    assert emitted['artifacts'] == []
    assert emitted['saved_data'][0]['schema'] == result['version']
    if mode == 'inspect_seqid_list':
        assert emitted['database_fields'][0]['value'] == 1
        assert emitted['database_fields'][0]['subject'] == {'kind': 'identifier_list', 'occurrence_id': 'ids'}
    elif mode == 'create_subset_alias':
        assert any(f['field_name'] == 'database_residue_count' and f['value'] == 13
                   for d in result['detail']['alias_documents'] for f in d['native_fields'])
    source_before = deepcopy(store.get(capture['source_ref']))
    shutil.rmtree(plan['attempt_directory'])
    for row in job['inputs']:
        Path(row['path']).unlink(missing_ok=True)
    for database in job['databases']:
        shutil.rmtree(Path(database['manifest_file']['path']).parent)
    monkeypatch.setattr(driver.subprocess, 'run', lambda *a, **k: pytest.fail('saved replay invoked native'))
    monkeypatch.setattr(assembly, 'assemble_blast_preparation_result',
        lambda **k: pytest.fail('saved projection reparsed original inputs'))
    replay = publish(store, prepared, chosen, tmp_path, name='saved-only')
    assert replay['saved_data'] == emitted['saved_data']
    for key in ('status', 'database_fields', 'preparation', 'failures', 'missing', 'artifacts'):
        assert replay[key] == emitted[key]
    assert publish(store, prepared, chosen, tmp_path) == emitted
    assert store.get(capture['source_ref']) == source_before
    assert len(calls) == 1 and len(workers) == 3


def test_missing_original_identifier_file_preserves_inspection_and_denies_artifact(tmp_path, monkeypatch):
    _, _, store, capture, _, _ = captured(tmp_path, monkeypatch, 'inspect_seqid_list', omit_original=True)
    inline_workers(monkeypatch)
    prepared = prepare(store, capture, tmp_path)
    assert prepared['worker_completed']
    result = payload(store, prepared)
    assert any(r['code'] == 'input_population_unavailable' for r in result['failures'])
    emitted = publish(store, prepared, selector(database_fields=['identifier_list_count'],
        artifacts=[{'direction': 'input', 'role': 'identifier_list', 'ordinal': 0}]), tmp_path)
    assert emitted['database_fields'][0]['value'] == 1
    assert emitted['artifacts'] == []
    assert emitted['status']['state'] == 'partial'
    assert any(r['reason'] == 'artifact_unavailable' for r in emitted['missing'])
