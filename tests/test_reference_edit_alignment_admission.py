"""Engineering admission controls; supplied native data is not an aligner proof.

The hand fixture ATGC versus ATAC is published by the actual ToolRegistry and
saved by the real Journal. No alignment/native job runs. Reads of the admitted
result must use only its already retained native/grading artifacts and metadata.
"""
from copy import deepcopy
from dataclasses import replace
from importlib.metadata import version
import json
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode import alignment_correspondence, biopython_pairwise_grader
from gene_annotation_episode import library_targets
from gene_annotation_episode.alignment_site_native import (
    _selected_reference_alignment_authority, read_selected_reference_alignment,
)
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import MEDIA_TYPE, SCHEMA, SCHEMA_V2
from gene_annotation_episode.tools import ToolRegistry
from test_alignment_site_action_records import RUN, setup_case, saved_context, perform, requested


def _native(*, mode='global'):
    start, length = (0, 4) if mode == 'global' else (2, 8)
    return dict(aligned=True, query_length=length, reference_length=length, mode=mode,
        matrix='engineering_supplied', gap_open=-2, gap_extend=-1, native_score=3,
        paired_positions=4, identical_positions=3, identity_fraction=.75,
        query_coverage=4/length, reference_coverage=4/length,
        query_interval=[start, start+4], reference_interval=[start, start+4],
        coordinates=[[start, start+4], [start, start+4]], aligned_query='ATGC', aligned_reference='ATAC',
        biopython_version=version('biopython'))


def _publish(case, context, monkeypatch, directory, *, molecule='dna', mode='global',
        retention='modern', native_changes=None, tool='sequence.align', queries=None):
    original_source = case.tools._source
    def source(provider, body, **options):
        if provider == 'biopython.alignment' and retention != 'modern':
            grading = options.pop('tool_grading')
            if retention == 'legacy_source':
                options.pop('operand_refs')
            if retention in ('legacy_companion', 'legacy_conflict', 'bad_companion', 'ambiguous_grading'):
                correspondence = deepcopy(grading.pop('correspondence'))
                if retention == 'legacy_conflict':
                    grading = deepcopy(grading)
                    grading['sheet']['traceback']['query'] = 'ATAC'
                native_ref = case.store.artifact(canonical(body), 'application/json')
                envelope = dict(schema=SCHEMA, provider=provider, native_artifact_ref=native_ref, grading=grading)
                if retention == 'bad_companion':
                    correspondence['instances'][0]['components']['rows'][0]['counts']['identical_positions'] = 99
                    envelope.update(schema=SCHEMA_V2, correspondence=correspondence)
                options['auxiliary_artifact_refs'] = [case.store.artifact(canonical(envelope), MEDIA_TYPE)]
                if retention == 'ambiguous_grading':
                    second = deepcopy(envelope)
                    second['grading']['failure'] = dict(code='engineering_ambiguous_grading', category='grading_input')
                    options['auxiliary_artifact_refs'].append(case.store.artifact(canonical(second), MEDIA_TYPE))
        return original_source(provider, body, **options)
    count = 0
    async def prepare(name, arguments, scope):
        nonlocal count
        def item():
            nonlocal count
            path = directory / ('engineering-native-' + str(count) + '.json')
            count += 1
            body = _native(mode=mode)
            body.update(native_changes or {})
            path.write_text(canonical(body))
            return SimpleNamespace(output_path=path, metadata=dict(engineering_supplied_result=True,
                native_execution_performed=False))
        assert name == tool
        if name == 'reads.align':
            return [dict(arguments=dict(query_ref=query, **{key: arguments[key]
                for key in ('reference_ref', 'molecule', 'mode')}), native=item()) for query in queries]
        return item()
    arguments = dict(reference_ref=case.reference, molecule=molecule, mode=mode)
    arguments['query_ref' if tool == 'sequence.align' else 'subject_refs'] = case.query if queries is None else queries
    with monkeypatch.context() as publication:
        publication.setattr(case.tools, '_prepare_sequence_work_async', prepare)
        publication.setattr(case.tools, '_source', source)
        outcome = perform(case, context, 0, tool, arguments)
    observations = [ref for ref in outcome['record_refs'] if case.store.get(ref)['record_type'] == 'observation']
    case.alignment = observations[-1]
    case.outcome, case.producer = outcome, context
    case.receipts.receive(context.episode_id, [case.alignment], kind='own_action', source_index=0)
    return outcome


