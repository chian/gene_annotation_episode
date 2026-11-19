"""A105 episode bindings for the generic runner (``episode_runtime``) and the A105 home factory.

Contract: docs/axis_restructure_20261117/BINDING_CONTRACT.md. Every A105 binding
(the head and the seven published-evidence bindings below it) mixes in
``EpisodeRuntimeContract`` and implements every hook.

- The head (``experimental_activity_evidence``) runs its own model-selected
  decisions (``runtime_source.ExperimentalActivityEvidenceSource``) over
  ``bound``, the ``store`` and ``model_provider`` collaborators and its own tool
  registry. Its commissioning parent chooses, per commission, one library
  thought pattern (``ChoiceField``) and the subset of the head's tools it may use
  (``SubsetField``); its evidence task is its own declaration (``DeclaredField``).
  Its controller is the configured accumulation yield controller over its
  unbounded finding credit, opened with the credit the Episode already holds.
- The seven literature bindings are subclasses of
  ``published_evidence_assessment/literature_binding.LiteratureBinding``.

``a105_home_factory`` constructs all eight with each binding's own tool registry
over the run's one shared store (C4). Nothing is defaulted: a missing service raises.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from types import MappingProxyType

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField, grain_name_for
from method_loop import ClosedRecord, Episode, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.domain import ContractError

AXIS = 'A105'
HEAD = 'experimental_activity_evidence'
TASK_KEY = AXIS + ':whole_axis_findings'
LITERATURE = HEAD + '/published_evidence_assessment'
_STRATEGY = LITERATURE + '/evidence_search_strategy_improvement'
_SEARCH = _STRATEGY + '/source_relevance_assessment'
_EXAMINATION = _SEARCH + '/source_evidence_examination'

# The explicit binding path of every A105 role. A child slot is named by the child's role.
ROLE_PATHS = MappingProxyType({
    HEAD: HEAD,
    'literature': LITERATURE,
    'literature_strategy': _STRATEGY,
    'literature_search': _SEARCH,
    'literature_page': _EXAMINATION,
    'literature_table': _EXAMINATION + '/table_evidence_extraction',
    'literature_ordered': _EXAMINATION + '/source_coverage_improvement',
    'literature_targeted': _EXAMINATION + '/passage_evidence_extraction',
})
REPORT_CONTRACT = {
    'decision': 'Admit the A105 experimental-activity findings into the commissioning episode',
    'measurements': {'credit': "This commission's A105 credit on its own unbounded scale"},
    'information': {'finding': 'The retained A105 experimental-activity findings of this commission'},
}
RETURN_FORM = RecordForm({
    'credit': Field('number', "This commission's A105 credit on its own unbounded scale (never clamped)"),
    'finding': Field('record', 'The retained A105 experimental-activity findings of this commission'),
})

_HEAD_GOAL = ('Improve the experimental-activity evidence about what the assigned target does: actual '
              'experiments and their results (published or in experiment databases) whose measured subject, '
              'conditions, controls and uncertainty bear on the target, each graded with its purpose-specific '
              'subscoring sheet and kept as a typed investigation finding with its unresolved target '
              'correspondence.')


@dataclass(frozen=True)
class A105Record(ClosedRecord):
    """A closed A105 controller input, request message or result."""
    value: Mapping

    def as_record(self):
        return json.loads(json.dumps(self.value, sort_keys=True, allow_nan=False))


def require_tool_registry(registry, store, what):
    """A binding's own tool registry over the run's one shared store."""
    for name in ('catalog', 'execute_async'):
        if not callable(getattr(registry, name, None)):
            raise ContractError('a105_tool_registry_interface:' + what + ':' + name)
    if getattr(registry, 'store', None) is not store:
        raise ContractError('a105_tool_registry_is_not_over_the_run_store:' + what)
    return registry


class EpisodeRuntimeContract:
    """The episode_runtime hooks shared by every A105 binding."""
    return_form = RETURN_FORM
    report_contract = MappingProxyType(REPORT_CONTRACT)

    @property
    def grain_name(self):
        return grain_name_for(self.binding_path)

    @property
    def child_slots(self):
        return MappingProxyType({child: ROLE_PATHS[child] for child in self.child_roles(self.roles[0])})

    def restore_controller_input(self, record):
        if not isinstance(record, Mapping) or 'credit' not in record:
            raise ContractError('a105_recorded_controller_input_requires_credit')
        return A105Record(dict(record))


class HeadRuntimeContract(EpisodeRuntimeContract):
    """The A105 axis head, commissioned by the root annotation episode or by an A105 head."""
    goal = _HEAD_GOAL
    unit = 'One selected A105 tool action, reasoning commit or commissioned literature/experimental-activity child'
    result = ("This commission's A105 credit on its own unbounded scale and the experimental-activity findings "
              'it retained about the subject')
    required_collaborators = ('store', 'model_provider')
    _literature = None

    def bind_literature(self, literature):
        """Take the literature binding (its assignment schema and commission) for the head's literature child."""
        if self._literature is not None:
            raise ContractError('a105_head_literature_already_bound')
        if literature.binding_path != ROLE_PATHS['literature']:
            raise ContractError('a105_head_literature_binding_required:' + str(literature.binding_path))
        self._literature = literature

    @property
    def literature_binding(self):
        if self._literature is None:
            raise ContractError('a105_head_literature_binding_unbound')
        return self._literature

    def _continuation(self):
        declaration = self._yield_bindings.get(TASK_KEY)
        if declaration is None:
            raise ContractError('scientific_yield_binding_missing_for_task:' + TASK_KEY)
        return declaration

    def evidence_task(self):
        """The head's own whole-axis task, fixed by its configured credit definition."""
        policy = self._continuation()['credit_definition'].get('policy')
        unit = policy.get('finding_unit') if isinstance(policy, Mapping) else None
        if isinstance(unit, bool) or not isinstance(unit, (int, float)):
            raise ContractError('a105_head_evidence_task_requires_declared_finding_unit')
        return {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': AXIS,
                'credit_unit': unit}

    @property
    def assignment_form(self):
        """``scope`` (and a held ``proposed_annotation_ref``) are filled by the commissioner; the evidence task
        is the head's own declaration; the thought pattern and tool subset are the commissioner's choice (C3, C6)."""
        return RecordForm({
            'scope': Field('record', 'The subject whose A105 experimental-activity evidence this episode improves'),
            'evidence_task': DeclaredField('record', 'The A105 whole-axis finding task and its credit unit',
                                           self.evidence_task()),
            'thought_pattern': ChoiceField('text', 'The library thought pattern this commission investigates with',
                                           tuple(sorted(self.thought_patterns))),
            'tools': SubsetField('text', 'The tools of this head this commission may use', self.selectable_tools),
            'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioner holds for this '
                                                     'subject, when it holds one', required=False),
        })

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        fields = {'scope', 'thought_pattern', 'tools'}
        if not isinstance(entry_input, Mapping) or not fields <= set(entry_input) or not set(entry_input) <= {
                *fields, 'proposed_annotation_ref'}:
            raise ContractError('a105_head_entry_requires_scope_thought_pattern_tools_and_optional_proposed_annotation')
        assignment = {name: entry_input[name] for name in entry_input}
        assignment.update(self.assignment_form.declared)
        message = A105Record({'scope': entry_input['scope']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract=REPORT_CONTRACT,
                                    task_context={'evidence_axis': AXIS})
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=REPORT_CONTRACT)
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT_CONTRACT)), assignment)

    def build_controller(self, bound, collaborators):
        """The configured accumulation yield controller, opened with the credit this Episode already holds."""
        return self.head_controller(bound, collaborators)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The head's own model-selected units (``runtime_source``) over ``bound`` and its collaborators."""
        from .runtime_source import ExperimentalActivityEvidenceSource
        from .yield_estimator import INITIAL_CREDIT_DECISION
        source = ExperimentalActivityEvidenceSource(self, bound, collaborators, child_builders)

        def build_result(record):
            return source.result(record, bound.recorder.recall(INITIAL_CREDIT_DECISION))
        return Episode(grain, bound.key, source, bound.request, build_result)


