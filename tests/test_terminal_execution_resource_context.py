"""The native launch child receives its actual configured staging transport."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

from gene_annotation_episode.component_axis_literature_prompt import with_fact_contract_instructions
from gene_annotation_episode.hpc_prompt import render_hpc_prompt
from gene_annotation_episode.terminal_execution_episodes import TerminalExecutionEpisodes


FIXTURE = Path(__file__).parent / 'fixtures/hpc/a107-genomic04-native-transport-context.json.gz'


def test_original_native_launch_input_receives_its_exact_transport(tmp_path):
    with gzip.open(FIXTURE, 'rt') as handle:
        original = json.load(handle)
    state = original['state']
    resource = original['configured_resource']
    before = deepcopy(state)
    assert 'ssh_argv' not in state['execution_resource']
    assert resource['ssh_argv'][-1] not in original['actual_input']
    # Exercise the real assignment/context provider without executing a command,
    # connecting to a host or replacing historical scientific/credit state.
    family = TerminalExecutionEpisodes(None, directory=tmp_path / 'native',
        resources={'hpc': resource})
    context = SimpleNamespace(role='launch_hpc', run_id='retained-transport-context',
        episode_id=original['episode_id'], assignment=state['execution_assignment'])
    current = family.decision_context(context, {})
    shown = {**deepcopy(state), 'execution_resource': current['execution_resource']}
    rendered = with_fact_contract_instructions(
        render_hpc_prompt(shown, original['instructions']), shown)
    assert current['execution_assignment'] == state['execution_assignment']
    assert current['execution_resource']['ssh_argv'] == resource['ssh_argv']
    for argument in resource['ssh_argv']:
        assert argument in rendered
    assert resource['python_executable'] in rendered
    assert resource['account'] in rendered
    assert current['execution_resource']['scheduler'] == resource['scheduler']
    assert {key: value for key, value in shown.items() if key != 'execution_resource'} == {
        key: value for key, value in state.items() if key != 'execution_resource'}
    assert state == before
    current['execution_resource']['ssh_argv'].append('changed-view-only')
    assert family.resources['hpc']['ssh_argv'] == resource['ssh_argv']
    assert 'exact configured transport prefix' in family.instructions(context)


def test_local_launch_does_not_invent_a_remote_connection(tmp_path):
    family = TerminalExecutionEpisodes(None, directory=tmp_path,
        resources={'local': {'kind': 'local', 'workspace': str(tmp_path)}})
    information = family._resource_information('local')
    assert information['resource_kind'] == 'local'
    assert 'ssh_argv' not in information