@pytest.fixture
def admission(tmp_path, monkeypatch):
    opened = []
    def make(*, molecule='dna', mode='global', retention='modern', native_changes=None,
            broad_scope=False, processing_model=None, external_query=False):
        directory = tmp_path / ('case-' + str(len(opened)))
        directory.mkdir()
        query, reference = ('ATGC', 'ATAC') if molecule == 'dna' else ('AUGC', 'AUAC')
        if mode == 'local':
            query, reference = 'GG' + query + 'GG', 'CC' + reference + 'CC'
        fasta = directory / 'operands.fa'
        fasta.write_text(f'>edited\n{query}\n>reference\n{reference}\n>other\n' + 'C'*len(query) + '\n')
        store = Store(directory / 'state')
        opened.append(store)
        query_ref, reference_ref, other = store.create_problem(fasta, molecule=molecule)['subject_refs']
        case = setup_case(store, ToolRegistry(store), scope={'subject_refs': [query_ref, other] if broad_scope else [query_ref]})
        if external_query:
            material = store.register_material(data=f'>registered_external_query\n{query}\n', format='fasta', molecule=molecule)
            parsed = store.parse_material(material['id'])
            member, = store.material_members(parsed['collection_ref'])['members']
            query_ref = store.material_reference(member['id'])['id']
        case.query, case.reference, case.other, case.directory = query_ref, reference_ref, other, directory
        context = saved_context(case, requested(), name='producer')
        _publish(case, context, monkeypatch, directory, molecule=processing_model or molecule, mode=mode,
            retention=retention, native_changes=native_changes)
        return case
    yield make
    for store in opened:
        store.close()


