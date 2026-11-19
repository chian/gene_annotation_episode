"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and its table or
sheet, or one byte window, to read), the commissioned literature task, the proposed annotation, the requested
components of the cell families this episode returns, the Store scope of the commission and the records passed in
custody. This is the only place the assignment is read.

The three ``requested_*_components`` arrays are the old assignment's properties of the cell families this episode
returns (``requested_assay_grading_components`` and ``requested_a105_aggregation_components`` of the assay-grading
population, ``requested_quantity_components`` of the quantity population), under their old names.

``version``, ``page``, ``selection``, ``literature_task`` and ``proposed_annotation_ref`` are the old assignment's
properties under their names (old ``from_parent.py`` ``assignment_schema`` and ``assignment_fields.py``).
``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its request and the
records it received from its binding context; the new commission names both. The old rate-population properties
(``requested_*_components``, ``requested_*_views``, ``requested_*_component_keys``) belong to the population route,
of the other families, which is not built: a commission that sends one is refused by this form."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (
    COMPONENTS as ASSAY_GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import (
    COMPONENTS as QUANTITY_COMPONENTS)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
REQUESTED_ASSAY_GRADING = 'requested_assay_grading_components'
REQUESTED_AGGREGATION = 'requested_a105_aggregation_components'
REQUESTED_QUANTITY = 'requested_quantity_components'
REQUESTED = (REQUESTED_ASSAY_GRADING, REQUESTED_AGGREGATION, REQUESTED_QUANTITY)

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
WHERE_FORM = RecordForm({
    'column': Field('text', 'The sheet column letters (A-Z) the literal value is matched in; omitted: any column',
                    required=False),
    'match': ChoiceField('text', 'How the value is matched', ('equals', 'contains')),
    'value': Field('text', 'The literal cell value'),
    'case_sensitive': Field('boolean', 'Whether the match is case sensitive', required=False),
})
# The old selection was one of two records: a table selection (source_ref, sheet_key, offset, limit, header_row,
# optional where) or a window selection (source_ref, representation, offset, limit). A form has no union, so one
# record declares every property; ``read_from_parent`` admits exactly one of the two shapes.
SELECTION_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the table or window; the page source'),
    'sheet_key': Field('text', 'Table selection: the XLSX sheet key (from source.xlsx.sheets); absent for a window',
                       required=False),
    'header_row': Field('integer', 'Table selection: the 1-based header row; omitted: no header row',
                        required=False),
    'where': Field('record', 'Table selection: rows matching one literal cell value (optional)', form=WHERE_FORM,
                   required=False),
    'representation': ChoiceField('text', 'Window selection: the representation the offsets count in',
                                  REPRESENTATIONS, required=False),
    'offset': Field('integer', 'First row (table selection) or first byte (window selection), 0 or more'),
    'limit': Field('integer', 'Rows (table selection) or bytes (window selection) selected'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The table or sheet of that source to investigate (sheet_key, offset, limit, '
                       'header_row, optional where), or one byte window (representation, offset, limit)',
                       form=SELECTION_FORM),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads, '
                             'source_answer, a105_experiments or a105_assembly), evidence_axis, credit_unit and, '
                             'for a source answer, answer_kind with its source_refs (assessment), examined spans '
                             '(screening) or selection and components (measurement); for a105_experiments the experiments '
                             '(experiment_ref, assay_type), for a105_assembly the experiment_refs and metrics'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    REQUESTED_ASSAY_GRADING: SubsetField('text', 'The assay-grading components the parent wants returned',
                                         ASSAY_GRADING_COMPONENTS, required=False),
    REQUESTED_AGGREGATION: SubsetField('text', 'The A105 aggregation components the parent wants returned',
                                       AGGREGATION_COMPONENTS, required=False),
    REQUESTED_QUANTITY: SubsetField('text', 'The quantity components the parent wants returned',
                                    QUANTITY_COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from, the '
                                  'proposed annotation and the records of the commissioned task, passed in '
                                  'custody (new field: old binding-context received records)'),
})

TASK_KINDS = ('verified_source_leads', 'source_answer', 'a105_experiments', 'a105_assembly')
ANSWER_KINDS = ('assessment', 'screening', 'measurement')


def task_key(task):
    """The old ``_task_key``: ``<axis>:<name>`` where the name is the kind (``a105_experiments`` is
    ``experiments``, ``a105_assembly`` is ``assembly``) and, for a source answer, ``:<answer_kind>`` follows."""
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def read_from_parent(assignment, message):
    """The parent input: the page, the spans, the task, the proposed annotation, the scope and the passed records,
    each span checked against the page (the old assignment validation that needs no Store)."""
    page, selection = assignment['page'], assignment['selection']
    if selection['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if selection['offset'] < 0:
        raise ValueError('literature_reading_window_out_of_range')
    if 'sheet_key' in selection:
        if 'representation' in selection or not selection['sheet_key'].strip():
            raise ValueError('literature_reading_selection_shape_invalid')
        if selection['limit'] < 0 or selection.get('header_row', 1) < 1:
            raise ValueError('literature_reading_window_out_of_range')
    else:
        if 'header_row' in selection or 'where' in selection or 'representation' not in selection:
            raise ValueError('literature_reading_selection_shape_invalid')
        if selection['representation'] != page['representation']:
            raise ValueError('literature_reading_representation_mismatch')
        if selection['limit'] < 1:
            raise ValueError('literature_reading_window_out_of_range')
    task = assignment['literature_task']
    if task.get('kind') not in TASK_KINDS or (task['kind'] == 'source_answer'
                                              and task.get('answer_kind') not in ANSWER_KINDS):
        raise ValueError('literature_original_task_invalid')
    if task.get('evidence_axis') != 'A105':
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    if task['kind'] == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if not experiments or len(set(experiments)) != len(experiments):
            raise ValueError('literature_task_duplicate_experiment')
    return {'page': page, 'selection': selection, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'requested': {name: assignment[name] for name in REQUESTED if name in assignment},
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
