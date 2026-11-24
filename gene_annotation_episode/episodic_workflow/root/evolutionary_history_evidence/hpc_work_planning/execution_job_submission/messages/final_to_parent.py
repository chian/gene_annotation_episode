"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (which
resources got a usable handoff and which launches ran), the original handoff records (returned in custody, so the
job's identity is preserved across a scientific return) and whether a usable handoff was received. Selectable: the
result, file source, file capture, HSP and pairwise sources and every array-valued source of the native result
families, the masking and utility sources included (a field name cannot contain a dot: ``execution.<name>`` is the
field ``execution_<name>``). A launch acquires no results: every one of them is empty for it."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.evolutionary_history_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.evolutionary_history_evidence.sequence_masking_result_views import (
    masking_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.blast_utility_result_views import (
    blast_utility_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_standard_database_result_views import (
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

_FAMILY_SOURCE_FUNCTIONS = (native_hmmer_fact_sources, standard_blast_database_fact_sources,
                            native_blast_database_fact_sources, preparation_fact_sources, native_blast_fact_sources,
                            masking_fact_sources, blast_utility_fact_sources)


def field_name(source):
    return source.replace('.', '_')


# The array-valued native result family sources by field name: ``(meaning)``.
FAMILY_SOURCES = {field_name(source): declared['meaning']
                  for declare in _FAMILY_SOURCE_FUNCTIONS for source, declared in declare().items()
                  if declared['type'] == 'array'}

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources got a usable handoff and which launches ran', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources received from the launch '
                                                   'children: the job identity, preserved across a return'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information (a '
                                            'usable handoff was received); yielding alone is false'),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                                  'acquires no results', required=False),
    'execution_file_source_refs': Field('record_refs', 'Source references of retained local file streams: none, a '
                                                       'launch acquires no results', required=False),
    'execution_file_capture_outcomes': Field('list', 'Recorded selected-file availability: always empty here',
                                             required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements of acquired HSPs: '
                                          'none for a launch', required=False),
    'execution_blast_pairwise_result_refs': Field('list', 'BLAST pairwise result references: none for a launch',
                                                  required=False),
    **{name: Field('list', meaning, required=False) for name, meaning in FAMILY_SOURCES.items()},
})


def facts(summary):
    """The facts a parent may select: the handoff references and whether one was received; every result source is
    empty."""
    recorded = {'execution_handoff_refs': sorted(summary['handoff_refs']),
                'execution_completed': bool(summary['handoff_resources']),
                'execution_result_refs': [], 'execution_file_source_refs': [], 'execution_file_capture_outcomes': [],
                'execution_blast_hsps': [], 'execution_blast_pairwise_result_refs': []}
    recorded.update({name: [] for name in FAMILY_SOURCES})
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
