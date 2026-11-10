"""Recall observed in-process units in their original completion order.

This is an opt-in journal projection, not an execution backend. It starts no
work, admits no new receipt and computes no credit. The ordinary controller
still re-observes the original inputs and must match its saved observations.
"""
from dataclasses import dataclass
import json

from method_loop import ClosedRecord, EpisodeGoal, EpisodeRecord, EpisodeRequest
from method_loop.episode import Contribution, EpisodeCompletion, EpisodeUpdate, _AcquiredUnit
from method_loop.identities import EpisodeRef, UnitRef
from method_loop.durable import canonical

from .episode_journal import WorkflowError
from .episode_return_records import EpisodeReturnRecords


VERSION = 'inprocess_completion_order_v1'


def require(condition, code):
    if not condition:
        raise WorkflowError('inprocess_replay_' + code)


@dataclass(frozen=True)
class _SavedRecord(ClosedRecord):
    value: dict
    identifiers: tuple = ()

    def as_record(self):
        return self.value

    def audit_identifiers(self):
        return self.identifiers


@dataclass(frozen=True)
class _ObservedUnit:
    label: str
    decision_index: int
    owner_path: tuple
    unit_ref: UnitRef
    acquired: _AcquiredUnit

    def acquire(self, context):
        parent = context._active_episodes.get(context.path)
        require(context.path == self.owner_path and parent is not None
            and EpisodeRef(context.require_run_id(), context.path).episode_id == self.unit_ref.episode_id
            and len(context._episode_records.get(context.path, ())) == self.unit_ref.unit_index,
            'completion_owner_conflict')
        child = self.acquired.child_record
        if child is not None:
            require(child.path[:-1] == context.path and child.run_id == context.require_run_id()
                and child.goal.parent_goal_id == parent.goal.goal_id, 'child_owner_conflict')
            require(not any(update.record_id == child.episode_id
                for update in context._child_updates.get(context.path, ())), 'duplicate_child_return')
            context._receive_child_update(self.acquired.contribution.episode_update)
        return self.acquired

    async def acquire_async(self, context):
        return self.acquire(context)


