"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the selected
table or window to read), the commissioned literature task, the proposed annotation, the structure components
requested, the Store scope of the commission and the records passed in custody.

``version``, ``page``, ``selection``, ``literature_task``, ``proposed_annotation_ref`` and
``requested_structure_components`` are the old assignment's properties under their names (old ``from_parent.py``
``assignment_schema``). ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from
its request and the records it received from its binding context; the new commission names both.

The old ``selection`` was ``anyOf`` a table selector (``source_ref``, ``sheet_key``, ``offset``, ``limit``,
``header_row``, ``where``) or a byte window (``source_ref``, ``representation``, ``offset``, ``limit``). A form has
no union and no null, so ``selection`` is one untyped ``record`` field and ``read_from_parent`` checks its exact
shape (new form detail: the old schema did it)."""
from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The table or window of that source to investigate: either a table selector '
                       '{source_ref, sheet_key, offset (0 or more), limit (0 or more), header_row (null or 1 or '
                       'more), where (null or {column (null or capital letters), match (equals or contains), '
                       'value, case_sensitive})} or a byte window {source_ref, representation, offset (0 or '
                       'more), limit (1 or more)}'),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads or '
                             'source_answer), evidence_axis, credit_unit and, for a source answer, answer_kind '
                             'with its source_refs (assessment) or examined spans (screening)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'requested_structure_components': Field('list', 'The structure components the parent requests (the old '
                                            'requested_structure_components; used by the structure population '
                                            'route, which is not built)', required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody (new field: old binding-context '
                                  'received records)'),
})

TASK_KINDS = ('verified_source_leads', 'source_answer')
ANSWER_KINDS = ('assessment', 'screening')
TABLE_KEYS = {'source_ref', 'sheet_key', 'offset', 'limit', 'header_row', 'where'}
WHERE_KEYS = {'column', 'match', 'value', 'case_sensitive'}
WINDOW_KEYS = {'source_ref', 'representation', 'offset', 'limit'}


def task_key(task):
    """The old ``_task_key``: ``<axis>:<kind>`` and, for a source answer, ``:<answer_kind>``."""
    name = task['kind']
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def natural(value, minimum):
    return type(value) is int and value >= minimum


def text(value):
    return type(value) is str and bool(value.strip())


def check_where(where):
    """The old ``_TABLE`` schema's ``where``: null, or exactly column, match, value and case_sensitive."""
    if where is None:
        return
    if not isinstance(where, dict) or set(where) != WHERE_KEYS:
        raise ValueError('literature_table_selection_invalid')
    column = where['column']
    if column is not None and not (type(column) is str and column.isascii() and column.isalpha()
                                   and column == column.upper()):
        raise ValueError('literature_table_selection_invalid')
    if where['match'] not in ('equals', 'contains') or not text(where['value']) \
            or type(where['case_sensitive']) is not bool:
        raise ValueError('literature_table_selection_invalid')


def check_selection(selection, page):
    """The selection is exactly a table selector or a window, and names the page's source (the old
    ``_validate_assignment`` checks that need no Store)."""
    if not isinstance(selection, dict):
        raise ValueError('literature_reading_selection_invalid')
    if set(selection) == TABLE_KEYS:
        header = selection['header_row']
        if not (text(selection['source_ref']) and text(selection['sheet_key']) and natural(selection['offset'], 0)
                and natural(selection['limit'], 0) and (header is None or natural(header, 1))):
            raise ValueError('literature_table_selection_invalid')
        check_where(selection['where'])
    elif set(selection) == WINDOW_KEYS:
        if not (text(selection['source_ref']) and selection['representation'] in REPRESENTATIONS
                and natural(selection['offset'], 0) and natural(selection['limit'], 1)):
            raise ValueError('literature_reading_window_out_of_range')
    else:
        raise ValueError('literature_reading_selection_invalid')
    if selection['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if 'representation' in selection and selection['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')


def read_from_parent(assignment, message):
    """The parent input: the page, the selection, the task, the proposed annotation, the scope and the passed
    records, the selection checked against the page (the old assignment validation that needs no Store)."""
    page, selection = assignment['page'], assignment['selection']
    check_selection(selection, page)
    task = assignment['literature_task']
    if task.get('kind') not in TASK_KINDS or (task['kind'] == 'source_answer'
                                              and task.get('answer_kind') not in ANSWER_KINDS):
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not unit > 0 or unit == float('inf'):
        raise ValueError('literature_finite_task_credit_unit_required')
    return {'page': page, 'selection': selection, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'requested_structure_components': assignment.get('requested_structure_components'),
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
