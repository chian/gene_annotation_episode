"""A real run of the pairwise_blast episode: the real runner, a real Store and journal, the run's real job services, a
real detached local job and the real BLAST programs. The episode asks no model, so there is no model call to see; the
collaborator the system requires is the real provider and the run checks that it was never used.

Usage (through the single-workflow launcher, one workload at a time):
    bash tools/one_workflow.sh runs/<unique> -- $PWD/.venv/bin/python -B -m \
        gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.pairwise_blast.tests.real_run \
        <work directory> <blast bin directory>

It runs the commission, the commissions that must fail, resume, and reads what the existing A101 score route makes of
the saved grading. Nothing is faked and no pytest is used."""
import asyncio
import json
import sys
from pathlib import Path

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services

from ..episode import PairwiseBlast

PATH = PairwiseBlast.binding_path
RESOURCE = 'local_test'
QUERY = 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG'
SUBJECT = 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQRESTLHLVLRLRGGAA'
SELECTION = ['execution_handoff_refs', 'execution_job_record_refs', 'execution_blast_graded_refs', 'execution_completed']


def configuration(directory):
    return {'local': {RESOURCE: {'workspace': str(directory / 'jobs'),
                                 'policy': {'memory_bytes': 1024 ** 3, 'scratch_bytes': 64 * 1024 ** 2},
                                 'cpu_threads': 1}},
            'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(directory / 'events'),
            'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
            'launch_instructions_directory': str(directory / 'unused_launch_library'),
            'tool_knowledge_directory': str(directory / 'unused_knowledge_library')}


def world(directory, bin_directory):
    """The Store with the two subject records the parent would hold, the job services and the settings."""
    store = Store(directory / 'store')
    manifest = directory / 'manifest.json'
    manifest.write_text(json.dumps({'schema_version': 2, 'entries': [
        {'sequence': QUERY, 'molecule': 'protein', 'name': 'query'},
        {'sequence': SUBJECT, 'molecule': 'protein', 'name': 'subject'}]}))
    store.create_problem(manifest_path=manifest)
    records = {}
    for ref in store.problem()['subject_refs']:
        sequence = store.get_artifact(store.get(ref)['sequence_ref']).decode('ascii')
        records['query' if sequence == QUERY else 'subject'] = (ref, store.get(ref)['sequence_ref'])
    settings = {'cost': 0.2, 'parameters': {'uncertainty_alpha': 0.05}, 'blast_executable_directory': str(bin_directory)}
    return store, job_services(configuration(directory)), records, settings


def commission(records, **changes):
    assignment = {'version': 'pairwise_blast_assignment_v1', 'analysis_kind': 'pairwise', 'program': 'blastp',
                  'query_refs': [records['query'][0]], 'subject_refs': [records['subject'][0]],
                  'resource_id': RESOURCE, 'information_unit': 1.0,
                  'record_refs': [value for pair in records.values() for value in pair]}
    assignment.update(changes)
    return {'assignment': {key: value for key, value in assignment.items() if value is not None},
            'message': {}, 'selection': SELECTION}


def collaborators(store, directory, services, settings, calls):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / calls, directory),
            'continuation': {PATH: settings}, 'services': services}


def dump(journal, run_id):
    """What the journal holds of the run: every episode, its units with the credit each earned, the model calls."""
    print('RUN STATE', journal.run_state(run_id)[0], 'FAILURE', journal.run_failure(run_id))
    for episode in journal.episodes(run_id):
        path = tuple(tuple(item) for item in episode['path'])
        print('EPISODE', episode['binding_path'], episode['state'], 'completion', episode['completion'])
        for label, _, outcome, _ in journal.units(run_id, path):
            print('  UNIT', label, json.dumps(outcome, default=str)[:420])
        print('  MODEL CALLS', len(journal.model_calls(run_id, path)))
        for step in journal.controller_steps(run_id, path):
            print('  STEP credit', step['credit'], 'stop', step['decision']['stop'])


def main(out, bin_directory):
    out.mkdir(parents=True, exist_ok=True)
    store, services, records, settings = world(out, bin_directory)
    journal, registry = RunJournal(out / 'journal.sqlite3'), BindingRegistry([PairwiseBlast()])

    def colls(name):
        return collaborators(store, out, services, settings, name)

    print('--- commissions that must fail')
    for label, changes in (('no declared kind', {'analysis_kind': None}),
                           ('kind outside the vocabulary', {'analysis_kind': 'database_search'}),
                           ('a query record custody does not hold', {'query_refs': ['subject_' + '0' * 64]})):
        try:
            link(registry, PATH, commission(records, **changes), run_id='bad-' + label.replace(' ', '-'),
                 journal=journal, collaborators=colls('model_calls_bad_' + label.replace(' ', '_')))
            print('WRONG COMMISSION ADMITTED:', label)
        except Exception as error:
            print('FAILS (' + label + '):', type(error).__name__, str(error)[:150])
    print('--- a protein pair compared with blastn')
    run = link(registry, PATH, commission(records, program='blastn'), run_id='blastn-on-proteins', journal=journal,
               collaborators=colls('model_calls_blastn'))
    try:
        asyncio.run(run.run())
        print('WRONG: the run ended')
    except Exception as error:
        print('RUN FAILS:', type(error).__name__, str(error)[:200])
    print('--- the commission')
    run = link(registry, PATH, commission(records), run_id='pairwise', journal=journal,
               collaborators=colls('model_calls'))
    try:
        closed = asyncio.run(run.run())
    finally:
        dump(journal, 'pairwise')
    result = closed['result'].as_record()
    print('RESULT', json.dumps(result, default=str))
    print('MODEL CALLS ON DISK', len(list(out.glob('model_calls*/call-*'))))
    print('--- resume')
    resumed = asyncio.run(resume(registry, run_id='pairwise', journal=journal, collaborators=colls('model_calls_resumed')).run())
    print('RESUME same result:', resumed['result'].as_record() == result, '| model calls on resume:',
          len(list(out.glob('model_calls_resumed/call-*'))))
    print('--- what the existing A101 score route makes of the saved grading')
    from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
        route_native_grading)
    from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
        source_tool_grading_entries)
    source = result['execution_blast_graded_refs'][0]
    entries = source_tool_grading_entries(store, source)
    comparisons = route_native_grading(entries[0]['grading'])
    print('SAVED GRADING:', len(entries), entries[0]['grading']['sheet']['schema'], store.get(source)['provider'])
    print('ROUTE ->', len(comparisons), 'comparison(s)', {key: comparisons[0][key] for key in (
        'algorithm', 'program', 'bits', 'alignment_identity', 'reference_paired_count', 'reference_length')},
          'residue_pairs', len(comparisons[0]['residue_pairs']))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
