"""The one implementation shared by the seven A106 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py``. It declares only what differs between the seven roles:
``binding_path``, ``role``, ``commissioning_parent``, ``child_role_names``,
``instruction`` and ``assignment_shape`` (``('question', version, refs_field)``,
``('page',)`` or ``('reading', selection)``).

Everything else (the episode_runtime hooks, the assignment check, the
commissioned task, credit, continuation and the decision source
``literature_source.LiteratureSource``) is here and in ``literature_credit``,
``literature_repositories`` and ``literature_source``, once.

Construction (the A106 home factory ``episode_contract.home``) gives each binding its own A106 ``ToolRegistry`` over the run's shared store,
its declared ``yield_bindings``, the ``outcome_page_size`` of its own-outcome
presentation, its explicit optional ``populations`` and their evidence origins,
and whether its analysis children (launch, results) are opened; nothing is
defaulted.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from types import MappingProxyType

from episode_runtime import Commission, Field, RecordForm
from method_loop import EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import REF, ContractError, obj, validate_schema
from ..episode_contract import CHILD_SLOTS, REPORT_CONTRACT, ContractRecord, EpisodeContract, L, P, R, S
from .literature_credit import commissioned_task, task_controller, task_schema, validate_yield_bindings
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import validate_populations

ROLE_PATHS = MappingProxyType({
    'literature': L, 'literature_strategy': S, 'literature_search': R, 'literature_page': P,
    'literature_table': P + '/table_evidence_extraction', 'literature_ordered': P + '/source_coverage_improvement',
    'literature_targeted': P + '/passage_evidence_extraction'})
ANALYSIS_SLOTS = ('launch', 'results')
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
_PURPOSE = MappingProxyType({
    'literature': 'the commissioned literature answer for the A106 perturbation question',
    'literature_strategy': 'the evidence-search strategy for the commissioned A106 literature question',
    'literature_search': 'the set of sources judged relevant to the commissioned A106 question',
    'literature_page': 'the examined source evidence for the commissioned A106 question',
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
# The typed answer a commissioning parent requests for each task (the old per-commission return schema's x-source).
ANSWER_FIELDS = MappingProxyType({
    'verified_source_leads': ('source_lead_dispositions', Field(
        'list', 'The latest disposition of each source verified for the question', items=_LEAD_FORM)),
    'assessment': ('changed_assessment_refs', Field(
        'list', 'The retained assessments of the question this commission holds')),
    'screening': ('screening_answers', Field(
        'list', 'The no-applicable-evidence answer over every requested span', items=_SCREENING_FORM)),
})


def answer_field(task):
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
        return source.get('text_ref') or source['artifact_ref']
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
        pending.extend(require_reference(store, current, scope, 'source').get('parent_source_refs', ()))
    return False


def assigned_page(role, assignment):
    """The page a page-family assignment is bound to (``None`` for a question assignment)."""
    return assignment if role == 'literature_page' else assignment.get('page')


class LiteratureBinding(EpisodeContract):
    """An A106 literature binding: its declarations, commission check, controller and episode."""
    required_collaborators = ('store', 'model_provider')
    assignment_form = RecordForm({
        'scope': Field('record', 'The Store scope this literature episode investigates within'),
        'received_record_refs': Field('list', 'The records of this scope the commissioner holds and passes on'),
        'episode_assignment': Field('record', 'The commissioned literature assignment, including its literature_task'),
    })

    def __init__(self, *, tool_registry, yield_bindings, outcome_page_size, populations, evidence_origins,
                 analysis_children):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ContractError('positive_literature_outcome_page_size_required')
        if type(analysis_children) is not bool or (analysis_children and self.role != 'literature'):
            raise ContractError('a106_literature_analysis_children_flag_invalid:' + self.binding_path)
        self.tool_registry = tool_registry
        self.outcome_page_size = outcome_page_size
        self.populations, self.evidence_origins = validate_populations(plain(populations), plain(evidence_origins))
        self.analysis_children = analysis_children
        self._yield_bindings = validate_yield_bindings(json.loads(json.dumps(plain(yield_bindings))))
        self._children = None

    # -- declarations ---------------------------------------------------------------------------------------------
    @property
    def child_slots(self):
        """Its literature child roles, and its analysis children only when this binding opens them."""
        opened = set(self.child_role_names) | (set(ANALYSIS_SLOTS) if self.analysis_children else set())
        return MappingProxyType({slot: path for slot, path in CHILD_SLOTS[self.binding_path].items()
                                 if slot in opened})

    @property
    def goal(self):
        return 'Improve ' + _PURPOSE[self.role]

    @property
    def unit(self):
        return 'One selected ' + self.role + ' tool action, reasoning commit or commissioned child'

    @property
    def result(self):
        return 'The records retained for ' + _PURPOSE[self.role] + ' and their projected credit'

    @property
    def purpose(self):
        return _PURPOSE[self.role]

    def bind_children(self, children):
        """Take this binding's literature child bindings (by role) once, for their assignment checks."""
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
        from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import TASK
        from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.perturbation_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
        from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import PERTURBATION_TASK
        return '\n'.join((INSTRUCTIONS, '\n\n'.join((self.instruction, PERTURBATION_TASK, TASK)),
                          REASONING_COMMIT_REQUIREMENT))

    def contract_credit_unit(self, assignment):
        task = commissioned_task(plain(assignment['episode_assignment']).get('literature_task'), self._yield_bindings)
        return task['credit_unit']

    # -- the commissioned assignment ------------------------------------------------------------------------------
    def assignment_schema(self):
        """The ``episode_assignment`` a commissioning parent fills (its task without the declared unit)."""
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
        page = assigned_page(self.role, value)
        selected_sources = task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
        if page is not None and any(ref != page['source_ref'] for ref in selected_sources):
            raise ContractError('literature_task_outside_assigned_source')
        if page is not None and task.get('answer_kind') == 'screening' and any(
                span['artifact_ref'] != page['artifact_ref'] for span in task['examined']):
            raise ContractError('literature_task_screening_artifact_mismatch')
        return {**value, 'literature_task': task}

    # -- the commissioned typed return (C5) -------------------------------------------------------------------------
    def commissioned_report(self, episode_assignment):
        """The report contract and form a commissioner requests for this assignment's task.

        The form keeps ``credit`` and ``finding`` and adds the task's typed answer; the contract asks for the
        finding and that answer. A commissioned episode is checked against exactly this form before it runs
        (``required_report_fields``).
        """
        task = commissioned_task(plain(episode_assignment).get('literature_task'), self._yield_bindings)
        fields = dict(self.return_form.fields)
        name, spec = answer_field(task)
        fields[name] = spec
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
        message = ContractRecord({'episode_assignment': assignment['episode_assignment']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=objective, result_contract=contract, task_context={'evidence_axis': 'A106'})
        else:
            goal = EpisodeGoal.child(parent_goal, objective=objective, result_contract=contract)
        return Commission(EpisodeRequest(goal, message, ReportContract(**contract)), assignment, form)

    # -- episode_runtime hooks ------------------------------------------------------------------------------------
    def entry_request(self, entry_input, collaborators, *, parent_goal):
        """An entry caller commissions this binding like a parent: with the typed report its task requires."""
        fields = {'objective', 'scope', 'received_record_refs', 'episode_assignment'}
        if not isinstance(entry_input, Mapping) or set(entry_input) != fields:
            raise ContractError('a106_literature_entry_requires_' + '_'.join(sorted(fields)))
        assignment = {name: entry_input[name] for name in ('scope', 'received_record_refs', 'episode_assignment')}
        return self.commission(parent_goal, entry_input['objective'], assignment)

    def build_controller(self, bound, collaborators):
        """The continuation the commissioned task selects from this binding's own declaration.

        A freshly commissioned literature episode holds no own lead, screening answer or received assessment,
        so it opens at zero credit.
        """
        task = commissioned_task(plain(bound.assignment['episode_assignment']).get('literature_task'),
                                 self._yield_bindings)
        return task_controller(task, bound.episode_id, 0.0)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """This literature episode's own model-selected units (``literature_source``)."""
        from method_loop import Episode
        from .literature_source import LiteratureSource
        source = LiteratureSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ANALYSIS_SLOTS', 'LiteratureBinding', 'PAGE', 'REFERENCES', 'ROLE_PATHS', 'TABLE', 'WINDOW',
           'answer_field', 'assigned_page', 'require_reference', 'source_artifact', 'within_source']
