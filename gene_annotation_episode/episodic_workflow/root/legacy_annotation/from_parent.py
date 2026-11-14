from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _object
from gene_annotation_episode.episodic_workflow.root.method_loop.episode import Episode
from gene_annotation_episode.episodic_workflow.root.task_values import _plain
from gene_annotation_episode.episodic_workflow.root.communication import interpretation_schema

class LegacyAnnotationFromParent:
    def __init__(self, workflow, path, request, scope):
        if (not path or path[-1][0] != 'improvement'
                or 'improvement' in workflow.episode_bindings.roles):
            raise ValueError('original_legacy_improvement_identity_required')
        self.workflow, self.path, self.request, self.scope = workflow, path, request, scope
        self.episode_id = Episode.identity(workflow.context, workflow.grains[path[-1][0]],
            path[-1][1], parent_path=path[:-1]).episode_id
        self.calls = 0
        self.feedback = None
        self.last_outcome = None
        self.last_outcome_index = None
        self.report_values = _plain(request.message.as_record()["initial_report"])
        self.report_basis = []
        self._restored = False
        self._unfinished_own_actions = []
        self._source_revision = None
        self._latest_effect_index = None
        self._restored_source_state = None
        self._model_snapshot = None
        self._presented_conversation_key = None
        self._selection_view = None
        self._delivery_resolution_ref = None
        self._execution_context = None
        self._suspension_condition = None
        self._inprocess_replay_ready = False
        self.interpret_schema = (interpretation_schema(request.report_contract.schema)
                                if request.report_contract else _object({}))

