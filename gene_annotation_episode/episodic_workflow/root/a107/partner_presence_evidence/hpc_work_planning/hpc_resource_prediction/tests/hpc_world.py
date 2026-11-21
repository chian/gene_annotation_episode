"""The held world of the A107 HPC planning episodes' tests: a real Store with a problem, one configured commission
with measured history (six earlier allocations to train on, two later ones held out for validation) and two
candidate portfolios, the configured ``pbs_ssh`` resource, and the real ``job_services``.

There is no HPC where the tests run. The resource's route is the real ``PbsSshRoute`` with one of two transports:

- ``absent`` (the model runs): the transport program does not exist, so every request to the resource fails with
  ``transport_unavailable`` and nothing remote is contacted, whatever the model selects;
- ``local_shell`` (the offline tests, which choose the commands themselves): the route's real remote program runs
  through a local shell, as in ``episode_support/jobs/tests/test_job_services.py``. No scheduler is installed.
"""
import sys

from episode_runtime import RunJournal
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services

RESOURCE = 'aurora'
PROJECT = '/lus/flare/projects/BioReason-Aurora-Test'
PRIOR = {'median_seconds': 120.0, 'log_sigma': 1.0, 'coefficient_variance': 1.0}
DAY = 86400.0
FIRST = 1790000000.0


def case(index, nodes, sequences, queue_seconds, day):
    """One measured earlier allocation: the work time falls with the nodes and grows with the sequences."""
    return {'id': 'case_' + str(index), 'observed_at': FIRST + day * DAY,
            'features': {'nodes': nodes, 'sequences': sequences},
            'metrics': {'queue': {'seconds': queue_seconds, 'censored': False},
                        'setup': {'seconds': 40.0, 'censored': False},
                        'work': {'seconds': 0.9 * sequences / nodes, 'censored': False}},
            'success': True, 'provenance': ['retained partner search allocation ' + str(index)]}


def candidate(identity, nodes, wall_seconds):
    return {'id': identity, 'queue': 'debug', 'nodes': nodes, 'wall_seconds': wall_seconds,
            'features': {'sequences': 4000},
            'units': [{'unit_id': 'search', 'obligation_id': 'partner_search',
                       'argv': ['python3', '{allocation_workspace}/search.py'], 'environment': {}, 'effort': 1.0}]}


def commission():
    history = [case(1, 1, 1000, 300.0, 0), case(2, 2, 1000, 420.0, 1), case(3, 1, 2000, 250.0, 2),
               case(4, 2, 4000, 900.0, 3), case(5, 4, 4000, 1500.0, 4), case(6, 1, 500, 200.0, 5),
               case(7, 2, 2000, 600.0, 8), case(8, 4, 8000, 1300.0, 9)]
    return {'objective': 'Search the partner protein set against the reference proteomes on one allocation',
            'resource_id': RESOURCE,
            'obligations': {'partner_search': {'credit': 1.0, 'acceptance': [
                {'field': ['status'], 'operator': 'eq', 'value': 'complete'}]}},
            'candidates': [candidate('one_node', 1, 3600), candidate('two_nodes', 2, 3600)],
            'model': {'features': [{'name': 'nodes', 'transform': 'log1p', 'scale': 1.0},
                                   {'name': 'sequences', 'transform': 'log1p', 'scale': 1.0}],
                      'priors': {metric: dict(PRIOR) for metric in ('queue', 'setup', 'work', 'return')},
                      'success_prior': [1.0, 1.0]},
            'history': history, 'validation_ids': ['case_7', 'case_8'],
            'credit': {'model_scale': 0.1, 'validation_scale': 1.0, 'validation_slots': [
                {'id': 'planned_work', 'phase': 'planned', 'metric': 'work', 'weight': 1.0,
                 'minimum_elapsed_seconds': 0.0}]},
            'preferences': {'elapsed_cost_per_second': 0.00001, 'node_hour_cost': 0.01},
            'limits': {'result_limit_bytes': 4096, 'queue_max_age_seconds': 600}}


def settings(**more):
    """The settings every episode of the subtree is linked with (its entry of ``continuation``)."""
    return {'resources': {RESOURCE: {'kind': 'pbs_ssh', 'workspace': PROJECT + '/chian/runs',
                                     'account': 'BioReason-Aurora-Test', 'python_executable': '/usr/bin/python3'}},
            'commissions': {'c1': commission()}, 'shared_execution_memory': False,
            'handoff_unit': 1.0, 'information_unit': 1.0, 'acquired_record_unit': 1.0, **more}


def services(tmp_path, transport):
    route = {'absent': {'ssh_argv': [str(tmp_path / 'no_transport_to_aurora')], 'python_executable': '/usr/bin/python3',
                        'workspace': PROJECT + '/chian/runs'},
             'local_shell': {'ssh_argv': ['/bin/sh', '-c'], 'python_executable': sys.executable,
                             'workspace': str(tmp_path / 'remote')}}[transport]
    return job_services({
        'local': {}, 'capabilities': [],
        'pbs': {RESOURCE: {**route, 'poll_seconds': 0.05,
                           'scheduler': {'qsub': 'qsub', 'qstat': 'qstat', 'qdel': 'qdel', 'qselect': 'qselect'}}},
        'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates.sqlite3'),
        'launch_instructions_directory': str(tmp_path / 'launch'),
        'tool_knowledge_directory': str(tmp_path / 'knowledge')})


def world(tmp_path, paths, *, transport, **more):
    """A Store with a problem, a journal and the collaborators for the binding ``paths``."""
    store = Store(tmp_path / 'store')
    store.create_problem(raw_sequence='ATGGCTGCTAAAGAAGCTTAA', molecule='dna')
    return {'store': store, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
            'scope': {'subject_refs': list(store.problem()['subject_refs'])},
            'collaborators': {'store': store,
                              'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
                              'continuation': {path: settings(**more) for path in paths},
                              'services': services(tmp_path, transport)}}


def ledger_of_the_prediction_sister(world, prediction, run_id='the_prediction_sister_opens_the_ledger'):
    """The HPC ledger of the commission as real runs make it: the prediction episode's own ``hpc_open`` tool, run
    as the first unit of a run of that episode in this world. ``(ledger id, the rows' references)`` for the entry
    assignment of an episode that works on the ledger (the caller writes no row itself)."""
    import asyncio

    from episode_runtime import BindingRegistry, link
    entry = {'assignment': {'owner_episode_id': 'episode_owner', 'commission_id': 'c1', 'scope': world['scope']},
             'message': {}, 'selection': []}
    run = link(BindingRegistry([prediction()]), prediction.binding_path, entry, run_id=run_id,
               journal=world['journal'], collaborators=world['collaborators'])
    opened = asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    return opened['outcome']['ledger']['ledger_id'], opened['outcome']['ledger']['ledger_refs']
