"""Credit, carried from the old ``credit.py`` (``HPCEpisodeCredit.credit_view`` and ``_quality``; ``credit_kind``,
always ``operational``, is deleted, README 3d).

``credit = commission.credit.model_scale * (current model quality - this episode's entry quality) + prospective
validation credit of this episode's predictions``; actual job credit is not counted here. Signed, never bounded,
clamped or rescaled. The quality of a model is the mean proper score on the commission's fixed validation cases,
and is ``None`` for a model trained on later allocations (those earn prospective credit when real outcomes
arrive) and when the commission has no validation cases: the gain is then zero.

``credit`` has no services and the ledger is not read here: ``messages/internal_summary.py`` reads the held ledger
rows (work table ``hpc_evidence``) through ``view.records`` and puts the components into the summary
(``model_quality_improvement``, ``prospective_validation_credit``, ``model_scale``), using the functions below."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence import (
    hpc_prediction as prediction)


def quality(ledger, model):
    """The old ``HPCEpisodeCredit._quality`` over the ledger read by ``task.read_ledger``."""
    history = ledger['commission']['history']
    if not set(model['training_ids']) <= {row['id'] for row in history}:
        return None
    selected = [row for row in history if row['id'] in ledger['commission']['validation_ids']]
    return prediction.quality(model, selected) if selected else None


def quality_improvement(entry_quality, current_quality):
    """Gain of the current model over the model at entry; zero when either quality is unknown."""
    if entry_quality is None or current_quality is None:
        return 0.
    return current_quality - entry_quality


def prospective_validation_credit(ledger, episode_id):
    """The old sum over ``credit_view()['contributions']`` of kind ``validation`` whose scored forecast was made
    by this episode's predictions (``prediction_episode_id``). A scored forecast is written after this episode
    closes, so within its own run the sum is zero unless the parent passed such rows."""
    total = 0.
    for slot in ledger['credits']:
        if slot['kind'] != 'validation':
            continue
        evidence = ledger['by_id'].get(slot['evidence_id'])
        if evidence is None:
            raise ValueError('unknown_hpc_evidence:' + slot['evidence_id'])
        if evidence['body'].get('prediction_episode_id') == episode_id:
            total += slot['credit']
    return total


def credit(summary, records):
    value = (summary['model_scale'] * summary['model_quality_improvement']
             + summary['prospective_validation_credit'])
    if not math.isfinite(value):
        raise ValueError('finite_hpc_prediction_credit_required')
    return value
