"""The return. Always returned: the credit (the system hands it in ``completion``) and the finding on the job.
Selectable: the facts of the saved command receipts, the handoffs and results, and the array-valued native result
families, which are empty for a launch."""
import re

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.evolutionary_history_evidence.hmmer_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.blast_pairwise_result_views import native_blast_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.hmmer_native_result_views import native_hmmer_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_database_result_views import native_blast_database_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_standard_database_result_views import standard_blast_database_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import digest

FINDING_FORM = RecordForm({
    'assignment_id': Field('text', 'The identity of the assigned job'),
    'resource_id': Field('text', 'The resource the job was assigned to'),
    'endpoint': Field('text', 'The endpoint the assignment asks to validate'),
    'completed': Field('boolean', 'Whether the original endpoint predicates have a recorded validated completion'),
    'satisfied_requirement_keys': Field('list', 'The requirement keys satisfied after the last command'),
    'commands_run': Field('integer', 'How many commands were run'),
    'commands_failed': Field('integer', 'How many commands ended in an execution failure'),
})

# The array-valued native result families: each is empty for a launch episode (it acquires no result).
NATIVE_FAMILIES = [name for source in (native_hmmer_fact_sources, standard_blast_database_fact_sources,
                                       native_blast_database_fact_sources, preparation_fact_sources,
                                       native_blast_fact_sources)
                   for name, fact in source().items() if re.fullmatch(r'[a-z][a-z0-9_]*', name)
                   and fact['type'] == 'array']

FIELDS = {
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the run of the job established', form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether the original requested endpoint predicates have a saved '
                                 'validated completion', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'The original selected command receipts, actual results and '
                                    'earned operational credit sources', required=False),
    'execution_handoff_refs': Field('record_refs', 'The command receipts that are qualified handoffs of the '
                                    'assigned job', required=False),
    'execution_result_refs': Field('record_refs', 'The qualified result acquisitions available to this episode '
                                   '(none: a launch episode acquires no result)', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information',
                                 required=False),
    'execution_blast_hsps': Field('list', 'Explicitly requested native HSP measurements (none for a launch '
                                  'episode)', required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'The native BLAST pairwise result references '
                                                  '(none for a launch episode)', required=False),
}
for _name in NATIVE_FAMILIES:
    FIELDS[_name] = Field('list', 'The native result family ' + _name + ' (empty for a launch episode)',
                          required=False)
RETURN_FORM = RecordForm(FIELDS)


def facts(summary):
    """The facts a parent may select, from the closed Episode's summary."""
    receipts = summary['receipts']
    values = {
        'practical_completed': summary['completion'] is not None,
        'practical_receipt_digests': [digest(receipt) for receipt in receipts],
        'practical_receipt_refs': list(summary['receipt_refs']),
        'execution_handoff_refs': sorted(summary['handoff_refs']),
        'execution_result_refs': [], 'execution_completed': summary['completion'] is not None,
        'execution_blast_hsps': [], 'execution_blast_pairwise_result_refs': [],
    }
    values.update({name: [] for name in NATIVE_FAMILIES})
    return values


def final_to_parent(summary, completion, selection):
    failed = sum(1 for receipt in summary['receipts']
                 if receipt['outcome'].get('native_outcome', {}).get('failure') is not None)
    assignment = summary['assignment']
    result = {'credit': completion['credit'],
              'finding': {'assignment_id': assignment['assignment_id'], 'resource_id': assignment['resource_id'],
                          'endpoint': assignment['endpoint'], 'completed': summary['completion'] is not None,
                          'satisfied_requirement_keys': list(summary['progress']['satisfied_keys']),
                          'commands_run': len(summary['receipts']), 'commands_failed': failed}}
    recorded = facts(summary)
    for name in selection:
        result[name] = recorded[name]
    return result
