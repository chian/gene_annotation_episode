"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources got a usable handoff and which launches ran). A parent selects ``execution_handoff_refs`` and
``execution_completed`` (what it selects to preserve the original job identity across a return), the result-side
facts and the native result families of the readers. A launch acquires no results: every result-side fact and every
family is empty for it, and ``execution_result_origin`` is ``{'retained': False}``."""
import re

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.\
    gene_context_evidence.hmmer_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.\
    gene_context_evidence.bvbrc_data_views import bvbrc_data_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.blast_pairwise_result_views import native_blast_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.bvbrc_minhash_views import minhash_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.hmmer_native_result_views import native_hmmer_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.native_blast_database_result_views import native_blast_database_fact_sources
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.\
    gene_context_evidence.native_blast_standard_database_result_views import standard_blast_database_fact_sources

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
                            bvbrc_data_fact_sources, minhash_fact_sources)
_IDENTIFIER = re.compile(r'^[a-z][a-z0-9_]*$')


def _family_sources():
    """The native result families of this role by name with their meaning: every family whose name a form can
    carry and whose value is a list."""
    found = {}
    for declare in _FAMILY_SOURCE_FUNCTIONS:
        for name, declared in declare().items():
            if _IDENTIFIER.fullmatch(name) and declared['type'] == 'array':
                found[name] = declared['meaning']
    return found


FAMILY_SOURCES = _family_sources()

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources got a usable handoff and which launches ran', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources received from the launch '
                                                   'children, including authenticated original failed native '
                                                   'database attempts for partial-output acquisition: the job '
                                                   'identity, preserved across a return; a failed attempt does not '
                                                   'establish a successful endpoint', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information (a '
                                            'usable handoff was received); yielding alone is false',
                                 required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                                  'acquires no results', required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results: none is retained '
                                               'by a launch', required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements of acquired HSPs: '
                                          'none for a launch', required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'Native BLAST pairwise result references: none for '
                                                                  'a launch', required=False),
    **{name: Field('list', meaning, required=False) for name, meaning in FAMILY_SOURCES.items()},
})


def facts(summary):
    """The facts of a launch, from the summary: the handoff references and whether one was received; every
    result-side fact and every family is empty."""
    recorded = {'execution_handoff_refs': sorted(summary['handoff_refs']),
                'execution_completed': bool(summary['handoff_resources']),
                'execution_result_refs': [], 'execution_result_origin': {'retained': False},
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
                                            'establish that no job was created')}}
    for name in selection:
        result[name] = recorded[name]
    return result
