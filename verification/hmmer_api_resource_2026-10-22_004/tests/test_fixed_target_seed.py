"""Synthetic original-input witnesses; no real case DB, model or native job."""
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.fixed_target_seed import FixedTargetSeedError, prepare_fixed_target_seed
from gene_annotation_episode.state import Store


def make_seed_witness(directory, *, sequence='ATGAAATAA', protein='MK', caller_context=None):
    """A tiny declared engineering case with original caller intake custody."""
    case = Path(directory)/'case'
    case.mkdir(parents=True)
    (case/'target.fna').write_text('>fixture_target original engineering input\n'+sequence+'\n')
    (case/'target.faa').write_text('>fixture_protein engineering reference\n'+protein+'\n')
    workspace = case/'workspace'
    context = {'fixture': 'synthetic caller input', 'conditions': ['α', 'engineering']} if caller_context is None else caller_context
    with Store(workspace) as store:
        problem = store.create_problem(case/'target.fna', molecule='dna', role='gene',
            caller_context=context, format='fasta')
        target = store.targets()[0]
    metadata = {'case_ref': 'fixed_seed_engineering_fixture', 'target_kind': 'single_gene',
        'target_ref': target['id'], 'problem_ref': problem['id'],
        'dna_length_nt': len(sequence), 'protein_length_aa': len(protein),
        'source_protein': 'fixture_protein',
        'target_files': {name: hashlib.sha256((case/name).read_bytes()).hexdigest()
                         for name in ('target.fna', 'target.faa')}}
    (case/'case.json').write_text(canonical(metadata)+'\n')
    return {'case_directory': case, 'source_workspace': workspace, 'problem': problem, 'target': target}


def invoke(witness, destination):
    return prepare_fixed_target_seed(case_directory=witness['case_directory'],
        source_workspace=witness['source_workspace'], destination_workspace=destination)


def tree_bytes(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


def test_complete_original_intake_and_explicit_baseline_without_old_work(tmp_path):
    original = make_seed_witness(tmp_path/'original')
    before = tree_bytes(original['source_workspace'])
    destination = original['case_directory']/'runs'/'new_run'/'workspace'
    receipt = invoke(original, destination)
    assert set(receipt) == {'version', 'source', 'workspace', 'fixed_identity', 'input_files',
        'intake_records', 'artifact_manifest', 'initial_known_record_refs', 'verification', 'exclusions'}
    assert receipt['version'] == 'fixed_target_seed_v1'
    assert json.loads((destination/'fixed-target-seed.json').read_text()) == receipt
    assert (destination/'fixed-target-seed.json').stat().st_mode & 0o777 == 0o444
    assert receipt['workspace'] == str(destination)
    assert receipt['fixed_identity']['dna_length_nt'] == 9
    assert receipt['fixed_identity']['protein_length_aa'] == 2
    after = tree_bytes(original['source_workspace'])
    bookkeeping = {'state.sqlite3-wal', 'state.sqlite3-shm'}
    assert {k: v for k, v in after.items() if k not in bookkeeping} == before
    reader = receipt['verification']['sqlite_reader_bookkeeping']
    assert reader['main_database_before'] == reader['main_database_after']
    assert reader['wal_before'] is None and reader['wal_after']['size'] == 0
    assert reader['observed_changes'] == ['empty_wal_created', 'shm_created']
    known = receipt['initial_known_record_refs']
    assert known == sorted(set(known)) and original['target']['id'] in known
    assert original['problem']['id'] not in known
    assert any(row['record_type'] == 'collection_member' for row in receipt['intake_records'])
    with Store(destination) as store:
        assert store.problem() == original['problem']
        assert store.targets() == [original['target']]
        assert all(store.get(ref) for ref in known)
        for row in receipt['intake_records']:
            assert row['content_sha256'] == hashlib.sha256(canonical(store.get(row['reference'])).encode()).hexdigest()
        for row in receipt['artifact_manifest']:
            assert hashlib.sha256(store.get_artifact(row['id'])).hexdigest() == row['sha256']
        assert store.db.execute('SELECT count(*) FROM current_revisions').fetchone()[0] == 0
        assert not store.db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'runtime_%'").fetchall()
    assert receipt['verification']['initial_known_record_ref_count'] == len(known)
    assert receipt['verification']['initial_known_record_refs_sha256'] == hashlib.sha256(canonical(known).encode()).hexdigest()
    assert not any(receipt['verification']['excluded_record_counts'].values())
    assert not any(receipt['verification']['excluded_table_counts'].values())
    assert not list(destination.parent.glob('.*.seed-*'))


@pytest.mark.parametrize('kind', ['directory', 'file', 'identical_completed'])
def test_existing_destinations_are_never_adopted_or_replaced(tmp_path, kind):
    original = make_seed_witness(tmp_path/'original')
    destination = tmp_path/'output'
    if kind == 'directory':
        destination.mkdir()
    elif kind == 'file':
        destination.write_bytes(b'caller-owned')
    else:
        invoke(original, destination)
    before = tree_bytes(destination) if destination.is_dir() else destination.read_bytes()
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, destination)
    assert caught.value.failure == {'version': 'fixed_target_seed_failure_v1',
        'code': 'destination_exists', 'affected_refs': [str(destination)], 'staging_workspace': None}
    assert (tree_bytes(destination) if destination.is_dir() else destination.read_bytes()) == before


