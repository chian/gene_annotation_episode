"""The one implementation shared by the seven A105 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py``. It declares only what differs between the seven roles:

- ``binding_path``, ``role`` and ``commissioning_parent``;
- ``child_role_names``: the literature roles it may commission;
- ``instruction``: its role-specific investigation instruction;
- ``acquisition``: whether it may use the public literature and experiment-database acquisition tools;
- ``assignment_shape``: the form of its commissioned assignment
  (``('question', version, refs_field)``, ``('page',)`` or ``('reading', selection)``).

Everything else (the episode_runtime hooks, the assignment check, the
commissioned task and typed report, credit, continuation and the decision
source ``literature_source.LiteratureSource``) is here and in
``literature_credit`` / ``literature_source`` / ``literature_populations``, once.

Construction (``create_binding_tree`` in ``published_evidence_assessment/episode.py``)
gives each binding its own tool registry over the run's shared store, its
declared ``yield_bindings`` (one per commissioned task kind), the
``outcome_page_size`` of its own-outcome presentation and its declared optional
``populations``; nothing is defaulted.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from types import MappingProxyType

from episode_runtime import Commission, Field, RecordForm
from method_loop import EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import REF, obj, plain, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.experimental_activity_evidence.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS
from ..runtime_binding import AXIS, REPORT_CONTRACT, ROLE_PATHS, A105Record, EpisodeRuntimeContract
from .literature_credit import (commissioned_task, task_controller, task_schema, task_sources, validate_commission,
                                validate_yield_bindings)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_populations import validate_populations

REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}
_REPRESENTATION = {'type': 'string', 'enum': ['text', 'original', 'stdout', 'stderr']}
_NATURAL = {'type': 'integer', 'minimum': 0}
_POSITIVE = {'type': 'integer', 'minimum': 1}
_TEXT = {'type': 'string', 'minLength': 1}
WINDOW = obj({'source_ref': REF, 'representation': _REPRESENTATION, 'offset': _NATURAL, 'limit': _POSITIVE})
TABLE = obj({'source_ref': REF, 'sheet_key': _TEXT, 'offset': _NATURAL, 'limit': _NATURAL,
             'header_row': {'type': ['integer', 'null'], 'minimum': 1},
             'where': {**obj({'column': {'type': ['string', 'null'], 'pattern': '^[A-Z]+$'},
                              'match': {'enum': ['equals', 'contains']}, 'value': _TEXT,
                              'case_sensitive': {'type': 'boolean'}}), 'type': ['object', 'null']}})
PAGE = obj({'version': {'const': 'page_assignment_v1'}, 'source_ref': REF, 'representation': _REPRESENTATION,
            'artifact_ref': REF, 'question_context_refs': REFERENCES, 'prior_delivery_refs': REFERENCES})
_SELECTIONS = MappingProxyType({
    'table': {'anyOf': [TABLE, WINDOW]},
    'window': WINDOW,
    'spans': obj({'spans': {'type': 'array', 'minItems': 1, 'items': WINDOW}}),
})
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.references',
                'source.experimental.records', 'source.archive.members', 'source.archive.extract',
                'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
                     *EXPERIMENT_DATABASE_TOOLS)
_PURPOSE = MappingProxyType({
    'literature': 'the commissioned literature answer for the A105 experimental-activity question',
    'literature_strategy': 'the evidence-search strategy for the commissioned A105 literature question',
    'literature_search': 'the set of sources judged relevant to the commissioned A105 question',
    'literature_page': 'the examined source evidence for the commissioned A105 question',
    'literature_table': 'the table evidence extracted from one examined source',
    'literature_ordered': 'the coverage of one examined source',
    'literature_targeted': 'the passage evidence extracted from one examined source',
})

_WITNESS_FORM = RecordForm({
    'source_ref': Field('text', 'The witnessed source'),
    'representation': Field('text', 'The witnessed representation'),
    'start': Field('integer', 'The witness start byte'),
    'end': Field('integer', 'The witness end byte'),
    'quote': Field('text', 'The exact witnessed quotation'),
})
_LEAD_FORM = RecordForm({
    'proposed_annotation_ref': Field('text', 'The commissioned question'),
    'source_ref': Field('text', 'The inspected source'),
    'subject_ref': Field('text', 'The anchored source subject'),
    'disposition': Field('text', 'relevant or not_relevant'),
    'relevance_rationale': Field('text', 'Why the witnessed subject bears on the question'),
    'witness': Field('record', 'The exact source witness', form=_WITNESS_FORM),
})
_SPAN_FORM = RecordForm({
    'source_ref': Field('text', 'The examined source'),
    'artifact_ref': Field('text', 'The examined artifact'),
    'start': Field('integer', 'The span start byte'),
    'end': Field('integer', 'The span end byte'),
})
_SCREENING_FORM = RecordForm({
    'proposed_annotation_ref': Field('text', 'The commissioned question'),
    'disposition': Field('text', 'no_applicable_evidence'),
    'examined': Field('list', 'Every requested span the screening covered', items=_SPAN_FORM),
    'annotation_support': Field('text', 'not_assessed'),
})
# The requested sheet cells a commissioning parent may ask for: requested field -> (returned cells field, form).
CELL_FIELDS = MappingProxyType({
    'requested_assay_grading_components': ('literature_assay_grading_cells', Field(
        'list', 'The requested cells of the A105 assay-grading subscoring sheets this commission holds')),
    'requested_a105_aggregation_components': ('literature_a105_aggregation_cells', Field(
        'list', 'The requested cells of the main A105 evidence sheets this commission holds')),
    'requested_quantity_components': ('literature_quantity_cells', Field(
        'list', 'The requested cells of the source quantity sheets this commission holds')),
})
# The typed answer a commissioning parent requests for each task.
ANSWER_FIELDS = MappingProxyType({
    'verified_source_leads': ('source_lead_dispositions', Field(
        'list', 'The latest disposition of each source verified for the question', items=_LEAD_FORM)),
    'assessment': ('changed_assessment_refs', Field(
        'list', 'The retained assessments of the question this commission holds')),
    'screening': ('screening_answers', Field(
        'list', 'The no-applicable-evidence answer over every requested span', items=_SCREENING_FORM)),
})
# A sheet answer is the requested cells of that sheet.
_SHEET_ANSWERS = MappingProxyType({'measurement': 'requested_quantity_components',
                                   'a105_experiments': 'requested_assay_grading_components',
                                   'a105_assembly': 'requested_a105_aggregation_components'})


def answer_requested(task):
    """The requested-components field whose cells answer a sheet task (``None`` for other tasks)."""
    return _SHEET_ANSWERS.get(task['kind'] if task['kind'] != 'source_answer' else task['answer_kind'])


def answer_field(task):
    requested = answer_requested(task)
    if requested is not None:
        return CELL_FIELDS[requested]
    return ANSWER_FIELDS[task['kind'] if task['kind'] == 'verified_source_leads' else task['answer_kind']]


def require_reference(store, reference, scope, namespace=None):
    """A record of this scope (of ``namespace`` when given); anything else raises."""
    if not isinstance(reference, str) or not store.reference_subset([reference], plain(scope)):
        raise ContractError('literature_reference_unavailable', detail={'reference': reference, 'namespace': namespace})
    record = store.get(reference)
    kind = record['record_type']
    if namespace and namespace != kind and not (namespace == 'subject'
                                                and kind in {'input', 'feature', 'product', 'read_subject'}):
        raise ContractError('literature_reference_unavailable', detail={'reference': reference, 'namespace': namespace})
    return record


def source_artifact(source, representation):
    if representation == 'original':
        return source['artifact_ref']
    if representation == 'text':
        return source['text_ref']
    return source.get(representation + '_ref')


def within_source(store, reference, root, scope):
    """Whether ``reference`` is ``root`` or derived from it through recorded parent sources."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(require_reference(store, current, scope).get('parent_source_refs', ()))
    return False


