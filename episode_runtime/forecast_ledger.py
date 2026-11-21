"""The runner's access to the estimate ledger for an Episode whose yield controller is a ``ForecastYieldController``.

Only the runner builds a ``ForecastLedger`` (``BoundEpisode.forecast_ledger``). It is given to the forecast controller
(read access: ``history``) and used by the Episode's source to record, in the ledger (``EstimateTable``,
``estimate_table.py``), what was expected of every unit before it ran (``expect``) and what happened (``resolve``).
No episode function, tool or model is handed it, so nothing a model does writes the ledger.

A unit's action kind is ``<binding path>:<action type>`` (for example ``a101/sequence_homology_evidence:bvbrc_msa``),
so the history of a kind carries over to every later run of the same episode. The ledger key of a unit is
``forecast:<episode id>:<position>``.

``history`` is the earlier runs' record of one action kind, in the form ``yield_control.forecast_actions`` reads. It is
recorded in the run journal the first time it is asked for in an Episode (like a clock point), so a resumed run, and
every replay of a decision, sees the history it first saw, whatever the ledger holds by then. The rows of this
Episode's own units are left out of it (they enter the controller as its own observations).

The definition: the forecast controller hands the ledger, once (``define``), the function that names, per action type,
the definition of credit and ceiling that action's shares are on (``ForecastParameters.definition_of``: the credit's
definition and the action's own ceiling version, so changing one action's ceiling leaves every other action's history
whole). Every forecast row ``expect`` writes records its action's definition, and the shares of ``history`` (``rows``)
are only the resolved rows of the action kind whose recorded definition is the action's; a row that records none
(written before definitions were recorded) or another one gives no share, since a share learned under another credit or
ceiling is on another scale. Seconds are not credit: the measured seconds of ``history`` (``seconds``: unit and decision
seconds) are every resolved row of the kind whatever its definition, and the job durations (``job_seconds``, the service
jobs' own rows) likewise. Writing or reading without a definition raises.
"""
from __future__ import annotations

from datetime import datetime, timezone

from yield_control import UNBOUNDED_TEXT

KEY_PREFIX = 'forecast:'
OUTCOME = 'finished'
ROWS_LIMIT = 1_000_000


def _seconds(value):
    return datetime.fromisoformat(value).timestamp()


class ForecastLedger:
    def __init__(self, run_services, user, recorder, *, episode_id, binding_path):
        self._services, self._user, self._recorder = run_services, user, recorder
        self._episode_id, self._binding_path = episode_id, binding_path
        self._definition_of = None

    def define(self, definition_of):
        """The function naming, per action type, the definition of credit and ceiling its forecasts are on; given
        once, by the controller."""
        if not callable(definition_of):
            raise ValueError('forecast_ledger_definition_required')
        if self._definition_of is not None:
            raise RuntimeError('forecast_ledger_already_has_a_definition')
        self._definition_of = definition_of

    def _defined(self, action_type):
        if self._definition_of is None:
            raise RuntimeError('forecast_ledger_has_no_definition')
        definition = self._definition_of(action_type)
        if type(definition) is not str or not definition:
            raise ValueError('forecast_ledger_definition_required:' + action_type)
        return definition

    def _table(self):
        return self._services.service('estimate_table', self._user)

    def kind(self, action_type):
        return self._binding_path + ':' + action_type

    def key(self, position):
        return KEY_PREFIX + self._episode_id + ':' + str(position)

    # -- history: read -----------------------------------------------------------------------------------------
    def history(self, action_type, job_prefix, forget):
        """The recorded history of ``action_type`` for the controller: ``{'rows': [{'ceiling', 'gain', 'weight'}],
        'seconds': [{'seconds', 'decision_seconds'}], 'job_seconds': [seconds]}``: ``rows`` (the shares) only those
        recorded under the action's definition, ``seconds`` every resolved row of the kind whatever its definition;
        ``job_prefix`` (or ``None``) names the ledger kinds of the jobs the action launches and ``forget`` weights the
        rows by the table's forgetting policy (and drops those past it). A history journaled before the seconds were
        kept apart (no ``seconds``) raises: it cannot be read under this rule."""
        name = 'forecast_history.' + action_type
        definition = self._defined(action_type)
        history = self._recorder.recorded(name, lambda: self._read(action_type, job_prefix, forget, definition))
        if set(history) != {'rows', 'seconds', 'job_seconds'}:
            raise RuntimeError('forecast_history_journaled_before_per_action_definitions:' + action_type)
        return history

    def _read(self, action_type, job_prefix, forget, definition):
        table = self._table()
        now = datetime.now(timezone.utc).timestamp()
        policy = table.policy()

        def weight(row):
            if not forget:
                return 1.0
            age = now - _seconds(row['expected_at'])
            if age > policy['history_seconds']:
                return None
            return 2 ** (-max(age, 0.0) / policy['history_half_life_seconds'])
        own = KEY_PREFIX + self._episode_id + ':'
        rows, seconds = [], []
        for row in table.rows(self.kind(action_type), ROWS_LIMIT):
            if row['actual'] is None or row['key'].startswith(own) or weight(row) is None:
                continue
            actual, expected = row['actual'], row['expected']
            seconds.append({'seconds': actual['duration_seconds'], 'decision_seconds': actual['decision_seconds']})
            if expected.get('definition') == definition:
                rows.append({'ceiling': expected['ceiling'], 'gain': actual['gain'], 'weight': weight(row)})
        job_seconds = []
        if job_prefix is not None:
            for kind in table.kinds():
                if kind.startswith(job_prefix):
                    job_seconds += [row['actual']['duration_seconds'] for row in table.rows(kind, ROWS_LIMIT)
                                    if row['actual'] is not None and row['actual']['outcome'] == OUTCOME
                                    and 'duration_seconds' in row['actual'] and weight(row) is not None]
        return {'rows': rows, 'seconds': seconds, 'job_seconds': job_seconds}

    # -- the unit's expectation and resolution: written by the runner only ------------------------------------
    def expect(self, position, action_type, row, at):
        """Record, before unit ``position`` runs, what the controller forecast for its action (``row`` of
        ``forecast_actions``), with the definition of its action it was made under. A forecast that is unknown is written as a gain
        of 0 with ``forecast`` null."""
        forecast, ceiling = row['forecast_gain'], row['ceiling']
        value = 0.0 if forecast is None else forecast
        upper = value if ceiling == UNBOUNDED_TEXT else ceiling
        self._table().expect(self.kind(action_type), {
            'gain': {'value': value, 'lower': 0.0, 'upper': upper},
            'cost': 0.0 if row['expected_seconds'] is None else row['expected_seconds'],
            'ceiling': ceiling, 'forecast': forecast, 'expected_seconds': row['expected_seconds'],
            'seconds_basis': row['seconds_basis'], 'definition': self._defined(action_type)}, key=self.key(position), at=at)

    def resolve(self, position, rise, unit_seconds, decision_seconds, at):
        """Record what unit ``position`` obtained: the rise of the credit and its measured seconds."""
        self._table().resolve(self.key(position), {
            'gain': rise, 'cost': unit_seconds, 'outcome': OUTCOME, 'duration_seconds': unit_seconds,
            'decision_seconds': decision_seconds}, at=at)