@pytest.mark.parametrize('kind', ['destination', 'dangling', 'parent', 'source', 'case_file'])
def test_symlinks_are_rejected_before_staging(tmp_path, kind):
    original = make_seed_witness(tmp_path/'original')
    destination = tmp_path/'output'
    expected = 'destination_invalid'
    if kind in ('destination', 'dangling'):
        destination.symlink_to(tmp_path/('missing' if kind == 'dangling' else 'original'), target_is_directory=True)
    elif kind == 'parent':
        (tmp_path/'alias').symlink_to(tmp_path/'original', target_is_directory=True)
        destination = tmp_path/'alias'/'output'
    elif kind == 'source':
        (tmp_path/'alias').symlink_to(original['source_workspace'], target_is_directory=True)
        original['source_workspace'] = tmp_path/'alias'
        expected = 'source_input_invalid'
    else:
        path = original['case_directory']/'target.fna'
        kept = original['case_directory']/'kept.fna'
        path.rename(kept)
        path.symlink_to(kept)
        expected = 'source_input_invalid'
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, destination)
    assert caught.value.failure['code'] == expected
    assert caught.value.failure['staging_workspace'] is None


@pytest.mark.parametrize('kind', ['inside_source', 'source_itself', 'source_ancestor', 'case_itself', 'old_run'])
def test_protected_overlap_is_rejected(tmp_path, kind):
    original = make_seed_witness(tmp_path/'original')
    if kind == 'inside_source':
        destination = original['source_workspace']/'new'
    elif kind == 'source_itself':
        destination = original['source_workspace']
    elif kind == 'source_ancestor':
        destination = tmp_path/'original'
    elif kind == 'case_itself':
        destination = original['case_directory']
    else:
        run = original['case_directory']/'runs'/'old_run'
        run.mkdir(parents=True)
        (run/'case-launch.json').write_text('{}')
        destination = run/'workspace'
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, destination)
    assert caught.value.failure['code'] == 'destination_overlap'
    assert caught.value.failure['staging_workspace'] is None


@pytest.mark.parametrize('kind', ['missing_context', 'corrupt_context', 'wrong_size', 'missing_material'])
def test_original_artifact_custody_is_checked_before_interpretation(tmp_path, kind):
    original = make_seed_witness(tmp_path/'original')
    with sqlite3.connect(original['source_workspace']/'state.sqlite3') as db:
        if kind == 'missing_material':
            source = json.loads(db.execute('SELECT data FROM records WHERE record_type=\'material\'').fetchone()[0])['source_ref']
            artifact = json.loads(db.execute('SELECT data FROM records WHERE id=?', (source,)).fetchone()[0])['artifact_ref']
        else:
            artifact = original['problem']['caller_context_ref']
        checksum = db.execute('SELECT sha256 FROM artifacts WHERE id=?', (artifact,)).fetchone()[0]
        if kind == 'wrong_size':
            db.execute('UPDATE artifacts SET size=size+1 WHERE id=?', (artifact,))
        else:
            path = original['source_workspace']/'artifacts'/checksum[:2]/checksum
            if kind == 'corrupt_context':
                path.write_bytes(b'not the original context')
            else:
                path.unlink()
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, tmp_path/'output')
    assert caught.value.failure['code'] == 'artifact_custody_failure'
    assert caught.value.failure['staging_workspace'] is None
    assert not (tmp_path/'output').exists()


