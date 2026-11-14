"""The existing root annotation binding and its local assembly."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from importlib import import_module
from .scoring import SignedEvidenceRootSupport
from .root_axis_scalars import AXES, VERSION
from .credit import RootCredit
from .task import AnnotationTask
RootYield = import_module('.yield', __package__).RootYield

@dataclass(frozen=True)
class SignedRootEpisodeBinding(RootCredit, RootYield):
    """The annotation root's own credit, score, and continuation binding."""
    roles = ('annotation',)
    entry_roles = ('annotation',)
    decision_source_type = AnnotationTask
    initial_known_record_refs: tuple[str, ...]
    axis_yield_cutoffs: Mapping[str, float]
    yield_parameters: object
    annotation_support: SignedEvidenceRootSupport

    @classmethod
    def from_record(cls, record):
        from .numerical import AnnotationAxisYieldController, YieldParameters
        if isinstance(record, dict) and record.get('version') == 'signed_root_episode_binding_v1':
            raise ValueError('legacy_signed_root_scalar_credit_incompatible')
        if not isinstance(record, dict) or set(record) != {'version', 'initial_known_record_refs', 'root_task', 'annotation_support'} or record['version'] != 'signed_root_episode_binding_v2':
            raise ValueError('explicit_signed_root_episode_binding_required')
        task = record['root_task']
        if not isinstance(task, dict) or set(task) != {'kind', 'cutoffs', 'yield_parameters'} or task['kind'] != 'annotation_axis_credit' or (not isinstance(task['cutoffs'], dict)) or (set(task['cutoffs']) != set(AXES)) or (not isinstance(task['yield_parameters'], dict)):
            raise ValueError('explicit_root_axis_yield_binding_required')
        support = record['annotation_support']
        if not isinstance(support, dict) or not {'version'} <= set(support) <= {'version', 'assertion_ref', 'comparison_ref', 'selections'} or support['version'] != VERSION or (not isinstance(support.get('selections', {}), dict)):
            raise ValueError('explicit_signed_root_annotation_support_required')
        refs = record['initial_known_record_refs']
        if not isinstance(refs, list) or any((not isinstance(ref, str) or not ref for ref in refs)) or len(refs) != len(set(refs)):
            raise ValueError('explicit_initial_known_record_refs_required')
        scorer = SignedEvidenceRootSupport(support.get('assertion_ref'), support.get('comparison_ref'), tuple(support.get('selections', {}).items()))
        if scorer.provides_single_annotation_score:
            raise ValueError('annotation_axis_root_requires_collection_scorer')
        parameters = YieldParameters(**task['yield_parameters'])
        cutoffs = dict(task['cutoffs'])
        AnnotationAxisYieldController('configuration', {'mode': 'annotation_axis_credit', 'arms': []}, cutoffs, parameters)
        return cls(tuple(refs), MappingProxyType(cutoffs), parameters, scorer)
from .root_assembly import create_signed_evidence_root_workflow
