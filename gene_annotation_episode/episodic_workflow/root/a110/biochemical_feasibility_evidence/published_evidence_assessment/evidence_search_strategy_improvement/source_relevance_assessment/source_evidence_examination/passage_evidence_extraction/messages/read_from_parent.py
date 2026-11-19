"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the spans to
read), the Store scope of the commission, the unit of finding credit and the records passed in custody. This is the
only place the assignment is read.

``version``, ``page`` and ``selection`` are the old assignment's properties under their names (old ``from_parent.py``
``assignment_schema``, ``_PAGE`` and ``_WINDOW`` of ``contracts.py``). ``requested_reaction_components`` is the old
``literature_component_binding.assignment_schema_fields()`` property (the requested reaction cells); its presence
selects the reaction lead (R10). The requested native positions were a return view of native observations, which no
controlled return carries; they are not declared. ``scope``, ``received_record_refs`` and ``finding_unit`` are new fields: the old episode took
the scope from its request, the records it received from its binding context and its credit unit from the old
``services.scientific_credit``."""
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
    'source_ref': Field('text', 'The source of the passage; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the passage (0 or more)'),
    'limit': Field('integer', 'Bytes of the passage (1 or more)'),
})
SELECTION_FORM = RecordForm({
    'spans': Field('list', 'The passages to investigate: one or more windows', items=WINDOW_FORM),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The passages of that source to investigate', form=SELECTION_FORM),
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
    """The parent input: the page, the spans, the scope, the unit and the passed records, each span checked against
    the page (the old ``_validate_assignment`` checks that need no Store)."""
    page, spans = assignment['page'], assignment['selection']['spans']
    if not spans:
        raise ValueError('reading_assignment_requires_a_span')
    for window in spans:
        if window['source_ref'] != page['source_ref']:
            raise ValueError('literature_reading_source_mismatch')
        if window['representation'] != page['representation']:
            raise ValueError('literature_reading_representation_mismatch')
        if window['offset'] < 0 or window['limit'] < 1:
            raise ValueError('literature_reading_window_out_of_range')
    unit = assignment['finding_unit']
    if not math.isfinite(unit) or not unit > 0:
        raise ValueError('explicit_positive_finding_unit_required')
    return {'page': page, 'spans': spans,
            'requested_reaction_components': (list(assignment['requested_reaction_components'])
                                              if 'requested_reaction_components' in assignment else []),
            'scope': assignment['scope'], 'finding_unit': unit,
            'received_record_refs': assignment['received_record_refs'], 'message': message}