def test_parser_drift_retains_stage_and_typed_failure(tmp_path, monkeypatch):
    original = make_seed_witness(tmp_path/'original')
    from gene_annotation_episode import materials
    monkeypatch.setattr(materials, 'VERSION', 'explicit_engineering_parser_drift')
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, tmp_path/'output')
    failure = caught.value.as_record()
    assert failure['code'] == 'intake_mismatch'
    assert Path(failure['staging_workspace']).is_dir()
    assert (Path(failure['staging_workspace'])/'state.sqlite3').is_file()
    assert not (tmp_path/'output').exists()
    assert set(failure) == {'version', 'code', 'affected_refs', 'staging_workspace'}


def test_original_member_index_mismatch_is_not_silently_repaired(tmp_path):
    original = make_seed_witness(tmp_path/'original')
    with sqlite3.connect(original['source_workspace']/'state.sqlite3') as db:
        db.execute("UPDATE material_members SET data=json_set(data,'$.source_byte_offset',99)")
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, tmp_path/'output')
    assert caught.value.failure['code'] == 'intake_mismatch'
    assert Path(caught.value.failure['staging_workspace']).is_dir()


def test_no_replace_publication_refuses_concurrent_empty_directory(tmp_path, monkeypatch):
    original = make_seed_witness(tmp_path/'original')
    from gene_annotation_episode import fixed_target_seed as module
    publish = module._publish_directory
    def raced(stage, destination, parent_fd):
        destination.mkdir()
        publish(stage, destination, parent_fd)
    monkeypatch.setattr(module, '_publish_directory', raced)
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, tmp_path/'output')
    assert caught.value.failure['code'] == 'destination_exists'
    assert (tmp_path/'output').is_dir() and not list((tmp_path/'output').iterdir())
    assert (Path(caught.value.failure['staging_workspace'])/'fixed-target-seed.json').is_file()


def test_publication_failure_retains_complete_seed_and_receipt(tmp_path, monkeypatch):
    original = make_seed_witness(tmp_path/'original')
    from gene_annotation_episode import fixed_target_seed as module
    def fail(*args):
        raise OSError('explicit engineering publication failure')
    monkeypatch.setattr(module, '_publish_directory', fail)
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, tmp_path/'output')
    assert caught.value.failure['code'] == 'publication_failure'
    stage = Path(caught.value.failure['staging_workspace'])
    assert json.loads((stage/'fixed-target-seed.json').read_text())['workspace'] == str(tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_parent_fsync_failure_reports_published_output_without_fictional_stage(tmp_path, monkeypatch):
    original = make_seed_witness(tmp_path/'original')
    from gene_annotation_episode import fixed_target_seed as module
    publish = module._publish_directory
    destination = tmp_path/'output'
    def parent_sync_fails(stage, destination, parent_fd):
        def fail(descriptor):
            raise OSError('explicit parent sync failure after rename')
        monkeypatch.setattr(module.os, 'fsync', fail)
        publish(stage, destination, parent_fd)
    monkeypatch.setattr(module, '_publish_directory', parent_sync_fails)
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, destination)
    assert caught.value.failure == {'version': 'fixed_target_seed_failure_v1',
        'code': 'publication_failure', 'affected_refs': [str(destination)], 'staging_workspace': None}
    assert (destination/'state.sqlite3').is_file()
    assert (destination/'fixed-target-seed.json').is_file()
    assert not list(tmp_path.glob('.output.seed-*'))
    with pytest.raises(FixedTargetSeedError) as repeated:
        invoke(original, destination)
    assert repeated.value.failure['code'] == 'destination_exists'


def test_parent_replacement_refuses_publication_and_reports_actual_retained_stage(tmp_path, monkeypatch):
    original = make_seed_witness(tmp_path/'original')
    from gene_annotation_episode import fixed_target_seed as module
    publish = module._publish_directory
    destination = tmp_path/'output-parent'/'workspace'
    moved = tmp_path/'moved-output-parent'
    def replace_parent(stage, destination, parent_fd):
        destination.parent.rename(moved)
        destination.parent.mkdir()
        publish(stage, destination, parent_fd)
    monkeypatch.setattr(module, '_publish_directory', replace_parent)
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, destination)
    failure = caught.value.failure
    assert failure['code'] == 'publication_failure'
    retained = Path(failure['staging_workspace'])
    assert retained.parent == moved
    assert (retained/'fixed-target-seed.json').is_file()
    assert (retained/'state.sqlite3').is_file()
    assert not destination.exists()
    assert not (moved/'workspace').exists()
    assert not list(destination.parent.iterdir())


