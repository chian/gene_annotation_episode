"""Retained real one-gene outputs, bounded parser jobs, actual canonical Store.

No new homology search, network request, model call or scientific score. A damaged
copy is an explicitly synthetic failure fixture, never relabeled native evidence.
"""
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from Bio import SeqIO
import pytest

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.homology_results import HomologyResults, NativePhmmerInput, recorded_coverage
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.phmmer_format import alignment_rows, paired_segments
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


CASE = Path(__file__).resolve().parents[1]/'cases/gene_001'
JOB = CASE/'jobs/homology_001'


def prepared(tmp_path):
    store = Store(tmp_path/'workspace')
    target = store.create_problem(CASE/'target.fna', molecule='dna', role='gene')['subject_refs'][0]
    scope = {'subject_refs': [target]}
    translated = ToolRegistry(store).execute('sequence.translate', {'subject_ref': target, 'code': 11, 'cds': True}, scope=scope)
    assert translated['status'] == 'completed', translated
    product = translated['result']['records'][0]['product_ref']
    job = json.loads((JOB/'job.json').read_text())
    inputs = NativePhmmerInput(product, CASE/'target.faa', JOB/'reviewed.fasta', JOB/'homology_search.stdout',
        JOB/'hits.tbl', job['database_sha256'], job['executable_sha256'],
        {'kind': 'retained_real_empirical_probe', 'original_job_manifest': job})
    adapter = HomologyResults(store, policy=LocalJobPolicy(256*1024**2, 4*1024**2))
    return store, adapter, inputs, scope


def extract(adapter, inputs, scope, **kwargs):
    return asyncio.run(adapter.extract(inputs, scope=scope, **kwargs))


def counts(store):
    return dict(store.db.execute('SELECT record_type,count(*) FROM records GROUP BY record_type'))


def test_finite_scan_matches_every_retained_domain_without_native_thresholds():
    query = str(SeqIO.read(CASE/'target.faa', 'fasta').seq)
    refs = {r.id: str(r.seq) for r in SeqIO.parse(JOB/'reported-references.faa', 'fasta')}
    events = list(alignment_rows(JOB/'homology_search.stdout', query_id='gene_001', query_length=253))
    assert all(event['kind'] == 'alignment' for event in events)
    expected = {(hit['reference_id'], row['domain_index']): row for hit in json.loads(
        (JOB/'inspection.json').read_text())['measurements'] for row in hit['alignments']}
    assert len(events) == len(expected) == 20
    for event in events:
        row = event['data']
        native = expected[row['reference_id'], row['domain_index']]
        for key in ('query_interval_aa_zero_based_half_open', 'reference_interval_aa_zero_based_half_open',
                    'query_aligned', 'reference_aligned', 'conditional_domain_evalue',
                    'independent_domain_evalue', 'domain_bitscore', 'native_inclusion_flag'):
            assert row[key] == native[key]
        paired_segments(row, query, refs[row['reference_id']])
    assert min(e['data']['domain_bitscore'] for e in events) < 0
    assert max(e['data']['independent_domain_evalue'] for e in events) > 100000


def test_unflushed_native_output_is_not_a_successful_zero_hit_report(tmp_path):
    empty = tmp_path/'empty-native.stdout'
    empty.write_bytes(b'')
    assert list(alignment_rows(empty, query_id='query', query_length=253)) == [
        {'kind':'error','data':{'code':'native_query_header_unavailable','role':'native_text','byte_span':[0,0]}}]