def assigned_page(role, assignment):
    """The page a page-family assignment is bound to (``None`` for a question assignment)."""
    return assignment if role == 'literature_page' else assignment.get('page')


class LiteratureBinding(EpisodeRuntimeContract):
    """An A105 literature binding: its declarations, commission check, controller and episode."""
    required_collaborators = ('store', 'model_provider')
    assignment_form = RecordForm({
        'scope': Field('record', 'The Store scope this literature episode investigates within'),
        'received_record_refs': Field('list', 'The records of this scope the commissioner holds and passes on'),
        'episode_assignment': Field('record', 'The commissioned literature assignment, including its literature_task'),
    })

    def __init__(self, *, tool_registry, yield_bindings, outcome_page_size, populations):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ContractError('positive_literature_outcome_page_size_required')
        self.tool_registry = tool_registry
        self.outcome_page_size = outcome_page_size
        self.populations = validate_populations(json.loads(json.dumps(plain(populations))))
        self._yield_bindings = validate_yield_bindings(json.loads(json.dumps(plain(yield_bindings))))
        self._children = None

    # -- declarations ---------------------------------------------------------------------------------------------
    @property
    def roles(self):
        return (self.role,)

    def child_roles(self, role):
        if role != self.role:
            raise ContractError('unsupported_literature_role:' + str(role))
        return tuple(self.child_role_names)

    @property
    def goal(self):
        return 'Improve ' + _PURPOSE[self.role]

    @property
    def unit(self):
        return 'One selected ' + self.role + ' tool action, graded reasoning commit or commissioned child'

    @property
    def result(self):
        return 'The records retained for ' + _PURPOSE[self.role] + ' and their projected credit'

    @property
    def purpose(self):
        return _PURPOSE[self.role]

    def bind_children(self, children):
        """Take this binding's child bindings (by role) once, for their assignment checks."""
        if self._children is not None:
            raise ContractError('literature_children_already_bound:' + self.binding_path)
        children = dict(children)
        if set(children) != set(self.child_role_names) or any(
                children[role].binding_path != ROLE_PATHS[role] for role in children):
            raise ContractError('literature_children_must_be_the_declared_bindings:' + self.binding_path)
        self._children = MappingProxyType(children)

    @property
    def children(self):
        if self._children is None:
            raise ContractError('literature_children_unbound:' + self.binding_path)
        return self._children

    def instructions(self):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
        return '\n'.join((INSTRUCTIONS, self.instruction + '\n' + _ITERATION, REASONING_COMMIT_REQUIREMENT))

    # -- the commissioned assignment ------------------------------------------------------------------------------
    def assignment_schema(self):
        """The ``episode_assignment`` a commissioning parent fills (its task without the declared unit)."""
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import COMPONENTS as AGGREGATION
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import COMPONENTS as GRADING
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import COMPONENTS as QUANTITIES
        shape = self.assignment_shape
        if shape[0] == 'question':
            _, version, field = shape
            schema = obj({'version': {'const': version}, 'question_context_refs': REFERENCES, field: REFERENCES})
        elif shape == ('page',):
            schema = deepcopy(PAGE)
        elif shape[0] == 'reading':
            schema = obj({'version': {'const': 'reading_assignment_v1'}, 'page': PAGE,
                          'selection': deepcopy(_SELECTIONS[shape[1]])})
        else:
            raise ContractError('literature_assignment_shape_unknown:' + repr(shape))
        schema = deepcopy(schema)
        schema['required'].extend(('literature_task', 'proposed_annotation_ref'))
        schema['properties']['literature_task'] = task_schema(commissioned=False)
        schema['properties']['proposed_annotation_ref'] = REF
        for requested, components in (('requested_assay_grading_components', GRADING),
                                      ('requested_a105_aggregation_components', AGGREGATION),
                                      ('requested_quantity_components', QUANTITIES)):
            schema['properties'][requested] = {'type': 'array', 'uniqueItems': True,
                                               'items': {'enum': list(components)}}
        return schema

    def _validate_page(self, store, page, scope):
        source = require_reference(store, page['source_ref'], scope, 'source')
        if source_artifact(source, page['representation']) != page['artifact_ref']:
            raise ContractError('literature_source_artifact_mismatch',
                                detail={'reference': page['source_ref'], 'artifact_ref': page['artifact_ref'],
                                        'representation': page['representation']})
        require_reference(store, page['artifact_ref'], scope, 'artifact')
        for reference in (*page['question_context_refs'], *page['prior_delivery_refs']):
            require_reference(store, reference, scope)

    def validate_assignment(self, store, assignment, scope):
        """The admitted assignment and its task completed with this binding's declared unit and settings."""
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema())
        shape = self.assignment_shape
        if shape[0] == 'question':
            for field, references in value.items():
                if field.endswith('_refs'):
                    for reference in references:
                        require_reference(store, reference, scope,
                                          None if field == 'question_context_refs' else 'source')
        else:
            page = assigned_page(self.role, value)
            self._validate_page(store, page, scope)
            if shape[0] == 'reading':
                selected = value['selection']
                for window in (selected['spans'] if shape[1] == 'spans' else [selected]):
                    if window['source_ref'] != page['source_ref']:
                        raise ContractError('literature_reading_source_mismatch')
                    if 'representation' in window and window['representation'] != page['representation']:
                        raise ContractError('literature_reading_representation_mismatch')
                    if 'representation' in window and window['offset'] > store.get(page['artifact_ref'])['size']:
                        raise ContractError('source_offset_out_of_bounds')
        task = commissioned_task(value['literature_task'], self._yield_bindings)
        validate_commission(task, value)
        requested = answer_requested(task)
        if requested is not None and not value.get(requested):
            raise ContractError('literature_sheet_answer_requires_requested_components:' + requested)
        page = assigned_page(self.role, value)
        if page is not None and any(ref != page['source_ref'] for ref in task_sources(task)):
            raise ContractError('literature_task_outside_assigned_source')
        if page is not None and task.get('answer_kind') == 'screening' and any(
                span['artifact_ref'] != page['artifact_ref'] for span in task['examined']):
            raise ContractError('literature_task_screening_artifact_mismatch')
        return {**value, 'literature_task': task}

    # -- the commissioned typed return (C5) -------------------------------------------------------------------------
    def commissioned_report(self, episode_assignment):
        """The report contract and form a commissioner requests for this assignment's task.

        The form keeps ``credit`` and ``finding`` and adds the task's typed answer and any requested sheet
        cells; the contract asks for the finding and that answer. A commissioned episode is checked
        against exactly this form before it runs (``required_report_fields``).
        """
        value = plain(episode_assignment)
        task = commissioned_task(value.get('literature_task'), self._yield_bindings)
        fields = dict(self.return_form.fields)
        name, spec = answer_field(task)
        fields[name] = spec
        for requested, (cell_name, cell_spec) in CELL_FIELDS.items():
            if value.get(requested):
                fields[cell_name] = cell_spec
        contract = {**REPORT_CONTRACT, 'information': {**REPORT_CONTRACT['information'], name: spec.meaning}}
        return contract, RecordForm(fields)

    def required_report_fields(self, episode_assignment, report_form):
        """The added fields of the commissioned form, checked against this task's typed return."""
        _, expected = self.commissioned_report(episode_assignment)
        for name, spec in expected.fields.items():
            if name not in report_form.fields or report_form.fields[name].as_record() != spec.as_record():
                raise ContractError('literature_task_typed_return_mismatch:' + name)
        unknown = sorted(set(report_form.fields) - set(expected.fields))
        if unknown:
            raise ContractError('literature_report_form_requests_unsupplied_fields:' + ','.join(unknown))
        return tuple(name for name in expected.fields if name not in self.return_form.fields)

    def commission(self, parent_goal, objective, assignment):
        """A commission of this binding: request, assignment and the typed report form its task requires."""
        contract, form = self.commissioned_report(assignment['episode_assignment'])
        message = A105Record({'episode_assignment': assignment['episode_assignment']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=objective, result_contract=contract, task_context={'evidence_axis': AXIS})
        else:
            goal = EpisodeGoal.child(parent_goal, objective=objective, result_contract=contract)
        return Commission(EpisodeRequest(goal, message, ReportContract(**contract)), assignment, form)

    # -- episode_runtime hooks ------------------------------------------------------------------------------------
    def entry_request(self, entry_input, collaborators, *, parent_goal):
        """An entry caller commissions this binding like a parent: with the typed report its task requires."""
        fields = {'objective', 'scope', 'received_record_refs', 'episode_assignment'}
        if not isinstance(entry_input, Mapping) or set(entry_input) != fields:
            raise ContractError('a105_literature_entry_requires_' + '_'.join(sorted(fields)))
        assignment = {name: entry_input[name] for name in ('scope', 'received_record_refs', 'episode_assignment')}
        return self.commission(parent_goal, entry_input['objective'], assignment)

    def build_controller(self, bound, collaborators):
        """The continuation the commissioned task selects from this binding's own declaration."""
        task = commissioned_task(plain(bound.assignment['episode_assignment']).get('literature_task'),
                                 self._yield_bindings)
        return task_controller(task, bound.episode_id, 0.0)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """This literature episode's own model-selected units (``literature_source``)."""
        from method_loop import Episode
        from .literature_source import LiteratureSource
        source = LiteratureSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


_ITERATION = ('This is an iterative scientific investigation. Earlier outcomes and admitted child returns inform '
              'later choices; no child order, reading quota or complete-document requirement is prescribed. '
              'Interpreting an applicable experiment or result selects its purpose-specific grader and saves its '
              'subscoring sheet in the same reasoning action; only a source-grounded finding that the examined '
              'material contains no applicable experiment or result omits grading.')

__all__ = ['ACCESS_TOOLS', 'ACQUISITION_TOOLS', 'CELL_FIELDS', 'LiteratureBinding', 'PAGE', 'REFERENCES', 'TABLE',
           'WINDOW', 'answer_field', 'answer_requested', 'assigned_page', 'require_reference', 'source_artifact',
           'within_source']