@pytest.mark.parametrize('kind', ['exists', 'marker'])
def test_destination_filesystem_errors_are_typed_before_staging(tmp_path, monkeypatch, kind):
    original = make_seed_witness(tmp_path/'original')
    destination = tmp_path/'output'
    method = 'exists' if kind == 'exists' else 'is_file'
    original_method = getattr(Path, method)
    def fail_selected(path):
        if (kind == 'exists' and path == destination or
                kind == 'marker' and path == tmp_path/'case-launch.json'):
            raise PermissionError('explicit engineering destination access failure')
        return original_method(path)
    monkeypatch.setattr(Path, method, fail_selected)
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, destination)
    assert caught.value.failure == {'version': 'fixed_target_seed_failure_v1',
        'code': 'destination_invalid', 'affected_refs': [str(destination)], 'staging_workspace': None}


def test_case_identity_mismatch_does_not_create_stage(tmp_path):
    original = make_seed_witness(tmp_path/'original')
    path = original['case_directory']/'case.json'
    case = json.loads(path.read_text())
    case['target_ref'] = 'input_'+'0'*24
    path.write_text(canonical(case))
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, tmp_path/'output')
    assert caught.value.failure['code'] == 'identity_mismatch'
    assert caught.value.failure['staging_workspace'] is None


@pytest.mark.parametrize('live', [False, True])
def test_missing_and_existing_wal_bookkeeping_is_reported_without_authority_changes(tmp_path, live):
    original = make_seed_witness(tmp_path/'original')
    writer = sqlite3.connect(original['source_workspace']/'state.sqlite3')
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE explicit_wal_fixture(value)')
    writer.commit()
    if not live:
        writer.close()
    before = tree_bytes(original['source_workspace'])
    try:
        receipt = invoke(original, tmp_path/'output')
        after = tree_bytes(original['source_workspace'])
        excluded = {'state.sqlite3-shm', 'state.sqlite3-wal'}
        assert {k: v for k, v in before.items() if k not in excluded} == {
            k: v for k, v in after.items() if k not in excluded}
        reader = receipt['verification']['sqlite_reader_bookkeeping']
        assert reader['authoritative_bytes_unchanged']
        assert reader['main_database_before'] == reader['main_database_after']
        if live:
            assert before['state.sqlite3-wal'] == after['state.sqlite3-wal']
            assert reader['wal_before'] == reader['wal_after']
            assert writer.execute('SELECT count(*) FROM explicit_wal_fixture').fetchone()[0] == 0
        else:
            assert reader['wal_before'] is None and reader['wal_after']['size'] == 0
            assert reader['observed_changes'] == ['empty_wal_created', 'shm_created']
    finally:
        if live:
            writer.close()


@pytest.mark.parametrize('kind', ['database', 'unrelated_custody'])
def test_detected_outside_change_refuses_publication_without_undo(tmp_path, monkeypatch, kind):
    original = make_seed_witness(tmp_path/'original')
    create = Store.create_problem
    def changed(store, *args, **kwargs):
        result = create(store, *args, **kwargs)
        if kind == 'database':
            with sqlite3.connect(original['source_workspace']/'state.sqlite3') as writer:
                writer.execute('CREATE TABLE explicit_outside_writer(value)')
        else:
            (original['source_workspace']/'outside-custody').write_bytes(b'outside writer')
        return result
    monkeypatch.setattr(Store, 'create_problem', changed)
    with pytest.raises(FixedTargetSeedError) as caught:
        invoke(original, tmp_path/'output')
    assert caught.value.failure['code'] == 'identity_mismatch'
    assert Path(caught.value.failure['staging_workspace']).is_dir()
    assert not (tmp_path/'output').exists()
    if kind == 'unrelated_custody':
        assert (original['source_workspace']/'outside-custody').read_bytes() == b'outside writer'