def _tables(store):
    return {row[0]: sorted(map(tuple, store.db.execute('SELECT * FROM "' + row[0] + '"')), key=repr)
        for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _no_math(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('admission must not run a native reader/calculator/aligner')
    for name in ('build_biopython_pairwise_sheet', 'calculate_biopython_pairwise_scores',
            '_calculate_biopython_artifacts', 'grade_biopython_pairwise'):
        monkeypatch.setattr(biopython_pairwise_grader, name, forbidden)
    monkeypatch.setattr(alignment_correspondence, 'calculate_correspondence_components', forbidden)
    monkeypatch.setattr(biopython_pairwise_grader, 'calculate_correspondence_components', forbidden)
    monkeypatch.setattr('gene_annotation_episode.sequence_ops.align_pair', forbidden)
    return forbidden


def _read(case, monkeypatch, *, context=None, cutoff=1, deny_all=False):
    context = case.producer if context is None else context
    source = case.store.get(case.store.get(case.alignment)['source_ref'])
    allowed = {source['artifact_ref'], *source.get('auxiliary_artifact_refs', [])}
    actual = case.store.get_artifact
    accessed = []
    def guarded(reference):
        accessed.append(reference)
        assert not deny_all and reference in allowed, 'unauthenticated or original sequence File opened'
        return actual(reference)
    before = _tables(case.store), case.store.db.total_changes
    with monkeypatch.context() as read:
        _no_math(read)
        read.setattr(case.store, 'get_artifact', guarded)
        try:
            capture = read_selected_reference_alignment(case.store, context, case.alignment,
                before_decision_index=cutoff)
        finally:
            assert (_tables(case.store), case.store.db.total_changes) == before
    assert set(capture) == {'source', 'operands', 'grading', 'correspondence', 'original_mappings'}
    return capture, accessed


@pytest.mark.parametrize('molecule', ['dna', 'rna'])
@pytest.mark.parametrize('mode', ['global', 'local'])
def test_actual_publication_admits_literal_nucleotide_alignment_without_input_bytes_or_grants(admission, monkeypatch, molecule, mode):
    case = admission(molecule=molecule, mode=mode)
    capture, accessed = _read(case, monkeypatch)
    assert capture['source']['provider'] == 'biopython.alignment'
    assert capture['source']['format'] == 'biopython_pairwise_json'
    assert capture['source']['alignment_ref'] == case.alignment
    assert capture['operands']['query']['subject_ref'] == case.query
    assert capture['operands']['reference']['subject_ref'] == case.reference
    assert all(row['alignment_unit'] == row['unit'] == 'nt' for row in capture['operands'].values())
    assert capture['grading']['sheet']['molecule'] == molecule and capture['grading']['sheet']['mode'] == mode
    assert capture['grading']['scores']['identical_positions'] == 3
    assert capture['grading']['scores']['substituted_positions'] == 1
    assert capture['correspondence']['version'] == 'alignment_correspondence_artifacts_v1'
    assert capture['original_mappings']['query'] == case.store.sequence_mapping(case.query)
    assert accessed and case.store.get(case.query)['sequence_ref'] not in accessed
    assert case.store.get(case.reference)['sequence_ref'] not in accessed


@pytest.mark.parametrize('retention', ['no_grading', 'legacy_source', 'legacy_companion'])
def test_missing_grading_and_missing_canonical_companion_remain_distinct(admission, monkeypatch, retention):
    case = admission(retention=retention)
    capture, _ = _read(case, monkeypatch)
    if retention == 'legacy_companion':
        assert capture['grading']['sheet']['schema'] == 'biopython_pairwise_sheet_v1'
        assert capture['grading']['scores']['identical_positions'] == 3
        assert capture['grading']['failure'] is None
    else:
        assert capture['grading'] is None
    assert capture['correspondence'] is None


def test_original_processing_model_is_independent_of_operand_molecule_metadata(admission, monkeypatch):
    case = admission(molecule='rna', processing_model='dna')
    capture, _ = _read(case, monkeypatch)
    assert capture['operands']['query']['molecule'] == 'rna'
    assert capture['grading']['sheet']['molecule'] == 'dna'


def test_registered_external_query_needs_no_input_credit_mapping_or_sequence_file_read(admission, monkeypatch):
    case = admission(external_query=True)
    assert case.store.roots(case.query) == case.store.coverage(case.query) == []
    capture, accessed = _read(case, monkeypatch)
    assert capture['operands']['query']['subject_ref'] == case.query
    assert capture['grading']['scores']['identical_positions'] == 3
    assert case.store.get(case.query)['sequence_ref'] not in accessed


def test_multiple_grading_media_artifacts_are_rejected_before_any_private_bytes(admission, monkeypatch):
    case = admission(retention='ambiguous_grading')
    with pytest.raises((ValueError, ContractError), match='ambiguous_grading'):
        _read(case, monkeypatch, deny_all=True)


@pytest.mark.parametrize('retention', ['legacy_conflict', 'bad_companion'])
def test_contradictory_saved_traceback_or_canonical_companion_is_rejected(admission, monkeypatch, retention):
    case = admission(retention=retention)
    expected = ('invalid_tool_grading_artifact' if retention == 'bad_companion'
        else 'biopython_pairwise_sheet_components_invalid')
    with pytest.raises((ValueError, ContractError), match=expected):
        _read(case, monkeypatch)


@pytest.mark.parametrize('role', ['native', 'grading'])
def test_retained_artifact_bytes_must_match_actual_source_identity(admission, monkeypatch, role):
    case = admission()
    source = case.store.get(case.store.get(case.alignment)['source_ref'])
    reference = source['artifact_ref'] if role == 'native' else source['auxiliary_artifact_refs'][0]
    sha = case.store.get(reference)['sha256']
    path = case.store.path / 'artifacts' / sha[:2] / sha
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises((ValueError, ContractError), match='artifact_digest_mismatch'):
        _read(case, monkeypatch)


def test_actual_grading_failure_and_partial_geometry_are_not_replaced_with_zero(admission, monkeypatch):
    failed = admission(native_changes={'aligned': 'invalid_boolean'})
    assert failed.outcome['status'] == 'partial'
    capture, _ = _read(failed, monkeypatch)
    assert capture['grading']['sheet'] is capture['grading']['scores'] is None
    assert capture['grading']['failure']['category'] == 'grading_input'
    assert capture['correspondence'] is None
    partial = admission(native_changes={'coordinates': None})
    capture, _ = _read(partial, monkeypatch)
    assert capture['grading']['sheet']['geometry']['available'] is False
    assert capture['grading']['scores']['paired_positions'] == 4
    assert capture['grading']['scores']['query_aligned_coverage'] is None


@pytest.mark.parametrize('cutoff', [None, True, False, -1, 1.0, '1', 0])
def test_cutoff_rejects_invalid_types_and_same_decision_result_before_bytes(admission, monkeypatch, cutoff):
    case = admission()
    with pytest.raises((ValueError, ContractError), match='cutoff|not_received'):
        _read(case, monkeypatch, cutoff=cutoff, deny_all=True)


@pytest.mark.parametrize('missing', ['source', 'observation'])
def test_both_observation_and_source_receipts_are_required_before_bytes(admission, monkeypatch, missing):
    case = admission()
    reference = case.alignment if missing == 'observation' else case.store.get(case.alignment)['source_ref']
    case.store.db.execute('DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?',
        (RUN, case.producer.episode_id, reference))
    with pytest.raises((ValueError, ContractError), match='not_received'):
        _read(case, monkeypatch, deny_all=True)


@pytest.mark.parametrize('before', [True, False])
def test_frozen_ancestry_uses_actual_original_producer_and_receipt_prefix(admission, monkeypatch, before):
    case = admission()
    receiver = case.producer
    if not before:
        case.store.db.execute('DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=?',
            (RUN, receiver.episode_id))
    path = (*receiver.path, ('scientific_process', 'descendant'))
    episode = EpisodeRef(RUN, path).episode_id
    request = {'message': {'scope': case.scope, 'episode_assignment': {}},
        'report_contract': {'measurements': {'schema': requested()}}}
    case.journal.save('runtime_episodes', dict(episode_id=episode, path=canonical(path),
        request=canonical(request), initial_credit=0., state='active'))
    case.receipts.bind(episode, receiver.episode_id)
    child = BindingContext(RUN, episode, 'scientific_process', path, case.scope, {}, request)
    if not before:
        case.receipts.receive(receiver.episode_id, [case.alignment], kind='child_form', source_index=4)
        with pytest.raises((ValueError, ContractError), match='not_received'):
            _read(case, monkeypatch, context=child, cutoff=0, deny_all=True)
    else:
        capture, _ = _read(case, monkeypatch, context=child, cutoff=0)
        assert capture['operands']['query']['subject_ref'] == case.query


@pytest.mark.parametrize('which', ['scope', 'assignment', 'path'])
def test_current_context_must_equal_its_actual_saved_assignment_before_bytes(admission, monkeypatch, which):
    case = admission()
    if which == 'path':
        # An inconsistent role/path cannot construct a BindingContext at all.
        with pytest.raises(ValueError, match='binding_context_path_must_match_role'):
            replace(case.producer, path=(('root', 'other'),))
        # A constructible same-role path must still match its saved episode.
        changed = {'path': (*case.producer.path[:-1], (case.producer.role, 'other'))}
    else:
        changed = ({'scope': {'subject_refs': [case.other]}} if which == 'scope'
            else {'assignment': {'invented': True}})
    with pytest.raises((ValueError, ContractError), match='context_conflict'):
        _read(case, monkeypatch, context=replace(case.producer, **changed), deny_all=True)


def test_actual_received_source_does_not_broaden_the_current_query_target_scope(admission, monkeypatch):
    case = admission()
    original_scope = case.scope
    case.scope = case.store.validate_scope({'subject_refs': [case.other]})
    receiver = saved_context(case, requested(), name='other-scope')
    case.scope = original_scope
    case.receipts.receive(receiver.episode_id, [case.alignment], kind='initial')
    with pytest.raises((ValueError, ContractError), match='query_outside_scope'):
        _read(case, monkeypatch, context=receiver, cutoff=0, deny_all=True)


@pytest.mark.parametrize('table', ['runtime_actions', 'tool_operations'])
def test_missing_original_action_or_operation_is_denied_before_bytes(admission, monkeypatch, table):
    case = admission()
    case.store.db.execute('DELETE FROM ' + table)
    with pytest.raises((ValueError, ContractError), match='unique_producer'):
        _read(case, monkeypatch, deny_all=True)


@pytest.mark.parametrize('change', ['arguments', 'outcome', 'producer_scope'])
def test_altered_original_action_joins_are_denied_before_bytes(admission, monkeypatch, change):
    case = admission()
    if change == 'arguments':
        row = case.store.db.execute('SELECT arguments FROM tool_operations').fetchone()
        arguments = json.loads(row[0]); arguments['reference_ref'] = case.other
        case.store.db.execute('UPDATE tool_operations SET arguments=?', (canonical(arguments),))
    elif change == 'outcome':
        row = case.store.db.execute('SELECT result FROM runtime_actions').fetchone()
        outcome = json.loads(row[0]); outcome['invented'] = True
        case.store.db.execute('UPDATE runtime_actions SET result=?', (canonical(outcome),))
    else:
        case.store.db.execute('UPDATE tool_operations SET scope=?', (canonical({'subject_refs': [case.other]}),))
    with pytest.raises((ValueError, ContractError), match='producer_'):
        _read(case, monkeypatch, deny_all=True)


def test_runtime_pending_metadata_is_allowed_but_not_a_second_producer(admission, monkeypatch):
    case = admission()
    row = case.store.db.execute('SELECT result FROM runtime_actions').fetchone()
    outcome = json.loads(row[0]); outcome['pending_work_after_action'] = []
    case.store.db.execute('UPDATE runtime_actions SET result=?', (canonical(outcome),))
    _read(case, monkeypatch)
    operation = dict(case.store.db.execute('SELECT * FROM tool_operations').fetchone())
    arguments = json.loads(operation['arguments'])
    key = f'{RUN}:{case.producer.episode_id}:2'
    operation_id = identity('operation', dict(key=key, name='sequence.align', arguments=arguments))
    duplicate = json.loads(operation['result']); duplicate['operation_ref'] = operation_id
    case.store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)',
        (key, operation_id, 'sequence.align', canonical(arguments), operation['scope'], canonical(duplicate)))
    case.journal.save('runtime_actions', dict(episode_id=case.producer.episode_id, decision_index=2,
        action=canonical(dict(kind='tool', tool='sequence.align', arguments=arguments)), result=canonical(duplicate), credit=0.))
    with pytest.raises((ValueError, ContractError), match='unique_producer'):
        _read(case, monkeypatch, cutoff=3, deny_all=True)


