"""A real held world for the A105 page: a Store with the problem, a synthetic paper and the proposed annotation, all passed to
the entry Episode in custody, as the page assignment of one paper for one claim (``verified_source_leads``)."""
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.state import Store

# The page's sheet update compares the paper's protein with the target by pairwise BLAST on a local resource: its settings
# hold the directory of the BLAST programs (A101's key) and the bound local resource that runs them.
BLAST_DIRECTORY = str(next(parent for parent in Path(__file__).parents
                           if (parent / 'resources' / 'software').is_dir()) / 'resources' / 'software' / 'ncbi-blast-2.17.0+' / 'bin')
LOCAL_RESOURCE = 'local'
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'blast_executable_directory': BLAST_DIRECTORY,
            'blast_resource_id': LOCAL_RESOURCE}


def job_world_services(directory):
    """The job services of a test run: one local resource under the test's own directory."""
    return job_services({
        'local': {LOCAL_RESOURCE: {'workspace': str(directory / 'jobs'), 'cpu_threads': 1,
                                   'policy': {'memory_bytes': 1024 ** 3, 'scratch_bytes': 64 * 1024 ** 2}}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'not_used_launch'),
        'tool_knowledge_directory': str(directory / 'not_used_knowledge')})

LINES = ['Experiment A: purified enzyme hydrolysis rate assay with a known normal fixed-prediction model.',
         'effect 12.5 U/mg; variance 0.25 U/mg_squared;',
         'recovery 0.9 fraction; attributed 0.6 fraction; total 0.8 fraction;',
         'condition test 0.8 fraction; condition reference 1 fraction;',
         'assertion prediction 12 U/mg; alternative prediction 0 U/mg.']
TEXT = '\n'.join(LINES)


def held_world(directory):
    """The Store and the entry input of the episode at ``page_assignment``."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    target = store.problem()['subject_refs'][0]
    scope = {'subject_refs': [target]}
    artifact = store.artifact(TEXT, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_a105_table', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'hydrolysis', 'label': 'Hydrolysis',
                                  'term_type': 'reaction', 'source_ref': source, 'anchor': None},
                         origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'catalyzes',
                                        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []},
                         origin='reasoning')['id']
    task = {'version': 'literature_local_task', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    page = {'version': 'page_assignment', 'source_ref': source, 'representation': 'original',
            'artifact_ref': artifact, 'question_context_refs': [], 'prior_delivery_refs': []}
    held = [target, source, artifact, reaction, proposed]
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': proposed, 'scope': scope,
                  'received_record_refs': held}
    names = {'store': store, 'target': target, 'source': source, 'artifact': artifact,
             'reaction': reaction, 'proposed': proposed, 'scope': scope}
    return {**names, 'input': {'assignment': assignment, 'message': {'objective': 'evidence_in_table'},
                               'selection': []}}


# A real model run: each unit costs 0.1 credit, so the controller stops the Episode when its forecast yield of a
# further unit no longer exceeds that.
MODEL_SETTINGS = {**SETTINGS, 'cost': 0.1}
CHILD_PATHS = ('table', 'report', 'chunk')
