"""Private root annotation task action units."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.method_loop import Leaf
from .episode_journal import WorkflowError
from .task_values import _json
from dataclasses import dataclass

class ActionFailure(WorkflowError):

    def __init__(self, feedback):
        self.feedback = feedback
        super().__init__(_json(feedback))

@dataclass(frozen=True, kw_only=True)
class ActionLeaf(Leaf):
    decision_index: int
