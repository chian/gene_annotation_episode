"""The world the hosted-database path of ``database_blast`` runs in: a real Store holding the protein that is the query,
the job services of ``job_services`` with the public NCBI BLAST service bound as an API resource, and the model provider
(which the code-decided episodes never ask). Nothing is faked.

The route is the public service with the spacing its usage guidelines ask for (ten seconds between contacts, sixty
between status requests of one job), a generic client name and no contact address; nothing authenticates. The world is
made once in a directory and opened again as it stands (its Store, journal and the route's workspace) by a later process,
so the recorded job and its handoff row can be continued by the monitor and the results episodes."""
from pathlib import Path

from episode_runtime import RunJournal
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services

RESOURCE = 'ncbi_blast'
# Human ubiquitin (76 residues): a short, abundant protein, so a search against Swiss-Prot is quick and its top hits
# are the ubiquitin sequences of many organisms.
QUERY = 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG'


def ncbi_route(workspace):
    return {'service': 'ncbi_blast', 'base_url': 'https://blast.ncbi.nlm.nih.gov/Blast.cgi',
            'workspace': str(workspace), 'client_name': 'public-api-job-client', 'contact_email': None,
            'request_spacing_seconds': 10, 'poll_spacing_seconds': 60, 'transport_timeout_seconds': 90}


def world(directory, *, query=QUERY):
    """The world in ``directory``: made there, or opened again as it stands when an earlier process made it."""
    directory = Path(directory)
    made_before = (directory / 'store').exists()
    store = Store(directory / 'store')
    if not made_before:
        store.create_problem(raw_sequence=query, molecule='protein')
    subject = store.problem()['subject_refs'][0]
    configuration = {
        'local': {}, 'pbs': {}, 'api': {RESOURCE: ncbi_route(directory / 'api_jobs')},
        'capabilities': [{'resource_id': RESOURCE, 'kind': 'api', 'availability': 'unknown',
                          'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [],
                          'tool_names': ['job.launch', 'job.check', 'job.fetch']}],
        'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'unused_launch_library'),
        'tool_knowledge_directory': str(directory / 'unused_knowledge_library')}
    calls = directory / ('model_calls_%d' % (len(list(directory.glob('model_calls*'))) + 1) if made_before
                         else 'model_calls')
    return {'store': store, 'subject': subject, 'sequence_ref': store.get(subject)['sequence_ref'],
            'directory': directory, 'configuration': configuration, 'journal': RunJournal(directory / 'journal.sqlite3'),
            'services': job_services(configuration),
            'model_provider': ModelProvider(load_config(), calls, directory)}


def collaborators(held, continuation):
    return {'store': held['store'], 'model_provider': held['model_provider'], 'continuation': continuation,
            'services': held['services']}
