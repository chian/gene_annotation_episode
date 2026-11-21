"""The HPC ledger as a declared work table: immutable evidence of one commissioned HPC parent, and its credit.

The ledger of an HPC commission (its forecasts, measurements, scores and accepted results) was one private SQLite
file per commissioned parent, shared by path with the parent's children. It is now rows of the declared work table
``HPC_LEDGER``, written and read only through the custody-scoped store. A row belongs to the Episode whose tool
wrote it; another Episode reads it only when it holds it, so a child returns the rows it wrote in a ``record_refs``
field and a parent passes the rows a child needs in the assignment. ``HpcLedger`` is the ledger an Episode sees:
the rows of one commission among the rows it holds.

    ledger = HpcLedger.open(ctx.store, commission)           # a tool: writes the commission row
    ledger = HpcLedger.existing(records, ledger_id)          # credit, summary, a child: reads held rows only

- **Evidence is immutable.** ``put(kind, body)`` names the row by ``kind`` and the digest of ``body`` (or by the
  ``identity`` given). The same evidence again is the same row; other content under a held identity raises
  ``immutable_hpc_evidence_conflict``.
- **Credit is derived, not stored.** ``credit_view()`` computes the credit from the held evidence in receipt order:
  an accepted obligation counts once (the first acceptance stands), the latest model credit replaces the earlier
  one, and each validation slot is scored against the first forecast that reserved it (``freeze``), a later
  measurement replacing an earlier one and a censored one never replacing an actual finish.
- **The scoring functions are the caller's.** ``score`` is given the episode's own ``log_score``,
  ``measured_value`` and ``forecast_metric`` (each axis keeps its prediction library).
- There is no record of operations that already ran: the system journals each unit, and a unit that runs again
  writes the same evidence.
"""
from __future__ import annotations

from method_loop.jsonvalue import canonical, closed_copy, content_digest
from episode_runtime import TableDeclaration

HPC_LEDGER = TableDeclaration(name='hpc_ledger',
                              columns=('ledger', 'identity', 'kind', 'body', 'slots', 'source_refs'),
                              key=('ledger', 'identity'), record_refs=('source_refs',))
COMMISSION = 'commission'


def ledger_id(commission):
    """The identity of the ledger of ``commission``: every Episode that is given the same commission names the
    same ledger."""
    return 'hpc_' + content_digest(commission)[:32]


