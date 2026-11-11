"""The BLAST launch request fixes the result identity, not a native command."""
import pytest

from gene_annotation_episode.api_blast import NCBIBlastService
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_blast_service import Client


def _owner(store, directory, client):
    return ExecutionEpisodes(None, store=store, directory=directory, run_id='blast-return-binding',
        resources={'blast': {'kind': 'api', 'service': 'ncbi_blast'}}, initial_information={},
        tool_registry=ToolRegistry(store, clients=client), handoff_unit=1,
        acquired_record_unit=1, log_window_bytes=8192, log_roles=['stdout', 'stderr'])


def _request(subject_ref, database=None):
    value = {'version': 'blast_database_grader_return_request_v1', 'resource_id': 'blast',
        'return_type': 'blast_database_sheet_v1', 'query_subject_ref': subject_ref}
    if database is not None:
        value['database'] = database
    return value


def _launch(request):
    return {'version': 'execution_launch_assignment_v1', 'requests': {'blast': request},
        'immutable_input_versions': [], 'constraints': {}}


def _selected(subject_ref, database):
    return {'version': 'api_service_assignment_v1', 'resource_id': 'blast',
        'service': 'ncbi_blast', 'request': {'subject_ref': subject_ref,
            'program': 'blastp', 'database': database}, 'endpoint': 'usable_handoff',
        'constraints': {}}


def test_blast_parent_return_requirement_leaves_unconstrained_database_open(tmp_path):
    with Store(tmp_path/'state') as store:
        query, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [query]}
        owner = _owner(store, tmp_path/'run', Client())
        open_request = owner._launch(_launch(_request(query)), scope=scope)
        for database in ('swissprot', 'nr_clustered_seq'):
            owner._validate_blast_launch_selection(open_request, _selected(query, database), scope)
        constrained = owner._launch(_launch(_request(query, 'swissprot')), scope=scope)
        owner._validate_blast_launch_selection(constrained, _selected(query, 'swissprot'), scope)
        with pytest.raises(ValueError, match='selected_database_conflict'):
            owner._validate_blast_launch_selection(constrained, _selected(query, 'nr_clustered_seq'), scope)


def test_retained_blast_grader_is_checked_against_query_and_native_database(tmp_path):
    with Store(tmp_path/'state') as store:
        query, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [query]}
        client = Client()
        owner = _owner(store, tmp_path/'run', client)
        service = NCBIBlastService(owner.tool_registry, client=client)
        request = _selected(query, 'swissprot')['request']
        prepared = service.prepare('api.blast.submit', request, {}, scope=scope,
            previous_events=[])
        submitted = service.invoke(prepared)
        event = service.decode(prepared, submitted)
        handle = event['native_handle']
        fetched = service.invoke(service.prepare('api.blast.fetch', request, {}, scope=scope,
            previous_events=[], handle=handle, selector={}))
        published = service.publish(request, {}, fetched, scope, 'blast-graded-result',
            submission_snapshot=submitted, handle=handle)
        source_ref = published['result']['source_ref']
        result_ref = 'result_fixture'
        owner.api_execution.read_result = lambda reference, _: {
            'target': {'assignment': _selected(query, 'swissprot'), 'handle': 'handoff_fixture'},
            'source_ref': source_ref, 'service_request': request}
        context = BindingContext('blast-return-binding', 'results-fixture', 'results',
            (('results', 'fixture'),), scope,
            {'version': 'execution_results_assignment_v1', 'handoff_ref': 'handoff_fixture',
             'selector': {}}, {})
        required = owner._blast_launch_requirement(_request(query, 'swissprot'), 'blast', scope)
        rows = owner._blast_grader_rows(context, [result_ref], required)
        assert len(rows) == 1 and rows[0]['sheet_schema'] == 'blast_database_sheet_v1'
        assert rows[0]['database'] == 'swissprot'
        with pytest.raises(ValueError, match='result_database_conflict'):
            owner._blast_grader_rows(context, [result_ref], {**required, 'database': 'nr_clustered_seq'})
        with pytest.raises(ValueError, match='result_query_conflict'):
            owner._blast_grader_rows(context, [result_ref], {**required, 'query_sha256': '0'*64})
