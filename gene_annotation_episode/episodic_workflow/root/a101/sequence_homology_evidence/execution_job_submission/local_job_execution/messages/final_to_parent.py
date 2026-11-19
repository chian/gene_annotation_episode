"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (whether
the requested endpoint was verified, which requirements are satisfied and which commands failed). Every other fact
is a selectable field the parent names in its commission.

The selectable facts: the terminal practical facts (``practical_completed``, ``practical_receipt_digests``,
``practical_receipt_refs``), ``execution_handoff_refs``, ``execution_result_refs``, ``execution_completed``,
``execution_result_origin`` (the empty record: a launch retains no result), ``execution_blast_hsps``,
``execution_blast_pairwise_result_refs`` and the array-typed native result families, whose names and meanings are
taken from the library functions that declare them (HMMER, standard BLAST database, BLAST database, HMMER
preparation, BLAST pairwise, BV-BRC data). A launch acquires no results: those sources are empty for it.

``NOT_DECLARABLE`` holds the sources whose names a form field cannot carry (the masking and BLAST utility sources
have dotted names)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.sequence_homology_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_views import (
    bvbrc_data_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.sequence_masking_result_views import (
    masking_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_result_views import (
    BLAST_HSP_FACT_SCHEMA)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_utility_result_views import (
    blast_utility_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'practical_completed': Field('boolean', 'Whether the original requested endpoint predicates have a verified '
                                            'completion'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'commands_run': Field('integer', 'The number of commands executed'),
    'satisfied_keys': Field('list', 'The original requirement keys currently satisfied'),
    'unsatisfied_keys': Field('list', 'The original requirement keys not satisfied'),
    'failures': Field('list', 'The recorded failures of the commands that failed, in order'),
})

def _refs_schema(source, namespace):
    return {'type': 'array', 'uniqueItems': True, 'items': {
        'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': source}

# The sources this episode computes itself, name -> entry.
OWN_SOURCES = {
    'practical_completed': {'type': 'boolean', 'meaning': 'Whether original requested endpoint predicates have a '
                                                          'saved validated completion.'},
    'practical_receipt_digests': {'type': 'array', 'meaning': 'Host-recorded digests of the original selected '
                                                              'command receipts.'},
    'practical_receipt_refs': {'type': 'array', 'meaning': 'Original selected command, actual result and earned '
                                                           'operational credit sources.',
                               'report_schema': _refs_schema('practical_receipt_refs', 'practical_receipt')},
    'execution_handoff_refs': {'type': 'array', 'meaning': 'Qualified original handoff sources actually available '
                                                           'to this episode, including authenticated original '
                                                           'failed native database attempts for partial-output '
                                                           'acquisition; failed attempts do not establish a '
                                                           'successful endpoint.',
                               'report_schema': _refs_schema('execution_handoff_refs', 'execution_handoff')},
    'execution_result_refs': {'type': 'array', 'meaning': 'Qualified actual requested result acquisitions '
                                                          'available to this episode. Generic native windows retain '
                                                          'current-filesystem observations. Explicit BLAST/HMMER '
                                                          'producer bundles retain original attempt outputs '
                                                          'matched by digest and requested numerical facts.',
                              'report_schema': _refs_schema('execution_result_refs', 'execution_result')},
    'execution_completed': {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint '
                                                          'information. Generic native results mean requested '
                                                          'current-filesystem acquisition plus independently '
                                                          'observed successful exact execution, without a '
                                                          'producing-attempt or atomic-version claim. Yielding '
                                                          'alone is false.'},
    'execution_result_origin': {'type': 'object', 'meaning': 'Actual acquisition semantics of retained results: '
                                                             'current-file windows, original producer output, or '
                                                             'explicitly received saved numerical data. No '
                                                             'qualified retained data yields the empty record.'},
    'execution_blast_hsps': {'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all '
                                                         'published HSPs of this acquired result. No automatic '
                                                         'ranking, top-N or significance filter.',
                             'report_schema': {**BLAST_HSP_FACT_SCHEMA, 'x-source': 'execution_blast_hsps'}},
    'execution_blast_pairwise_result_refs': {
        'type': 'array', 'meaning': 'Native BLAST pairwise result references (typed as '
                                    'references)',
        'report_schema': _refs_schema('execution_blast_pairwise_result_refs', 'native_blast_pairwise_row')},
}
LIBRARY_SOURCES = {}
for _function in (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
                  standard_blast_database_fact_sources, native_blast_database_fact_sources,
                  preparation_fact_sources, native_blast_fact_sources, bvbrc_data_fact_sources):
    LIBRARY_SOURCES.update(_function())
SOURCES = {**LIBRARY_SOURCES, **OWN_SOURCES}
NOT_DECLARABLE = tuple(sorted(name for name in SOURCES if not name.isidentifier() or name != name.lower()))
# A source whose value for a launch is an empty list (every array source but the ones this episode has facts for).
_OWN_VALUED = ('practical_completed', 'practical_receipt_digests', 'practical_receipt_refs', 'execution_handoff_refs',
               'execution_completed')
_EMPTY = tuple(sorted(name for name, entry in SOURCES.items()
                      if name not in NOT_DECLARABLE and name not in _OWN_VALUED and entry['type'] == 'array'))

OBJECT_SOURCES = tuple(sorted(name for name, entry in SOURCES.items() if entry['type'] == 'object'
                                and name not in NOT_DECLARABLE and name != 'execution_result_origin'))


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
    'finding': Field('record', 'Whether the requested endpoint was verified, and what each command did',
                     form=FINDING_FORM),
    **{name: _field(source) for name, source in SOURCES.items()
       if name not in NOT_DECLARABLE and name not in OBJECT_SOURCES},
})


def _facts(summary):
    """The facts for a practical assignment: the terminal facts and the handoff
    references, and an empty list for every result source (a launch acquires no results)."""
    completed = summary['execution_completion'] is not None
    return {**{name: [] for name in _EMPTY},
            'practical_completed': completed,
            'practical_receipt_digests': [digest(receipt) for receipt in summary['receipts']],
            'practical_receipt_refs': list(summary['receipt_refs']),
            'execution_handoff_refs': sorted(summary['handoff_refs']),
            'execution_result_origin': {}, 'execution_completed': completed}


def final_to_parent(summary, completion, selection):
    progress = summary['execution_progress']
    satisfied = list(progress['satisfied_keys'])
    unsatisfied = [row['key'] for row in progress['requirements'] if not row['satisfied']]
    failures = [command['failure'] for command in summary['commands'] if command['failure'] is not None]
    facts = _facts(summary)
    result = {'credit': completion['credit'],
              'finding': {'practical_completed': facts['practical_completed'],
                          'endpoint': summary['assignment']['endpoint'], 'commands_run': len(summary['commands']),
                          'satisfied_keys': satisfied, 'unsatisfied_keys': unsatisfied, 'failures': failures}}
    for name in selection:
        result[name] = facts[name]
    return result