@pytest.mark.parametrize('role', ['query', 'reference'])
def test_validly_hashed_same_length_operand_reassignment_is_denied_before_bytes(admission, monkeypatch, role):
    case = admission(broad_scope=True)
    original = case.store.get(case.alignment)
    payload = {key: deepcopy(value) for key, value in original.items() if key not in ('id', 'origin', 'record_type')}
    field = 'subject_refs' if role == 'query' else 'source_subject_refs'
    old = payload[field][0]; payload[field] = [case.other]
    payload['dependencies'] = [case.other if ref == old else ref for ref in payload['dependencies']]
    for interval in payload['operand_intervals'] or []:
        if interval['role'] == role: interval['subject_ref'] = case.other
    forged = case.store.put('observation', payload, origin='tool')
    case.alignment = forged['id']
    case.receipts.receive(case.producer.episode_id, [case.alignment], kind='own_action', source_index=0)
    with pytest.raises((ValueError, ContractError), match='outside_scope|membership|operand'):
        _read(case, monkeypatch, deny_all=True)


def test_native_length_conflict_is_not_equated_with_same_length_operand_metadata(admission, monkeypatch):
    case = admission(native_changes={'query_length': 5})
    with pytest.raises((ValueError, ContractError), match='native_length_conflict'):
        _read(case, monkeypatch)


