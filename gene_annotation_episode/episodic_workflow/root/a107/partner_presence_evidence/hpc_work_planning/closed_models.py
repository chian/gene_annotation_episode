"""Private closed models for A107 hpc."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107 import hpc_queue
import json
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain




class ClosedModels:
    def frozen_reference(self, context, reference, namespace):
        """Validate a closed model identifier without reopening writable state."""
        if namespace != 'hpc_model' or context.role not in self.roles or self.store is None:
            return False
        from gene_annotation_episode.episodic_workflow.root.a107.episode_return_records import EpisodeReturnRecords
        import sqlite3
        from contextlib import closing
        EpisodeReturnRecords(self.store, self.run_id, failure_prefix='hpc_closed_').authenticate(context)
        saved = self.store.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if saved is None or json.loads(saved[0]).get('hpc_model_ref') != reference:
            return False
        owner = context.episode_id
        path = self.directory / 'hpc' / hpc_queue.digest([context.run_id, owner]) / 'hpc.sqlite'
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            ownership = db.execute("SELECT body FROM evidence WHERE id='owner'").fetchone()
            model = db.execute("SELECT 1 FROM evidence WHERE id=? AND kind='model'", (reference,)).fetchone()
        return bool(ownership and model and (json.loads(ownership[0])['run_id'] == context.run_id) and (json.loads(ownership[0])['episode_id'] == owner) and (json.loads(ownership[0])['scope'] == plain(context.scope)))
