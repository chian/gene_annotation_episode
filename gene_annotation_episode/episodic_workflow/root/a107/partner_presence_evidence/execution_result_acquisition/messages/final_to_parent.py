"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (whether
the requested acquisition is complete, what was acquired and what failed). Every other fact source of the ``results``
role is a selectable field: the results-only sources (``execution_file_source_refs``,
``execution_file_capture_outcomes``, the handoff, result, completed, origin and HSP sources) and the sources of the
library functions that declare them (HMMER, masking, BLAST utility, standard BLAST database, BLAST database, HMMER
preparation, BLAST pairwise, expression NMF, RNA structure and its comparison, UniProt). The child declares every field
it can return, so all of them are declared.

A form field name is a lowercase identifier, so the dotted masking (``execution.masking_*``) and BLAST utility
(``execution.blast_utility_*``) sources are not fields (``NOT_DECLARABLE``). ``execution_result_origin`` is the empty
record when nothing is retained. The object-typed family sources (``DEFERRED_OBJECT_SOURCES``) are not fields."""
from copy import deepcopy

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.execution_contracts import (
    obj)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_and_context_sources.uniprot_return_contracts import (
    uniprot_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation.expression_nmf_return_views import (
    expression_nmf_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.partner_presence_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.rna_structure.rna_structure_comparison_views import (
    rna_comparison_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.rna_structure.rna_structure_result_views import (
    rna_structure_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.partner_presence_evidence.sequence_masking_result_views import (
    masking_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.blast_result_views import (
    BLAST_HSP_FACT_SCHEMA)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.blast_utility_result_views import (
    blast_utility_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.records.local_execution.local_file_capture_results import (
    OUTCOMES_SCHEMA)

# The origin of the generic native windows.
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

FINDING_FORM = RecordForm({
    'execution_completed': Field('boolean', 'Whether the requested acquisition is complete: a completed attempt '
                                            'with return code 0 and every requested window covered'),
    'target_family': Field('text', 'The family of the original target: native_bytes'),
    'handoff_ref': Field('text', 'The original handoff the results were acquired through'),
    'acquisitions': Field('integer', 'The number of acquisitions that completed'),
    'invalid_acquisitions': Field('integer', 'The number of selected operations that returned an invalid outcome'),
    'windows_acquired': Field('integer', 'The number of byte windows this episode retained'),
    'bytes_acquired': Field('integer', 'The number of bytes this episode retained'),
    'failures': Field('list', 'The window failures and invalid outcomes, in order'),
})


def _refs_schema(source, namespace):
    return {'type': 'array', 'uniqueItems': True, 'items': {
        'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': source}


# The results-only sources, name -> entry.
OWN_SOURCES = {
    'execution_file_source_refs': {
        'type': 'array', 'meaning': 'Source references for selected local file streams actually retained by this '
                                    'results episode; no producing-execution or atomic-version identity is '
                                    'established.', 'report_schema': _refs_schema('execution_file_source_refs', 'source')},
    'execution_file_capture_outcomes': {
        'type': 'array', 'meaning': 'Recorded selected-file availability, original job status and file-custody '
                                    'qualifications; successful byte retention alone does not establish execution '
                                    'success or closed writers.',
        'report_schema': {**deepcopy(OUTCOMES_SCHEMA), 'x-source': 'execution_file_capture_outcomes'}},
    'execution_handoff_refs': {
        'type': 'array', 'meaning': 'Qualified original handoff sources actually available to this episode, '
                                    'including authenticated original failed native database attempts for '
                                    'partial-output acquisition; failed attempts do not establish a successful '
                                    'endpoint.', 'report_schema': _refs_schema('execution_handoff_refs',
                                                                               'execution_handoff')},
    'execution_result_refs': {
        'type': 'array', 'meaning': 'Qualified actual requested result acquisitions available to this episode. '
                                    'Generic native windows retain current-filesystem observations. Explicit '
                                    'BLAST/HMMER producer bundles retain original attempt outputs matched by digest '
                                    'and requested numerical facts.',
        'report_schema': _refs_schema('execution_result_refs', 'execution_result')},
    'execution_completed': {
        'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Generic '
                                      'native results mean requested current-filesystem acquisition plus '
                                      'independently observed successful exact execution, without a '
                                      'producing-attempt or atomic-version claim. Yielding alone is false.'},
    'execution_result_origin': {
        'type': 'object', 'meaning': 'Actual acquisition semantics of retained results: current-file windows, '
                                     'original producer output, or explicitly received saved numerical data. No '
                                     'qualified retained data yields the empty record.',
        'report_schema': {**obj({key: {'type': 'string', 'enum': [value]} for key, value in
                                 NATIVE_RESULT_ORIGIN.items()}), 'type': ['object', 'null'],
                          'x-source': 'execution_result_origin'}},
    'execution_blast_hsps': {
        'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all published HSPs of '
                                    'this acquired result. No automatic ranking, top-N or significance filter. '
                                    'target_coverage is native reference/hit coverage, not original gene-target '
                                    'coverage. HSP/reference records support later scoped reads; selected HSP '
                                    'references can instead be returned through a parent-chosen typed field. No '
                                    'functional assignment or annotation score.',
        'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}},
    'execution_blast_pairwise_result_refs': {
        'type': 'array', 'meaning': 'Native BLAST pairwise result references, typed as '
                                    'references',
        'report_schema': _refs_schema('execution_blast_pairwise_result_refs', 'native_blast_pairwise_row')},
}
LIBRARY_SOURCES = {}
for _function in (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
                  standard_blast_database_fact_sources, native_blast_database_fact_sources,
                  preparation_fact_sources, native_blast_fact_sources, uniprot_fact_sources,
                  expression_nmf_fact_sources, rna_comparison_fact_sources, rna_structure_fact_sources):
    LIBRARY_SOURCES.update(_function())
SOURCES = {**LIBRARY_SOURCES, **OWN_SOURCES}
NOT_DECLARABLE = tuple(sorted(name for name in SOURCES if not name.isidentifier() or name != name.lower()))
DEFERRED_OBJECT_SOURCES = tuple(sorted(name for name, entry in SOURCES.items() if entry['type'] == 'object'
                                         and name != 'execution_result_origin' and name not in NOT_DECLARABLE))
# The sources whose value for a native byte target the summary carries.
_VALUED = ('execution_handoff_refs', 'execution_result_refs', 'execution_file_source_refs',
           'execution_file_capture_outcomes', 'execution_result_origin', 'execution_completed')
# Every other array source is empty for a native byte target.
_EMPTY = tuple(sorted(name for name, entry in SOURCES.items()
                      if name not in NOT_DECLARABLE and name not in _VALUED and entry['type'] == 'array'))


def _field(source):
    if source['type'] == 'boolean':
        return Field('boolean', source['meaning'], required=False)
    if source['type'] == 'object':
        return Field('record', source['meaning'], required=False)
    items = source.get('report_schema', {}).get('items', {})
    if items.get('format') == 'reference':
        return Field('record_refs', source['meaning'], required=False)
    return Field('list', source['meaning'], required=False)


RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested acquisition is complete, what was acquired and what failed',
                     form=FINDING_FORM),
    **{name: _field(source) for name, source in SOURCES.items() if name not in NOT_DECLARABLE + DEFERRED_OBJECT_SOURCES},
})


def _facts(summary):
    """The facts for a native byte target: the progress the summary holds and an empty list for every other source;
    the origin is the empty record when nothing is retained."""
    facts = {**{name: [] for name in _EMPTY}, **summary['execution_progress']}
    facts['execution_result_origin'] = facts['execution_result_origin'] or {}
    return facts


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