def test_actual_read_batch_admits_record_beyond_twelve_row_preview(tmp_path, monkeypatch):
    fastq = tmp_path / 'reads.fastq'
    fastq.write_text(''.join(f'@read-{i}\nATGC\n+\nIIII\n' for i in range(13)))
    with Store(tmp_path / 'state') as store:
        library, = store.create_problem(fastq, molecule='dna')['subject_refs']
        material = store.register_material(data='>comparison\nATAC\n', format='fasta', molecule='dna')
        parsed = store.parse_material(material['id'])
        member, = store.material_members(parsed['collection_ref'])['members']
        reference = store.material_reference(member['id'])
        case = setup_case(store, ToolRegistry(store), scope={'subject_refs': [library]})
        members = library_targets.member_page(store, library, limit=20, scope=case.scope)['members']
        queries = [member['id'] for member in members]
        assert len(queries) == 13
        case.query, case.reference = queries[-1], reference['id']
        context = saved_context(case, requested(), name='read-producer')
        outcome = _publish(case, context, monkeypatch, tmp_path, tool='reads.align', queries=queries)
        assert len(outcome['result']['records']) == 12
        assert case.alignment not in [item['observation_ref'] for item in outcome['result']['records']]
        capture, _ = _read(case, monkeypatch)
        assert capture['operands']['query']['subject_ref'] == queries[-1]
        assert capture['original_mappings']['query'] == store.sequence_mapping(queries[-1])


