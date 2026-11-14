"""Private credit for A102 prediction."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.library import hpc_prediction as prediction



class HPCEpisodeCredit:
    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_hpc_role')
        return 'operational'

    @staticmethod
    def _quality(ledger, model):
        if not set(model['training_ids']) <= {row['id'] for row in ledger.commission['history']}:
            return None
        selected = [row for row in ledger.commission['history'] if row['id'] in ledger.commission['validation_ids']]
        return prediction.quality(model, selected) if selected else None

    def credit_view(self, context, receiver_selection):
        ledger = self.state(context)
        entries = ledger.records('model_entry')
        entry = next((row['body'] for row in entries if row['id'] == 'entry:'+context.episode_id), None)
        current = self._quality(ledger, ledger.read(self._current_model(ledger)))
        gain = current-entry['quality'] if entry and current is not None and entry['quality'] is not None else 0.
        validation = sum(row['credit'] for row in ledger.credit_view()['contributions']
            if row['kind'] == 'validation' and
            ledger.read(row['evidence_id']).get('prediction_episode_id') == context.episode_id)
        return {'credit': ledger.commission['credit']['model_scale']*gain+validation,
                'model_quality_improvement': gain, 'prospective_validation_credit': validation,
                'actual_job_credit_counted_here': False}
