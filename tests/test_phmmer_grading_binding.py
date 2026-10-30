"""Native phmmer custody and numerical integration; synthetic faults are labeled.

Tiny new searches use the existing bounded runner with 20 GiB/4 GiB/no wall
limit. The one-gene 17-target/20-domain data are retained native output. No
API, HPC, model invocation, database BLAST or production credit policy is used.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess

import pytest

from gene_annotation_episode import homology_results as publication
from gene_annotation_episode import phmmer_grading_worker as grading_worker
from gene_annotation_episode import phmmer_result_worker as worker
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.hmmer_graders import HMMER_DOMAIN_METRICS
from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, digest
from gene_annotation_episode.homology_results import HomologyResults, NativePhmmerInput
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.native_lifecycle import wait_job
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from test_homology_results import CASE, JOB, prepared


POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3)
PROGRAM = CASE.parents[1]/'resources/software/infernal-1.1.5/hmmer/src/phmmer'


def run_extract(adapter, inputs, scope, **kwargs):
    return asyncio.run(adapter.extract(inputs, scope=scope, **kwargs))


def values(store, reference):
    return {row['name']: row['value']['value'] for row in store.get(reference)['measurements']
            if row['value']['type'] == 'number'}


def saved_grade(store, observation):
    source = store.get(store.get(observation)['source_ref'])
    grades = source_tool_gradings(store, source['id'])
    assert len(grades) == 1
    return grades[0]


def assert_paired_aliases_equal_shared(store, observation):
    grading = saved_grade(store, observation)
    score = grading['scores']['domains'][0] if grading.get('scores') else {}
    measured = values(store, observation)
    for alias, component in (('query_coverage', 'paired_model_coverage'),
            ('target_coverage', 'paired_sequence_coverage'), ('identity_fraction', 'sequence_identity_fraction')):
        if score.get(component) is None:
            assert alias not in measured
        else:
            assert measured[alias] == measured[component] == score[component]


@pytest.fixture(scope='module')
def tiny(tmp_path_factory):
    """Two actual sequence matches; the second has an inserted triplet."""
    path = tmp_path_factory.mktemp('phmmer-grading-native')
    sequence = ''.join((CASE/'target.faa').read_text().splitlines()[1:])
    database = path/'references.faa'
    database.write_text('>self\n'+sequence+'\n>insert\n'+sequence[:125]+'GGG'+sequence[125:]+'\n')
    jobs = HomologyJobs.create(path/'jobs', executable=FileAsset(PROGRAM, digest(PROGRAM)),
        reference_database=FileAsset(database, digest(database)), policy=POLICY, max_cpu=1)
    try:
        job = jobs.order(query_ref='explicit_fixture_query', query_fasta='>query\n'+sequence+'\n',
            cpu=1, operation_key='tiny_actual_native_fixture')
        jobs.configure(job, 1); jobs.stage(job); jobs.submit(job)
        result = wait_job(jobs._handle(job))
        assert result.returncode == 0
        directory = jobs._directory(job)
        assert jobs._handle(job).read()['metadata']['policy'] == POLICY.to_dict()
        yield directory, sequence, jobs._handle(job).read()
    finally:
        jobs.close()


def workspace(tmp_path, tiny, *, native=None, domain=None):
    directory, sequence, handle = tiny
    store = Store(tmp_path/'state')
    query, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
    inputs = NativePhmmerInput(query, directory/'query.faa', directory/'references.faa',
        native or directory/'native.stdout', directory/'hits.tbl', digest(directory/'references.faa'),
        digest(PROGRAM), {'kind': 'actual_tiny_native_fixture', 'native_handle': handle},
        directory/'domains.tbl' if domain is None else domain)
    return store, HomologyResults(store, policy=POLICY), inputs, {'subject_refs': [query]}


def request_for(tmp_path, tiny):
    directory, sequence, handle = tiny
    return {'directory': str(tmp_path), 'query_fasta': str(directory/'query.faa'),
        'reference_fasta': str(directory/'references.faa'), 'native_text': str(directory/'native.stdout'),
        'hit_table': str(directory/'hits.tbl'), 'domain_table': str(directory/'domains.tbl'),
        'expected_query_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
        'database_sha256': digest(directory/'references.faa'), 'executable_sha256': digest(PROGRAM),
        'native_parameters': {'command': handle['command']},
        'grading_artifacts': {role: {'artifact_ref': 'explicit_fixture_'+role} for role in
            ('stdout', 'tblout', 'domtblout', 'query_fasta', 'query_sequence')}}


def worker_rows(tmp_path, request):
    worker.extract(request)
    with sqlite3.connect(tmp_path/'measurements.sqlite') as db:
        rows = [json.loads(row[0]) for row in db.execute('SELECT data FROM measurements ORDER BY ordinal')]
        errors = [json.loads(row[0]) for row in db.execute('SELECT data FROM errors ORDER BY ordinal')]
    grades = [json.loads((tmp_path/row['grading_file']).read_text()) for row in rows if 'grading_file' in row]
    return rows, errors, grades


def test_retained_17_targets_20_domains_fill_actual_numerical_sheets(tmp_path, monkeypatch):
    store, adapter, inputs, scope = prepared(tmp_path)
    adapter.policy = POLICY
    inputs = replace(inputs, domain_table=JOB/'domains.tbl')
    with store:
        result = run_extract(adapter, inputs, scope, limit=100)
        assert result['status'] == 'completed', result
        assert len(result['result']['reference_refs']) == 17
        assert len(result['result']['comparison_refs']) == 20
        snapshot = json.loads(store.db.execute('SELECT body FROM homology_result_snapshots').fetchone()[0])
        assert artifact_path(store, snapshot['domain_table_artifact']).read_bytes() == (JOB/'domains.tbl').read_bytes()
        assert snapshot['native_parameters']['command'] == inputs.provenance['original_job_manifest']['command']
        all_scores = []
        for observation in result['result']['comparison_refs']:
            grading = saved_grade(store, observation)
            sheet, scores = grading['sheet'], grading['scores']
            row, = scores['domains']; native, = sheet['domains']
            assert sheet['operation']['engine_version'] == '3.4'
            assert native['locator']['artifact_role'] == 'domtblout'
            assert native['associations'][0]['locator']['artifact_role'] == 'stdout'
            assert native['quantities']['actual_sequence_correspondence'] is True
            assert values(store, observation)['paired_model_coverage'] == values(store, observation)['query_coverage']
            assert values(store, observation)['paired_sequence_coverage'] == values(store, observation)['target_coverage']
            assert_paired_aliases_equal_shared(store, observation)
            assert row['native_domain_bias_bits'] is not None and row['native_accuracy'] is not None
            assert row['sequence_envelope_residues'] >= row['sequence_span_residues']
            assert row['posterior_lower_mean'] <= row['posterior_upper_mean']
            assert 'api_identity_fraction' not in values(store, observation)
            if row['target_name'] == 'sp|A6H7I3|ANGE2_BOVIN':
                assert row['model_span_positions'] == 152
                assert row['sequence_span_residues'] == 157
                assert row['sequence_envelope_residues'] == 175
                assert row['model_span_coverage'] == 152/253
                assert row['sequence_span_coverage'] == 157/544
                assert row['native_accuracy'] == .70
                assert row['paired_positions'] < 152
            all_scores.append(row)
            # Saved calculators touch neither Store/filesystem nor a native tool.
            before = deepcopy(grading)
            with monkeypatch.context() as blocked:
                blocked.setattr(socket, 'create_connection', lambda *a, **k: pytest.fail('network'))
                blocked.setattr(Path, 'open', lambda *a, **k: pytest.fail('filesystem'))
                blocked.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('native rerun'))
                assert calculate_hmmer_search_scores(sheet) == scores
            assert grading == before
        assert min(row['native_domain_score_bits'] for row in all_scores) < 0
        assert store.count('observation') == 21
        assert store.count('annotation') == store.count('assessment') == 0


def test_tiny_capture_paging_custody_signature_replay_and_original_sites(tmp_path, tiny):
    store, adapter, inputs, scope = workspace(tmp_path, tiny)
    with store:
        first = run_extract(adapter, inputs, scope, limit=3)
        assert first['status'] == 'completed', first
        snapshot = first['result']['snapshot_ref']
        last = run_extract(adapter, inputs, scope, snapshot_ref=snapshot, offset=3, limit=10)
        assert first['result']['total'] == 4 and last['result']['next_offset'] is None
        combined = [*first['result']['comparison_refs'], *last['result']['comparison_refs']]
        assert len(combined) == 2
        original = {reference: store.get(reference) for reference in combined}
        grade = saved_grade(store, combined[1])
        domain = grade['scores']['domains'][0]
        assert domain['sequence_span_residues'] == 256 and domain['paired_positions'] == 253
        assert domain['insert_positions'] == 3 and domain['sequence_span_coverage'] == 1
        assert domain['paired_sequence_coverage'] == 253/256
        assert values(store, combined[1])['target_coverage'] == 253/256
        assert values(store, combined[1])['target_coverage'] != domain['sequence_span_coverage']
        for reference in combined:
            assert_paired_aliases_equal_shared(store, reference)
        before = store.count('observation')
        replay = run_extract(adapter, inputs, scope, snapshot_ref=snapshot, limit=10)
        assert replay['changed_record_refs'] == [] and store.count('observation') == before
        assert {reference: store.get(reference) for reference in combined} == original
        from gene_annotation_episode.tools import ToolRegistry
        sites = ToolRegistry(store).execute('sequence.sites', {'alignment_ref': combined[1],
            'positions': [124, 125, 127, 128]}, scope=scope)
        assert sites['status'] == 'completed'
        # Mutated live output cannot alter the retained snapshot or original source.
        altered = tmp_path/'synthetic-table-append.tbl'
        altered.write_bytes(inputs.domain_table.read_bytes()+b'# synthetic nonmeasurement comment\n')
        new = run_extract(adapter, replace(inputs, domain_table=altered), scope, limit=10)
        assert new['result']['snapshot_ref'] != snapshot
        assert new['result']['comparison_refs'] == combined and new['changed_record_refs'] == []
        for reference in combined:
            assert store.get(reference) == original[reference]
        saved = store.db.execute('SELECT body FROM homology_result_snapshots WHERE source_ref=?', (snapshot,)).fetchone()[0]
        body = json.loads(saved)
        assert len(body['parser_implementation_sha256']) == 64
        assert artifact_path(store, body['domain_table_artifact']).read_bytes() == inputs.domain_table.read_bytes()


def test_missing_domain_table_preserves_stdout_measurements_and_explicit_absence(tmp_path, tiny):
    store, adapter, inputs, scope = workspace(tmp_path, tiny, domain=tmp_path/'absent.tbl')
    with store:
        result = run_extract(adapter, inputs, scope, limit=10)
        assert result['status'] == 'completed'
        grading = saved_grade(store, result['result']['comparison_refs'][0])
        row = grading['sheet']['domains'][0]
        assert row['locator']['artifact_role'] == 'stdout'
        assert any(issue['code'] == 'hmmer_native_table_unavailable' for issue in row['issues'])
        assert grading['sheet']['artifacts']['domtblout']['availability'] == 'unavailable'
        assert grading['scores']['domains'][0]['native_accuracy'] == 1.0


def test_cache_reuses_numbers_with_current_capture_metadata_and_immutable_saved_sheets(tmp_path, tiny, monkeypatch):
    store, adapter, inputs, scope = workspace(tmp_path, tiny)
    with store:
        first = run_extract(adapter, inputs, scope, limit=0)
        first_ref = first['result']['snapshot_ref']
        first_row = store.db.execute('SELECT directory,body FROM homology_result_snapshots WHERE source_ref=?',
            (first_ref,)).fetchone()
        first_snapshot = json.loads(first_row['body'])
        assert first_snapshot['native_parameters']['command']
        directory = Path(first_row['directory'])
        saved = {path.name: path.read_bytes() for path in directory.glob('grading-*.json')}
        assert len(saved) == 2
        for raw in saved.values():
            assert json.loads(raw)['sheet']['inputs']['native_parameters'] == first_snapshot['native_parameters']
        second_inputs = replace(inputs, provenance={'kind': 'synthetic_new_capture_wrapper',
            'actual_retained_origin': inputs.provenance})
        monkeypatch.setattr(publication, 'start_job', lambda *args, **kwargs: pytest.fail('identical native bytes reparsed'))
        second = run_extract(adapter, second_inputs, scope, limit=10)
        assert second['status'] == 'completed'
        assert len(second['changed_record_refs']) == 2
        assert second['result']['snapshot_ref'] != first_ref
        second_row = store.db.execute('SELECT directory,body FROM homology_result_snapshots WHERE source_ref=?',
            (second['result']['snapshot_ref'],)).fetchone()
        assert second_row['directory'] == first_row['directory']
        assert json.loads(second_row['body'])['native_parameters'] == {}
        for observation in second['result']['comparison_refs']:
            grade = saved_grade(store, observation)
            assert grade['sheet']['inputs']['native_parameters'] == {}
            assert calculate_hmmer_search_scores(grade['sheet']) == grade['scores']
        assert {path.name: path.read_bytes() for path in directory.glob('grading-*.json')} == saved
        assert json.loads(store.db.execute('SELECT body FROM homology_result_snapshots WHERE source_ref=?',
            (first_ref,)).fetchone()[0]) == first_snapshot


def test_duplicate_table_domain_is_not_joined_to_an_arbitrary_row(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    raw = Path(request['domain_table']).read_text()
    native_row = next(row for row in raw.splitlines(keepends=True) if row and not row.startswith('#'))
    copied = tmp_path/'synthetic-duplicate-domtblout'
    copied.write_text(raw+native_row)
    request['domain_table'] = str(copied)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len(grades) == 2 and all(grade.get('failure') is None for grade in grades)
    domain = grades[0]['sheet']['domains'][0]
    assert domain['locator']['artifact_role'] == 'stdout'
    assert 'associations' not in domain
    assert any(issue['code'] == 'hmmer_table_stdout_association_ambiguous' for issue in domain['issues'])
    assert grades[1]['sheet']['domains'][0]['locator']['artifact_role'] == 'domtblout'


def test_duplicate_stdout_target_is_explicitly_ambiguous(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    raw = Path(request['native_text']).read_text()
    block = raw[raw.index('>> self'):raw.index('>> insert')]
    copied = tmp_path/'synthetic-duplicate-target-stdout'
    copied.write_text(raw.replace('Internal pipeline statistics', block+'Internal pipeline statistics'))
    request['native_text'] = str(copied)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len(grades) == 3
    assert grades[0]['failure']['code'] == grades[2]['failure']['code'] == 'phmmer_grading_alignment_association_ambiguous'
    assert grades[1]['scores']['domains'][0]['target_name'] == 'insert'


def test_printed_zero_evalues_are_preserved_as_zero_components(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    lines = Path(request['domain_table']).read_text().splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line and not line.startswith('#'):
            fields = line.split(maxsplit=22)
            for field in (6, 11, 12):
                fields[field] = '0'
            lines[index] = ' '.join(fields)+'\n'
    copied = tmp_path/'synthetic-zero-evalues-domtblout'; copied.write_text(''.join(lines))
    request['domain_table'] = str(copied)
    rows, errors, grades = worker_rows(tmp_path, request)
    for grading in grades:
        row = grading['scores']['domains'][0]
        assert row['native_independent_evalue'] == row['native_conditional_evalue'] == 0
        assert row['components']['native_independent_evalue']['value'] == 0
        assert 'native_independent_evalue' not in row['unavailable']


def test_wrong_program_table_cannot_supply_phmmer_numbers(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    copied = tmp_path/'synthetic-wrong-program-domtblout'
    copied.write_text(Path(request['domain_table']).read_text().replace('# Program:         phmmer',
        '# Program:         hmmsearch'))
    assert '# Program:         hmmsearch' in copied.read_text()
    request['domain_table'] = str(copied)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert 'hmmer_native_program_mismatch' in {error['code'] for error in errors}
    for grade in grades:
        row = grade['sheet']['domains'][0]
        assert row['locator']['artifact_role'] == 'stdout'
        assert any(issue['code'] == 'hmmer_native_artifact_identity_conflict' for issue in row['issues'])


def test_malformed_later_table_domain_preserves_valid_siblings(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    lines = Path(request['domain_table']).read_text().splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line and not line.startswith('#')]
    lines[indices[-1]] = 'synthetic truncated later row\n'
    copied = tmp_path/'synthetic-malformed-domtblout'; copied.write_text(''.join(lines))
    request['domain_table'] = str(copied)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len(grades) == 2 and 'hmmer_truncated_table_row' in {error['code'] for error in errors}
    assert grades[0]['sheet']['domains'][0]['locator']['artifact_role'] == 'domtblout'
    assert grades[1]['sheet']['domains'][0]['locator']['artifact_role'] == 'stdout'
    assert all(grade['scores']['domains'][0]['paired_positions'] == 253 for grade in grades)


def test_bounded_malformed_table_publication_retains_full_original_bytes(tmp_path, tiny):
    directory, _, _ = tiny
    raw = (directory/'domains.tbl').read_bytes()+b'synthetic malformed later domain\n'
    copied = tmp_path/'synthetic-malformed-table.tbl'; copied.write_bytes(raw)
    store, adapter, inputs, scope = workspace(tmp_path, tiny, domain=copied)
    with store:
        result = run_extract(adapter, inputs, scope, limit=10)
        assert result['status'] == 'partial'
        assert len(result['result']['comparison_refs']) == 2
        assert result['feedback']['native_error_count'] == 1
        assert result['feedback']['grading_error_count'] == 0
        assert result['result']['native_result_complete'] is False
        snapshot = json.loads(store.db.execute('SELECT body FROM homology_result_snapshots').fetchone()[0])
        assert artifact_path(store, snapshot['domain_table_artifact']).read_bytes() == raw
        assert all(values(store, reference)['paired_positions'] == 253
            for reference in result['result']['comparison_refs'])


def test_changed_reference_fasta_is_rejected_under_saved_identity(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    copied = tmp_path/'synthetic-changed-reference.faa'
    copied.write_text(Path(request['reference_fasta']).read_text().replace('M', 'A', 1))
    request['reference_fasta'] = str(copied)
    with pytest.raises(ValueError, match='native_reference_database_identity_changed'):
        worker.extract(request)
    with sqlite3.connect(tmp_path/'measurements.sqlite') as db:
        assert db.execute('SELECT count(*) FROM measurements').fetchone()[0] == 0


def test_duplicate_reference_identity_does_not_publish_false_correspondence(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    copied = tmp_path/'synthetic-duplicate-reference.faa'
    copied.write_text(Path(request['reference_fasta']).read_text()+'\n>self\nACDEFGHIK\n')
    request.update(reference_fasta=str(copied), database_sha256=digest(copied))
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len(grades) == 1 and grades[0]['scores']['domains'][0]['target_name'] == 'insert'
    assert 'native_reference_identifier_ambiguous' in {error['code'] for error in errors}


def test_grader_failure_keeps_original_alignment_and_valid_neighbor(tmp_path, tiny, monkeypatch):
    request = request_for(tmp_path, tiny)
    original = grading_worker.calculate_hmmer_search_scores
    def fail_one(sheet):
        if sheet['domains'][0]['target_name'] == 'insert':
            raise ValueError('synthetic_one_domain_grader_failure')
        return original(sheet)
    monkeypatch.setattr(grading_worker, 'calculate_hmmer_search_scores', fail_one)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len([row for row in rows if row['kind'] == 'alignment']) == 2
    assert grades[0]['scores']['domains'][0]['paired_positions'] == 253
    assert grades[1]['scores'] is None and grades[1]['failure']['code'] == 'synthetic_one_domain_grader_failure'
    assert 'phmmer_grading_failed' in {error['code'] for error in errors}


def test_parser_failure_keeps_original_rows_and_explicit_grading_failure(tmp_path, tiny, monkeypatch):
    request = request_for(tmp_path, tiny)
    def broken(*args, **kwargs):
        raise ValueError('synthetic_native_event_reader_failure')
    monkeypatch.setattr(grading_worker, 'iter_hmmer_stdout_events', broken)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len(grades) == 2
    assert all(grade['scores'] is None for grade in grades)
    assert {error['code'] for error in errors} >= {'phmmer_grading_native_capture_failed', 'phmmer_grading_failed'}


def test_partial_stdout_retains_complete_alignment_and_unknown_completion(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    raw = Path(request['native_text']).read_bytes()
    copied = tmp_path/'synthetic-truncated-stdout'
    copied.write_bytes(raw[:raw.index(b'>> insert')])
    request['native_text'] = str(copied)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len(grades) == 1 and grades[0]['scores']['domains'][0]['paired_positions'] == 253
    assert grades[0]['sheet']['completion']['output_complete'] is False
    assert 'native_reported_hit_without_complete_alignment' in {error['code'] for error in errors}


def test_unexpected_later_query_never_gets_assigned_query_metadata(tmp_path, tiny):
    request = request_for(tmp_path, tiny)
    raw = Path(request['native_text']).read_text()
    copied = tmp_path/'synthetic-extra-query-stdout'
    copied.write_text(raw+raw[raw.index('Query:'):].replace('query', 'other'))
    request['native_text'] = str(copied)
    rows, errors, grades = worker_rows(tmp_path, request)
    assert len(grades) == 2
    assert all(grade['sheet']['inputs']['query']['name'] == 'query' for grade in grades)
    assert 'phmmer_grading_unexpected_query' in {error['code'] for error in errors}


def test_native_zero_results_is_distinct_from_missing_output(tmp_path, tiny):
    # Actual same tiny database with the selected impossible reporting cutoff.
    directory, sequence, _ = tiny
    from gene_annotation_episode.local_jobs import run_local_job
    result = run_local_job([str(PROGRAM), '--cpu', '1', '-T', '1000000', '--tblout', 'hits.tbl',
        '--domtblout', 'domains.tbl', str(directory/'query.faa'), str(directory/'references.faa')],
        cwd=tmp_path, policy=POLICY, stdout_path=tmp_path/'native.stdout', stderr_path=tmp_path/'native.stderr')
    assert result.returncode == 0
    request = request_for(tmp_path, tiny)
    request.update(native_text=str(tmp_path/'native.stdout'), hit_table=str(tmp_path/'hits.tbl'),
                   domain_table=str(tmp_path/'domains.tbl'))
    rows, errors, grades = worker_rows(tmp_path, request)
    assert rows == errors == grades == []
    assert json.loads((tmp_path/'summary.json').read_text())['rows'] == 0


def test_publication_grading_failure_is_partial_without_losing_original_measurement(tmp_path, tiny, monkeypatch):
    store, adapter, inputs, scope = workspace(tmp_path, tiny)
    def reject(sheet):
        raise ValueError('synthetic_publication_grading_failure')
    monkeypatch.setattr(grading_worker, 'calculate_hmmer_search_scores', reject)
    def synthetic_in_process_parser(directory, request, policy, *, cancel_event=None):
        # This fault injection does not claim a native resource-boundary test.
        worker.extract(request)
        return {'native': {'fixture': 'synthetic_in_process_grader_fault'}, 'failure': None}
    monkeypatch.setattr(publication, '_parse', synthetic_in_process_parser)
    with store:
        result = run_extract(adapter, inputs, scope, limit=10)
        assert result['status'] == 'partial' and len(result['result']['comparison_refs']) == 2
        assert result['result']['native_result_complete'] is True
        assert result['feedback']['native_error_count'] == 0
        assert result['feedback']['grading_error_count'] == 2
        assert 'synthetic_publication_grading_failure' in json.dumps(result['feedback'])
        for reference in result['result']['comparison_refs']:
            measured = values(store, reference)
            assert not {'query_coverage', 'target_coverage', 'identity_fraction', 'model_span_coverage'} & measured.keys()
            assert 'bitscore' in measured and 'evalue' in measured
            grading = saved_grade(store, reference)
            assert grading['scores'] is None and grading['sheet'] is None
            assert grading['failure']['code'] == 'synthetic_publication_grading_failure'
            assert_paired_aliases_equal_shared(store, reference)
        assert store.count('observation') == 2


def test_historical_snapshot_keeps_its_recorded_parser_semantics(tmp_path, tiny):
    store, adapter, inputs, scope = workspace(tmp_path, tiny)
    with store:
        captured = run_extract(adapter, inputs, scope, limit=0)
        saved = store.db.execute('SELECT * FROM homology_result_snapshots WHERE source_ref=?',
            (captured['result']['snapshot_ref'],)).fetchone()
        historical = json.loads(saved['body'])
        historical['parser_version'] = 'explicit_synthetic_historical_parser_v7'
        directory = tmp_path/'historical-parser-fixture'
        shutil.copytree(Path(saved['directory']), directory)
        with sqlite3.connect(directory/'measurements.sqlite') as db:
            for ordinal, raw in db.execute('SELECT ordinal,data FROM measurements').fetchall():
                row = json.loads(raw)
                row = {key: value for key, value in row.items() if not key.startswith('grading_')}
                db.execute('UPDATE measurements SET data=? WHERE ordinal=?', (canonical(row), ordinal))
        source = adapter._source('native.phmmer.parsed_snapshot', historical,
            parents=[historical['native_source_ref']], operands=[inputs.query_ref])
        store.db.execute('INSERT INTO homology_result_snapshots VALUES(?,?,?,?,?)',
            (source['id'], 'explicit-historical-fixture', inputs.query_ref, str(directory), canonical(historical)))
        old = run_extract(adapter, inputs, scope, snapshot_ref=source['id'], limit=10)
        assert old['status'] == 'partial'
        assert all(error['grading_failure']['code'] == 'phmmer_shared_grading_unavailable'
            for error in old['feedback']['publication_errors'])
        old_rows = {reference: store.get(reference) for reference in old['result']['comparison_refs']}
        for reference in old_rows:
            original = store.get(store.get(reference)['source_ref'])
            assert original['version'] == historical['parser_version']
            grade = saved_grade(store, reference)
            assert grade['failure']['code'] == 'phmmer_shared_grading_unavailable'
            semantic = json.loads(store.get_artifact(original['artifact_ref']))
            assert semantic['paired_residues'] > 0
            assert semantic['numerical_projection_version'] == 'hmmer_shared_paired_aliases_v1'
            assert not {'query_coverage', 'target_coverage', 'identity_fraction', 'model_span_coverage'} & values(store, reference).keys()
        new = run_extract(adapter, inputs, scope, snapshot_ref=captured['result']['snapshot_ref'], limit=10)
        assert set(new['result']['comparison_refs']).isdisjoint(old_rows)
        assert {reference: store.get(reference) for reference in old_rows} == old_rows
        replay = run_extract(adapter, inputs, scope, snapshot_ref=source['id'], limit=10)
        assert replay['result'] == old['result'] and replay['changed_record_refs'] == []
        assert replay['status'] == old['status']
        assert replay['feedback'] == old['feedback']


def test_shared_alias_cells_are_projected_without_raw_count_or_consensus_fallback(tmp_path, tiny, monkeypatch):
    """Injected shared cells are projection sentinels, not native measurements."""
    store, adapter, inputs, scope = workspace(tmp_path, tiny)
    original = adapter._grading
    def injected(*args, **kwargs):
        grading = original(*args, **kwargs)
        score, = grading['scores']['domains']
        for name, value in (('paired_model_coverage', .125), ('paired_sequence_coverage', .625),
                ('sequence_identity_fraction', None)):
            score[name] = score['components'][name]['value'] = score['derived'][name] = value
        assert score['consensus_identity_fraction'] == 1
        return grading
    monkeypatch.setattr(adapter, '_grading', injected)
    with store:
        result = run_extract(adapter, inputs, scope, limit=10)
        assert result['status'] == 'completed'
        for reference in result['result']['comparison_refs']:
            assert_paired_aliases_equal_shared(store, reference)
            measured = values(store, reference)
            assert measured['query_coverage'] == .125 and measured['target_coverage'] == .625
            assert 'identity_fraction' not in measured
            assert measured['consensus_identity_fraction'] == 1


def test_preexisting_ungraded_observation_cache_and_witness_remain_unchanged(tmp_path, tiny, monkeypatch):
    """A synthetic historical Store record must keep its originally saved values."""
    store, adapter, inputs, scope = workspace(tmp_path, tiny)
    monkeypatch.setattr(adapter, '_grading', lambda *args, **kwargs: None)
    with store:
        captured = run_extract(adapter, inputs, scope, limit=10)
        historical_refs = []
        for reference in captured['result']['comparison_refs']:
            observed = store.get(reference)
            source = store.get(observed['source_ref'])
            semantic = json.loads(store.get_artifact(source['artifact_ref']))
            semantic.pop('numerical_projection_version')
            old_source = adapter._source('native.phmmer.alignment', semantic,
                parents=source['parent_source_refs'], operands=source['operand_refs'],
                parser_version=source['version'])
            historical = {k: v for k, v in observed.items() if k not in {'id', 'origin', 'record_type'}}
            historical['source_ref'] = old_source['id']
            historical['measurements'] += [{'name': name, 'value': {
                'type': 'number', 'value': value, 'unit_ref': None}}
                for name, value in (('query_coverage', .123), ('target_coverage', .456), ('identity_fraction', .789))]
            old = store.put('observation', historical, origin='tool', scope=scope)
            store.db.execute('UPDATE homology_measurements SET observation_ref=? WHERE measurement_key=?',
                (old['id'], semantic['measurement_key']))
            store.db.execute('UPDATE homology_result_witnesses SET record_ref=? WHERE record_ref=?',
                (old['id'], reference))
            historical_refs.append(old['id'])
        records = [tuple(row) for row in store.db.execute('SELECT * FROM records ORDER BY id')]
        cache = [tuple(row) for row in store.db.execute('SELECT * FROM homology_measurements ORDER BY measurement_key')]
        witnesses = [tuple(row) for row in store.db.execute('SELECT * FROM homology_result_witnesses ORDER BY snapshot_ref,ordinal')]
        replay = run_extract(adapter, inputs, scope, snapshot_ref=captured['result']['snapshot_ref'], limit=10)
        assert replay['status'] == 'completed' and replay['feedback'] is None
        assert replay['result']['comparison_refs'] == historical_refs
        assert replay['changed_record_refs'] == []
        assert [tuple(row) for row in store.db.execute('SELECT * FROM records ORDER BY id')] == records
        assert [tuple(row) for row in store.db.execute('SELECT * FROM homology_measurements ORDER BY measurement_key')] == cache
        assert [tuple(row) for row in store.db.execute('SELECT * FROM homology_result_witnesses ORDER BY snapshot_ref,ordinal')] == witnesses
        for reference in historical_refs:
            measured = values(store, reference)
            assert measured['query_coverage'] == .123 and measured['target_coverage'] == .456
            assert measured['identity_fraction'] == .789
            assert source_tool_gradings(store, store.get(reference)['source_ref']) == []