class InProcessReplay:
    def __init__(self, workflow):
        self.workflow, self.store, self.db = workflow, workflow.store, workflow.store.db
        self.run_id = workflow.run_id
        with self.store.transaction():
            self.db.execute('''CREATE TABLE IF NOT EXISTS runtime_inprocess_completion_revisions(
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                revision INTEGER NOT NULL, original_decision_index INTEGER NOT NULL,
                snapshot TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,sequence,revision))''')

    def _latest(self, episode_id, sequence):
        return self.db.execute('SELECT revision,snapshot FROM runtime_inprocess_completion_revisions '
            'WHERE run_id=? AND episode_id=? AND sequence=? ORDER BY revision DESC LIMIT 1',
            (self.run_id, episode_id, sequence)).fetchone()

    def _archive(self, record):
        reference = getattr(record, 'archived_record', None) or getattr(record, 'reference', None)
        return (reference if reference is not None else self.workflow.archive.store(record)).descriptor()

    def capture(self, source):
        """Append metadata only for actual observed units and explicit report revisions."""
        context = source._execution_context
        if context is None:
            return
        records = context._episode_records.get(source.path, ())
        for unit in records:
            sequence = unit.unit_ref.unit_index
            observed = self.workflow.journal.row('runtime_observations', source.episode_id, sequence)
            if observed is None:
                continue  # An acquisition/observation which has not committed is not a receipt.
            observation = json.loads(observed['observation'])
            require(observation['unit_ref'] == unit.unit_ref.as_record()
                and observation['label'] == unit.unit_label, 'observed_unit_conflict')
            previous = self._latest(source.episode_id, sequence)
            old = None if previous is None else json.loads(previous['snapshot'])
            update = unit.episode_update.as_record() if unit.episode_update is not None else None
            if old is not None and old['episode_update'] == update:
                continue
            admission_index = observation['decision_index']
            if update is not None:
                attempts = self.db.execute('SELECT decision_index,contract,form,failure '
                    'FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? '
                    'AND child_episode_id=? ORDER BY decision_index DESC',
                    (self.run_id, source.episode_id, update['record_id']))
                matching = [row for row in attempts if (
                    update['report'] is not None and row['form'] is not None and row['failure'] is None
                    and json.loads(row['form']) == update['report']
                    and json.loads(row['contract']) == update['report_contract']) or (
                    update['report'] is None and row['failure'] is not None
                    and json.loads(row['failure']) in update['delivery_failures'])]
                require(bool(matching), 'original_report_attempt_required')
                admission_index = matching[0]['decision_index']
            snapshot = {'version': VERSION, 'run_id': self.run_id, 'episode_id': source.episode_id,
                'unit_ref': unit.unit_ref.as_record(), 'original_decision_index': observation['decision_index'],
                'episode_update': update, 'admission_decision_index': admission_index,
                'child_archive': None if unit.child is None else self._archive(unit.child),
                'child_result_archive': None if unit.child_result is None else self._archive(unit.child_result),
                'audit_identifiers': [] if unit.episode_update is None
                    else list(unit.episode_update._audit_identifiers),
                'goal_result': None if unit.goal_result is None else unit.goal_result.as_record()
                    if hasattr(unit.goal_result, 'as_record') else unit.goal_result,
                'received_record_refs': list(self.workflow.receipts.known(source.episode_id))}
            if old is not None:
                require(all(snapshot[key] == old[key] for key in (
                    'version', 'run_id', 'episode_id', 'unit_ref', 'original_decision_index',
                    'child_archive', 'child_result_archive', 'goal_result')), 'unit_revision_conflict')
                require(update is not None and admission_index > old['admission_decision_index'],
                    'explicit_report_revision_required')
            revision = 0 if previous is None else previous['revision'] + 1
            self.db.execute('INSERT INTO runtime_inprocess_completion_revisions VALUES(?,?,?,?,?,?)',
                (self.run_id, source.episode_id, sequence, revision,
                 observation['decision_index'], canonical(snapshot)))

    def unfinished(self, source):
        from .episode_completion import observes_action_outcome
        result = []
        rows = self.db.execute('SELECT a.decision_index,a.action,a.result FROM runtime_actions a '
            'LEFT JOIN runtime_observations o ON o.run_id=a.run_id AND o.episode_id=a.episode_id '
            "AND json_extract(o.observation,'$.decision_index')=a.decision_index "
            'WHERE a.run_id=? AND a.episode_id=? AND o.unit_index IS NULL ORDER BY a.decision_index',
            (self.run_id, source.episode_id))
        for row in rows:
            action = json.loads(row['action'])
            outcome = None if row['result'] is None else json.loads(row['result'])
            if outcome is None or observes_action_outcome(action['kind'], outcome.get('status')):
                result.append(row['decision_index'])
        return result

    def unit(self, source, sequence):
        from .runtime import Record, TypedReportContract
        observed = self.workflow.journal.row('runtime_observations', source.episode_id, sequence)
        if observed is None:
            return None
        saved = self._latest(source.episode_id, sequence)
        require(saved is not None, 'original_completion_snapshot_required')
        snapshot, observation = json.loads(saved['snapshot']), json.loads(observed['observation'])
        reference = UnitRef(source.episode_id, sequence)
        index = observation['decision_index']
        require(source.request.message.as_record().get('inprocess_completion_order') == {'version': VERSION}
            and snapshot['version'] == VERSION and snapshot['run_id'] == self.run_id
            and snapshot['episode_id'] == source.episode_id
            and snapshot['unit_ref'] == observation['unit_ref'] == reference.as_record()
            and snapshot['original_decision_index'] == index, 'completion_identity_conflict')
        action = self.workflow.journal.row('runtime_actions', source.episode_id, index)
        require(action is not None and action['credit'] is not None
            and action['credit'] == observation['credit']['credit'], 'original_action_credit_conflict')
        require(set(snapshot['received_record_refs']) <= set(self.workflow.receipts.known(source.episode_id)),
            'original_receipt_prefix_missing')
        controller_input = Record(observation['credit'])
        update, child_record, child_result = None, None, None
        body = snapshot['episode_update']
        if body is not None:
            records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='inprocess_replay_')
            parent_context = self.workflow.binding_context(source)
            records.authenticate(parent_context)
            child_row = self.workflow.journal.row('runtime_episodes', body['record_id'])
            require(child_row is not None and child_row['state'] == 'yielded'
                and json.loads(child_row['archive']) == snapshot['child_archive'], 'child_archive_conflict')
            archive = self.workflow.archive_reference(snapshot['child_archive'])
            closed = archive.load()
            request_value = json.loads(child_row['request'])
            path = tuple(map(tuple, json.loads(child_row['path'])))
            require(closed['request'] == request_value and closed['goal'] == body['goal']
                and path[:-1] == source.path and closed['episode_id'] == body['record_id']
                and closed['run_id'] == self.run_id
                and closed['units_consumed'] == body['completion']['units_consumed']
                and closed['ended_by'] == body['completion']['ended_by']
                and closed['end_reason'] == body['completion']['end_reason']
                and body['controller_input'] == observation['credit'], 'original_child_conflict')
            form, contract_body = body['report'], body['report_contract']
            identifiers = tuple(snapshot['audit_identifiers'])
            report = None
            if form is not None:
                admitted_child, original_form, schema = records._attempt(
                    parent_context, snapshot['admission_decision_index'])
                require(admitted_child.episode_id == body['record_id'] and original_form == form
                    and contract_body['measurements']['schema'] == schema, 'original_admission_conflict')

                def original_admission(value):
                    require(value == form, 'frozen_form_conflict')
                    # These are already-owned receipts. No receive/grant callback runs.
                    return snapshot['received_record_refs']

                contract = TypedReportContract(contract_body['decision'], schema, lambda *_: False,
                    recorded_admission=original_admission)
                require(contract.as_record() == contract_body, 'frozen_contract_conflict')
                report = contract.admit(form, audit_identifiers=identifiers)
            else:
                attempt = self.db.execute('SELECT failure FROM runtime_report_attempts WHERE run_id=? '
                    'AND parent_episode_id=? AND decision_index=?',
                    (self.run_id, source.episode_id, snapshot['admission_decision_index'])).fetchone()
                require(attempt is not None and attempt['failure'] is not None
                    and json.loads(attempt['failure']) in body['delivery_failures'], 'original_failure_conflict')
            original_contract = request_value['report_contract']
            child_contract = TypedReportContract(original_contract['decision'],
                original_contract['measurements']['schema'], lambda *_: False)
            require(child_contract.as_record() == original_contract, 'child_request_contract_conflict')
            request = EpisodeRequest(EpisodeGoal.from_record(request_value['goal']),
                Record(request_value['message']), child_contract)
            child_record = EpisodeRecord(path[-1][0], path[-1][1], closed['units_consumed'],
                closed['ended_by'], (), closed['controller_state'], request, path=path,
                end_reason=closed['end_reason'], episode_ref=EpisodeRef(self.run_id, path), archived_record=archive)
            result = self.workflow.archive_reference(snapshot['child_result_archive']).load()
            child_result = _SavedRecord(result, identifiers)
            update = EpisodeUpdate(body['record_id'], EpisodeGoal.from_record(body['goal']),
                EpisodeCompletion(**body['completion']), controller_input, report,
                tuple(Record(failure) for failure in body['delivery_failures']), identifiers)
        else:
            require(snapshot['child_archive'] is None and snapshot['child_result_archive'] is None,
                'unexpected_child_archive')
        acquired = _AcquiredUnit(Contribution(controller_input, update, snapshot['goal_result']),
            child_record, child_result)
        return _ObservedUnit(observation['label'], index, source.path, reference, acquired)