def test_actual_bounded_extraction_pages_typed_references_and_reuses_canonical_measurements(tmp_path, monkeypatch):
    store, adapter, inputs, scope = prepared(tmp_path)
    with store:
        # Publication may not hydrate entire native/reference artifacts in the
        # workflow host. Workers and bounded artifact streams perform that work.
        read_artifact = store.get_artifact
        monkeypatch.setattr(store, 'get_artifact', lambda *_: (_ for _ in ()).throw(AssertionError('whole-artifact hydration')))
        first = extract(adapter, inputs, scope, limit=10)
        assert first['status'] == 'completed', first
        snapshot = first['result']['snapshot_ref']
        assert [row['ordinal'] for row in first['result']['publication_rows']] == list(range(1, 11))
        progress = adapter.coverage(snapshot, query_ref=inputs.query_ref, scope=scope)
        assert progress['parsed_row_count'] == 37 and progress['acquired_row_count'] == 10
        assert progress['acquired_ordinal_intervals'] == [[1, 11]]
        assert progress['all_parsed_rows_acquired'] is False
        assert progress['parser_finished'] is progress['native_termination_seen'] is progress['native_result_complete'] is True
        refs, comparisons = set(first['result']['reference_refs']), set(first['result']['comparison_refs'])
        offset = first['result']['next_offset']
        while offset is not None:
            page = extract(adapter, inputs, scope, snapshot_ref=snapshot, offset=offset, limit=10)
            assert page['status'] == 'completed', page
            refs.update(page['result']['reference_refs']); comparisons.update(page['result']['comparison_refs'])
            offset = page['result']['next_offset']
        assert len(refs) == 17 and len(comparisons) == 20
        progress = adapter.coverage(snapshot, query_ref=inputs.query_ref, scope=scope)
        assert progress['acquired_row_count'] == 37 and progress['acquired_ordinal_intervals'] == [[1, 38]]
        assert progress['all_parsed_rows_acquired'] is True
        assert store.count('observation') == 21  # 20 native HSPs + actual translation
        assert store.count('annotation') == store.count('assessment') == 0
        assert [row['id'] for row in store.targets()] == scope['subject_refs']
        schema = {'type':'object','additionalProperties':False,'required':['comparisons'],
            'properties':{'comparisons':{'type':'array','items':{'type':'string','format':'reference','x-reference-namespace':'observation'}}}}
        validate_form({'comparisons': list(comparisons)}, schema,
            lambda ref,namespace: ref in store.reference_subset([ref],scope) and store.get(ref)['record_type']==namespace)
        before = counts(store)
        replay = extract(adapter, inputs, scope, snapshot_ref=snapshot, limit=100)
        assert counts(store) == before and replay['changed_record_refs'] == []
        assert len(replay['result']['publication_rows']) == 37
        assert {row['record_ref'] for row in replay['result']['publication_rows']} == refs | comparisons
        # Another captured raw-output version is another witness, not another
        # contribution for identical deterministic measurements.
        extended = tmp_path/'extended-native.stdout'
        extended.write_bytes(inputs.native_text.read_bytes()+b'\n# fixture append: no new scientific measurement\n')
        again = extract(adapter, replace(inputs, native_text=extended), scope, limit=100)
        assert again['result']['snapshot_ref'] != snapshot
        assert set(again['result']['comparison_refs']) == comparisons
        assert again['changed_record_refs'] == [] and store.count('observation') == 21
        assert store.db.execute('SELECT count(*) FROM homology_result_witnesses').fetchone()[0] == 74
        for original_row, reused_row in zip(replay['result']['publication_rows'], again['result']['publication_rows'], strict=True):
            assert {key: original_row[key] for key in ('ordinal', 'record_ref', 'record_type')} == {
                key: reused_row[key] for key in ('ordinal', 'record_ref', 'record_type')}
            assert [span['byte_span'] for span in original_row['source_byte_spans']] == [
                span['byte_span'] for span in reused_row['source_byte_spans']]
        # The returned measurement is directly usable by the existing site
        # inspection tool, with amino-acid case/gap notation normalized once.
        monkeypatch.setattr(store, 'get_artifact', read_artifact)
        for observed in comparisons:
            data = json.loads(read_artifact(store.get(store.get(observed)['source_ref'])['artifact_ref']))
            if data['reference_id'] == 'sp|A6H7I3|ANGE2_BOVIN':
                break
        positions = [0, 197, 200, 220, 281, 353]
        result = ToolRegistry(store).execute('sequence.sites', {'alignment_ref': observed, 'positions': positions}, scope=scope)
        assert result['status'] == 'completed', result
        mapped = {site['reference_position']: site for site in result['result']['sites']}
        assert mapped[0]['relationship'] == 'outside_alignment'
        q,r = data['query_interval_aa_zero_based_half_open'][0], data['reference_interval_aa_zero_based_half_open'][0]
        for a,b in zip(data['query_aligned'].upper(), data['reference_aligned'].upper()):
            if b not in '-.' and r in positions:
                assert mapped[r]['reference_residue'] == b
                assert mapped[r]['query_position'] == (q if a not in '-.' else None)
            q += a not in '-.'
            r += b not in '-.'


