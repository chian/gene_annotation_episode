"""Actual map completeness, resource variants and frozen child information."""
import asyncio
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.api_blast import NCBIBlastService
from gene_annotation_episode.api_bvbrc import BVBRCDataService
from gene_annotation_episode.api_uniprot import UniProtService
from gene_annotation_episode.practical_resource_episodes import operation_catalog
from gene_annotation_episode.execution_episodes import launch_operation_catalog, native_result_operation_catalog
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.providers import ModelRole
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.scientific_tool_retrieval import ScientificToolRetriever, tool_info_output_schema
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_information import resource_kind, selectors, tool_info_selection
from gene_annotation_episode.tools import ToolRegistry


CONFIG = {'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
    'model': {'model': 'gpt-6-luna', 'reasoning_effort': 'none'}}


@pytest.fixture
def actual(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        tools = ToolRegistry(store)
        library = ScientificToolLibrary.freeze(tmp_path/'tool-information', catalog=tools.catalog(), tool_info=True)
        yield store, tools, library, target


def test_every_actual_registry_and_execution_operation_has_four_fields(actual):
    _, tools, library, target = actual
    metadata = library.parent_tool_info()
    assert all(set(row) == {'name', 'description', 'resources'} for row in metadata)
    rows = library.resolve_tool_info(selectors(metadata))
    indexed = {(row['name'], row['resources']): row for row in rows}
    for name, contract in tools.catalog().items():
        row = indexed[name, resource_kind(name)]
        assert set(row) == {'name', 'description', 'resources', 'instructions'}
        assert row['description'] == contract['description']
        assert row['instructions'].strip() and name in row['instructions']
    for kind in ('local', 'hpc'):
        for operation in [*operation_catalog(kind), *native_result_operation_catalog()]:
            assert (operation['name'], kind) in indexed
    for operation in launch_operation_catalog():
        assert (operation['name'], 'local') in indexed
    from types import SimpleNamespace
    monitor = MonitorEpisodes(None).catalog(SimpleNamespace(role='monitor'))
    for kind in ('api', 'local', 'hpc'):
        for operation in monitor:
            assert (operation['name'], kind) in indexed
    for role in ('job_launch', 'job_monitor', 'job_results'):
        for operation in HomologyEpisodes.catalog(None, SimpleNamespace(path=((role, 'test'),))):
            assert (operation['name'], 'local') in indexed
    for service, request, selector in (
            (NCBIBlastService(tools), {'subject_ref': target, 'program': 'blastp', 'database': 'swissprot'}, {}),
            (UniProtService(tools), {'operation': 'record', 'accession': 'P12345'}, {}),
            (BVBRCDataService(tools), {'collection': 'genome_feature',
                'filters': [{'field': 'gene', 'operator': 'eq', 'value': 'ybhP'}]}, {})):
        for operation in [*service.launch_catalog(request), *service.result_catalog(request, selector)]:
            selected = [{'name': operation['name'], 'resources': 'api'}]
            resolved, = library.resolve_invocations(selected, [{**operation, 'resources': 'api'}])
            assert resolved['input_schema'] == operation['input_schema']
    assert ('sequence.align', 'hpc') not in indexed
    assert not any(row['name'] in {'exec_command', 'apply_patch', 'spawn_agent'} for row in rows)


def test_same_name_resource_variants_resolve_exact_instructions_and_contracts(actual):
    _, tools, library, _ = actual
    selected = [{'name': 'practical.job.start', 'resources': kind} for kind in ('local', 'hpc')]
    rows = library.resolve_tool_info(selected)
    assert rows[0]['instructions'] != rows[1]['instructions']
    assert 'EpiCalib' in rows[1]['instructions'] and 'actual assigned HPC' in rows[1]['instructions']
    contracts = library.resolve_invocations(selected)
    assert contracts[0]['input_schema'] == next(row['input_schema'] for row in operation_catalog('local') if row['name'] == 'practical.job.start')
    assert contracts[1]['input_schema'] == next(row['input_schema'] for row in operation_catalog('hpc') if row['name'] == 'practical.job.start')
    with pytest.raises(ValueError, match='contract_changed'):
        library.resolve_invocations(selected, tools.catalog())  # These are not ordinary registry callables.
    altered = deepcopy(rows); altered[0]['instructions'] = 'Invented replacement instructions'
    with pytest.raises(ValueError, match='info_changed'):
        library.resolve_tool_info(altered)
    with pytest.raises(ValueError, match='duplicate'):
        tool_info_selection([selected[0], selected[0]])
    with pytest.raises(ValueError, match='unknown'):
        library.resolve_tool_info([{'name': 'sequence.align', 'resources': 'hpc'}])


def test_parent_information_excludes_instructions_child_gets_actual_contract_and_executes(actual):
    store, tools, library, target = actual
    row = next(row for row in library.parent_tool_info(tools.catalog()) if row['name'] == 'sequence.inspect')
    assert set(row) == {'name', 'description', 'resources'}
    info, = library.resolve_tool_info([{'name': row['name'], 'resources': row['resources']}], tools.catalog())
    invocation, = library.resolve_invocations([info], tools.catalog())
    assert info['instructions'] == invocation['instructions']
    assert invocation['input_schema'] == tools.catalog()['sequence.inspect']['input_schema']
    result = tools.execute(invocation['name'], {'subject_ref': target}, operation_key='actual-local-call')
    assert result['status'] == 'completed' and result['result']['length'] == 8
    assert store.count('annotation') == 0


def test_new_snapshot_reopens_frozen_information_and_legacy_snapshot_is_not_upgraded(actual, tmp_path, monkeypatch):
    _, tools, library, _ = actual
    selection = [{'name': 'sequence.inspect', 'resources': 'local'}]
    original = library.resolve_tool_info(selection)
    from gene_annotation_episode import tool_information
    monkeypatch.setattr(tool_information, '_documents', lambda *_: 'Future tool instructions')
    reopened = ScientificToolLibrary.freeze(library.directory, catalog=tools.catalog(), tool_info=True)
    assert reopened.resolve_tool_info(selection) == original
    future = ScientificToolLibrary.freeze(tmp_path/'future', catalog=tools.catalog(), tool_info=True)
    assert future.resolve_tool_info(selection) != original
    old = ScientificToolLibrary.freeze(tmp_path/'legacy', catalog=tools.catalog())
    before = (old.directory/'index.json').read_bytes()
    frozen = ScientificToolLibrary.freeze(old.directory, catalog=tools.catalog(), tool_info=True)
    assert not frozen.supports_tool_info and (old.directory/'index.json').read_bytes() == before
    assert set(frozen.retrieve_literal_test('sequence inspect')) == {'investigation', 'tools', 'catalog'}


class Provider:
    roles = {'FAST': ModelRole('gpt-6-luna', 'none')}

    def __init__(self, response):
        self.response, self.calls, self.released = response, [], []

    async def complete(self, call_id, role, instructions, context, output_schema):
        self.calls.append(deepcopy(context))
        assert all(set(row) == {'name', 'description', 'resources'} for row in context['catalog'])
        return deepcopy(self.response)

    async def release(self, call_id):
        self.released.append(call_id)


def test_semantic_retrieval_only_selects_real_pairs_and_replays_cached_metadata(actual):
    store, tools, library, _ = actual
    choice = [{'name': 'sequence.inspect', 'resources': 'local'}, {'name': 'public.uniprot.record', 'resources': 'api'}]
    provider = Provider({'child_tool_info': choice})
    retriever = ScientificToolRetriever(store, run_id='run', provider=provider, library=library, configuration=CONFIG)
    async def retrieve():
        return await retriever.retrieve('Inspect sequence and acquire a source protein', episode_id='child',
            operation_key='run:child:0', available_catalog=tools.catalog())
    result = asyncio.run(retrieve())
    assert result['status'] == 'completed'
    assert set(result['result']) == {'investigation', 'child_tool_info'}
    assert all(set(row) == {'name', 'description', 'resources'} for row in result['result']['child_tool_info'])
    assert len(provider.calls[0]['catalog']) == len(tools.catalog())
    assert asyncio.run(retrieve()) == result and len(provider.calls) == len(provider.released) == 1
    canonical = library.resolve_tool_info(choice, tools.catalog())
    assert all(row['instructions'] for row in canonical)
    assert not store.count('source') - 1  # Only the original input source exists.


def test_repeated_names_use_exact_resource_pairs_in_model_schema_and_selection(actual):
    store, _, library, _ = actual
    available = [{**entry, 'resources': kind} for kind in ('local', 'hpc') for entry in operation_catalog(kind)]
    choice = [{'name': 'practical.job.start', 'resources': kind} for kind in ('local', 'hpc')]
    schema = tool_info_output_schema(library.parent_tool_info(available))
    assert Draft202012Validator(schema).is_valid({'child_tool_info': choice})
    assert not Draft202012Validator(schema).is_valid({'child_tool_info': [{'name': 'practical.job.start', 'resources': 'api'}]})
    assert not Draft202012Validator(schema).is_valid({'child_tool_info': [{**choice[0], 'instructions': 'model-made'}]})
    provider = Provider({'child_tool_info': choice})
    retriever = ScientificToolRetriever(store, run_id='run', provider=provider, library=library, configuration=CONFIG)
    outcome = asyncio.run(retriever.retrieve('Prepare the assigned job where it can run', episode_id='child',
        operation_key='run:child:0', available_catalog=available))
    assert outcome['status'] == 'completed'
    assert selectors(outcome['result']['child_tool_info']) == choice
    literal = library.retrieve_literal_test('submit queue', available_catalog=available)
    assert all(row['resources'] in {'local', 'hpc'} and row['name'].startswith('practical.')
               for row in literal['child_tool_info'])
