"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (which
resources got a usable handoff and which launches ran), the original handoff records (returned in custody, so the job
identity is preserved across a scientific return) and whether a usable handoff was received. Every other fact source
of the ``launch`` role is a selectable field; a field name is the fact-source name with dots written as underscores
(a field name cannot contain a dot). The fact-source declarations come from the library's views of this axis, the same
set the API child declares. A launch acquires no results: every family source and the result, file and hsp sources
are empty for it, and ``execution_result_origin`` is the empty record."""
from copy import deepcopy

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_and_context_sources.uniprot_return_contracts import (
    uniprot_fact_sources)
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

LAUNCH_FORM = RecordForm({
    'slot': Field('text', 'The launch child commissioned'),
    'resource_id': Field('text', 'The resource it was commissioned on'),
    'completed': Field('boolean', 'Whether the child verified the requested endpoint'),
    'handoff_refs': Field('list', 'The handoff records the child returned'),
})
FINDING_FORM = RecordForm({
    'handoff_established': Field('boolean', 'Whether at least one usable handoff was received'),
    'handoff_resources': Field('list', 'The resource ids that have a usable handoff from this launch'),
    'new_handoff_count': Field('integer', 'The handoffs of resources that had none when this launch began'),
    'launches_run': Field('integer', 'The launch children commissioned'),
    'launches': Field('list', 'Each launch child commissioned, in order', items=LAUNCH_FORM),
    'qualification': Field('text', 'What the recorded handoffs establish: a received handoff is not a finished job '
                                   'and a missing reply does not establish that no job was created'),
})

# The fact sources, by recorded source name, from the library views that declare them.
SOURCES = {}
for _declare in (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
                 uniprot_fact_sources, standard_blast_database_fact_sources, native_blast_database_fact_sources,
                 preparation_fact_sources, native_blast_fact_sources):
    SOURCES.update(_declare())
SOURCES = {source: spec for source, spec in SOURCES.items() if spec['type'] == 'array'}
EMPTY = {'list': [], 'record_refs': [], 'record': {}}


def field_name(source):
    return source.replace('.', '_')


def _declared(spec):
    kind = spec['type']
    items = (spec.get('report_schema') or {}).get('items') or {}
    if kind == 'array':
        kind = 'record_refs' if items.get('format') == 'reference' else 'list'
    return Field(kind, spec['meaning'], required=False)


FIELDS = {field_name(source): _declared(spec) for source, spec in SOURCES.items()}
FIELD_SOURCE = {field_name(source): source for source in SOURCES}
FIXED = {
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                   'acquires no results', required=False),
    'execution_file_source_refs': Field('record_refs', 'Source references of retained local file streams: none, a '
                                        'launch acquires no results', required=False),
    'execution_file_capture_outcomes': Field('list', 'Recorded selected-file availability: always empty here',
                                             required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results; the empty record '
                                     'when none is retained', required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements of acquired HSPs: '
                                  'none for a launch', required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'BLAST pairwise result references: none for a '
                                                  'launch', required=False),
    'bvbrc_appservice_support_refs': Field('record_refs', 'Actually received BV-BRC AppService support receipts',
                                           required=False),
}
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources got a usable handoff and which launches ran', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources received from the launch '
                                    'children: the job identity, preserved across a return'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information (a '
                                 'usable handoff was received); yielding alone is false'),
    **FIXED,
    **FIELDS,
})


def facts(summary):
    """The facts a parent may select, from the summary: the handoff references and whether a
    usable one was received; every result source is empty."""
    recorded = {'execution_handoff_refs': sorted(summary['handoff_refs']),
                'execution_completed': bool(summary['handoff_resources'])}
    recorded.update({name: deepcopy(EMPTY[field.type]) for name, field in {**FIXED, **FIELDS}.items()
                     })
    return recorded


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    new = len(set(summary['handoff_resources']) - set(summary['received_handoff_resources']))
    established = recorded['execution_completed']
    result = {'credit': completion['credit'],
              'finding': {'handoff_established': established, 'handoff_resources': list(summary['handoff_resources']),
                          'new_handoff_count': new, 'launches_run': len(summary['launches']),
                          'launches': [{'slot': launch['slot'], 'resource_id': launch['resource_id'],
                                        'completed': launch['completed'], 'handoff_refs': launch['handoff_refs']}
                                       for launch in summary['launches']],
                          'qualification': ('a usable original handoff was received from a launch child'
                                            if established else
                                            'no usable original handoff was received; a missing reply does not '
                                            'establish that no job was created')},
              'execution_handoff_refs': recorded['execution_handoff_refs'],
              'execution_completed': established}
    for name in selection:
        result[name] = recorded[name]
    return result
