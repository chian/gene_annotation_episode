"""A108 episode bindings for the generic runner (``episode_runtime``).

Every A108 binding mixes in ``EpisodeRuntimeContract`` and so implements each
hook of docs/axis_restructure_20261117/BINDING_CONTRACT.md. ``a108_home_factory``
is the A108 home factory used by ``BindingRegistry.compose``.

The head (``sample_context_evidence``) runs its own decision behaviour on the
runner: ``build_episode`` builds ``runtime_source.SampleContextEvidenceSource``
over ``bound``, the ``store`` and ``model_provider`` collaborators and the head's own
tool registry, and its controller is its own unbounded yield controller over
its finding-progress credit.

The seven literature bindings are subclasses of
``published_evidence_assessment/literature_binding.LiteratureBinding`` (one shared
implementation; each binding declares its own path, role, children, instruction,
acquisition permission and assignment shape). Their decision source is
``published_evidence_assessment/literature_source.LiteratureSource``.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from types import MappingProxyType

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField, grain_name_for
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.domain import ContractError

AXIS = 'A108'
HEAD_PATH = 'sample_context_evidence'
LITERATURE_PATH = 'sample_context_evidence/published_evidence_assessment'
STRATEGY_PATH = LITERATURE_PATH + '/evidence_search_strategy_improvement'
SEARCH_PATH = STRATEGY_PATH + '/source_relevance_assessment'
PAGE_PATH = SEARCH_PATH + '/source_evidence_examination'
# The explicit binding path of each A108 role. Child slots are named by role.
ROLE_PATHS = MappingProxyType({
    'sample_context_evidence': HEAD_PATH,
    'literature': LITERATURE_PATH,
    'literature_strategy': STRATEGY_PATH,
    'literature_search': SEARCH_PATH,
    'literature_page': PAGE_PATH,
    'literature_table': PAGE_PATH + '/table_evidence_extraction',
    'literature_ordered': PAGE_PATH + '/source_coverage_improvement',
    'literature_targeted': PAGE_PATH + '/passage_evidence_extraction',
})
REPORT_CONTRACT = {
    'decision': 'Admit the A108 findings into the commissioning episode',
    'measurements': {'credit': "This commission's credit on the binding's own unbounded scale"},
    'information': {'finding': 'The retained A108 sample-context findings of this commission'},
}
RETURN_FORM = RecordForm({
    'credit': Field('number', "This commission's credit on the binding's own unbounded scale"),
    'finding': Field('record', 'The retained A108 sample-context findings of this commission'),
})


@dataclass(frozen=True)
class RuntimeRecord(ClosedRecord):
    """A closed A108 controller input or request message."""
    value: dict

    def as_record(self):
        return json.loads(json.dumps(self.value, sort_keys=True, allow_nan=False))


def _unbounded_controller(epoch, declaration, what):
    """The binding's own continuation; a bounded-credit controller is refused."""
    from yield_control import (
        AccumulationYieldController, CompletionYieldController, YieldParameters)
    parameters = YieldParameters(**declaration['parameters'])
    if declaration['kind'] == 'accumulation':
        return AccumulationYieldController(epoch, 0.0, declaration['cutoff'], parameters)
    if declaration['kind'] == 'completion':
        return CompletionYieldController(epoch, 0.0, declaration['cutoff'],
                                         declaration['credit_definition']['maximum_credit'], parameters)
    raise ContractError('a108_runtime_continuation_must_be_unbounded:' + what + ':' + str(declaration['kind']))


class EpisodeRuntimeContract:
    """The episode_runtime hooks shared by every A108 binding."""
    return_form = RETURN_FORM
    report_contract = MappingProxyType(REPORT_CONTRACT)

    @property
    def grain_name(self):
        return grain_name_for(self.binding_path)

    @property
    def child_slots(self):
        return MappingProxyType({child: ROLE_PATHS[child] for child in self.child_roles(self.roles[0])})

    def restore_controller_input(self, record):
        return RuntimeRecord(dict(record))


