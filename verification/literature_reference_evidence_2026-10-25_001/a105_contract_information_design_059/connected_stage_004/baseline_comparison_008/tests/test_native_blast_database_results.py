"""Synthetic complete numerical generations, failure custody and frozen replay."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.native_blast_database_result_publication import validate_native_blast_database_publication
from test_native_blast_database_episode_binding import SyntheticHost, selector


def query_selection(h, *, kind='sequence', subject_ref=None):
    """Explicit synthetic parent-received proof and complete query relation."""
    from gene_annotation_episode.execution_contracts import canonical
    proof_artifact = h.store.artifact(b'{"relation":true}', 'application/json')
    proof = h.store.put('source', dict(provider='caller', accession='synthetic-query-relation', uri=None,
        artifact_ref=proof_artifact, text_ref=None, request_ref=None, version='synthetic_v1', retrieved_at=None), origin='caller')['id']
    artifact = h.store.get(proof_artifact)
    source = dict(source_ref=proof, artifact_ref=proof_artifact, sha256=artifact['sha256'], size_bytes=artifact['size'])
    payload = dict(schema='native_blast_database_query_metadata_v1', documents=[dict(document_key='proof',
        artifact=dict(kind='received', **source), format='json')], sequence_records=[], effective_msa_masters=[],
        master_subjects=[], search_bindings=[], target_contexts=[])
    subject = subject_ref or h.scope['subject_refs'][0]
    relation = dict(input_key='query', record_ordinal=0, subject_ref=subject,
        source=dict(source_ref='proof', pointer='/relation'))
    if kind == 'sequence':
        payload['sequence_records'] = [dict(**relation, identity=None)]
    else:
        import hashlib
        from gene_annotation_episode.native_hmmer_result_publication import _subject_chunks
        sequence = b''.join(_subject_chunks(h.store, subject))
        payload['master_subjects'] = [dict(**relation, kind=kind, sequence_sha256=hashlib.sha256(sequence).hexdigest())]
    if h.job['program'] == 'deltablast':
        payload['search_bindings'] = [dict(search_key=dict(output_key='report', member_ordinal=None, report_index=0,
            search_pointer='/BlastOutput2/0/report/results/search'), stage='sequence_database', biological_round=None,
            database_key='target', input_pssm_key=None, provenance=dict(source_ref='proof', pointer='/relation'))]
    reference = h.store.artifact(canonical(payload), 'application/json'); metadata = h.store.get(reference)
    h.receipts.receive(h.root.episode_id, [proof, proof_artifact, reference], kind='initial')
    return selector('hsp', metadata_inputs=[dict(input_key='query-binding', consumer='query_identity', schema_id=payload['schema'],
        artifact_ref=reference, sha256=metadata['sha256'], size_bytes=metadata['size'])], retained_sources=[source])


def test_actual_preparation_and_frozen_replay_without_remote_or_calculation(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results(typed=False)
        outcome = h.select(child, 0, 'execution.results.collect')
        assert outcome['status'] == 'completed', outcome
        body = outcome['result']
        assert body['complete'], body['failures']
        row, = body['publication']['rows_by_family']['hsp']
        assert row['measurements'][0]['value'] == 20
        assert row['measurements'][1]['value'] == 0.0
        bundle = json.loads(h.store.get_artifact(body['capture']['bundle_artifact_ref']))
        source = h.store.get(body['publication']['source_ref'])
        assert source['auxiliary_artifact_refs'] == [body['capture']['artifact_refs'][r['artifact_key']] for r in bundle['artifacts']]
        root = __import__('pathlib').Path(bundle['plan']['attempt_directory'])
        root.rename(root.with_name('offline-attempt'))
        monkeypatch.setattr(h.family.job_progress_provider.targets, 'observe_target', lambda *a, **k: pytest.fail('replay observed remote'))
        monkeypatch.setattr(h.family.job_progress_provider.targets, 'read_file', lambda *a, **k: pytest.fail('replay read remote'))
        monkeypatch.setattr('gene_annotation_episode.native_blast_database_result_publication.run_local_job', lambda *a, **k: pytest.fail('replay ran worker'))
        assert validate_native_blast_database_publication(h.store, context=child, publication=body['publication']) == body['publication']
        assert h.family.native_blast_database_results.read_result(source['id'], h.scope)['publication'] == body['publication']
        artifact_path(h.store, body['preparation']['full_rows_artifact_ref']).write_bytes(b'changed retained rows')
        with pytest.raises(ValueError, match='digest|frozen'):
            validate_native_blast_database_publication(h.store, context=child, publication=body['publication'])
    finally:
        h.store.close()


def test_nonzero_native_retains_readable_rows_without_completion(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch, nonzero=True)
    try:
        child = h.results(typed=False)
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert body['capture']['status'] == 'complete'
        assert body['publication']['rows_by_family']['hsp']
        assert not body['publication']['native_execution_successful']
        assert not body['complete']
        assert h.family.completion_for_action(child, body['operation_key']) is None
    finally:
        h.store.close()


def test_missing_explicit_row_is_specific_incomplete_projection(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        selection = selector('hsp')
        selection['projections'][0]['rows'] = {'record_keys': ['explicit-missing-row']}
        child = h.results(selection, typed=False)
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert not body['complete']
        assert body['publication']['rows_by_family']['hsp'] == []
        assert body['failures'][-1]['detail_code'] == 'explicit_row_missing'
    finally:
        h.store.close()


def test_selected_metadata_requires_actual_parent_receipt(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        ref = h.store.artifact(b'{}', 'application/json'); artifact = h.store.get(ref)
        selection = selector('hsp', metadata_inputs=[dict(input_key='additional', consumer='profile', schema_id='unknown.future',
            artifact_ref=ref, sha256=artifact['sha256'], size_bytes=artifact['size'])])
        with pytest.raises(ValueError, match='selected_input_not_received'):
            h.results(selection, typed=False)
        h.receipts.receive(h.root.episode_id, [ref], kind='initial')
        child = h.results(selection, typed=False)
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert body['publication']['rows_by_family']['hsp']
        assert not body['complete']
        assert any(row['code'] == 'native_blast_metadata_schema_unsupported' for row in body['failures'])
    finally:
        h.store.close()


@pytest.mark.parametrize('program', ['psiblast', 'deltablast', 'rpsblast', 'rpstblastn', 'blastn_vdb', 'tblastn_vdb'])
def test_received_complete_query_publishes_only_native_query_observation(tmp_path, monkeypatch, program):
    from gene_annotation_episode.native_blast_database_result_publication import validate_native_blast_database_observation
    options = {}
    native = dict(query_from=1, query_to=4, hit_from=1, hit_to=4, align_len=4, identity=4,
        qseq='ACGT', hseq='ACGT', gaps=0, bit_score=20, score=40, evalue=0.0)
    if program == 'rpstblastn':
        native.update(query_to=12, query_frame=1)
        options.update(query_bytes=b'>one\nGCTTGTGGTACC\n', sequence='GCTTGTGGTACC', native_hsp=native)
    if program == 'tblastn_vdb':
        native.update(hit_to=12, hit_frame=1)
        options['native_hsp'] = native
    h = SyntheticHost(tmp_path, monkeypatch, program, **options)
    try:
        child = h.results(query_selection(h))
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert body['complete'], body['failures']
        row, = body['publication']['rows_by_family']['hsp']
        assert row['publication_status'] == 'published', body['failures']
        observed = h.store.get(row['observation_ref'])
        full = validate_native_blast_database_observation(h.store, observed)
        assert len(full['measurements']) > len(row['measurements']) == 2
        assert observed['source_subject_refs'] == row['reference_refs'] == []
        assert observed['dependencies'] == [row['source_ref'], h.scope['subject_refs'][0]]
        assert all(r['role'] == 'query' for r in observed['operand_intervals'])
        values = {r['name']: r['value']['value'] for r in observed['measurements']}
        assert values['native_score_bits'] == 20 and values['native_evalue'] == 0 and values['native_raw_score'] == 40
        assert observed['kind'] == ('profile_match' if program in {'rpsblast', 'rpstblastn'} else 'comparison')
        assert ('paired_identity' not in values) == (program in {'rpsblast', 'rpstblastn'})
        form, schema = h.returned(child)
        assert h.family.native_blast_database_returns.received_facts(h.root, schema)['execution_blast_database_hsp_rows'] == [row]
        assert h.family.resolve_received_reference(h.root, row['subject_ref'], 'subject') is True
        assert h.family.resolve_received_reference(h.root, row['source_ref'], 'subject') is False
    finally:
        h.store.close()


def test_empty_streams_and_projection_reuse_preserve_original_source_and_observation(tmp_path, monkeypatch):
    from gene_annotation_episode import native_blast_database_result_publication as publication
    h = SyntheticHost(tmp_path, monkeypatch, empty_logs=True)
    try:
        selection = query_selection(h)
        child = h.results(selection)
        first = h.select(child, 0, 'execution.results.collect')['result']
        assert first['complete'], first['failures']
        bundle = json.loads(h.store.get_artifact(first['capture']['bundle_artifact_ref']))
        streams = [r for r in bundle['artifacts'] if r['role'] in {'stdout', 'stderr'}]
        assert len(streams) == 2 and streams[0]['artifact_key'] != streams[1]['artifact_key']
        assert all(r['size_bytes'] == 0 for r in streams)
        refs = [first['capture']['artifact_refs'][r['artifact_key']] for r in streams]
        assert refs[0] == refs[1]
        source = h.store.get(first['publication']['source_ref'])
        assert source['auxiliary_artifact_refs'] == list(dict.fromkeys(
            first['capture']['artifact_refs'][r['artifact_key']] for r in bundle['artifacts']))
        assert source['auxiliary_artifact_refs'].count(refs[0]) == 1
        form, schema = h.returned(child)
        original_worker = publication.run_local_job
        calls = []
        def bounded(argv, **kwargs):
            assert 'gene_annotation_episode.native_blast_database_result_worker' not in argv, 'projection reran numerical worker'
            calls.append(argv)
            return original_worker(argv, **kwargs)
        monkeypatch.setattr(publication, 'run_local_job', bounded)
        selection['projections'][0]['metrics'] = ['native_raw_score']
        other = h.results(selection, index=2)
        second = h.select(other, 0, 'execution.results.collect')['result']
        assert second['complete'], second['failures']
        left, right = first['publication'], second['publication']
        assert left['source_ref'] == right['source_ref'] and left['calculation_id'] == right['calculation_id']
        assert left['record_refs'] == right['record_refs']
        assert right['rows_by_family']['hsp'][0]['measurements'][0]['value'] == 40
        assert h.store.query_records('observation')['total'] == 1
        assert h.family.native_blast_database_results.credit_view(other, dict(known_record_refs=right['record_refs'],
            initial_known_record_refs=left['record_refs']))['credit'] == 0
    finally:
        h.store.close()


@pytest.mark.parametrize('kind', ['msa', 'pssm'])
def test_saved_complete_master_map_publishes_without_redecoding(tmp_path, monkeypatch, kind):
    from gene_annotation_episode.native_blast_database_result_publication import validate_native_blast_database_observation
    query = (b'CLUSTAL W\n\none A-CGT\ntwo ATCGT\n' if kind == 'msa' else b'''PssmWithParameters ::= { pssm { isProtein TRUE, numRows 2, numColumns 4,
      rowLabels { "A", "C" }, query seq { id { local str "one" }, descr { title "one" },
      inst { repr raw, mol aa, length 4, seq-data iupacaa "ACGT" } },
      finalData { scores { 1,2,3,4,5,6,7,8 }, lambda 1.0, kappa 1.0, h 1.0 } } }''')
    h = SyntheticHost(tmp_path, monkeypatch, query_kind=kind, query_bytes=query)
    try:
        child = h.results(query_selection(h, kind=kind))
        body = h.select(child, 0, 'execution.results.collect')['result']
        row, = body['publication']['rows_by_family']['hsp']
        assert row['publication_status'] == 'published', body['failures']
        observed = h.store.get(row['observation_ref'])
        assert observed['native_blast_database']['query_axis_kind'] == kind + '_master'
        assert len(observed['dependencies']) == 3
        for module, name in [('blast_pssm_inputs', 'read_blast_pssm'), ('blast_pssm_inputs', 'read_blast_msa_master'),
                             ('blast_pssm_master_inputs', 'extract_blast_pssm_master_metadata'),
                             ('blast_pssm_calculators', 'calculate_blast_pssm_components')]:
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name,
                lambda *a, **k: pytest.fail('frozen validation redecoded or recalculated master'))
        assert validate_native_blast_database_observation(h.store, observed)['record_key'] == row['record_key']
    finally:
        h.store.close()


def test_invalid_model_before_generation_retains_original_exception(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch, model={'function_priors': None})
    try:
        child = h.results()
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert not body['complete'] and body['preparation'] is None and body['publication'] is None
        failure, = body['failures']
        assert (failure['stage'], failure['code'], failure['detail_code']) == (
            'calculation', 'native_blast_database_calculation_failed', 'calculator_contract_invalid')
        retained = [json.loads(h.store.get_artifact(r)) for r in body['diagnostic_artifact_refs']]
        invalid = next(r for r in retained if r.get('version') == 'native_blast_database_result_worker_request_v1')
        assert invalid['sequence_model'] == {'function_priors': None} and 'calculation_id' not in invalid
        errors = [r['errors'] for r in retained if r.get('schema') == 'native_blast_database_diagnostics_v1']
        assert any(dict(failure_index=0, exception_type='builtins.ValueError', message='native_blast_database_sequence_model_invalid') in r for r in errors)
        assert not list((h.store.path / 'native-blast-database-generations').glob('*/output/worker-manifest.json'))
        h.returned(child)
    finally:
        h.store.close()


def test_abrupt_worker_failure_retains_atomic_siblings_without_valid_manifest(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from pathlib import Path
    from gene_annotation_episode import native_blast_database_result_publication as publication
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        original = publication.run_local_job
        def kill_worker(argv, **kwargs):
            if 'gene_annotation_episode.native_blast_database_result_worker' not in argv:
                return original(argv, **kwargs)
            request = json.loads(Path(argv[-1]).read_text())
            output = Path(request['output_directory']); output.mkdir(parents=True)
            (output / 'collection.json').write_text('{"synthetic_atomic_sibling":true}\n')
            (output / 'rows.ndjson.partial').write_text('{"half_written":')
            kwargs['stderr_path'].write_text('synthetic SIGKILL injection; no actual resource exhaustion')
            return SimpleNamespace(returncode=-9, metadata={'synthetic_failure_injection': 'SIGKILL'})
        monkeypatch.setattr(publication, 'run_local_job', kill_worker)
        child = h.results()
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert not body['complete'] and body['capture']['status'] == 'complete'
        prepared = body['preparation']
        assert prepared['status'] == 'failed' and prepared['worker_manifest_artifact_ref'] is None
        assert prepared['collection_artifact_ref'] is None and prepared['full_rows_artifact_ref'] is None
        envelope = json.loads(h.store.get_artifact(prepared['source_grading_artifact_ref']))['grading']
        assert set(envelope['unsealed_artifact_refs']) == {'collection'}
        assert json.loads(h.store.get_artifact(envelope['unsealed_artifact_refs']['collection'])) == {'synthetic_atomic_sibling': True}
        assert any(r['code'] == 'native_blast_database_worker_resource_limit' for r in body['failures'])
        assert body['publication']['rows_by_family']['hsp'] == []
        h.returned(child)
    finally:
        h.store.close()


def test_original_metadata_tuple_order_retains_independent_outcomes(tmp_path, monkeypatch):
    payload = dict(schema='native_blast_database_query_metadata_v1', documents=[], sequence_records=[],
        effective_msa_masters=[], master_subjects=[], search_bindings=[], target_contexts=[])
    tuples = [dict(input_key='metadata', consumer='query_identity', schema_id=payload['schema']),
        dict(input_key='metadata', consumer='profile', schema_id='unregistered.synthetic')]
    h = SyntheticHost(tmp_path, monkeypatch, metadata=payload, tuples=tuples)
    try:
        child = h.results()
        body = h.select(child, 0, 'execution.results.collect')['result']
        envelope = json.loads(h.store.get_artifact(body['preparation']['source_grading_artifact_ref']))['grading']
        request = json.loads(h.store.get_artifact(envelope['request_artifact_ref']))
        assert [{k: r[k] for k in ('input_key', 'consumer', 'schema_id')} for r in request['metadata_descriptors']] == tuples
        inputs = json.loads(h.store.get_artifact(envelope['artifact_refs']['inputs']))
        assert [r['status'] for r in inputs['metadata']] == ['valid', 'unsupported']
        assert all(r['payload'] == payload for r in inputs['metadata'])
        assert body['publication']['rows_by_family']['hsp'][0]['measurements'][0]['value'] == 20
        assert not body['complete']
        h.returned(child)
    finally:
        h.store.close()


@pytest.mark.parametrize('fault', ['wrong_sequence', 'wrong_molecule', 'unreceived_subject'])
def test_complete_biological_identity_is_required_without_losing_native_rows(tmp_path, monkeypatch, fault):
    options = {'sequence': 'AGGT'} if fault == 'wrong_sequence' else {'molecule': 'dna'} if fault == 'wrong_molecule' else {}
    h = SyntheticHost(tmp_path, monkeypatch, **options)
    try:
        other = None
        if fault == 'unreceived_subject':
            other = h.store.put('feature', dict(subject_ref=h.scope['subject_refs'][0], kind='region',
                segments=[dict(start=0, end=4)], strand='+', context_refs=[]), origin='caller')['id']
            assert other not in h.receipts.known(h.root.episode_id)
        child = h.results(query_selection(h, subject_ref=other))
        body = h.select(child, 0, 'execution.results.collect')['result']
        row, = body['publication']['rows_by_family']['hsp']
        assert row['publication_status'] == 'source_only' and row['observation_ref'] is None
        assert row['subject_ref'] is None and row['reference_refs'] == []
        assert next(cell['value'] for cell in row['measurements'] if cell['name'] == 'native_score_bits') == 20
        assert h.store.query_records('observation')['total'] == 0
        assert any(failure['code'] == 'native_blast_database_query_unbound' for failure in body['failures'])
    finally:
        h.store.close()


def test_original_input_store_possession_does_not_authorize_launch(tmp_path, monkeypatch):
    from gene_annotation_episode.execution_episodes import LAUNCH_VERSION
    from gene_annotation_episode.native_blast_database_contracts import requested_job_from_native_blast_database
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        job = deepcopy(h.job)
        reference = h.store.artifact(Path(job['inputs'][0]['path']).read_bytes(), 'application/octet-stream')
        job['inputs'][0]['artifact_ref'] = reference
        assignment = deepcopy(h.assignment); assignment['requested_job'] = requested_job_from_native_blast_database(job)
        launch = dict(version=LAUNCH_VERSION, requests={'synthetic-hpc': assignment}, immutable_input_versions=[], constraints={})
        before = len(h.calls)
        with pytest.raises(ValueError, match='original_input_not_received'):
            h.family.prepare_assignment(h.root, 'launch', launch, h.scope, 'new-original-selected-job')
        assert len(h.calls) == before
        h.receipts.receive(h.root.episode_id, [reference], kind='initial')
        selected = h.family.prepare_assignment(h.root, 'launch', launch, h.scope, 'new-original-selected-job')
        assert selected['requests']['synthetic-hpc']['requested_job'] == assignment['requested_job']
        assert selected['requests']['synthetic-hpc']['constraints'] == assignment['constraints']
    finally:
        h.store.close()


def test_original_handoff_must_have_been_received_by_commissioning_parent(tmp_path, monkeypatch):
    from gene_annotation_episode.execution_episodes import RESULTS_VERSION
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        outsider = h.context((('annotation', 'other-root'),), {}, None)
        assignment = dict(version=RESULTS_VERSION, handoff_ref=h.handoff, selector=selector('hsp'))
        before = len(h.calls)
        with pytest.raises(ValueError, match='original_handoff_not_received'):
            h.family.prepare_assignment(outsider, 'results', assignment, h.scope, 'unreceived-original-handoff')
        assert len(h.calls) == before
    finally:
        h.store.close()