def a105_home_factory(services):
    """Construct every A105 binding: the head and its seven literature bindings.

    ``services['store']`` is the run's one shared ``gene_annotation_episode.state.Store``; each binding gets its
    own ``a105.tools.A105ToolRegistry`` over it (C4). ``services['a105']`` supplies A105's construction-time
    settings:

    - ``tool_settings``: the registry's operands (``pdfinfo_executable``, ``pdftotext_executable``,
      ``pdftoppm_executable``, ``job_limits`` with its ``memory_bytes`` and ``scratch_bytes``);
    - ``head``: the head's frozen ``library``, its ``child_roles`` and its ``yield_bindings``;
    - ``literature``: the literature bindings' ``yield_bindings``, ``outcome_page_size`` and ``populations``.
    """
    if not isinstance(services, Mapping):
        raise TypeError('a105_construction_services_must_be_a_mapping')
    try:
        store, configuration = services['store'], services['a105']
        tool_settings, head, literature = (configuration[name] for name in ('tool_settings', 'head', 'literature'))
    except KeyError as error:
        raise ContractError('a105_home_factory_requires_service:' + str(error.args[0])) from error
    if not isinstance(tool_settings, Mapping):
        raise ContractError('a105_home_factory_tool_settings_must_be_a_mapping')
    from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence.tools import A105ToolRegistry
    from .episode import ExperimentalActivityEvidenceEpisode
    from .published_evidence_assessment.episode import create_binding_tree

    def registry(what):
        return require_tool_registry(A105ToolRegistry(store, **tool_settings), store, what)
    tree = create_binding_tree(tool_registry=registry, **dict(literature))
    head_binding = ExperimentalActivityEvidenceEpisode(tool_registry=registry(HEAD), **dict(head))
    if 'literature' in head_binding.child_slots:
        head_binding.bind_literature(tree[0])
    return (head_binding, *tree)


__all__ = ['A105Record', 'AXIS', 'EpisodeRuntimeContract', 'HEAD', 'HeadRuntimeContract',
           'LITERATURE', 'REPORT_CONTRACT', 'RETURN_FORM', 'ROLE_PATHS', 'TASK_KEY', 'a105_home_factory',
           'require_tool_registry']
