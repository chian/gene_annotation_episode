"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (what was
acquired and how it is qualified), the retained result records in custody and whether the requested acquisition is
complete. A commissioner may select any other fact: the handoff records, the retained-result origin, the local file
sources and their capture outcomes, and the typed result families (a generic native acquisition has no value for them,
so each is empty). A field name has an underscore where a source name has a dot: a form field name is a lowercase
identifier."""
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

# What the retained bytes are and are not.
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

FINDING_FORM = RecordForm({
    'complete': Field('boolean', 'Whether the requested windows are fully acquired from a completed, successful '
                      'observation of the exact attempt. Yielding alone is false'),
    'requested_paths': Field('list', 'The requested paths with their offset and limit'),
    'acquired_window_count': Field('integer', 'How many byte windows were retained'),
    'failure_count': Field('integer', 'How many windows were unavailable'),
    'acquired_selector_fraction': Field('number', 'The mean over the requested paths of the newly covered fraction '
                                        'of the requested byte positions'),
    'observation_states': Field('list', 'The state and return code of each observation of the exact attempt'),
    'qualification': Field('record', 'What the retained bytes are: current resource filesystem content, the attempt '
                           'output version unverified, separate windows not an atomic snapshot'),
})

# The typed result families that the reader functions describe: one list field each (a generic native acquisition
# has no value for them, so each is empty).
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
        'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources actually available to '
                                        'this episode. Failed attempts do not establish a successful endpoint.',
                                        required=False),
        'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results: current-file '
                                         'windows, with whether any window was retained.',
                                         required=False),
        'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                      'HSPs of an acquired result; a generic native acquisition has none.',
                                      required=False),
        'execution_blast_pairwise_result_refs': Field('record_refs', 'Pairwise BLAST result references; a generic '
                                                      'native acquisition has none.', required=False),
        'execution_file_source_refs': Field('record_refs', 'Source references for selected local file streams '
                                            'retained by this results episode; no producing-execution or '
                                            'atomic-version identity is established.', required=False),
        'execution_file_capture_outcomes': Field('list', 'Recorded selected-file availability, original job status '
                                                 'and file-custody qualifications; successful byte retention alone '
                                                 'does not establish execution success or closed writers.',
                                                 required=False),
    }


RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What was acquired and how it is qualified', form=FINDING_FORM),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to '
                                   'this episode. Generic native windows retain current-filesystem observations'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information: '
                                 'requested current-filesystem acquisition plus independently observed successful '
                                 'exact execution, without a producing-attempt or atomic-version claim. Yielding '
                                 'alone is false'),
    **_selectable(),
    **_family_fields(),
})


def _facts(summary):
    """The facts of a generic native target: every typed family empty, the handoff and the retained results of the
    summary, and the completion of the requested acquisition."""
    facts = {name: [] for name, spec in RETURN_FORM.fields.items()
             if spec.type == 'list' or (spec.type == 'record_refs' and not spec.required)}
    facts.update({'execution_handoff_refs': list(summary['handoff_refs']),
                  'execution_result_refs': list(summary['result_refs']), 'execution_completed': summary['completed'],
                  'execution_result_origin': {'retained': summary['has_windows'], **NATIVE_RESULT_ORIGIN}})
    return facts


def _finding(summary, credit):
    return {'complete': summary['completed'], 'requested_paths': summary['requested_paths'],
            'acquired_window_count': summary['window_count'], 'failure_count': summary['failure_count'],
            'acquired_selector_fraction': credit / summary['acquired_record_unit'],
            'observation_states': summary['observation_states'], 'qualification': dict(NATIVE_RESULT_ORIGIN)}


def final_to_parent(summary, completion, selection):
    facts = _facts(summary)
    result = {'credit': completion['credit'], 'finding': _finding(summary, completion['credit']),
              'execution_result_refs': facts['execution_result_refs'],
              'execution_completed': facts['execution_completed']}
    for name in selection:
        result[name] = facts[name]
    return result
