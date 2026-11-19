"""The world of the graded local phmmer return: a real Store with the protein query of a local phmmer job, the
fetched native phmmer output of that query (``fixtures/phmmer``: HMMER 3.4 text, per-sequence and per-domain
tables, the query and the reference FASTA; two hits, one printed domain each) and the entry input of the result
acquisition episode that passes them. Nothing is faked."""
from pathlib import Path

from episode_runtime import BindingRegistry, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from ..episode import ExecutionResultAcquisition
from .blast_world import job_access, settings as blast_settings

FIXTURES = Path(__file__).parent / 'fixtures' / 'phmmer'
PATH = ExecutionResultAcquisition.binding_path
QUERY = 'ACDEFGHIKLMNPQRSTVWY'
SELECTOR = {'version': 'native_hmmer_result_selector_v1', 'acquisition': 'complete_bound_bundle',
            'projection': {'family': 'protein_domain', 'rows': {'offset': 0, 'limit': 10},
                           'metrics': ['native_domain_score_bits', 'native_independent_evalue']}}
PROFILE_KEY = 'results:typed_native_hmmer_' + SELECTOR['version']
FILES = {'native_text_ref': 'phmmer.stdout', 'hit_table_ref': 'phmmer.tblout', 'domain_table_ref': 'phmmer.domtblout',
         'query_fasta_ref': 'query.fa', 'reference_fasta_ref': 'references.fa'}


def settings(directory):
    value = blast_settings(directory)
    value['task_yield_profiles'] = {PROFILE_KEY: {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}}
    return value


def held_world(directory):
    """The Store, the query, the fetched output files, and the entry input that passes them."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence=QUERY, molecule='protein')
    subject = store.problem()['subject_refs'][0]
    sequence_ref = store.get(subject)['sequence_ref']
    files = {name: store.artifact((FIXTURES / filename).read_bytes(), 'text/plain')
             for name, filename in FILES.items()}
    job = {'program': 'phmmer', 'mode': 'sequence',
           'operand_bindings': [{'operand_role': 'query_sequence', 'record_ordinal': 0, 'native_accession': None,
                                 'subject_ref': subject, 'reference_ref': None}]}
    target = {'version': 'execution_target_v1', 'handle': 'job_handoff_of_the_phmmer_launch', 'run_id': 'launch_run',
              'resource_id': 'local', 'resource_kind': 'local', 'execution_id': 'phmmer_fixture',
              'request_sha256': '0' * 64, 'origin_episode_id': 'launch_episode',
              'assignment': {'resource_id': 'local', 'resource_kind': 'local', 'workspace': '/work/space',
                             'requested_job': {'native_hmmer': job}, 'endpoint': 'completed_job_outputs',
                             'constraints': {}},
              'scope': {'subject_refs': [subject]}}
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': target['handle'],
                  'selector': SELECTOR, 'target': target, 'acquired_record_unit': 1.0,
                  'record_refs': [subject, sequence_ref, *files.values()],
                  'initial_result_refs': list(files.values())}
    return {'store': store, 'subject': subject, 'files': files,
            'input': {'assignment': assignment, 'message': {'objective': 'grade the phmmer return'},
                      'selection': ['execution_phmmer_graded_refs']}}


def linked(directory, world, run_id):
    journal = RunJournal(directory / 'journal.sqlite3')
    registry = BindingRegistry([ExecutionResultAcquisition()])
    world['collaborators'] = {
        'store': world['store'], 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
        'continuation': {PATH: settings(directory)}, 'services': {'job_access': job_access(directory)}}
    return registry, journal, link(registry, PATH, world['input'], run_id=run_id, journal=journal,
                                   collaborators=world['collaborators'])


def grade_call(world, without=()):
    """The grading unit the model is offered: each fetched file in its role."""

    target = world['input']['assignment']['target']
    files = {name: ref for name, ref in world['files'].items() if name not in without}
    return ToolCall('phmmer_grade', {'files': files, 'query_ref': world['subject'],
                                     'scope': target['scope'], 'handoff_ref': target['handle'],
                                     'native_parameters': target['assignment']['requested_job']['native_hmmer']})
