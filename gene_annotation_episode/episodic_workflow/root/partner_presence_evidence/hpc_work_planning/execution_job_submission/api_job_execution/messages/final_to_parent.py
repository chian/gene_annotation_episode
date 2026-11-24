"""What this episode returns: ``credit`` (the system hands it in ``completion``), ``finding`` (what was established about
the request or job) and the selectable facts: ``execution_handoff_refs``, ``execution_result_refs``,
``execution_completed``, ``execution_result_origin`` (the empty record: an API job retains no result windows) and the
three native hmmer family sources (always empty for an API job).
"""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    partner_presence_evidence.hmmer_native_result_views import FAMILY_SOURCES

FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The configured API resource that ran the work'),
    'service': Field('text', 'The API service that carried out the work'),
    'handoff_established': Field('boolean', 'Whether a usable monitoring/results handoff was recorded'),
    'completed': Field('boolean', 'Whether the original handoff completion was verified'),
    'last_status': Field('text', 'The status of the last unit that ran, as the service reported it'),
    'interpretation': Field('text', "The model's latest interpretation of the job for the parent"),
})
FAMILY_FIELDS = tuple(FAMILY_SOURCES.values())
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What was established about the assigned request or job', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The records that hold the usable handoff', required=False),
    'execution_result_refs': Field('record_refs', 'The records that hold acquired results', required=False),
    'execution_completed': Field('boolean', 'Whether the original handoff completion is verified', required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of retained results: the empty record, an API job retains none',
                                     required=False),
    **{name: Field('list', 'Native hmmer family rows: always empty for an API job', required=False)
       for name in FAMILY_FIELDS},
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': {'resource_id': summary['resource_id'], 'service': summary['service'],
                          'handoff_established': bool(summary['handoff_refs']), 'completed': summary['completed'],
                          'last_status': 'none' if summary['last_status'] is None else summary['last_status'],
                          'interpretation': summary['report_update']}}
    if 'execution_handoff_refs' in selection:
        result['execution_handoff_refs'] = summary['handoff_refs']
    if 'execution_result_refs' in selection:
        result['execution_result_refs'] = summary['result_refs']
    if 'execution_completed' in selection:
        result['execution_completed'] = summary['completed']
    if 'execution_result_origin' in selection:
        result['execution_result_origin'] = {}
    for name in FAMILY_FIELDS:
        if name in selection:
            result[name] = []
    return result
