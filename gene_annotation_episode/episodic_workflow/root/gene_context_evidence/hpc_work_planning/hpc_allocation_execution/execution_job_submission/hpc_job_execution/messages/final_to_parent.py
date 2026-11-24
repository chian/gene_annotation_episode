"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (what the
execution reached), the handoff records of the job in custody and whether the commissioned endpoint is verified.
Every other fact is a selectable field the commissioner may ask for; a launch acquires no results, so the result-side
facts and the result families are empty.

Where a fact source name contains a dot (the masking and BLAST utility families) the field name has an
underscore in its place: a form field name is a lowercase identifier."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.gene_context_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.gene_context_evidence.bvbrc_data_views import (
    bvbrc_data_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.gene_context_evidence.sequence_masking_result_views import (
    masking_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.blast_utility_result_views import (
    blast_utility_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'endpoint': Field('text', 'The commissioned endpoint'),
    'completed': Field('boolean', 'Whether the commissioned endpoint has a verified completion'),
    'handed_off': Field('boolean', 'Whether a command observed the requested job submitted with a handoff'),
    'receipt_count': Field('integer', 'How many commands ran and left a receipt'),
    'satisfied_keys': Field('list', 'The original requirement keys currently satisfied'),
    'operational_credit': Field('number', 'The credit of the currently satisfied original requirements'),
    'job': Field('record', 'The requested job as the latest command observed it: status, execution identity, handoff',
                 required=False),
})

# The list-valued fact sources of this role that the library functions describe (meaning); the form
# fields are made from them.
_FAMILIES = (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
             standard_blast_database_fact_sources, native_blast_database_fact_sources, preparation_fact_sources,
             native_blast_fact_sources, bvbrc_data_fact_sources)


def _family_fields():
    fields = {}
    for function in _FAMILIES:
        for source, declared in function().items():
            if declared['type'] == 'array':
                fields[source.replace('.', '_')] = Field('list', declared['meaning'], required=False)
    return fields


def _selectable():
    return {
        'practical_completed': Field('boolean', 'Whether original requested endpoint predicates have a saved validated '
                                     'completion.', required=False),
        'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts.',
                                           required=False),
        'practical_receipt_refs': Field('record_refs', 'Original selected command, actual result and earned '
                                        'operational credit sources.', required=False),
        'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to '
                                       'this episode; a launch episode acquires none.', required=False),
        'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results; a launch '
                                         'episode retains none.', required=False),
        'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                      'HSPs of an acquired result; a launch episode acquires none.', required=False),
        'execution_blast_pairwise_result_refs': Field('record_refs', 'Pairwise BLAST result references; a launch '
                                                      'episode acquires none.', required=False),
    }


RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the execution reached', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources: the command receipts that '
                                    'observed the requested job submitted with a handoff'),
    'execution_completed': Field('boolean', 'Whether this assignment has a verified endpoint. Yielding alone is '
                                 'false.'),
    **_selectable(),
    **_family_fields(),
})


def _facts(summary):
    """The practical facts and the handoffs of the receipts; the results families are empty."""
    receipts, completed = summary['receipts'], summary['completion'] is not None
    facts = {'practical_completed': completed, 'practical_receipt_digests': [digest(receipt) for receipt in receipts],
             'practical_receipt_refs': list(summary['receipt_refs']),
             'execution_handoff_refs': list(summary['handoff_refs']), 'execution_result_refs': [],
             'execution_completed': completed, 'execution_result_origin': {'retained': False},
             'execution_blast_hsps': [], 'execution_blast_pairwise_result_refs': []}
    facts.update({name: [] for name, spec in RETURN_FORM.fields.items()
                  if spec.type == 'list' and name not in facts})
    return facts


def _finding(summary):
    receipts = summary['receipts']
    finding = {'endpoint': summary['assignment']['endpoint'], 'completed': summary['completion'] is not None,
               'handed_off': bool(summary['handoff_refs']), 'receipt_count': len(receipts),
               'satisfied_keys': summary['progress']['satisfied_keys'],
               'operational_credit': summary['progress']['operational_credit']}
    jobs = [receipt['outcome']['facts']['requested_job'] for receipt in receipts
            if 'requested_job' in receipt['outcome']['facts']]
    if jobs:
        finding['job'] = jobs[-1]
    return finding


def final_to_parent(summary, completion, selection):
    facts = _facts(summary)
    result = {'credit': completion['credit'], 'finding': _finding(summary),
              'execution_handoff_refs': facts['execution_handoff_refs'],
              'execution_completed': facts['execution_completed']}
    for name in selection:
        result[name] = facts[name]
    return result
