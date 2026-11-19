"""What this episode returns. Always returned: ``credit`` (the system's ``completion['credit']``) and ``finding``
(what was established about the request or job).

Selectable facts: ``execution_handoff_refs``, ``execution_result_refs``, ``execution_completed``,
``execution_result_origin`` (``{}``: this episode retains no result with an acquisition origin),
``execution_blast_hsps``, ``execution_blast_pairwise_result_refs`` and one array-typed field for each source of the
A101 result views in the library (native HMMER, BLAST and database families, BV-BRC data, MinHash). A source the
service did not report is ``[]``."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.\
    sequence_homology_evidence.hmmer_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.\
    sequence_homology_evidence.bvbrc_data_views import bvbrc_data_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    sequence_homology_evidence.blast_pairwise_result_views import native_blast_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    sequence_homology_evidence.bvbrc_minhash_views import minhash_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    sequence_homology_evidence.hmmer_native_result_views import native_hmmer_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    sequence_homology_evidence.native_blast_database_result_views import native_blast_database_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    sequence_homology_evidence.native_blast_standard_database_result_views import (
        standard_blast_database_fact_sources)

SOURCES = {name: source for name, source in {**native_hmmer_fact_sources(), **preparation_fact_sources(),
                                              **native_blast_fact_sources(), **native_blast_database_fact_sources(),
                                              **standard_blast_database_fact_sources(), **bvbrc_data_fact_sources(),
                                              **minhash_fact_sources()}.items() if source['type'] == 'array'}


def library_fields(sources):
    return {name: Field('list', source['meaning'], required=False) for name, source in sources.items()}


FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The configured API resource that ran the work'),
    'service': Field('text', 'The API service that carried out the work'),
    'handoff_established': Field('boolean', 'Whether a usable monitoring/results handoff was recorded'),
    'completed': Field('boolean', 'Whether the original handoff completion was verified'),
    'last_status': Field('text', 'The status of the last unit that ran, as the service reported it'),
    'interpretation': Field('text', "The model's latest interpretation of the job for the parent"),
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
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results: empty, this '
                                     'episode retains no result with an origin', required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                  'HSPs of an acquired result; no ranking, top-N or significance filter',
                                  required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'Pairwise BLAST result references of a native '
                                                  'result', required=False),
    **library_fields(SOURCES),
})


def fact(summary, name):
    """One recorded fact: what the service reported, or ``[]`` for a source it did not report."""
    return summary['facts'][name] if name in summary['facts'] else []


def final_to_parent(summary, completion, selection):
    recorded = {'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
                'execution_completed': summary['completed'], 'execution_result_origin': {}}
    result = {'credit': completion['credit'],
              'finding': {'resource_id': summary['resource_id'], 'service': summary['service'],
                          'handoff_established': bool(summary['handoff_refs']), 'completed': summary['completed'],
                          'last_status': 'none' if summary['last_status'] is None else summary['last_status'],
                          'interpretation': summary['report_update']}}
    for name in selection:
        result[name] = recorded[name] if name in recorded else fact(summary, name)
    return result
