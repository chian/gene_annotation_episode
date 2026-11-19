"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the table or
window to investigate), the Store scope of the commission, the unit of finding credit and the records passed in
custody. This is the only place the assignment is read.

``version``, ``page`` and ``selection`` are the old assignment's properties under their names (old ``from_parent.py``
``assignment_schema``, ``_PAGE``, ``_TABLE`` and ``_WINDOW`` of ``contracts.py``). The old ``selection`` was
``anyOf [table, window]``; a form has no union, so ``kind`` names which one it is and the fields of the other are
omitted (new field: ``kind``). ``header_row`` and ``where`` were nullable; here they are omitted when null. ``requested_reaction_components`` is
the old ``literature_component_binding.assignment_schema_fields()`` property (the requested reaction cells); its
presence selects the reaction lead (R10). The requested native positions were a return view of native observations,
which no controlled return carries; they are not declared.
``scope``, ``received_record_refs`` and ``finding_unit`` are new fields: the old episode took the scope from its
request, the records it received from its binding context and its credit unit from ``services.scientific_credit``."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.biochemical_feasibility_evidence.literature_reaction_calculations import (
    COMPONENTS)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
MATCHES = ('equals', 'contains')

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
WHERE_FORM = RecordForm({
    'column': Field('text', 'The column letters the literal is matched in (A-Z); omitted for every column',
                    required=False),
    'match': ChoiceField('text', 'How the literal is matched', MATCHES),
    'value': Field('text', 'The literal'),
    'case_sensitive': Field('boolean', 'Whether the match is case sensitive'),
})
SELECTION_FORM = RecordForm({
    'kind': ChoiceField('text', 'Whether the selection is a table (an XLSX sheet) or a window of the source',
                        ('table', 'window')),
    'source_ref': Field('text', 'The source of the selection; the page source'),
    'offset': Field('integer', 'First row (table) or first byte (window), 0 or more'),
    'limit': Field('integer', 'Rows (table, 0 or more) or bytes (window, 1 or more)'),
    'sheet_key': Field('text', 'The sheet of the table selection', required=False),
    'header_row': Field('integer', 'The header row of the table selection (1 or more); omitted for none',
                        required=False),
    'where': Field('record', 'The row filter of the table selection; omitted for none', required=False,
                   form=WHERE_FORM),
    'representation': ChoiceField('text', 'The representation the offsets of a window count in', REPRESENTATIONS,
                                  required=False),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The table or window of that source to investigate', form=SELECTION_FORM),
    'requested_reaction_components': SubsetField('text', 'The reaction cells the parent requests graded from this '
                                                 'table', COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding; positive (new field: the unit '
                          'of the old scientific credit)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'records that give the question its context, passed in custody (new field: old '
                                  'binding-context received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the page, the selection, the scope, the unit and the passed records, the selection
    checked against the page (the old ``_validate_assignment`` checks that need no Store)."""
    page, selection = assignment['page'], assignment['selection']
    if selection['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if selection['offset'] < 0:
        raise ValueError('literature_reading_offset_out_of_range')
    if selection['kind'] == 'table':
        if 'sheet_key' not in selection:
            raise ValueError('literature_table_selection_requires_sheet_key')
        if 'representation' in selection:
            raise ValueError('literature_table_selection_has_no_representation')
        if selection['limit'] < 0:
            raise ValueError('literature_reading_limit_out_of_range')
        if 'header_row' in selection and selection['header_row'] < 1:
            raise ValueError('literature_table_header_row_out_of_range')
    else:
        if 'representation' not in selection or {'sheet_key', 'header_row', 'where'} & set(selection):
            raise ValueError('literature_window_selection_takes_a_representation_and_no_table_fields')
        if selection['representation'] != page['representation']:
            raise ValueError('literature_reading_representation_mismatch')
        if selection['limit'] < 1:
            raise ValueError('literature_reading_window_out_of_range')
    unit = assignment['finding_unit']
    if not math.isfinite(unit) or not unit > 0:
        raise ValueError('explicit_positive_finding_unit_required')
    return {'page': page, 'selection': selection,
            'requested_reaction_components': (list(assignment['requested_reaction_components'])
                                              if 'requested_reaction_components' in assignment else []),
            'scope': assignment['scope'], 'finding_unit': unit,
            'received_record_refs': assignment['received_record_refs'], 'message': message}