def test_truncated_alignment_and_unflushed_table_keep_complete_preceding_domains(tmp_path):
    store, adapter, inputs, scope = prepared(tmp_path)
    text = inputs.native_text.read_bytes()
    begin = text.index(b'>> sp|A6H7I3|')
    cut = text.index(b'gene_001 115', begin)+len(b'gene_001 115')
    damaged = tmp_path/'explicitly-truncated-fixture.stdout'
    damaged.write_bytes(text[:cut])
    partial = replace(inputs, native_text=damaged, hit_table=tmp_path/'not-flushed.tbl',
        provenance={'kind': 'synthetic_truncation_of_retained_real_output', 'original_sha256': hashlib.sha256(text).hexdigest()})
    with store:
        result = extract(adapter, partial, scope, limit=100)
        assert result['status'] == 'partial', result
        assert len(result['result']['comparison_refs']) == 4
        assert len(result['result']['reference_refs']) == 17
        errors = adapter.errors(result['result']['snapshot_ref'], scope=scope, offset=0, limit=100)
        assert 'native_hit_table_unavailable' in {row['code'] for row in errors['errors']}
        assert errors['total'] > 1
        coverage = adapter.coverage(result['result']['snapshot_ref'], query_ref=inputs.query_ref, scope=scope)
        assert coverage['parsed_row_count'] == coverage['acquired_row_count'] == 21
        assert coverage['all_parsed_rows_acquired'] is True
        assert coverage['native_error_count'] == errors['total']
        assert coverage['parser_finished'] is True and coverage['native_result_complete'] is False
        assert all(store.get(row['source_ref'])['record_type'] == 'source' for row in errors['errors'])
        assert store.count('annotation') == 0


def test_one_publication_failure_retains_siblings_and_returns_no_dangling_references(tmp_path, monkeypatch):
    store, adapter, inputs, scope = prepared(tmp_path)
    original = store.put
    failed = False
    def one_failure(kind, data, **kwargs):
        nonlocal failed
        if kind == 'observation' and not failed:
            failed = True
            raise ContractError('synthetic_row_publication_failure')
        return original(kind, data, **kwargs)
    monkeypatch.setattr(store, 'put', one_failure)
    with store:
        result = extract(adapter, inputs, scope, limit=100)
        assert result['status'] == 'partial', result
        assert len(result['result']['comparison_refs']) == 19
        assert result['feedback']['publication_errors'] == [{'ordinal': 18, 'code': 'synthetic_row_publication_failure'}]
        assert [row['ordinal'] for row in result['result']['publication_rows']] == [*range(1, 18), *range(19, 38)]
        coverage = adapter.coverage(result['result']['snapshot_ref'], query_ref=inputs.query_ref, scope=scope)
        assert coverage['parsed_row_count'] == 37 and coverage['acquired_row_count'] == 36
        assert coverage['acquired_ordinal_intervals'] == [[1, 18], [19, 38]]
        assert coverage['all_parsed_rows_acquired'] is False and coverage['native_result_complete'] is True
        assert all(store.get(ref)['id'] == ref for ref in result['record_refs'])
        monkeypatch.setattr(store, 'put', original)
        restored = extract(adapter, inputs, scope, snapshot_ref=result['result']['snapshot_ref'], offset=17, limit=1)
        assert restored['status'] == 'completed'
        assert len(restored['changed_record_refs']) == 1 and store.count('observation') == 21
        assert restored['result']['publication_rows'][0]['ordinal'] == 18
        assert adapter.coverage(result['result']['snapshot_ref'], query_ref=inputs.query_ref, scope=scope)['acquired_ordinal_intervals'] == [[1, 38]]