def _authority(case, monkeypatch, *, context=None, cutoff=1):
    before = _tables(case.store), case.store.db.total_changes
    with monkeypatch.context() as metadata:
        forbidden = _no_math(metadata)
        metadata.setattr(case.store, 'get_artifact', forbidden)
        metadata.setattr(case.tools, '_sequence', forbidden)
        metadata.setattr('gene_annotation_episode.alignment_site_native.source_descriptor', forbidden)
        metadata.setattr('gene_annotation_episode.alignment_site_native._reference_alignment_sheet', forbidden)
        try:
            return _selected_reference_alignment_authority(case.store,
                case.producer if context is None else context, case.alignment,
                before_decision_index=cutoff)
        finally:
            assert (_tables(case.store), case.store.db.total_changes) == before


@pytest.mark.parametrize('retention', ['modern', 'legacy_source', 'legacy_companion', 'no_grading'])
def test_metadata_authority_pins_original_producer_and_files_without_payload_or_grants(admission, monkeypatch, retention):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.execution_contracts import digest
    case = admission(retention=retention)
    authority = _authority(case, monkeypatch)
    assert set(authority) == {'alignment', 'source', 'operands', 'arguments', 'previews', 'admission'}
    witness = authority['admission']
    assert set(witness) == {'version', 'receiver', 'selection', 'producer'}
    assert witness['version'] == 'selected_reference_alignment_admission_v1'
    receiver = witness['receiver']
    assert set(receiver) == {'run_id', 'episode_id', 'before_decision_index',
        'request_sha256', 'scope_sha256', 'receipt_lineage_sha256'}
    assert (receiver['run_id'], receiver['episode_id'], receiver['before_decision_index']) == (
        RUN, case.producer.episode_id, 1)
    assert receiver['request_sha256'] == digest(plain(case.producer.request))
    assert receiver['scope_sha256'] == digest(plain(case.producer.scope))
    assert len(receiver['receipt_lineage_sha256']) == 64
    selected = witness['selection']
    assert set(selected) == {'alignment_ref', 'alignment_record_sha256', 'source_ref',
        'source_record_sha256', 'native_artifact', 'grading_artifacts'}
    assert selected['alignment_ref'] == case.alignment
    assert selected['alignment_record_sha256'] == digest(authority['alignment'])
    assert selected['source_ref'] == authority['source']['id']
    assert selected['source_record_sha256'] == digest(authority['source'])
    assert selected['native_artifact'] == case.store.get(authority['source']['artifact_ref'])
    assert len(selected['grading_artifacts']) == (retention in ('modern', 'legacy_companion'))
    assert all(row['record_type'] == 'artifact' and row['media_type'] == MEDIA_TYPE
        for row in selected['grading_artifacts'])
    operation = dict(case.store.db.execute('SELECT * FROM tool_operations').fetchone())
    action = dict(case.store.db.execute('SELECT * FROM runtime_actions').fetchone())
    producer = witness['producer']
    assert set(producer) == {'run_id', 'episode_id', 'decision_index', 'operation_key',
        'operation_ref', 'name', 'arguments', 'scope', 'operation_outcome_sha256',
        'selected_action_sha256', 'actual_outcome_sha256'}
    assert (producer['run_id'], producer['episode_id'], producer['decision_index']) == (
        RUN, case.producer.episode_id, 0)
    assert producer['operation_key'] == operation['operation_key']
    assert producer['operation_ref'] == operation['id']
    assert producer['name'] == operation['name'] == 'sequence.align'
    assert producer['arguments'] == authority['arguments'] == json.loads(operation['arguments'])
    assert producer['scope'] == json.loads(operation['scope'])
    assert producer['operation_outcome_sha256'] == digest(json.loads(operation['result']))
    assert producer['selected_action_sha256'] == digest(json.loads(action['action']))
    assert producer['actual_outcome_sha256'] == digest(json.loads(action['result']))
    json.dumps(witness, allow_nan=False)
    authority['alignment']['measurements'].clear()
    authority['admission']['producer']['arguments'].clear()
    fresh = _authority(case, monkeypatch)
    assert fresh['alignment']['measurements'] and fresh['arguments']