class HpcLedger:
    """The evidence rows of one HPC commission that an Episode holds, through ``store`` (``ctx.store`` in a tool,
    the read-only ``records`` elsewhere; a write needs ``ctx.store``)."""

    def __init__(self, store, ledger):
        self._store, self.ledger = store, ledger
        self.commission = self.read(COMMISSION)

    @classmethod
    def open(cls, store, commission):
        """The ledger of ``commission``, with its commission row written by this unit when the Episode does not
        hold it yet."""
        commission = closed_copy(commission, 'hpc_commission', ValueError)
        ledger = ledger_id(commission)
        if not store.table(HPC_LEDGER).select({'ledger': ledger, 'identity': COMMISSION}):
            store.table(HPC_LEDGER).put({'ledger': ledger, 'identity': COMMISSION, 'kind': COMMISSION,
                                         'body': commission, 'slots': [], 'source_refs': []})
        return cls(store, ledger)

    @classmethod
    def existing(cls, store, ledger):
        """The ledger ``ledger`` as the Episode holds it; ``original_hpc_commission_missing`` when it does not
        hold the commission row."""
        return cls(store, ledger)

    # -- evidence --------------------------------------------------------------------------------------------
    def _rows(self, where):
        return self._store.table(HPC_LEDGER).select({'ledger': self.ledger, **where})

    def refs(self):
        """The reference of every held row of this ledger and of every Store record a row names in its
        ``source_refs``, in receipt order (to pass or return in custody: a pass carries only the records named,
        so the artifact a row names travels with the row)."""
        return list(dict.fromkeys(ref for row in self._rows({}) for ref in (row['id'], *row['source_refs'])))

    def read(self, identity):
        rows = self._rows({'identity': identity})
        if not rows:
            raise ValueError(('original_hpc_commission_missing:' if identity == COMMISSION
                              else 'unknown_hpc_evidence:') + str(identity))
        if any(canonical(row['body']) != canonical(rows[0]['body']) or row['kind'] != rows[0]['kind']
               for row in rows):
            raise ValueError('immutable_hpc_evidence_conflict:' + identity)
        return rows[0]['body']

    def records(self, kind):
        """The held evidence of ``kind`` in receipt order, each identity once: ``[{'id', 'body', 'slots'}]``."""
        found = {}
        for row in self._rows({'kind': kind}):
            found.setdefault(row['identity'], {'id': row['identity'], 'body': row['body'], 'slots': row['slots']})
        return list(found.values())

    def put(self, kind, body, *, identity=None, slots=(), source_refs=()):
        """Write one piece of evidence; its identity. ``source_refs`` are Store records the evidence was made
        from (they must be readable by the unit)."""
        body = closed_copy(body, 'hpc_evidence', ValueError)
        identity = kind + '_' + content_digest(body) if identity is None else identity
        held = self._rows({'identity': identity})
        if any(row['kind'] != kind or canonical(row['body']) != canonical(body) for row in held):
            raise ValueError('immutable_hpc_evidence_conflict:' + identity)
        if not held:
            self._store.table(HPC_LEDGER).put({'ledger': self.ledger, 'identity': identity, 'kind': kind,
                                               'body': body, 'slots': list(slots),
                                               'source_refs': list(source_refs)})
        return identity

    # -- forecasts, scores and credit ------------------------------------------------------------------------
    def freeze(self, body, eligible_slots):
        """Freeze a forecast; it reserves each of ``eligible_slots`` that no earlier forecast reserved."""
        return self.put('forecast', body, slots=eligible_slots)

    def reserved_slots(self):
        """``{slot: forecast identity}``: the first held forecast that named each slot."""
        reserved = {}
        for record in self.records('forecast'):
            for slot in record['slots']:
                reserved.setdefault(slot, record['id'])
        return reserved

    def model_credit(self, model_ref, improvement):
        """A new model replaces the model credit, negative corrections included."""
        return self.put('model_credit', {'model_ref': model_ref, 'improvement': improvement})

    def accept(self, obligation_id, result_ref):
        """The obligation's frozen accomplishment predicate was checked against the result by the caller."""
        if obligation_id not in self.commission['obligations']:
            raise ValueError('unknown_hpc_obligation:' + str(obligation_id))
        return self.put('accept', {'obligation_id': obligation_id, 'result_ref': result_ref})

    def score(self, measured_ref, *, log_score, measured_value, forecast_metric):
        """Score the measurement ``measured_ref`` against the forecast that reserved each validation slot; the
        identities of the scores written. A forecast is never scored against an event known when it was issued."""
        measured = self.read(measured_ref)
        reserved = self.reserved_slots()
        credit = self.commission['credit']
        written = []
        for slot in credit['validation_slots']:
            metric = slot['metric']
            if slot['id'] not in reserved or metric not in measured['metrics']:
                continue
            forecast_id = reserved[slot['id']]
            forecast = self.read(forecast_id)
            observation = measured['metrics'][metric]
            if forecast['plan_id'] != measured['plan_id'] or observation['observed_at'] <= forecast['issued_at']:
                continue
            baseline = forecast_metric(forecast['reference'], metric)
            predicted = forecast_metric(forecast['prediction'], metric)
            if predicted is None or baseline is None:
                continue
            elapsed = forecast['elapsed'].get(metric, 0.)
            actual = measured_value(metric, observation)
            predicted_elapsed = predicted.get('elapsed', elapsed)
            baseline_elapsed = baseline.get('elapsed', elapsed)
            if actual < max(predicted_elapsed, baseline_elapsed):
                continue
            censored = observation.get('censored', False)
            gain = (log_score(predicted, actual - predicted_elapsed, censored=censored)
                    - log_score(baseline, actual - baseline_elapsed, censored=censored))
            written.append(self.put('score', {
                'forecast_id': forecast_id, 'measured_ref': measured_ref, 'slot': slot['id'],
                'value': credit['validation_scale'] * slot['weight'] * gain, 'censored': censored,
                'observed_at': observation['observed_at'],
                'prediction_episode_id': forecast.get('prediction_episode_id'),
                'model_ref': forecast.get('model_ref')}))
        return written

    def credit_view(self):
        """``{'credit', 'components': {'actual', 'model', 'validation'}, 'contributions'}`` from the held evidence."""
        contributions = {}
        for record in self.records('accept'):
            obligation = record['body']['obligation_id']
            contributions.setdefault('actual:' + obligation, {
                'kind': 'actual', 'credit': self.commission['obligations'][obligation]['credit'],
                'evidence_id': record['body']['result_ref']})
        for record in self.records('model_credit'):
            contributions['model'] = {
                'kind': 'model', 'credit': self.commission['credit']['model_scale'] * record['body']['improvement'],
                'evidence_id': record['body']['model_ref']}
        chosen = {}
        for record in self.records('score'):
            body, prior = record['body'], chosen.get(record['body']['slot'])
            if prior is not None and (prior['body']['observed_at'] > body['observed_at']
                                      or (not prior['body']['censored'] and body['censored'])):
                continue
            chosen[body['slot']] = record
        for slot, record in chosen.items():
            contributions['validation:' + slot] = {'kind': 'validation', 'credit': record['body']['value'],
                                                   'evidence_id': record['id']}
        rows = [{'slot': slot, **contributions[slot]} for slot in sorted(contributions)]
        components = {kind: sum(row['credit'] for row in rows if row['kind'] == kind)
                      for kind in ('actual', 'model', 'validation')}
        return {'credit': sum(components.values()), 'components': components, 'contributions': rows}


__all__ = ['HPC_LEDGER', 'HpcLedger', 'ledger_id']
