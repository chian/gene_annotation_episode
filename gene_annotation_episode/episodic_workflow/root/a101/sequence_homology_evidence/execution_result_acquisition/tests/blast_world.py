"""The world of the graded BLAST return: a real Store with a protein target, a fetched native BLAST JSON2 result of
that target (the synthetic native document of the A101 BLAST grader tests, three hits over a ten-residue query) and
the entry input of the result acquisition episode that passes them. Nothing is faked."""
import hashlib
import json

from episode_runtime import BindingRegistry, RunJournal, link
from episode_runtime.job_access import JobAccess
from gene_annotation_episode.local_job_policy import LocalJobPolicy
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_return_contracts import (
    BLAST_GRADED_REQUEST_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_job_route import LocalJobRoute

from ..episode import ExecutionResultAcquisition

PATH = ExecutionResultAcquisition.binding_path
RESOURCE = 'ncbi_blast_api'
QUERY = 'ACDEFGHIKL'
PROFILE_KEY = 'results:api_ncbi_blast_' + BLAST_GRADED_REQUEST_VERSION


def native_document():
    hits = []
    for accession, taxid, bits in (('SYN_A', 562, 10), ('SYN_B', 620, 9), ('SYN_C', 562, 10)):
        hits.append({'num': len(hits) + 1, 'len': 10,
                     'description': [{'id': accession, 'accession': accession,
                                      'title': 'Synthetic source description', 'taxid': taxid,
                                      'sciname': 'Synthetic organism ' + str(taxid)}],
                     'hsps': [{'num': 1, 'bit_score': bits, 'score': bits * 2, 'evalue': 0.01,
                               'query_from': 1, 'query_to': 5, 'hit_from': 1, 'hit_to': 5,
                               'identity': 5, 'positive': 5, 'align_len': 5, 'gaps': 0,
                               'qseq': 'ACDEF', 'hseq': 'ACDEF'}]})
    return {'BlastOutput2': [{'report': {'program': 'blastp', 'version': 'BLASTP synthetic fixture',
                                         'search_target': {'db': 'synthetic_db'}, 'params': {'expect': 10},
                                         'results': {'search': {'query_id': 'synthetic_query',
                                                                'query_title': 'synthetic_query', 'query_len': 10,
                                                                'hits': hits,
                                                                'stat': {'db_num': 1000, 'db_len': 10000}}}}}]}


def settings(directory):
    return {'log_window_bytes': 4096,
            'task_yield_profiles': {PROFILE_KEY: {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}}}


def held_world(directory, *, database='synthetic_db'):
    """The Store, the target, the fetched result, and the entry input that passes them."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence=QUERY, molecule='protein')
    subject = store.problem()['subject_refs'][0]
    sequence_ref = store.get(subject)['sequence_ref']
    result_ref = store.artifact(json.dumps(native_document()), 'application/json')
    selector = {'version': BLAST_GRADED_REQUEST_VERSION, 'resource_id': RESOURCE,
                'return_type': 'blast_database_sheet_v1', 'query_subject_ref': subject, 'database': database}
    target = {'version': 'execution_target_v1', 'handle': 'job_handoff_of_the_launch', 'run_id': 'launch_run',
              'resource_id': RESOURCE, 'resource_kind': 'api', 'execution_id': 'blast_rid_fixture',
              'request_sha256': hashlib.sha256(json.dumps(selector, sort_keys=True).encode()).hexdigest(),
              'origin_episode_id': 'launch_episode', 'assignment': {'service': 'ncbi_blast'},
              'scope': {'subject_refs': [subject]}}
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': target['handle'],
                  'selector': selector, 'target': target, 'acquired_record_unit': 1.0,
                  'record_refs': [subject, sequence_ref, result_ref], 'initial_result_refs': [result_ref]}
    return {'store': store, 'subject': subject, 'result_ref': result_ref,
            'input': {'assignment': assignment, 'message': {'objective': 'grade the BLAST return'},
                      'selection': ['execution_blast_graded_refs']}}


def job_access(directory):
    """The run's job service: one local route (it is built only if a unit asks for it)."""
    def build():
        route = LocalJobRoute(directory / 'jobs', LocalJobPolicy(memory_bytes=1 << 30, scratch_bytes=1 << 30),
                              directory / 'events', resource_id=RESOURCE)
        return JobAccess({RESOURCE: route})
    return build


def collaborators(directory, store, path=PATH, extra=None):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': {path: settings(directory), **(extra or {})},
            'services': {'job_access': job_access(directory)}}


def linked(directory, world, run_id):
    journal = RunJournal(directory / 'journal.sqlite3')
    registry = BindingRegistry([ExecutionResultAcquisition()])
    world['collaborators'] = collaborators(directory, world['store'])
    return registry, journal, link(registry, PATH, world['input'], run_id=run_id, journal=journal,
                                   collaborators=world['collaborators'])
