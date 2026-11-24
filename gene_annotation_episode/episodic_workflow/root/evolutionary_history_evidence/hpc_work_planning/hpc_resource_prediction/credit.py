"""Credit: ``model_scale`` times the measured held-out improvement of the current model over the model this episode
entered with, plus the validation credit the parent ledger attributes to predictions made in this episode.

Carried from the old ``credit.py`` (``HPCEpisodeCredit.credit_view``; ``_quality`` is ``task.py model_quality``
because the fit tool uses it too; ``credit_kind`` is deleted). Credit is signed (a worse current model gives a
negative gain) and is never bounded, clamped or rescaled here. A model trained on any case outside the
commission's original history has no measured quality and adds no gain: its improvement is credited later,
prospectively, when real outcomes arrive. Actual job credit is not counted here
(``actual_job_credit_counted_here`` is ``False``). Repeated polling adds none.

The ledger reads (the commission, the entry row, the current model, the credit rows) go through the ledger
primitives of ``task.py``, which are BLOCKED-ON-JOB-SERVICE (the parent-owned HPC ledger is not custody records
yet): they raise where they are reached. Before this episode's first unit (``hpc_initialize``) the model entry
does not exist and no prediction was made in this episode, so the old formula's value is zero and nothing is read;
``summary['initialized']`` says whether that unit completed."""
from .task import (current_model, ledger_commission, ledger_credit_view, ledger_read, ledger_records,
                   model_quality)


def credit_view(reader, owner, episode_id, initialized):
    """The old ``credit_view``: the credit and its parts."""
    if not initialized:
        return {'credit': 0.0, 'model_quality_improvement': 0.0, 'prospective_validation_credit': 0.0,
                'actual_job_credit_counted_here': False}
    commission = ledger_commission(reader, owner)
    entries = ledger_records(reader, owner, 'model_entry')
    entry = next((row['body'] for row in entries if row['id'] == 'entry:' + episode_id), None)
    current = model_quality(commission, ledger_read(reader, owner, current_model(reader, owner)))
    gain = (current - entry['quality'] if entry and current is not None and entry['quality'] is not None
            else 0.)
    validation = sum(row['credit'] for row in ledger_credit_view(reader, owner)['contributions']
                     if row['kind'] == 'validation'
                     and ledger_read(reader, owner, row['evidence_id']).get('prediction_episode_id') == episode_id)
    return {'credit': commission['credit']['model_scale'] * gain + validation,
            'model_quality_improvement': gain, 'prospective_validation_credit': validation,
            'actual_job_credit_counted_here': False}


def credit(summary, records):
    return credit_view(records, summary['owner_episode_id'], summary['episode_id'], summary['initialized'])['credit']