def test_identical_bytes_reuse_parsing_while_preserving_new_capture_origin(tmp_path, monkeypatch):
    from gene_annotation_episode import homology_results as module
    store, adapter, inputs, scope = prepared(tmp_path)
    with store:
        first = extract(adapter, inputs, scope, limit=100)
        def forbidden(*args, **kwargs):
            raise AssertionError('identical current parsing must be reused')
        monkeypatch.setattr(module, 'start_job', forbidden)
        second = extract(adapter, replace(inputs, provenance={'kind':'synthetic_second_capture_context',
            'actual_retained_origin':inputs.provenance}), scope, limit=100)
        assert first['result']['snapshot_ref'] != second['result']['snapshot_ref']
        assert first['result']['execution_source_ref'] != second['result']['execution_source_ref']
        assert first['result']['comparison_refs'] == second['result']['comparison_refs']
        assert second['changed_record_refs'] == []
        observed = first['result']['comparison_refs'][0]
        witnesses = adapter.witnesses(observed, scope=scope, offset=0, limit=100)
        assert witnesses['total'] == 2
        assert {r['snapshot_ref'] for r in witnesses['witnesses']} == {
            first['result']['snapshot_ref'], second['result']['snapshot_ref']}


def test_explicit_retry_after_environment_repair_keeps_original_failure_and_sources(tmp_path, monkeypatch):
    from gene_annotation_episode import homology_results as module
    store, adapter, inputs, scope = prepared(tmp_path)
    original = module.start_job
    def unavailable(*args, **kwargs):
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
                               operational={'reason':'explicitly_synthetic_unavailable_boundary'})
    monkeypatch.setattr(module, 'start_job', unavailable)
    with store:
        failed = extract(adapter, inputs, scope, limit=100)
        assert failed['status'] == 'failed'
        snapshot = failed['result']['snapshot_ref']
        assert store.get(snapshot)['record_type'] == 'source'
        errors = adapter.errors(snapshot, scope=scope, offset=0, limit=10)
        assert errors['status'] == 'unavailable' and errors['total'] is None
        coverage = adapter.coverage(snapshot, query_ref=inputs.query_ref, scope=scope)
        assert coverage['status'] == 'unavailable' and coverage['parsed_row_count'] is None
        assert coverage['acquired_row_count'] == 0 and coverage['all_parsed_rows_acquired'] is None
        assert coverage['parser_finished'] is False and coverage['native_result_complete'] is False
        assert coverage['parse_execution_failure']['code'] == 'local_job_boundary_unavailable'
        monkeypatch.setattr(module, 'start_job', original)  # Relevant environment/implementation change.
        assert extract(adapter, inputs, scope, limit=100)['status'] == 'failed'  # No hidden retry.
        repaired = extract(adapter, inputs, scope, limit=100, retry_from=snapshot, attempt_key='chosen-repair-action')
        assert repaired['status'] == 'completed' and len(repaired['result']['comparison_refs']) == 20
        historical = extract(adapter, inputs, scope, snapshot_ref=snapshot, limit=100)
        assert historical['status'] == 'failed' and historical['feedback'] == failed['feedback']
        replay = extract(adapter, inputs, scope, limit=100, retry_from=snapshot, attempt_key='chosen-repair-action')
        assert replay['result']['snapshot_ref'] == repaired['result']['snapshot_ref']
        assert replay['changed_record_refs'] == []


