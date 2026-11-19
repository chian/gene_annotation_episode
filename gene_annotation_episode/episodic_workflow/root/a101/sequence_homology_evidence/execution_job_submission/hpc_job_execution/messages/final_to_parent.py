"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
episode's own: whether the requested endpoint is completed, how many commands ran and failed, the satisfied
requirement keys). Every fact a parent may select is a field the parent names in its commission.

This episode receives no result or handoff records and runs no result acquisition, so ``execution_result_refs``,
``execution_file_source_refs``, ``execution_file_capture_outcomes`` and every native result family below are always
empty, and ``execution_result_origin`` is the empty record.

The native result families (BLAST pairwise and database searches, HMMER, BV-BRC data pages) take their names and
meanings from the library's own ``*_fact_sources`` functions."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.sequence_homology_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_views import (
    bvbrc_data_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'completed': Field('boolean', 'Whether the assigned endpoint has a saved, validated completion'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'commands_run': Field('integer', 'How many commands this episode ran'),
    'commands_failed': Field('integer', 'How many of them recorded an execution failure'),
    'satisfied_keys': Field('list', 'The requirement keys satisfied when the episode ended'),
    'qualification': Field('text', 'What the saved receipts do and do not establish: a command that ran is not a '
                           'completed endpoint, and a submission with an uncertain outcome is not a duplicate'),
})

# The native result families (always empty for this role), by their fact-source names.
NATIVE_FAMILY_SOURCES = {}
for _family in (native_hmmer_fact_sources, preparation_fact_sources, native_blast_fact_sources,
                standard_blast_database_fact_sources, native_blast_database_fact_sources, bvbrc_data_fact_sources):
    NATIVE_FAMILY_SOURCES.update(_family())
NATIVE_FAMILY_SOURCES['execution_blast_pairwise_result_refs'] = {
    'meaning': 'Native BLAST pairwise result references (none: this episode acquires no results)'}
NATIVE_FAMILY_SOURCES['execution_blast_hsps'] = {
    'meaning': 'Optional native measurements for the published HSPs of an acquired result (none)'}
NATIVE_FAMILY_FIELDS = {name: source['meaning'] for name, source in NATIVE_FAMILY_SOURCES.items()}

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the assigned job execution', form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether original requested endpoint predicates have a saved validated '
                                 'completion', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'Original selected command, actual result and earned '
                                    'operational credit sources, saved as records', required=False),
    'execution_handoff_refs': Field('record_refs', 'Own command receipts that are returnable handoffs for this '
                                    'exact assignment', required=False),
    'execution_result_refs': Field('record_refs', 'Actual requested result acquisitions available to this episode '
                                   '(none: this episode acquires no results)', required=False),
    'execution_file_source_refs': Field('record_refs', 'Selected local file sources retained by this episode '
                                        '(none)', required=False),
    'execution_file_capture_outcomes': Field('list', 'Selected file availability and custody qualifications '
                                             '(none)', required=False),
    'execution_completed': Field('boolean', 'Whether the assigned endpoint has verified completion information',
                                 required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of a retained result (the empty record: no '
                                     'result windows exist for this episode)', required=False),
    **{name: Field('list', meaning, required=False) for name, meaning in NATIVE_FAMILY_FIELDS.items()},
})


def facts(summary):
    """The terminal facts plus the execution facts, from the summary."""
    completed = summary['completion_proof'] is not None
    return {**{name: [] for name in NATIVE_FAMILY_FIELDS},
            'practical_completed': completed,
            'practical_receipt_digests': [digest(receipt) for receipt in summary['receipts']],
            'practical_receipt_refs': list(summary['receipt_refs']),
            'execution_handoff_refs': sorted(summary['handoff_refs']),
            'execution_result_refs': [], 'execution_file_source_refs': [],
            'execution_file_capture_outcomes': [], 'execution_result_origin': {},
            'execution_completed': completed}


def final_to_parent(summary, completion, selection):
    receipts = summary['receipts']
    failed = sum(1 for receipt in receipts if 'failure' in receipt['outcome'].get('native_outcome', {}))
    completed = summary['completion_proof'] is not None
    finding = {'completed': completed, 'endpoint': summary['assignment']['endpoint'],
               'commands_run': len(receipts), 'commands_failed': failed,
               'satisfied_keys': list(summary['progress']['satisfied_keys']),
               'qualification': ('the endpoint predicates have a saved, validated completion' if completed else
                                 'no saved, validated completion of the requested endpoint: the satisfied '
                                 'requirement keys are listed')}
    recorded = facts(summary)
    result = {'credit': completion['credit'], 'finding': finding,
              **{name: recorded[name] for name in selection}}
    return result