class HeadRuntimeContract(EpisodeRuntimeContract):
    """The A108 axis head, commissioned by the root annotation episode."""
    goal = ('Increase the retained, source-grounded organism and sample-context findings that bear on the '
            'commissioned subject')
    unit = 'One selected A108 tool action, reasoning commit or commissioned literature/sample-context child'
    result = 'The retained A108 sample-context findings and their projected finding credit'
    required_collaborators = ('store', 'model_provider')
    _literature_assignment_schema = None

    def bind_literature(self, literature):
        """Take the literature binding's own assignment schema for the head's literature child action."""
        if self._literature_assignment_schema is not None:
            raise ContractError('a108_head_literature_already_bound')
        if literature.binding_path != ROLE_PATHS['literature']:
            raise ContractError('a108_head_literature_binding_required:' + str(literature.binding_path))
        self._literature_assignment_schema = json.loads(json.dumps(literature.assignment_schema()))
        self._literature_binding = literature

    @property
    def literature_binding(self):
        if self._literature_assignment_schema is None:
            raise ContractError('a108_head_literature_binding_unbound')
        return self._literature_binding

    def literature_assignment_schema(self):
        if self._literature_assignment_schema is None:
            raise ContractError('a108_head_literature_assignment_schema_unbound')
        return json.loads(json.dumps(self._literature_assignment_schema))

    def _continuation(self):
        task = AXIS + ':whole_axis_findings'
        if task not in self._yield_bindings:
            raise ContractError('scientific_yield_binding_missing_for_task:' + task)
        return self._yield_bindings[task]

    @property
    def assignment_form(self):
        """``scope`` is filled by the commissioner; the evidence task is the head's own declaration."""
        policy = self._continuation()['credit_definition'].get('policy')
        unit = policy.get('finding_unit') if isinstance(policy, Mapping) else None
        if isinstance(unit, bool) or not isinstance(unit, (int, float)):
            raise ContractError('a108_head_evidence_task_requires_declared_finding_unit')
        task = {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': AXIS,
                'credit_unit': unit}
        return RecordForm({
            'scope': Field('record', 'The subject whose A108 sample-context findings this episode improves'),
            'evidence_task': DeclaredField('record', 'The A108 whole-axis finding task and its credit unit', task),
            'thought_pattern': ChoiceField('text', 'The library thought pattern this commission investigates with',
                                           tuple(sorted(self.thought_patterns))),
            'tools': SubsetField('text', 'The tools of this head this commission may use', self.selectable_tools),
        })

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if not isinstance(entry_input, Mapping) or set(entry_input) != {'scope', 'thought_pattern', 'tools'}:
            raise ContractError('a108_head_entry_requires_scope_thought_pattern_and_tools')
        assignment = {name: entry_input[name] for name in ('scope', 'thought_pattern', 'tools')}
        assignment.update(self.assignment_form.declared)
        message = RuntimeRecord({'scope': entry_input['scope']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract=REPORT_CONTRACT,
                                    task_context={'evidence_axis': AXIS})
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=REPORT_CONTRACT)
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT_CONTRACT)), assignment)

    def build_controller(self, bound, collaborators):
        """The head's own unbounded yield controller; its declared credit definition must be the projector's."""
        from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import canonical
        from .runtime_source import head_credit_projector
        declaration = self._continuation()
        projector = head_credit_projector(bound.assignment['evidence_task'])
        if canonical(projector.as_record()) != canonical(declaration['credit_definition']):
            raise ContractError('scientific_yield_credit_definition_mismatch:' + AXIS + ':whole_axis_findings')
        if projector.yield_method != declaration['kind']:
            raise ContractError('scientific_yield_method_credit_mismatch:' + AXIS + ':whole_axis_findings')
        return _unbounded_controller(bound.episode_id, declaration, self.binding_path)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The head's own model-selected units (``runtime_source``) over ``bound`` and its collaborators."""
        from method_loop import Episode
        from .runtime_source import SampleContextEvidenceSource
        source = SampleContextEvidenceSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


def a108_home_factory(services):
    """Construct every A108 binding: the head and its seven literature bindings.

    ``services['store']`` is the run's one shared ``gene_annotation_episode.state.Store``.
    ``services['a108']`` supplies A108's construction-time services: ``binding_services``
    (the head's application ports), ``head`` (the head's library, child roles and yield
    declaration), ``tools`` (the settings of each A108 binding's own ``ToolRegistry`` over the
    shared store) and ``literature`` (the literature bindings' ``yield_bindings`` and
    ``outcome_page_size``).
    """
    from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tools import ToolRegistry
    from .episode import SampleContextEvidenceEpisode
    from .published_evidence_assessment.episode import create_binding_tree
    try:
        store, configuration = services['store'], services['a108']
        ports, head, tools, literature = (configuration[name]
                                          for name in ('binding_services', 'head', 'tools', 'literature'))
    except KeyError as error:
        raise ContractError('a108_home_factory_requires_service:' + str(error.args[0])) from error
    tree = create_binding_tree(store=store, tools=tools, **literature)
    head_binding = SampleContextEvidenceEpisode(ports, tool_registry=ToolRegistry(store, **tools), **head)
    if 'literature' in head_binding.child_slots:
        head_binding.bind_literature(tree[0])
    return (head_binding, *tree)
