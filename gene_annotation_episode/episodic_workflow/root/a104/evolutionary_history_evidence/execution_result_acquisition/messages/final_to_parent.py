"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (whether
the requested acquisition is complete, what was acquired and what failed). Selectable: the handoff, result, file
source, file capture, completed and HSP sources of the results role and every array-valued source of the native
result families (HMMER, standard BLAST database, BLAST database, HMMER preparation, BLAST pairwise); their values
come from the progress the summary holds, and a source the summary holds nothing for is empty."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.evolutionary_history_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)

FINDING_FORM = RecordForm({
    'execution_completed': Field('boolean', 'Whether the requested acquisition is complete: a completed attempt '
                                            'with return code 0 and every requested window covered'),
    'target_family': Field('text', 'The family of the original target: native_bytes or a typed native family'),
    'handoff_ref': Field('text', 'The original handoff the results were acquired through'),
    'acquisitions': Field('integer', 'The number of acquisitions that completed'),
    'invalid_acquisitions': Field('integer', 'The number of selected operations that returned an invalid outcome'),
    'windows_acquired': Field('integer', 'The number of byte windows this episode retained'),
    'bytes_acquired': Field('integer', 'The number of bytes this episode retained'),
    'failures': Field('list', 'The window failures and invalid outcomes, in order'),
})

# The sources of the results role: name -> (field type, meaning).
OWN_SOURCES = {
    'execution_file_source_refs': ('record_refs', 'Source references for selected local file streams actually '
                                   'retained by this results episode; no producing-execution or atomic-version '
                                   'identity is established.'),
    'execution_file_capture_outcomes': ('list', 'Recorded selected-file availability, original job status and '
                                        'file-custody qualifications; successful byte retention alone does not '
                                        'establish execution success or closed writers.'),
    'execution_handoff_refs': ('record_refs', 'Qualified original handoff sources actually available to this '
                               'episode, including authenticated original failed native database attempts for '
                               'partial-output acquisition; failed attempts do not establish a successful '
                               'endpoint.'),
    'execution_result_refs': ('record_refs', 'Qualified actual requested result acquisitions available to this '
                              'episode. Generic native windows retain current-filesystem observations. Explicit '
                              'BLAST/HMMER producer bundles retain original attempt outputs matched by digest and '
                              'requested numerical facts.'),
    'execution_completed': ('boolean', 'Whether this assignment has actual verified endpoint information. Generic '
                            'native results mean requested current-filesystem acquisition plus independently '
                            'observed successful exact execution, without a producing-attempt or atomic-version '
                            'claim. Yielding alone is false.'),
    'execution_blast_hsps': ('list', 'Optional explicitly requested native measurements for all published HSPs of '
                             'this acquired result. No automatic ranking, top-N or significance filter. '
                             'target_coverage is native reference/hit coverage, not original gene-target coverage. '
                             'No functional assignment or annotation score.'),
    'execution_blast_pairwise_result_refs': ('record_refs', 'Native BLAST pairwise result references'),
}
# The array-valued sources of the native result families, empty unless the summary's progress holds them.
FAMILY_SOURCES = {name: ('list', declared['meaning'])
                  for declare in (native_hmmer_fact_sources, standard_blast_database_fact_sources,
                                  native_blast_database_fact_sources, preparation_fact_sources,
                                  native_blast_fact_sources)
                  for name, declared in declare().items()
                  if name.isidentifier() and name == name.lower() and declared['type'] == 'array'}
SOURCES = {**FAMILY_SOURCES, **OWN_SOURCES}

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested acquisition is complete, what was acquired and what failed',
                     form=FINDING_FORM),
    **{name: Field(kind, meaning, required=False) for name, (kind, meaning) in SOURCES.items()},
})


def _facts(summary):
    """The facts a parent may select: an empty list for every source the progress does not hold, then the progress
    the summary holds."""
    return {**{name: [] for name in FAMILY_SOURCES}, 'execution_blast_hsps': [],
            'execution_blast_pairwise_result_refs': [], **summary['execution_progress']}


def _finding(summary):
    own = [result for result in summary['results'] if not result['initial']]
    failures = [failure for result in own for failure in result['failures']]
    failures += [{'tool': row['tool'], 'code': row['feedback']['code']}
                 for row in summary['acquisitions'] if row['status'] != 'completed']
    windows = [window for result in own for window in result['windows']]
    return {'execution_completed': summary['execution_completed'], 'target_family': summary['family'],
            'handoff_ref': summary['assignment']['handoff_ref'],
            'acquisitions': sum(1 for row in summary['acquisitions'] if row['status'] == 'completed'),
            'invalid_acquisitions': sum(1 for row in summary['acquisitions'] if row['status'] != 'completed'),
            'windows_acquired': len(windows), 'bytes_acquired': sum(window['returned_bytes'] for window in windows),
            'failures': failures}


def final_to_parent(summary, completion, selection):
    facts = _facts(summary)
    result = {'credit': completion['credit'], 'finding': _finding(summary)}
    for name in selection:
        result[name] = facts[name]
    return result
