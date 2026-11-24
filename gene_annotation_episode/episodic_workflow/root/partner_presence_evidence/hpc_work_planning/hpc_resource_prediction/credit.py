"""Credit: the measured model improvement, carried from the old ``credit.py`` (``HPCEpisodeCredit.credit_view``;
credit kind ``operational``).

``credit = commission.credit.model_scale * gain + validation`` where ``gain`` is the held-out quality of the current
model minus the quality recorded at this episode's entry (``model_entry``), and ``validation`` is the sum of the
ledger's ``validation`` contributions attributed to this prediction episode. Actual job credit is not counted here.
Never bounded, clamped or rescaled.

``credit`` has no services and the ledger is outside the Store, so what the old credit read from the ledger is in the
summary: every tool of this episode ends by returning the ledger's present view in its outcome (``ledger``:
the current model's held-out quality, the entry quality, the validation contribution), and ``internal_summary``
keeps the latest one. Before the first unit (the ledger not yet opened) no model has been measured: gain and
validation are zero and the credit is zero."""


def credit_view(state):
    """The old credit view over the state (a summary, or its base before the credit view is added)."""
    ledger = state['ledger']
    if ledger is None:
        return {'credit': 0.0, 'model_quality_improvement': 0.0, 'prospective_validation_credit': 0.0,
                }
    entry, current = ledger['model_entry'], ledger['current_quality']
    gain = current - entry['quality'] if entry and current is not None and entry['quality'] is not None else 0.
    validation = ledger['validation_credit']
    return {'credit': ledger['commission']['credit']['model_scale'] * gain + validation,
            'model_quality_improvement': gain, 'prospective_validation_credit': validation,
            }


def credit(summary, records):
    return credit_view(summary)['credit']
