"""Scientific source readers preserve actual receipt subsets across scope forms.

The tiny saved host contexts authenticate the original invocations. These are
source-port checks, not an autonomous investigation or HPC execution claim.
"""
import asyncio
from dataclasses import replace

from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.a107_tools import A107ToolRegistry
from gene_annotation_episode.a110_tools import A110ToolRegistry
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from test_state import source


def saved_context(store, target, sources, axis):
    run = 'source-reader-binding'
    path = (('annotation', 'root'), ('scientific_process', 'source-reader'))
    episode = EpisodeRef(run, path).episode_id
    scope = store.validate_scope()
    assignment = {'selection': {'evidence_axis': {'option_id': axis}}}
    request = {'message': {'scope': scope, 'episode_assignment': assignment}}
    store.db.execute('CREATE TABLE runtime_episodes '
        '(run_id TEXT,episode_id TEXT,path TEXT,request TEXT)')
    store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
        (run, episode, canonical(path), canonical(request)))
    return BindingContext(run, episode, 'scientific_process', path, scope,
        assignment, request, (target, *sources))


def registry(store, path, axis):
    return (A107ToolRegistry(store, a107_work_directory=path / 'native-work')
        if axis == 'A107' else A110ToolRegistry(store))


def scan(tools, context, target, selected, *, permitted=None, operation='original-scan'):
    args = {'subject_ref': target, 'source_ref': selected, 'representation': 'original',
        'offset': 0, 'window_bytes': 4096, 'minimum_length': 8}
    with tools.current_invocation(context, read_received=None,
            tool_name='source.sequence.scan', arguments=args, operation_key=operation):
        return asyncio.run(tools.execute_async('source.sequence.scan', args,
            scope=plain(context.scope), operation_key=operation, permitted_record_refs=permitted))


@pytest.mark.parametrize('axis', ['A107', 'A110'])
def test_actual_received_source_reaches_scanner_from_frozen_scientific_scope(tmp_path, axis):
    with Store(tmp_path / 'state') as store:
        sequence = 'MKWACDEFGHIKLMNPQRSTVWY'
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        src = source(store, '>declared-protein\n' + sequence + '\n\nEnd of declaration.\n')
        context = saved_context(store, target, [src['id']], axis)
        assert context.scope != plain(context.scope)  # The original failing representation comparison.
        result = scan(registry(store, tmp_path, axis), context, target, src['id'])
        assert result['status'] == 'completed', result
        candidate, = result['result']['candidates']
        assert candidate['comparison']['relationship'] == 'full_string_equal'
        assert candidate['normalized_sequence'] == sequence
        assert not store.list('assessment') and not store.current_annotations()


@pytest.mark.parametrize('axis', ['A107', 'A110'])
def test_unreceived_source_and_explicit_subset_remain_unreadable(tmp_path, axis, monkeypatch):
    with Store(tmp_path / 'state') as store:
        sequence = 'MKWACDEFGHIKLMNPQRSTVWY'
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        allowed = source(store, '>allowed\n' + sequence + '\n\nEnd.\n')
        hidden = source(store, '>hidden\n' + sequence + '\n\nEnd.\n')
        context = saved_context(store, target, [allowed['id']], axis)
        tools = registry(store, tmp_path, axis)
        original = store.get_artifact
        def received_bytes_only(ref, *args, **kwargs):
            assert ref != hidden['artifact_ref'], 'unreceived source bytes were opened'
            return original(ref, *args, **kwargs)
        monkeypatch.setattr(store, 'get_artifact', received_bytes_only)
        result = scan(tools, context, target, hidden['id'])
        assert result['status'] == 'invalid' and 'not_received' in result['feedback']['code']
        widened = replace(context, received_record_refs=(*context.received_record_refs, hidden['id']))
        result = scan(tools, widened, target, hidden['id'], permitted=context.received_record_refs,
            operation='explicit-original-subset')
        assert result['status'] == 'invalid' and 'not_received' in result['feedback']['code']


def test_unregistered_host_context_does_not_gain_implicit_receipts(tmp_path):
    with Store(tmp_path / 'state') as store:
        sequence = 'MKWACDEFGHIKLMNPQRSTVWY'
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        src = source(store, '>declared\n' + sequence + '\n\nEnd.\n')
        context = saved_context(store, target, [src['id']], 'A107')
        store.db.execute('DELETE FROM runtime_episodes')
        result = scan(registry(store, tmp_path, 'A107'), context, target, src['id'])
        assert result['status'] == 'invalid'
