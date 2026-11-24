"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources handed off, through which child, and whether each handoff is verified complete). Every fact source of this
launch role is a selectable field (a dot of the source name is written as an underscore: a field name cannot contain
a dot): the handoff and result references, ``execution_completed``, ``execution_result_origin``,
``execution_blast_hsps``, the BLAST pairwise result references, the AppService support references and the native
result families of the library views.

A launch acquires no results: every fact except the handoff references and the completion is empty, and
``execution_result_origin`` is the empty record. The commissioner selects ``execution_handoff_refs`` when it wants
it."""
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
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.bvbrc_minhash_views import (
    minhash_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)

COMMISSION_FORM = RecordForm({
    'resource_id': Field('text', 'The resource the request was commissioned on'),
    'slot': Field('text', 'The resource child that ran it: launch_api, launch_local or launch_hpc'),
    'handoff_established': Field('boolean', 'Whether the child returned a usable handoff'),
    'completed': Field('boolean', 'Whether the child verified the handoff completion'),
})
FINDING_FORM = RecordForm({
    'commissions': Field('list', 'Each commissioned request in order: the resource, the child and what it returned',
                         items=COMMISSION_FORM),
    'handoff_resource_ids': Field('list', 'The resources with a usable received handoff'),
    'new_handoff_count': Field('integer', 'How many of them were not already handed off at the commission'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})

# The fact sources of the launch role, by recorded source name, from the library views that declare them.
SOURCES = {}
for _declare in (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
                 standard_blast_database_fact_sources, native_blast_database_fact_sources, preparation_fact_sources,
                 native_blast_fact_sources, bvbrc_data_fact_sources, minhash_fact_sources):
    SOURCES.update(_declare())
EMPTY = {'list': [], 'record_refs': [], 'record': {}, 'boolean': False}


def field_name(source):
    return source.replace('.', '_')


def declared(spec):
    kind = spec['type']
    items = (spec.get('report_schema') or {}).get('items') or {}
    if kind == 'array':
        kind = 'record_refs' if items.get('format') == 'reference' else 'list'
    elif kind == 'object':
        kind = 'record'
    return Field(kind, spec['meaning'], required=False)


FIELDS = {field_name(source): declared(spec) for source, spec in SOURCES.items()}
FIXED = {
    'execution_handoff_refs': 'Qualified original handoff sources actually available to this episode, as received '
                              'from the resource children; a failed attempt does not establish a successful endpoint.',
    'execution_result_refs': 'Qualified actual requested result acquisitions available to this episode: none, a '
                             'launch acquires no results.',
    'execution_blast_pairwise_result_refs': 'Qualified BLAST pairwise result records of this episode: none.',
    'bvbrc_appservice_support_refs': 'Actually received AppService preparation, Workspace, upload or observation '
                                     'receipts; these are not scientific result acquisitions.',
}
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources handed off the commissioned execution requests',
                     form=FINDING_FORM),
    **{name: Field('record_refs', meaning, required=False) for name, meaning in FIXED.items()},
    'execution_completed': Field('boolean', 'Whether any received handoff has actual verified endpoint '
                                 'information. Yielding alone is false.', required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results; the empty record '
                                     'when no qualified retained data exists (always, for a launch).',
                                     required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                  'HSPs of an acquired result: none, a launch acquires no results.', required=False),
    **FIELDS,
})


def facts(summary):
    """The facts of a launch, from the summary: the received handoff references and whether any is
    complete; every other source is empty."""
    recorded = {name: EMPTY[field.type] for name, field in FIELDS.items()}
    recorded.update({'execution_handoff_refs': list(summary['handoff_refs']), 'execution_result_refs': [],
                     'execution_blast_pairwise_result_refs': [], 'bvbrc_appservice_support_refs': [],
                     'execution_completed': summary['completed'], 'execution_result_origin': {},
                     'execution_blast_hsps': []})
    return recorded


def final_to_parent(summary, completion, selection):
    finding = {'commissions': [{'resource_id': commission['resource_id'], 'slot': commission['slot'],
                                'handoff_established': commission['usable_handoff'],
                                'completed': commission['completed']}
                               for commission in summary['commissions']],
               'handoff_resource_ids': list(summary['handed_off']),
               'new_handoff_count': len(summary['new_handoff_resource_ids']),
               'qualification': ('a handoff is usable when its resource child returned handoff references; the '
                                 'record itself is not re-read here, and no result was acquired')}
    recorded = facts(summary)
    result = {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
    return result
