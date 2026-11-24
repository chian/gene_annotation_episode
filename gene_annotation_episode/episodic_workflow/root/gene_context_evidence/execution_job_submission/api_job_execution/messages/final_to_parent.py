"""What this episode returns. Always returned: ``credit`` (the system's ``completion['credit']``) and ``finding``
(what was established about the assigned request or job). A parent may select ``execution_handoff_refs``,
``execution_result_refs``, ``execution_completed``, ``execution_result_origin`` (``{'retained': False}``: the API
service retains no results here), ``execution_blast_hsps``, ``execution_blast_pairwise_result_refs`` and the native
result families the reader functions of the library describe (native HMMER, HMMER preparation, BLAST pairwise, BLAST
database and standard database families, BV-BRC data, MinHash). A family the service did not report is empty."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.\
    gene_context_evidence.hmmer_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.\
    gene_context_evidence.bvbrc_data_views import bvbrc_data_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.blast_pairwise_result_views import native_blast_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.bvbrc_minhash_views import minhash_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.hmmer_native_result_views import native_hmmer_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.native_blast_database_result_views import native_blast_database_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.native_blast_standard_database_result_views import standard_blast_database_fact_sources

NATIVE_SOURCES = {**native_hmmer_fact_sources(), **preparation_fact_sources(), **native_blast_fact_sources(),
                  **native_blast_database_fact_sources(), **standard_blast_database_fact_sources()}
SERVICE_SOURCES = {**bvbrc_data_fact_sources(), **minhash_fact_sources()}


def library_fields(sources):
    return {name: Field('list', source['meaning'], required=False)
            for name, source in sources.items() if source['type'] == 'array'}


FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The bound API resource that ran the work'),
    'service': Field('text', 'The API service that carried out the work'),
    'handoff_established': Field('boolean', 'Whether a usable monitoring/results handoff was recorded'),
    'completed': Field('boolean', 'Whether the original handoff completion was verified'),
    'last_status': Field('text', 'The status of the last unit that ran, as the service reported it'),
    'qualification': Field('text', 'What the recorded service facts establish about the handoff and the '
                           'submission; a missing reply does not establish that no job was created'),
    'job_identity': Field('text', 'The actual job identity (the native handle), when a service reported one',
                          required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What was established about the assigned request or job', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources actually available to this '
                                    'episode; a failed attempt does not establish a successful endpoint',
                                    required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to '
                                   'this episode', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information; '
                                 'yielding alone is false', required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results: none is retained '
                                     'by this episode', required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                  'HSPs of an acquired result; no ranking, top-N or significance filter',
                                  required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'Pairwise BLAST result references of a native '
                                                  'result', required=False),
    **library_fields(NATIVE_SOURCES), **library_fields(SERVICE_SOURCES),
})


def fact(summary, name):
    """One recorded fact: what the service reported, or an empty list for a family it did not report."""
    return summary['facts'][name] if name in summary['facts'] else []


def recorded_facts(summary):
    return {'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
            'execution_completed': summary['completed'], 'execution_result_origin': {'retained': False}}


def final_to_parent(summary, completion, selection):
    established = bool(summary['handoff_refs'])
    finding = {'resource_id': summary['resource_id'], 'service': summary['service'],
               'handoff_established': established, 'completed': summary['completed'],
               'last_status': 'none' if summary['last_status'] is None else summary['last_status'],
               'qualification': ('original usable handoff established from recorded service facts' if established
                                 else 'original handoff not established; a missing reply does not establish that '
                                      'no job was created')}
    if summary['job_identity'] is not None:
        finding['job_identity'] = summary['job_identity']
    result = {'credit': completion['credit'], 'finding': finding}
    recorded = recorded_facts(summary)
    for name in selection:
        result[name] = recorded[name] if name in recorded else fact(summary, name)
    return result
