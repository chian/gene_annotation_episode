"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources got a usable handoff and which launches ran). Every fact of the ``launch`` role is a selectable field:
``execution_handoff_refs`` and ``execution_completed`` (what the parent selects to preserve the original job identity
across a return), the result, file and hsp sources, the pairwise and Infernal result references,
``bvbrc_appservice_support_refs``, and the native result family sources of the readers. A launch acquires no results:
every family source and the result, file and hsp sources are empty for it, and ``execution_result_origin`` is the
empty record. The 21 masking (``execution.masking_*``) and BLAST utility (``execution.blast_utility_*``) sources have
dotted names, which a field name cannot carry. The object-typed native family sources are
not fields."""
import re

from method_loop import Field, RecordForm

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
})

_FAMILY_SOURCE_FUNCTIONS = (native_hmmer_fact_sources, standard_blast_database_fact_sources,
                            native_blast_database_fact_sources, preparation_fact_sources, native_blast_fact_sources,
                            rna_structure_fact_sources, rna_comparison_fact_sources, expression_nmf_fact_sources)
# The sources whose names contain a dot: no field can carry them.
DOTTED_SOURCES = frozenset(masking_fact_sources()) | frozenset(blast_utility_fact_sources())
_IDENTIFIER = re.compile(r'^[a-z][a-z0-9_]*$')


def _family_sources():
    """The native result family sources of this role by name: ``(meaning, type, report schema)`` for every
    source whose name a form can carry."""
    found = {}
    for declare in _FAMILY_SOURCE_FUNCTIONS:
        for name, declared in declare().items():
            if _IDENTIFIER.fullmatch(name) and declared['type'] != 'object':
                found[name] = (declared.get('meaning', name), declared['type'], declared.get('report_schema'))
    return found


FAMILY_SOURCES = _family_sources()

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources got a usable handoff and which launches ran', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources received from the launch '
                                                   'children: the job identity, preserved across a return',
                                    required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information (a '
                                            'usable handoff was received); yielding alone is false',
                                 required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                                  'acquires no results', required=False),
    'execution_file_source_refs': Field('record_refs', 'Source references of retained local file streams: none, a '
                                                       'launch acquires no results', required=False),
    'execution_file_capture_outcomes': Field('list', 'Recorded selected-file availability: always empty here',
                                             required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results: the empty '
                                               'record, a launch retains none', required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements of acquired HSPs: '
                                          'none for a launch', required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'BLAST pairwise result references: none for a '
                                                                  'launch', required=False),
    'execution_infernal_result_refs': Field('record_refs', 'Infernal result references: none for a launch',
                                            required=False),
    'bvbrc_appservice_support_refs': Field('record_refs', 'Actually received BV-BRC AppService support receipts '
                                                          '(no launch child returns any)', required=False),
    **{name: Field('list', meaning, required=False)
       for name, (meaning, kind, _) in FAMILY_SOURCES.items()},
})


def facts(summary):
    """The facts a parent may select, from the summary: the handoff references and whether one was
    received; every result source is empty."""
    recorded = {'execution_handoff_refs': sorted(summary['handoff_refs']),
                'execution_completed': bool(summary['handoff_resources']),
                'execution_result_refs': [], 'execution_file_source_refs': [], 'execution_file_capture_outcomes': [],
                'execution_blast_hsps': [], 'execution_blast_pairwise_result_refs': [],
                'execution_infernal_result_refs': [], 'execution_result_origin': {},
                'bvbrc_appservice_support_refs': []}
    recorded.update({name: [] for name, (_, kind, _) in FAMILY_SOURCES.items()})
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
                                       for launch in summary['launches']]}}
    for name in selection:
        result[name] = recorded[name]
    return result
