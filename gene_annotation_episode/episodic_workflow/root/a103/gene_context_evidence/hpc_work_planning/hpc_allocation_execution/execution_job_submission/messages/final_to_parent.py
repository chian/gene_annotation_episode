"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (which
permitted requests received a usable handoff), ``execution_handoff_refs`` (the handoff records of the jobs, returned
in custody) and ``execution_completed``. Every other fact source of the ``launch`` role is a selectable field. A
launch acquires no results, so the result, file, HSP and native result family sources are empty for it. A name with a
dot (the masking and BLAST utility families, ``execution.<name>``) is written with an underscore, because a form
field name is a lowercase identifier. ``execution_result_origin`` is the empty record: no result is retained."""
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

FINDING_FORM = RecordForm({
    'requested_resource_ids': Field('list', 'The resource ids whose requests the constraints permit'),
    'already_handed_off': Field('list', 'The resource ids that already had a usable handoff when the commission '
                                        'began'),
    'handed_off': Field('list', 'The resource ids that newly received a usable handoff'),
    'handoff_complete': Field('boolean', 'Whether a received handoff is marked complete by its child'),
    'qualification': Field('text', 'What the received handoffs do and do not establish'),
})

# The fact sources of role launch that the library views declare (type and meaning), by name.
SOURCES = {}
for _declare in (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
                 standard_blast_database_fact_sources, native_blast_database_fact_sources, preparation_fact_sources,
                 native_blast_fact_sources, bvbrc_data_fact_sources, minhash_fact_sources):
    SOURCES.update(_declare())


def field_name(source):
    return source.replace('.', '_')


def _declared(spec):
    kind = spec['type']
    items = (spec.get('report_schema') or {}).get('items') or {}
    if kind == 'array':
        kind = 'record_refs' if items.get('format') == 'reference' else 'list'
    elif kind == 'object':
        kind = 'record'
    return Field(kind, spec['meaning'], required=False)


FIELDS = {field_name(source): _declared(spec) for source, spec in SOURCES.items() if spec['type'] == 'array'}
FIXED = {
    'execution_result_refs': ('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                             'acquires no results'),
    'execution_blast_pairwise_result_refs': ('record_refs', 'Pairwise BLAST result references: none for a launch'),
    'bvbrc_appservice_support_refs': ('record_refs', 'Actually received AppService preparation, Workspace, upload '
                                                     'or observation receipts: none for a launch'),
    'execution_blast_hsps': ('list', 'Optional explicitly requested native measurements of acquired HSPs: none for '
                                     'a launch'),
}
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the launch established about the permitted requests', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources the resource children '
                                    'returned; a failed attempt does not establish a successful endpoint'),
    'execution_completed': Field('boolean', 'Whether a received handoff is marked complete. Yielding alone is '
                                 'false.'),
    **{name: Field(kind, meaning, required=False) for name, (kind, meaning) in FIXED.items()},
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results: the empty record '
                                     'when no qualified retained data exists', required=False),
    **{name: field for name, field in FIELDS.items() if name not in FIXED},
})


def facts(summary):
    """The facts this Episode recorded."""
    recorded = {'execution_handoff_refs': list(summary['handoff_refs']), 'execution_completed': summary['completed'],
                'execution_result_origin': {}}
    for name, field in RETURN_FORM.fields.items():
        if name not in recorded and not field.required and field.type in ('list', 'record_refs'):
            recorded[name] = []
    return recorded


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    finding = {'requested_resource_ids': list(summary['permitted_resource_ids']),
               'already_handed_off': list(summary['already_handed_off']), 'handed_off': list(summary['handed_off']),
               'handoff_complete': summary['completed'],
               'qualification': ('a usable handoff was received for every resource listed as handed off; a handoff '
                                 'is a record of where the job continues, not an acquired result'
                                 if summary['handed_off'] else 'no usable handoff was received by this launch')}
    result = {'credit': completion['credit'], 'finding': finding,
              'execution_handoff_refs': recorded['execution_handoff_refs'],
              'execution_completed': recorded['execution_completed']}
    for name in selection:
        result[name] = recorded[name]
    return result
