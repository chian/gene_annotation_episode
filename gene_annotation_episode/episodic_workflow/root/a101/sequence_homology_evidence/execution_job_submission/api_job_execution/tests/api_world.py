"""The world the A101 ``api_job_execution`` episode runs in: a real Store holding the protein target that is the
query of the job, the job services of ``job_services`` with one API route bound as the assigned resource, the
frozen instruction libraries of the axis, the episode's own settings, and the entry input a launching parent would
commission (the query in custody, the database fixed, the program and hit-list size left to the episode).

The route is the caller's: the public NCBI BLAST service (``ncbi_route``) or a service of the test process that
speaks the same protocol (``episode_support/jobs/tests/blast_url_api_server.py``). Nothing is faked."""
from pathlib import Path

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

from ..episode import ApiJobExecution

LIBRARY = Path(__file__).resolve().parents[6] / 'episode_support'
PATH = ApiJobExecution.binding_path
RESOURCE = 'ncbi_blast'
QUERY = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV'
PROFILE = 'launch_api:api_ncbi_blast_swissprot_handoff'
SELECTION = ['execution_handoff_refs', 'execution_completed']


def ncbi_route(workspace):
    """The public NCBI BLAST service, with the spacing its usage guidelines ask for: ten seconds between contacts
    and sixty between status requests of one job. No contact address is given and nothing authenticates."""
    return {'service': 'ncbi_blast', 'base_url': 'https://blast.ncbi.nlm.nih.gov/Blast.cgi',
            'workspace': str(workspace), 'client_name': 'public-api-job-client', 'contact_email': None,
            'request_spacing_seconds': 10, 'poll_spacing_seconds': 60, 'transport_timeout_seconds': 90}


def world(directory, route, *, libraries=True):
    """The world in ``directory``: made there, or, when an earlier process made it there, opened again as it
    stands (its Store, journal, frozen libraries and the route's workspace), so that its recorded run resumes."""
    made_before = (directory / 'store').exists()
    # A model provider records into a directory of its own: each process that opens the world has one.
    calls = directory / ('model_calls_%d' % (len(list(directory.glob('model_calls*'))) + 1) if made_before
                         else 'model_calls')
    store = Store(directory / 'store')
    if not made_before:
        store.create_problem(raw_sequence=QUERY, molecule='protein')
    subject = store.problem()['subject_refs'][0]
    settings = {'task_yield_profiles': {PROFILE: {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}}}
    if libraries:
        if not made_before:
            ToolKnowledge.freeze(directory / 'knowledge', source=LIBRARY / 'knowledge' / 'sequence_homology_evidence')
            LaunchInstructions.freeze(directory / 'launch',
                                      source=LIBRARY / 'instructions' / 'launch' / 'sequence_homology_evidence')
        settings['tool_knowledge_directory'] = str(ToolKnowledge(directory / 'knowledge').directory)
        settings['launch_instructions_directory'] = str(LaunchInstructions(directory / 'launch').directory)
    configuration = {
        'local': {}, 'pbs': {}, 'api': {RESOURCE: route},
        'capabilities': [{'resource_id': RESOURCE, 'kind': 'api', 'availability': 'unknown',
                          'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [],
                          'tool_names': ['job.launch', 'job.check', 'job.fetch']}],
        'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'run_launch_library'),
        'tool_knowledge_directory': str(directory / 'run_knowledge_library')}
    assignment = {'resource_id': RESOURCE, 'service': 'ncbi_blast', 'query_subject_refs': [subject],
                  'input_refs': [store.get(subject)['sequence_ref']], 'fixed_request': {'database': 'swissprot'},
                  'completion_target': 1.0}
    return {'store': store, 'subject': subject, 'directory': directory, 'configuration': configuration,
            'made_before': made_before, 'journal': RunJournal(directory / 'journal.sqlite3'),
            'entry': {'assignment': assignment, 'message': {'resource_id': RESOURCE}, 'selection': SELECTION},
            'collaborators': {'store': store, 'continuation': {PATH: settings},
                              'services': job_services(configuration),
                              'model_provider': ModelProvider(load_config(), calls, directory)}}


def linked(world, run_id):
    return link(BindingRegistry([ApiJobExecution()]), PATH, world['entry'], run_id=run_id, journal=world['journal'],
                collaborators=world['collaborators'])


def resumed(world, run_id):
    return resume(BindingRegistry([ApiJobExecution()]), run_id=run_id, journal=world['journal'],
                  collaborators=world['collaborators'])


def path_of(run_id):
    return ((PATH.replace('/', '__'), run_id),)


def show(request):
    """Print a model request as the model is given it."""
    import json
    print('\n=== INSTRUCTIONS ===\n' + request.instructions, flush=True)
    print('=== CONTEXT ===\n' + json.dumps(request.context, indent=1))
    print('=== OUTPUT SCHEMA ===\n' + json.dumps(request.output_schema, indent=1))
