"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the one
window to read first), the reaction components the parent requests, the Store scope of the commission, the unit of
finding credit and the records passed in custody. This is the only place the assignment is read.

``version``, ``page`` and ``selection`` are the old assignment's properties under their names (old ``from_parent.py``
``assignment_schema``, ``_PAGE`` and ``_WINDOW`` of ``contracts.py``; this episode's selection is one window only).
``requested_reaction_components`` is the old ``literature_component_binding.assignment_schema_fields()`` property
(the requested reaction cells, a subset of the fifteen components); its presence selects the reaction lead
(``literature_reaction_instructions.selected_family``, R10). The requested native positions of the same old
schema were a return view of native observations, which no controlled return carries; they are not declared.
``scope``, ``received_record_refs`` and ``finding_unit`` are new fields: the old episode took the scope from its
request, the records it received from its binding context and its credit unit from the old
``services.scientific_credit``. The old checks against the Store (``source_offset_out_of_bounds``, the page custody
of ``source_custody._validate_page``, the containment in the parent's source of ``prepare_assignment``) are checks
of a commission and are not carried."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.biochemical_feasibility_evidence.literature_reaction_calculations import (
    COMPONENTS)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the window; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the window (0 or more)'),
    'limit': Field('integer', 'Bytes of the window (1 or more)'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The window of that source the ordered reading starts from', form=WINDOW_FORM),
    'requested_reaction_components': SubsetField('text', 'The reaction cells the parent requests graded from this '
                                                 'source', COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding; positive (new field: the unit '
                          'of the old scientific credit)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'records that give the question its context, passed in custody (new field: old '
                                  'binding-context received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the page, the window, the requested reaction cells (empty when none), the scope, the unit
    and the passed records, the window checked against the page (the old ``_validate_assignment`` checks that need
    no Store)."""
    page, window = assignment['page'], assignment['selection']
    if window['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if window['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    if window['offset'] < 0 or window['limit'] < 1:
        raise ValueError('literature_reading_window_out_of_range')
    unit = assignment['finding_unit']
    if not math.isfinite(unit) or not unit > 0:
        raise ValueError('explicit_positive_finding_unit_required')
    return {'page': page, 'window': window,
            'requested_reaction_components': (list(assignment['requested_reaction_components'])
                                              if 'requested_reaction_components' in assignment else []),
            'scope': assignment['scope'], 'finding_unit': unit,
            'received_record_refs': assignment['received_record_refs'], 'message': message}
