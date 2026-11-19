"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (whether the
requested acquisition is complete, what was retained and how the retained bytes are qualified). Every fact source is
a selectable field the parent selects in its commission.

Where a fact source name contains a dot (the masking and BLAST utility families) the field name has an underscore in
its place: a form field name is a lowercase identifier. A generic native acquisition has no value for the families of
the typed targets: selecting one returns an empty list. ``execution_result_origin`` is the empty record when no window
is retained. ``execution_result_artifact_refs`` is the artifact of each retained result source, returned with it
because a returned record does not bring the records it names. The object-typed family sources are not fields."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.partner_presence_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.partner_presence_evidence.sequence_masking_result_views import (
    masking_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.blast_utility_result_views import (
    blast_utility_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)

# What the retained bytes are and are not.
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

FINDING_FORM = RecordForm({
    'complete': Field('boolean', 'Whether the requested windows are fully acquired from a completed, successful '
                      'observation of the exact attempt. Yielding alone is false'),
    'requested_paths': Field('list', 'The requested paths with their offset and limit'),
    'acquired_window_count': Field('integer', 'How many byte windows the retained results hold'),
    'failure_count': Field('integer', 'How many windows were unavailable'),
    'acquired_selector_fraction': Field('number', 'The mean over the requested paths of the newly covered fraction '
                                        'of the requested byte positions'),
    'observation_states': Field('list', 'The state and return code of each observation of the exact attempt'),
    'qualification': Field('record', 'What the retained bytes are: current resource filesystem content, the attempt '
                           'output version unverified, separate windows not an atomic snapshot'),
})

# The fact sources of the typed families that the library functions describe (type and meaning); a source keeps its
# meaning.
_FAMILIES = (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
             standard_blast_database_fact_sources, native_blast_database_fact_sources, preparation_fact_sources,
             native_blast_fact_sources)
_FORM_TYPES = {'object': 'record', 'array': 'list', 'boolean': 'boolean', 'number': 'number', 'integer': 'integer',
               'string': 'text'}


def _family_fields():
    fields = {}
    for function in _FAMILIES:
        for source, declared in function().items():
            if declared['type'] == 'object':
                continue
            fields[source.replace('.', '_')] = Field(_FORM_TYPES[declared['type']], declared['meaning'],
                                                     required=False)
    return fields


def _selectable():
    return {
        'execution_handoff_refs': Field('record_refs', 'Qualified original handoff records actually available to '
                                        'this episode. Failed attempts do not establish a successful endpoint.',
                                        required=False),
        'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to '
                                       'this episode, each with its windows. Generic native windows retain '
                                       'current-filesystem observations', required=False),
        'execution_result_artifact_refs': Field('record_refs', 'The artifact of each result source in '
                                                'execution_result_refs, with the retained result body',
                                                required=False),
        'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information: '
                                     'requested current-filesystem acquisition plus independently observed '
                                     'successful exact execution, without a producing-attempt or atomic-version '
                                     'claim. Yielding alone is false', required=False),
        'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results: current-file '
                                         'windows. The empty record when no qualified data is retained.',
                                         required=False),
        'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                      'HSPs of an acquired result; a generic native acquisition has none.',
                                      required=False),
        'execution_blast_pairwise_result_refs': Field('record_refs', 'Pairwise BLAST result references; a generic '
                                                      'native acquisition has none.', required=False),
        'bvbrc_appservice_support_refs': Field('record_refs', 'Received BV-BRC AppService support records; a '
                                               'generic native acquisition has none.', required=False),
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
    **_selectable(),
    **_family_fields(),
})


def facts(summary):
    """The facts of a generic native target: every typed family empty, the handoff and the retained
    results of the summary, and the completion of the requested acquisition."""
    values = {name: [] for name, spec in RETURN_FORM.fields.items()
              if spec.type in ('list', 'record_refs') and not spec.required}
    values.update({'execution_handoff_refs': list(summary['handoff_refs']),
                   'execution_result_refs': list(summary['result_refs']),
                   'execution_result_artifact_refs': list(summary['result_artifact_refs']),
                   'execution_completed': summary['completed']})
    values['execution_result_origin'] = dict(NATIVE_RESULT_ORIGIN) if summary['has_windows'] else {}
    return values


def finding(summary, credit):
    return {'complete': summary['completed'], 'requested_paths': summary['requested_paths'],
            'acquired_window_count': summary['window_count'], 'failure_count': summary['failure_count'],
            'acquired_selector_fraction': credit / summary['acquired_record_unit'],
            'observation_states': summary['observation_states'], 'qualification': dict(NATIVE_RESULT_ORIGIN)}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    result = {'credit': completion['credit'], 'finding': finding(summary, completion['credit'])}
    for name in selection:
        result[name] = recorded[name]
    return result