def test_zero_page_and_read_only_coverage_preserve_source_bound_row_facts(tmp_path, monkeypatch):
    from gene_annotation_episode import homology_results as module
    store, adapter, inputs, scope = prepared(tmp_path)
    with store:
        empty_page = extract(adapter, inputs, scope, limit=0)
        snapshot = empty_page['result']['snapshot_ref']
        initial = adapter.coverage(snapshot, query_ref=inputs.query_ref, scope=scope)
        assert initial['parsed_row_count'] == 37 and initial['acquired_row_count'] == 0
        assert initial['acquired_ordinal_intervals'] == [] and initial['all_parsed_rows_acquired'] is False
        page = extract(adapter, inputs, scope, snapshot_ref=snapshot, offset=16, limit=3)
        assert [row['ordinal'] for row in page['result']['publication_rows']] == [17, 18, 19]
        for row in page['result']['publication_rows']:
            assert store.get(row['record_ref'])['record_type'] == row['record_type']
            assert len(row['source_byte_spans']) == 1
            for span in row['source_byte_spans']:
                start, end = span['byte_span']
                assert 0 <= start < end
                with artifact_path(store, span['artifact_ref']).open('rb') as stream:
                    stream.seek(start)
                    native = stream.read(end-start)
                assert (b'== domain' in native) if row['record_type'] == 'observation' else (b'sp|' in native)
            witnesses = adapter.witnesses(row['record_ref'], scope=scope, offset=0, limit=10)
            assert witnesses['witnesses'][0]['ordinal'] == row['ordinal']
            assert witnesses['witnesses'][0]['source_byte_spans'] == row['source_byte_spans']
        saved = store.db.execute('SELECT directory FROM homology_result_snapshots WHERE source_ref=?', (snapshot,)).fetchone()
        directory = Path(saved[0])
        directory.rename(directory.with_name(directory.name+'-unavailable'))
        def forbidden(*args, **kwargs):
            raise AssertionError('coverage must not start work or open the parser cache')
        monkeypatch.setattr(module, 'start_job', forbidden)
        monkeypatch.setattr(module.sqlite3, 'connect', forbidden)
        before = store.db.total_changes
        with store.read_snapshot():
            assert store.db.in_transaction
            progress = recorded_coverage(store, snapshot, query_ref=inputs.query_ref, scope=scope)
            assert store.db.in_transaction
        assert store.db.total_changes == before
        assert progress['acquired_row_count'] == 3 and progress['acquired_ordinal_intervals'] == [[17, 20]]
        assert progress['parser_finished'] is progress['native_result_complete'] is True
        with pytest.raises(ContractError, match='does_not_resolve_for_query'):
            recorded_coverage(store, snapshot, query_ref=scope['subject_refs'][0], scope=scope)
        narrow = {'subject_refs': scope['subject_refs'], 'segments': [
            {'target_ref': scope['subject_refs'][0], 'start': 0, 'end': 3, 'unit': 'nt'}]}
        with pytest.raises(ContractError, match='outside_assigned_scope'):
            recorded_coverage(store, snapshot, query_ref=inputs.query_ref, scope=narrow)


def test_all_acquired_clean_parse_prefix_does_not_claim_complete_native_results(tmp_path):
    store, adapter, inputs, scope = prepared(tmp_path)
    raw = inputs.native_text.read_bytes()
    prefix = tmp_path/'synthetic-clean-prefix.stdout'
    prefix.write_bytes(raw[:raw.index(b'Internal pipeline statistics')])
    with store:
        result = extract(adapter, replace(inputs, native_text=prefix,
            provenance={'kind': 'synthetic_clean_prefix_of_retained_output'}), scope, limit=100)
        assert result['status'] == 'completed'  # Representation/publication succeeded.
        assert result['result']['native_result_complete'] is False
        progress = adapter.coverage(result['result']['snapshot_ref'], query_ref=inputs.query_ref, scope=scope)
        assert progress['parsed_row_count'] == progress['acquired_row_count'] == 37
        assert progress['parser_finished'] is progress['all_parsed_rows_acquired'] is True
        assert progress['native_error_count'] == 0 and progress['parse_execution_failure'] is None
        assert progress['native_termination_seen'] is progress['native_result_complete'] is False


