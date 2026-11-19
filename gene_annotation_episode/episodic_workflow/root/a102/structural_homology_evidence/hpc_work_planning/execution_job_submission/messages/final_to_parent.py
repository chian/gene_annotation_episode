"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources handed off and whether each handoff is verified complete). Selectable: ``execution_handoff_refs``,
``execution_result_refs``, ``execution_completed``, ``execution_result_origin``, ``execution_file_source_refs``,
``execution_file_capture_outcomes`` and the four protein-structure fact sources. A launch acquires no results:
every source except the handoff references and the completion is empty, and ``execution_result_origin`` is the
empty record."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.structural_homology_evidence.protein_structure_result_views import (
    protein_structure_fact_sources)

PROTEIN_FACT_SOURCES = tuple(protein_structure_fact_sources())

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
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources handed off the commissioned execution requests',
                     form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The usable handoff records received from the resource '
                                    'children', required=False),
    'execution_result_refs': Field('record_refs', 'Actual requested result acquisitions: none, a launch acquires '
                                   'no results', required=False),
    'execution_completed': Field('boolean', 'Whether any received handoff is verified complete', required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of a retained result (the empty record: a launch '
                                     'retains no result)', required=False),
    'execution_file_source_refs': Field('record_refs', 'Selected local file sources retained (none)',
                                        required=False),
    'execution_file_capture_outcomes': Field('list', 'Selected file availability and custody qualifications '
                                             '(none)', required=False),
    **{name: Field('list', 'A protein-structure result fact source (empty: a launch acquires no results)',
                   required=False) for name in PROTEIN_FACT_SOURCES},
})


def facts(summary):
    """The facts a parent may select."""
    return {'execution_handoff_refs': list(summary['handoff_refs']), 'execution_result_refs': [],
            'execution_completed': summary['completed'], 'execution_result_origin': {},
            'execution_file_source_refs': [], 'execution_file_capture_outcomes': [],
            **{name: [] for name in PROTEIN_FACT_SOURCES}}


def final_to_parent(summary, completion, selection):
    finding = {'commissions': [{'resource_id': commission['resource_id'], 'slot': commission['slot'],
                                'handoff_established': bool(commission['handoff_refs']),
                                'completed': commission['completed']}
                               for commission in summary['commissions']],
               'handoff_resource_ids': list(summary['handed_off']),
               'new_handoff_count': len(summary['new_handoff_resource_ids']),
               'qualification': ('a handoff is usable when its resource child returned handoff references; the '
                                 'record itself is not re-read here, and no result was acquired')}
    recorded = facts(summary)
    result = {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
    return result