@pytest.mark.parametrize('external_query', [False, True])
def test_reader_uses_the_same_metadata_authority_once_and_keeps_five_key_capture(admission, monkeypatch, external_query):
    case = admission(external_query=external_query)
    authority = _authority(case, monkeypatch)
    calls = []
    def selected(store, context, alignment_ref, *, before_decision_index):
        result = _selected_reference_alignment_authority(store, context, alignment_ref,
            before_decision_index=before_decision_index)
        calls.append(result)
        return result
    with monkeypatch.context() as reader:
        reader.setattr('gene_annotation_episode.alignment_site_native._selected_reference_alignment_authority', selected)
        capture, accessed = _read(case, reader)
    assert calls == [authority]
    assert capture['operands'] == authority['operands']
    assert capture['source']['alignment_ref'] == authority['alignment']['id']
    assert capture['source']['source_ref'] == authority['source']['id']
    assert set(accessed) == {authority['source']['artifact_ref'],
        *authority['source'].get('auxiliary_artifact_refs', [])}


def test_metadata_custody_does_not_claim_payload_validation(admission, monkeypatch):
    case = admission()
    authority = _authority(case, monkeypatch)
    sha = authority['admission']['selection']['native_artifact']['sha256']
    path = case.store.path / 'artifacts' / sha[:2] / sha
    path.write_bytes(path.read_bytes() + b' ')
    assert _authority(case, monkeypatch) == authority
    with pytest.raises((ValueError, ContractError), match='artifact_digest_mismatch'):
        _read(case, monkeypatch)


@pytest.mark.parametrize('denial', ['cutoff', 'receipt', 'context', 'producer', 'ambiguity', 'scope'])
def test_metadata_authority_retains_actual_prebyte_denials(admission, monkeypatch, denial):
    case = admission(retention='ambiguous_grading' if denial == 'ambiguity' else 'modern')
    context, cutoff = case.producer, 1
    if denial == 'cutoff': cutoff = 0
    elif denial == 'receipt':
        case.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?', (case.alignment,))
    elif denial == 'context': context = replace(context, assignment={'invented': True})
    elif denial == 'producer': case.store.db.execute('DELETE FROM tool_operations')
    elif denial == 'scope':
        original_scope = case.scope
        case.scope = case.store.validate_scope({'subject_refs': [case.other]})
        context = saved_context(case, requested(), name='metadata-other-scope')
        case.scope = original_scope
        case.receipts.receive(context.episode_id, [case.alignment], kind='initial')
        cutoff = 0
    with pytest.raises((ValueError, ContractError), match={
            'cutoff': 'not_received', 'receipt': 'not_received', 'context': 'context_conflict',
            'producer': 'unique_producer', 'ambiguity': 'ambiguous_grading', 'scope': 'query_outside_scope'}[denial]):
        _authority(case, monkeypatch, context=context, cutoff=cutoff)


def test_metadata_witness_preserves_original_cutoff_and_frozen_inherited_prefix(admission, monkeypatch):
    case = admission()
    path = (*case.producer.path, ('scientific_process', 'metadata-descendant'))
    episode = EpisodeRef(RUN, path).episode_id
    request = {'message': {'scope': case.scope, 'episode_assignment': {}},
        'report_contract': {'measurements': {'schema': requested()}}}
    case.journal.save('runtime_episodes', dict(episode_id=episode, path=canonical(path),
        request=canonical(request), initial_credit=0., state='active'))
    case.receipts.bind(episode, case.producer.episode_id)
    child = BindingContext(RUN, episode, 'scientific_process', path, case.scope, {}, request)
    original = _authority(case, monkeypatch, context=child, cutoff=0)
    # Later direct receipts cannot replace the inherited proof at this cutoff.
    case.receipts.receive(child.episode_id, [case.alignment], kind='own_action', source_index=10)
    case.receipts.receive(case.producer.episode_id, [case.other], kind='own_action', source_index=11)
    assert _authority(case, monkeypatch, context=child, cutoff=0) == original
    later = _authority(case, monkeypatch, context=child, cutoff=11)
    assert later['admission']['receiver'] != original['admission']['receiver']
    assert later['admission']['producer'] == original['admission']['producer']
    case.store.db.execute('UPDATE runtime_receipt_inheritance SET through_receipt_index=0 '
        'WHERE run_id=? AND episode_id=?', (RUN, child.episode_id))
    with pytest.raises((ValueError, ContractError), match='not_received'):
        _authority(case, monkeypatch, context=child, cutoff=0)