def test_job_bound_snapshots_require_their_actual_capture_identity_without_reparsing(tmp_path, monkeypatch):
    from gene_annotation_episode import homology_results as module
    store, adapter, inputs, scope = prepared(tmp_path)
    # Explicit identity fixtures; these do not claim new physical job execution.
    context = {'job_ref': 'fixture_job_A', 'registry_ref': 'fixture_registry'}
    first_inputs = replace(inputs, provenance=context)
    other_inputs = replace(inputs, provenance={**context, 'job_ref': 'fixture_job_B'})
    with store:
        first = extract(adapter, first_inputs, scope, limit=100)
        snapshot = first['result']['snapshot_ref']
        def forbidden(*args, **kwargs):
            raise AssertionError('identical native bytes must reuse the parse')
        monkeypatch.setattr(module, 'start_job', forbidden)
        with pytest.raises(ContractError, match='execution_context_mismatch'):
            extract(adapter, other_inputs, scope, snapshot_ref=snapshot, limit=1)
        with pytest.raises(ContractError, match='execution_context_mismatch'):
            extract(adapter, inputs, scope, snapshot_ref=snapshot, limit=1)
        for wrong in (None, other_inputs.provenance, {**context, 'registry_ref': 'other_registry'}):
            with pytest.raises(ContractError, match='execution_context_mismatch'):
                recorded_coverage(store, snapshot, query_ref=inputs.query_ref, scope=scope, execution_context=wrong)
            with pytest.raises(ContractError, match='execution_context_mismatch'):
                adapter.errors(snapshot, query_ref=inputs.query_ref, scope=scope, offset=0, limit=1,
                    execution_context=wrong)
        assert adapter.errors(snapshot, scope=scope, offset=0, limit=1, execution_context=context)['total'] == 0
        progress = recorded_coverage(store, snapshot, query_ref=inputs.query_ref, scope=scope, execution_context=context)
        assert progress['execution_context'] == context and progress['acquired_row_count'] == 37
        second = extract(adapter, other_inputs, scope, limit=100)
        assert second['result']['snapshot_ref'] != snapshot
        assert second['result']['publication_rows'] == first['result']['publication_rows']
        assert second['changed_record_refs'] == []
        assert store.db.execute('SELECT count(*) FROM homology_result_witnesses').fetchone()[0] == 74


def test_historical_capture_without_ordinal_inventory_stays_unknown(tmp_path):
    store, adapter, inputs, scope = prepared(tmp_path)
    with store:
        result = extract(adapter, inputs, scope, limit=0)
        saved = store.db.execute('SELECT * FROM homology_result_snapshots WHERE source_ref=?',
            (result['result']['snapshot_ref'],)).fetchone()
        historical = json.loads(saved['body'])
        for key in ('parse_inventory', 'native_termination_seen', 'publication_witness_version'):
            historical.pop(key)
        # Explicit old-metadata fixture; no ordinal or parse fact is invented.
        source = adapter._source('native.phmmer.parsed_snapshot', historical,
            parents=[historical['native_source_ref']], operands=[inputs.query_ref])
        store.db.execute('INSERT INTO homology_result_snapshots VALUES(?,?,?,?,?)',
            (source['id'], saved['signature'], inputs.query_ref, saved['directory'], json.dumps(historical)))
        progress = recorded_coverage(store, source['id'], query_ref=inputs.query_ref, scope=scope)
        for key in ('parsed_row_count', 'acquired_row_count', 'acquired_ordinal_intervals',
                'all_parsed_rows_acquired', 'parser_finished', 'native_error_count',
                'native_termination_seen', 'native_result_complete'):
            assert progress[key] is None
        assert progress['status'] == 'unavailable'
