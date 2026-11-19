"""What the parent gives: the page assignment ``page_assignment_v1`` (the one source to examine, the representation
and its artifact, the records that give the question its context and the records earlier readings delivered), the
Store scope of the commission, the unit of finding credit and the records passed in custody. This is the only
place the assignment is read.

``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs`` and
``prior_delivery_refs`` are the old assignment's properties under their names (old ``from_parent.py``
``assignment_schema`` = ``_PAGE`` of ``contracts.py``; the assignment is the page). ``requested_reaction_components`` is
the old ``literature_component_binding.assignment_schema_fields()`` property (the requested reaction cells); this
episode selects its reaction lead by it (R10) and passes it to its children. The requested native positions were a
return view of native observations, which no controlled return carries; they are not declared. ``scope``, ``received_record_refs`` and ``finding_unit`` are new fields: the old
episode took the scope from its request, the records it received from its binding context and its credit unit from
the old ``services.scientific_credit``. The old checks against the Store (``source_custody._validate_page``: the
artifact of the representation, the records in scope) are checks of a commission and are not carried."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.biochemical_feasibility_evidence.literature_reaction_calculations import (
    COMPONENTS)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The one source to examine'),
    'representation': ChoiceField('text', 'The representation of the source that is examined', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier examinations of this source'),
    'requested_reaction_components': SubsetField('text', 'The reaction cells the parent requests graded from this '
                                                 'source', COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding; positive (new field: the unit '
                          'of the old scientific credit)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'records that give the question its context, passed in custody (new field: old '
                                  'binding-context received records)'),
})
PAGE_KEYS = ('version', 'source_ref', 'representation', 'artifact_ref', 'question_context_refs',
             'prior_delivery_refs')


def read_from_parent(assignment, message):
    """The parent input: the page, the scope, the unit and the passed records."""
    unit = assignment['finding_unit']
    if not math.isfinite(unit) or not unit > 0:
        raise ValueError('explicit_positive_finding_unit_required')
    return {'page': {key: assignment[key] for key in PAGE_KEYS},
            'requested_reaction_components': (list(assignment['requested_reaction_components'])
                                              if 'requested_reaction_components' in assignment else []),
            'scope': assignment['scope'],
            'finding_unit': unit, 'received_record_refs': assignment['received_record_refs'], 'message': message}
