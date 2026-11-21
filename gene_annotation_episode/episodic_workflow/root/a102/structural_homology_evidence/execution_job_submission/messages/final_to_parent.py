"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources handed off and whether each handoff is verified complete). Selectable: ``execution_handoff_refs``,
``execution_result_refs``, ``execution_completed``, ``execution_result_origin``, ``execution_file_source_refs``,
``execution_file_capture_outcomes`` and the four protein-structure fact sources (``execution_protein_structure_*``).
A launch acquires no results: every source except the handoff references and the completion is empty, and
``execution_result_origin`` is the empty record."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.structural_homology_evidence.protein_structure_result_views import (
    protein_structure_fact_sources)

HANDOFF_SOURCE = 'execution_handoff_refs'
RESULT_SOURCE = 'execution_result_refs'
COMPLETED_SOURCE = 'execution_completed'
ORIGIN_SOURCE = 'execution_result_origin'
FILE_SOURCES = 'execution_file_source_refs'
FILE_OUTCOMES = 'execution_file_capture_outcomes'
PROTEIN_SOURCES = tuple(protein_structure_fact_sources())

COMMISSION_FORM = RecordForm({
    'resource_id': Field('text', 'The resource the request was commissioned on'),
    'slot': Field('text', 'The resource child that carried it out: launch_api, launch_local or launch_hpc'),
    'handoff_established': Field('boolean', 'Whether the child returned a usable handoff'),
    'completed': Field('boolean', 'Whether the child verified the handoff completion'),
})
FINDING_FORM = RecordForm({
    'commissions': Field('list', 'Each commissioned request in order: the resource, the child and what it returned',
                         items=COMMISSION_FORM),
    'handoff_resource_ids': Field('list', 'The resources with a usable received handoff'),
    'new_handoff_count': Field('integer', 'How many of them were not already handed off at the commission'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources handed off the commissioned execution requests',
                     form=FINDING_FORM),
    HANDOFF_SOURCE: Field('record_refs', 'Authenticated original execution handoffs available to this episode.',
                          required=False),
    RESULT_SOURCE: Field('record_refs', 'Actual requested A102 result acquisitions available to this episode: '
                         'none, a launch acquires no results.', required=False),
    COMPLETED_SOURCE: Field('boolean', 'Whether the assigned A102 endpoint has verified completion information.',
                            required=False),
    ORIGIN_SOURCE: Field('record', 'Acquisition semantics of a retained A102 result (the empty record: a launch '
                         'retains no result)', required=False),
    FILE_SOURCES: Field('record_refs', 'Selected local file sources retained by this episode (none: a launch '
                        'retains no file)', required=False),
    FILE_OUTCOMES: Field('list', 'Selected file availability, status and custody qualifications (empty: a launch '
                         'acquires no file)', required=False),
    **{name: Field('list', protein_structure_fact_sources()[name]['meaning'] + ' (empty: a launch acquires no '
                   'result)', required=False) for name in PROTEIN_SOURCES},
})


def facts(summary):
    """The facts a parent may select."""
    return {HANDOFF_SOURCE: list(summary['handoff_refs']), RESULT_SOURCE: [],
            COMPLETED_SOURCE: summary['completed'], ORIGIN_SOURCE: {}, FILE_SOURCES: [], FILE_OUTCOMES: [],
            **{name: [] for name in PROTEIN_SOURCES}}


def final_to_parent(summary, completion, selection):
    finding = {'commissions': [{'resource_id': commission['resource_id'], 'slot': commission['slot'],
                                'handoff_established': bool(commission['handoff_refs']),
                                'completed': commission['completed']}
                               for commission in summary['commissions']],
               'handoff_resource_ids': list(summary['handed_off']),
               'new_handoff_count': len(summary['new_handoff_resource_ids'])}
    recorded = facts(summary)
    result = {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
    return result
