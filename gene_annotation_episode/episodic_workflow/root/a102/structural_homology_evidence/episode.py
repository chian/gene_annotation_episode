"""The A102 head binding (``structural_homology_evidence``) on the generic runner.

It is constructed by the A102 home factory (``contract_binding.a102_home_factory``)
with its frozen ``StructuralHomologyEvidenceLibrary`` publication, its own
``ToolRegistry`` over the run's shared Store and its per-task yield declarations
(``yield_bindings['A102:<task>']``). Its commission (``assignment_form``) carries
the subject scope and proposed annotation the root holds, and the A102 task,
thought pattern and tool subset the root chooses among the options declared here
(C3/C6). Its decisions, credit and continuation are ``runtime_head``.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import math

from episode_runtime import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import TASKS
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError
from .contract_binding import A102ContractBinding
from .runtime_head import evidence_axis_entry, thought_patterns

ROLE = 'structural_homology_evidence'
_YIELD_KINDS = frozenset({'accumulation', 'bounded_quality', 'completion'})


def _yield_bindings(value):
    """Each declaration: kind, cutoff, parameters (uncertainty_alpha) and its exact credit definition."""
    if not isinstance(value, Mapping) or not value:
        raise ContractError('scientific_yield_bindings_invalid')
    from yield_control import YieldParameters
    bindings = json.loads(json.dumps(dict(value), allow_nan=False))
    for task, declaration in bindings.items():
        if (not isinstance(task, str) or not task.startswith('A102:') or not isinstance(declaration, dict)
                or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
                or declaration['kind'] not in _YIELD_KINDS or not isinstance(declaration['parameters'], dict)
                or set(declaration['parameters']) != {'uncertainty_alpha'}
                or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']
                or isinstance(declaration['cutoff'], bool) or not isinstance(declaration['cutoff'], (int, float))
                or not math.isfinite(declaration['cutoff'])):
            raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
        try:
            YieldParameters(**declaration['parameters'])
        except (TypeError, ValueError) as error:
            raise ContractError('scientific_yield_task_binding_invalid:' + task) from error
    return bindings


class StructuralHomologyEvidenceEpisode(A102ContractBinding):
    """The A102 axis head, commissioned by the root annotation episode."""
    binding_path = ROLE
    commissioning_parent = 'annotation'
    required_collaborators = ('store', 'model_provider')

    def __init__(self, *, library, tool_registry, yield_bindings):
        self.library = library
        evidence_axis_entry(library)
        self.thought_patterns = thought_patterns(library)
        if not self.thought_patterns:
            raise ContractError('a102_head_library_requires_thought_patterns')
        self.tool_registry = tool_registry
        self.selectable_tools = tuple(sorted(tool_registry.catalog()))
        if not self.selectable_tools:
            raise ContractError('a102_head_tool_registry_offers_no_tools')
        self.yield_bindings = _yield_bindings(yield_bindings)

    @property
    def assignment_form(self):
        """What the root fills (scope, proposed annotation) and chooses (task, thought pattern, tools)."""
        return RecordForm({
            'scope': Field('record', 'The subject whose structural-homology evidence is investigated'),
            'evidence_axis': DeclaredField('text', 'The evidence axis this head investigates', 'A102'),
            'a102_task': ChoiceField('text', 'The A102 structural evidence task this commission investigates',
                                     TASKS),
            'proposed_annotation_ref': Field('text', 'The proposed annotation this commission evaluates'),
            'thought_pattern': ChoiceField('text', 'The library thought pattern this commission investigates with',
                                           tuple(sorted(self.thought_patterns))),
            'tools': SubsetField('text', 'The tools of this head this commission may use', self.selectable_tools),
        })

    def build_controller(self, bound, collaborators):
        from .runtime_head import head_controller
        return head_controller(self, bound, collaborators['store'])

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        from .runtime_head import StructuralHomologyEvidenceSource
        source = StructuralHomologyEvidenceSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ROLE', 'StructuralHomologyEvidenceEpisode']
