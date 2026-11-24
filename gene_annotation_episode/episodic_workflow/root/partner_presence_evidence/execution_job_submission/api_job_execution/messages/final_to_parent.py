"""What this episode returns: ``credit`` (the system hands it in ``completion``), ``finding`` (what was established about
the request or job) and the selectable facts: ``execution_handoff_refs``, ``execution_result_refs``,
``execution_completed``, ``execution_result_origin`` (the empty record: an API job retains no result windows),
``execution_blast_hsps``, ``execution_blast_pairwise_result_refs`` and the fact sources of the A107 result views in the
library (native HMMER and HMMER preparation, pairwise BLAST and the native and standard BLAST database families), one
field each. A source the service did not report is empty.
"""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.\
    partner_presence_evidence.hmmer_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    partner_presence_evidence.blast_pairwise_result_views import native_blast_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    partner_presence_evidence.hmmer_native_result_views import native_hmmer_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    partner_presence_evidence.native_blast_database_result_views import native_blast_database_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    partner_presence_evidence.native_blast_standard_database_result_views import (
        standard_blast_database_fact_sources)

_LIBRARY_SOURCES = {**native_hmmer_fact_sources(), **preparation_fact_sources(), **native_blast_fact_sources(),
                    **native_blast_database_fact_sources(), **standard_blast_database_fact_sources()}
NATIVE_SOURCES = {name: source for name, source in _LIBRARY_SOURCES.items() if source['type'] == 'array'}
OWN_SOURCES = ('execution_handoff_refs', 'execution_result_refs', 'execution_completed', 'execution_result_origin',
               'execution_blast_hsps', 'execution_blast_pairwise_result_refs')


def library_fields(sources):
    return {name: Field('list', source['meaning'], required=False)
            for name, source in sources.items()}


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
    'execution_result_origin': Field('record', 'Acquisition semantics of retained results: the empty record, an API job retains none',
                                     required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                  'HSPs of an acquired result; no ranking, top-N or significance filter',
                                  required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'Pairwise BLAST result references of a native '
                                                  'result', required=False),
    **library_fields(NATIVE_SOURCES),
})


def fact(summary, name):
    """One recorded fact: what the service reported, or the empty value of a family it did not report."""
    if name in summary['facts']:
        return summary['facts'][name]
    return []


def recorded_facts(summary):
    return {'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
            'execution_completed': summary['completed'], 'execution_result_origin': {}}


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': {'resource_id': summary['resource_id'], 'service': summary['service'],
                          'handoff_established': bool(summary['handoff_refs']), 'completed': summary['completed'],
                          'last_status': 'none' if summary['last_status'] is None else summary['last_status'],
                          'interpretation': summary['report_update']}}
    recorded = recorded_facts(summary)
    for name in selection:
        result[name] = recorded[name] if name in recorded else fact(summary, name)
    return result
