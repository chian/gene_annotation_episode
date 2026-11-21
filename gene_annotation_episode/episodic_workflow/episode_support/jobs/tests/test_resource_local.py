"""The local wrapper (``resource_local.execute_on_local_resource``), run by the real runner on real jobs.

Every test links the ``resource_local_probe`` test episode with a real ``Store``, ``RunJournal`` and model provider
and the services ``job_services`` builds. A local job is a real detached systemd service of this machine
(``LocalJobRoute``), so these tests need the workflow launcher (``tools/one_workflow.sh``): a local job runs inside
the launcher's slice. Nothing is faked and no model is asked."""
import asyncio
import sys

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.local_job_policy import LocalJobPolicy
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_job_route import LocalJobRoute

from .resource_local_probe.episode import ResourceLocalProbe

SETTINGS = {'resource_local_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}
LOCAL, HUGE = 'local_test', 'local_huge'
POLICY = {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2}
# More memory than any machine this runs on has: the resource refuses every launch (a real refusal).
HUGE_POLICY = {'memory_bytes': 1024 ** 6, 'scratch_bytes': 64 * 1024 ** 2}
PATH = (('resource_local_probe', 'wrapper'),)


class Switch:
    """A real service of the test run: whether the cut a plan step asks for is still wanted."""

    def __init__(self):
        self.fail = False


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    configuration = {
        'local': {LOCAL: {'workspace': str(tmp_path / 'jobs'), 'policy': POLICY, 'cpu_threads': 1},
                  HUGE: {'workspace': str(tmp_path / 'huge'), 'policy': HUGE_POLICY, 'cpu_threads': 1}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(tmp_path / 'not_used_launch'),
        'tool_knowledge_directory': str(tmp_path / 'not_used_knowledge')}
    switch = Switch()
    yield {'store': store, 'tmp': tmp_path, 'switch': switch, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'services': {**job_services(configuration), 'switch': lambda: switch},
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)}
    store.close()


def collaborators(world):
    return {'store': world['store'], 'model_provider': world['provider'], 'continuation': SETTINGS,
            'services': world['services']}


def run(world, plan, *, input_refs=()):
    entry = {'assignment': {'input_refs': list(input_refs)}, 'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([ResourceLocalProbe()]), 'resource_local_probe', entry, run_id='wrapper',
                  journal=world['journal'], collaborators=collaborators(world))
    return asyncio.run(linked.run())['result'].as_record()


def outcomes(world):
    return [unit[2]['outcome'] for unit in world['journal'].units('wrapper', PATH)]


def step(code, *, wait, resource_id=LOCAL, environment=None, inputs=None, cut=False):
    return {'resource_id': resource_id, 'command': [sys.executable, '-c', code], 'environment': environment or {},
            'wait': wait, 'inputs': inputs or {}, 'cut': cut}


def ended(world, outcome):
    """Wait on the launched job itself until it has ended (no clock), so no test leaves a job running."""
    route = LocalJobRoute(world['tmp'] / 'jobs', LocalJobPolicy.from_config(POLICY), world['tmp'] / 'events',
                          resource_id=LOCAL)
    asyncio.run(route.wait(outcome['job'], None))
    return world['tmp'] / 'jobs' / outcome['job']


def test_a_waited_command_runs_verbatim_and_its_output_and_exit_code_come_back_verbatim(world):
    code = ("import os,sys\nsys.stdout.write('  two  spaces\\nGREETING=' + os.environ['GREETING'] + '\\n\\n')\n"
            "sys.stderr.write('warn: \\ttabbed\\n')\nopen('made.txt','w').write('by the command')")
    result = run(world, [step(code, wait=True, environment={'GREETING': 'hello  world'})])
    done, = outcomes(world)
    assert done['status'] == 'completed' and done['returncode'] == 0
    assert done['stdout'] == '  two  spaces\nGREETING=hello  world\n\n'       # nothing trimmed or rewritten
    assert done['stderr'] == 'warn: \ttabbed\n'
    files = {item['name']: world['store'].get_artifact(item['ref']) for item in done['fetch']['results']}
    assert files['stdout.log'].decode() == done['stdout'] and files['made.txt'] == b'by the command'
    assert done['launch']['kind'] == 'local' and done['fetch']['outcome'] == 'results_acquired'
    # The handoff row, the closure row and the files are in the Episode's custody, produced by the unit.
    held = {item['ref']: item['how'] for item in world['journal'].receipts('wrapper', PATH)}
    assert held[done['launch']['handoff_ref']] == held[done['fetch']['closure_ref']] == 'produced'
    assert set(done['fetch']['result_refs']) <= set(result['record_refs'])
    assert result['credit'] == 1.0


def test_a_command_that_exits_nonzero_is_a_completed_execution_with_its_code(world):
    run(world, [step("import sys\nprint('partial')\nsys.stderr.write('it broke\\n')\nsys.exit(3)", wait=True)])
    done, = outcomes(world)
    assert done['status'] == 'completed' and done['returncode'] == 3 and done['fetch']['state'] == 'failed'
    assert done['stdout'] == 'partial\n' and done['stderr'] == 'it broke\n'


def test_a_launch_returns_at_handoff_and_the_job_goes_on_after_the_episode(world):
    release = world['tmp'] / 'release'
    code = ("import pathlib,time\nwhile not pathlib.Path(" + repr(str(release)) + ").exists(): time.sleep(0.02)\n"
            "pathlib.Path('answer.txt').write_text('42')")
    result = run(world, [step(code, wait=False)])
    launched, = outcomes(world)
    assert launched['status'] == 'completed' and (launched['adopted'], launched['replayed']) == (False, False)
    assert 'stdout' not in launched
    assert set(result['record_refs']) == {launched['reply_ref'], launched['handoff_ref']}
    held = {item['ref']: item['how'] for item in world['journal'].receipts('wrapper', PATH)}
    assert launched['handoff_ref'].startswith('row_') and held[launched['handoff_ref']] == 'produced'
    assert not (world['tmp'] / 'jobs' / launched['job'] / 'answer.txt').exists()      # the Episode closed first
    release.touch()
    assert (ended(world, launched) / 'answer.txt').read_text() == '42'


def test_an_input_the_episode_holds_is_staged_for_the_command(world):
    question = world['store'].artifact('six times seven', 'text/plain')
    run(world, [step("print(open('question.txt').read().upper())", wait=True, inputs={'question.txt': question})],
        input_refs=[question])
    done, = outcomes(world)
    assert done['stdout'] == 'SIX TIMES SEVEN\n'
    assert 'question.txt' not in [item['name'] for item in done['fetch']['results']]     # an input is no result


def test_a_launch_the_resource_refuses_is_a_returned_failure_and_no_row(world):
    run(world, [step("print('never')", wait=False, resource_id=HUGE), step("print('never')", wait=True,
                                                                         resource_id=HUGE)])
    launched, waited = outcomes(world)
    assert launched['status'] == 'failed' and launched['failure']['code'] and 'handoff_ref' not in launched
    assert waited['status'] == 'failed' and waited['launch']['failure'] == launched['failure']
    assert waited['fetch'] is None and 'stdout' not in waited
    assert world['journal'].receipts('wrapper', PATH) == []


def test_a_unit_cut_after_its_launch_starts_nothing_twice_when_it_runs_again(world):
    log = world['tmp'] / 'ran.log'
    code = "with open(" + repr(str(log)) + ",'a') as s: s.write('ran\\n')"
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='cut after the execution'):
        run(world, [step(code, wait=False, cut=True)])
    world['switch'].fail = False
    asyncio.run(resume(BindingRegistry([ResourceLocalProbe()]), run_id='wrapper', journal=world['journal'],
                       collaborators=collaborators(world)).run())
    launched, = outcomes(world)
    assert launched['status'] == 'completed' and launched['replayed'] is True
    ended(world, launched)
    assert log.read_text() == 'ran\n'
