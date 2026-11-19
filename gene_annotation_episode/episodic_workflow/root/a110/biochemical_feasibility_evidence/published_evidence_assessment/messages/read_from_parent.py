"""What the parent gives: the literature assignment ``literature_assignment_v1`` (the records that give the question
its context and the sources to investigate), the Store scope of the commission, the unit of finding credit and the
records passed in custody. This is the only place the assignment is read.

``version``, ``question_context_refs`` and ``source_refs`` are the old assignment's properties under their names
(old ``from_parent.py`` ``assignment_schema``). ``requested_reaction_components`` is the old
``literature_component_binding.assignment_schema_fields()`` property (the requested reaction cells); this episode
selects its reaction lead by it (R10) and passes it to its child. The requested native positions were a return view
of native observations, which no controlled return carries; they are not declared. ``scope``, ``received_record_refs`` and ``finding_unit`` are new fields: the old
episode took the scope from its request, the records it received from its binding context and its credit unit from
the old ``services.scientific_credit``. The old checks of a commission against the Store (every ``*_refs`` entry in
scope, ``source_refs`` of kind source) and the non-empty operation key are checks of a commission and are not
carried."""
import math

from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.biochemical_feasibility_evidence.literature_reaction_calculations import (
    COMPONENTS)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The literature assignment version', 'literature_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'source_refs': Field('record_refs', 'The source records to investigate'),
    'requested_reaction_components': SubsetField('text', 'The reaction cells the parent requests graded', COMPONENTS,
                                                 required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding; positive (new field: the unit '
                          'of the old scientific credit)'),
    'received_record_refs': Field('record_refs', 'The sources, their artifacts, the sources they derive from and '
                                  'the records that give the question its context, passed in custody (new field: '
                                  'old binding-context received records)'),
})
ASSIGNMENT_KEYS = ('version', 'question_context_refs', 'source_refs')


def read_from_parent(assignment, message):
    """The parent input: the assignment, the scope, the unit and the passed records."""
    unit = assignment['finding_unit']
    if not math.isfinite(unit) or not unit > 0:
        raise ValueError('explicit_positive_finding_unit_required')
    return {'assignment': {key: assignment[key] for key in ASSIGNMENT_KEYS},
            'requested_reaction_components': (list(assignment['requested_reaction_components'])
                                              if 'requested_reaction_components' in assignment else []),
            'scope': assignment['scope'],
            'finding_unit': unit, 'received_record_refs': assignment['received_record_refs'], 'message': message}
