"""Private launch_hpc retained receiving received_action_identity responsibilities."""
from __future__ import annotations
from .result_records import NATIVE_RESULT_ORIGIN
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable
from .action_outcome import _outcome
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _read
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import digest
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class HPCExecutionReceivedActionIdentity:

    def _selected_result_action(self, episode_id, key, name, arguments):
        prefix = self.run_id + ':' + episode_id + ':'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('execution_result_selected_action_missing')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('execution_result_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('execution_result_selected_action_conflict')
        return row

