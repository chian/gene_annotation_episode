"""What the runner records for every Episode besides its units: the credit its yield controller is built from,
model calls, what its decisions read from services, record custody and unit attempts.

The runner builds these per Episode and gives them to the Episode type on its ``BoundEpisode``. Everything is
written to the run journal; on resume they are rebuilt from it, so the controller is built from the recorded
initial credit, recorded model responses are returned instead of asking again and every receipt is reloaded.
(Units, their controller inputs, steps, outcomes and updates are recorded by the runner's ``on_unit`` hook from
``method_loop``'s own trace and restored as ``ResumeUnit``s.)
An episode's own files never call these objects: ``EpisodeBinding`` does. An episode receives the read-only
``RecordReader`` (``view.records``, ``records`` of ``credit``, ``action`` and ``read_from_child``), the
``DecisionContext`` (``ctx`` of ``decide`` and ``action``: settings, read handles of the declared services whose
reads are recorded per unit position, the recorded clock) and, in a tool, the ``UnitContext`` (``ctx``: the
custody-scoped store, services, the recorded model, operation key, what an abandoned attempt left).

**Custody.** An Episode holds a Store record, artifact or work-table row only by a receipt the runner recorded:

- ``entry``: named in a ``record_refs`` field of the entry assignment (the run's caller supplied it);
- ``commissioned``: named in a ``record_refs`` field of the assignment its parent commissioned it with;
  the runner admits the pass only when the parent itself holds the record;
- ``returned``: named in a ``record_refs`` field of a direct child's admitted result; the runner admits it
  only when the child holds the record;
- ``produced``: written to the Store by one of its own tool units through the custody-scoped store
  (``ctx.store``). Every write runs in a Store transaction (the tool's own ``ctx.store.transaction()``, or one
  the scoped store opens for the single write). The receipt is written in that same Store transaction (a system
  table of the Store file, ``store_ledger.py``), so a record and its receipt commit or roll back together; the
  journal's copy is written after the commit and, when a process is cut between the two, written from the
  Store's the next time the Episode is built.

A receipt names the record, how it was received, from which Episode, to which Episode, at which unit of the
giving (commission) or receiving (return, production) Episode, and which Episode produced it at which unit
(``None`` for a record the entry caller supplied). The first receipt of a record stands. Reading any other
record raises ``CustodyError``. Record content stays in the run's one shared Store. The three passes between
Episodes (``admit_entry``, ``pass_records``, ``return_records``) are functions of this module that only the
runner calls; no object an episode receives has an admission method.

**Unit attempts.** Before a tool runs or a child is commissioned the runner journals that the unit began
(its label, its operation key and the digest of its arguments); the unit's completion marks it finished. On
resume a unit that began and did not finish runs again with the same operation key and ``resumed`` true.

**What an unfinished unit wrote: one rule.** When a run is resumed, what a unit that did not finish produced is
abandoned before anything else happens: its receipts leave the Episode's custody (they stay in the journal as
trace), a work-table row it created is removed and a row it rewrote is put back as it stood before the unit.
From then on nothing the abandoned attempt wrote is visible through ``view.records`` or the ``records`` of
``credit``, ``action`` and ``read_from_child``, so the decision for that unit is rebuilt from the state the
first attempt was decided on. Only the rerun's tool is told (``ctx.abandoned``) and, while it runs, may read the
abandoned records through ``ctx.store``; ``ctx.store.reclaim(ref)`` makes one its own product again (it is then
held as produced by the rerun). What it does not reclaim is readable by nothing once the tool returns. The system
guarantees the key and the journal, not the external world: a tool with an external side effect must be
idempotent on the key.

**The diagnostics of tool outcomes.** A tool that reports what went wrong names the record of it in what it
returns, under a key ``diagnostic_ref`` (at any depth). Custody knows those references for the Episode's tool
units (``is_diagnostic``): of every recorded unit from the journal, and of the unit whose tool has just returned
from the moment it returned. The reader answers ``is_diagnostic_ref(ref)`` from it, so that a library function
can keep a diagnostic from being read as a source; nothing is kept for it but the unit outcomes themselves.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import threading

from method_loop import UNBOUNDED
from method_loop.jsonvalue import closed_copy, content_digest


class CustodyError(RuntimeError):
    """A record was read, passed, returned or written against the custody rules."""


def diagnostic_refs(value):
    """Every reference a tool's returned value names as a diagnostic: the text under a key ``diagnostic_ref``, at
    any depth of the value."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == 'diagnostic_ref':
                if type(child) is str:
                    yield child
            else:
                yield from diagnostic_refs(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from diagnostic_refs(child)


class UnitPosition:
    """The unit an Episode's source is choosing or acquiring (``bound.position``). Model calls and record
    receipts are keyed by it; it starts after the units already recorded for the Episode."""

    def __init__(self, journal, run_id, path):
        self.position = len(journal.units(run_id, path))

    def begin(self, position):
        """The Episode's source is choosing unit ``position``."""
        if type(position) is not int or position < 0:
            raise ValueError('unit_position_must_be_a_nonnegative_integer')
        self.position = position


class RecordedModel:
    """The run's model provider for one Episode; every call is recorded and replayed by unit and call index.

    The same object serves the decision loop (``decide`` asking through a ``ModelRequest``) and the Episode's
    tools (``ctx.model``): the calls of one unit position are numbered in the order they are made, the decision's
    first and the tool's after them, so a unit that runs again is given its recorded responses in the same order.
    """

    def __init__(self, journal, run_id, path, episode_id, provider, position):
        self._journal, self._run_id, self._path = journal, run_id, tuple(path)
        self._episode_id, self._provider, self._position = episode_id, provider, position
        self._calls = {}

    async def complete(self, role, instructions, context, output_schema):
        position = self._position.position
        index = self._calls.get(position, 0)
        self._calls[position] = index + 1
        request = closed_copy({'role': role, 'instructions': instructions, 'context': context,
                               'output_schema': output_schema}, 'model_request', TypeError)
        recorded = self._journal.recorded_model_call(self._run_id, self._path, position, index, request)
        if recorded is not None:
            return recorded
        response = await self._provider.complete(self._episode_id, role, instructions, context, output_schema)
        return self._journal.record_model_call(self._run_id, self._path, position, index, request,
                                               closed_copy(response, 'model_response', TypeError))


class InitialCredit:
    """The credit an Episode's yield controller is built from (``bound.initial_credit``): ``credit`` of the
    Episode's summary before any unit, recorded in the run journal. ``recorded(compute)`` is the recorded value, or
    ``compute()`` recorded now, when the Episode is entered for the first time. An Episode that is entered again
    (a resumed run, closed or cut; a child whose parent's unit runs again) holds from the start what its recorded
    units produced, so the credit its summary before any unit has by then is not the credit its controller
    started from: the controller is built from the record, and the units replayed to it give the recorded
    steps and the recorded stop."""

    def __init__(self, journal, run_id, path):
        self._journal, self._run_id, self._path = journal, run_id, tuple(path)

    def recorded(self, compute):
        return self._journal.initial_credit(self._run_id, self._path, compute)


class ServiceReads:
    """What the decisions of one Episode read from its declared services (``bound.reads``), recorded in the run
    journal by unit position. ``at(position)`` is the ``recorded(request, ask)`` function of the decision for unit
    ``position`` (``services.DecisionServices``): the value recorded for ``request`` at that position, or
    ``ask()`` recorded now. A decision that is made again (after a rejected answer, for a unit that runs again,
    on resume) therefore reads what it first read, whatever the service says by then."""

    def __init__(self, journal, run_id, path):
        self._journal, self._run_id, self._path = journal, run_id, tuple(path)

    def at(self, position):
        if type(position) is not int or position < 0:
            raise ValueError('service_read_position_must_be_a_nonnegative_integer')
        return lambda request, ask: self._journal.service_read(self._run_id, self._path, position, request, ask)


class Custody:
    """The records one Episode holds, with their receipts, and what its current unit attempt produced.

    Only the runner builds a ``Custody``. The readers and the scoped store an episode receives ask it whether a
    record may be read and tell it what a unit wrote; it has no admission method (see the module functions).

    Building it brings the Episode's custody to where its recorded units end: what a unit that did not finish
    produced is abandoned, the row writes of such a unit are taken back, the ``returned`` receipts of such a unit
    are dropped (the child unit runs again), and the journal's copy of every produced receipt is written from the
    Store's (``store_ledger.StoreLedger``)."""

    def __init__(self, journal, ledger, run_id, path, episode_id, position):
        self._journal, self._ledger, self._run_id, self.path = journal, ledger, run_id, tuple(path)
        self._owner = (run_id, episode_id)
        self._position = position
        self._recover()
        self._held = {receipt['ref']: receipt for receipt in journal.receipts(run_id, path)}
        # What the outcomes of the Episode's tool units name as their diagnostics (``is_diagnostic``).
        self._diagnostics = {ref for _, _, outcome, _ in journal.units(run_id, path) if outcome['kind'] == 'tool'
                             for ref in diagnostic_refs(outcome['outcome'])}
        self._attempt_produced = []
        self._abandoned = {}        # reference -> entry of ``abandoned()``, only while the rerun's own work runs
        self._pending = []          # one list of references per open scoped-store transaction, innermost last
        self.operation_key = None   # of the unit attempt in progress (``None`` outside a tool unit)
        self._unit_thread = None    # the thread the unit attempt in progress runs in
        self._open = []             # what the unit's tool has open besides transactions (a scratch directory)

    def _in_unit_thread(self):
        """Raise when custody is asked from a thread other than the one its unit runs in. A tool that computes in
        a worker thread gives the thread files of its own (``ctx.store.scratch()``); the thread has no Store."""
        if self._unit_thread is not None and threading.get_ident() != self._unit_thread:
            raise CustodyError('scoped_store_used_outside_the_thread_of_its_unit:' + repr(self.path))

    def _recover(self):
        unfinished = self._position.position
        self._ledger.abandon_unfinished(self._run_id, self.path, self._owner, unfinished)
        self._journal.drop_unfinished_returns(self._run_id, self.path, unfinished)
        for ref, unit, abandoned in self._ledger.receipts(self._run_id, self.path):
            if abandoned:
                self._journal.abandon_receipt(self._run_id, self.path, unit, ref)
            else:
                self._journal.record_receipt(self._run_id, self.path, self._produced_receipt(ref, unit))

    @property
    def unit(self):
        """The unit position the Episode is choosing or running."""
        return self._position.position

    # -- what the Episode holds ------------------------------------------------------
    def _provisional(self, ref):
        return any(ref in refs for refs in self._pending)

    def holds(self, ref):
        """Held by a recorded receipt, or written in a transaction of this unit that is still open."""
        self._in_unit_thread()
        return ref in self._held or self._provisional(ref)

    def refs(self):
        """Every held record reference, in receipt order (then what open transactions wrote)."""
        self._in_unit_thread()
        return tuple(dict.fromkeys((*self._held, *(ref for refs in self._pending for ref in refs))))

    def receipt(self, ref):
        """How this Episode holds ``ref``: ``{'ref', 'how', 'from', 'to', 'unit', 'producer', 'producer_unit'}``."""
        self._in_unit_thread()
        if ref in self._held:
            return dict(self._held[ref])
        if self._provisional(ref):
            return self._produced_receipt(ref, self._position.position)
        raise CustodyError('record_not_held:' + repr(self.path) + ':' + str(ref))

    def require_readable(self, ref):
        """Raise unless this Episode holds ``ref``. This is the rule of every read outside a running tool."""
        if not self.holds(ref):
            raise CustodyError('record_not_held:' + repr(self.path) + ':' + str(ref))

    def require_unit_readable(self, ref):
        """Raise unless the running tool may read ``ref``: the Episode holds it, or an abandoned attempt of the
        unit now running again produced it."""
        self._in_unit_thread()
        if not self.holds(ref) and ref not in self._abandoned:
            raise CustodyError('record_not_held:' + repr(self.path) + ':' + str(ref))

    def require_held(self, refs, code):
        """Raise ``CustodyError(code...)`` unless every one of ``refs`` is held by a recorded receipt."""
        unheld = [ref for ref in refs if ref not in self._held]
        if unheld:
            raise CustodyError(code + ':' + repr(self.path) + ':' + ','.join(unheld))

    # -- what the current unit attempt writes ----------------------------------------
    def _produced_receipt(self, ref, unit):
        return {'ref': ref, 'how': 'produced', 'from': self.path, 'to': self.path, 'unit': unit,
                'producer': self.path, 'producer_unit': unit}

    def produced(self, ref):
        """The current unit wrote ``ref`` inside the scoped-store transaction now open. The write is receipted
        when the outermost transaction commits."""
        self._in_unit_thread()
        if self.operation_key is None:
            raise CustodyError('record_written_outside_a_tool_unit:' + repr(self.path) + ':' + str(ref))
        if not self._pending:
            raise CustodyError('record_written_outside_a_scoped_store_transaction:' + repr(self.path) + ':'
                               + str(ref))
        if ref not in self._pending[-1]:
            self._pending[-1].append(ref)

    def in_transaction(self):
        return bool(self._pending)

    def begin_transaction(self):
        self._in_unit_thread()
        self._pending.append([])

    # -- what the unit's tool has open besides transactions ----------------------------
    def require_unit(self, what):
        """Raise unless a tool unit of this Episode is running, in this thread; its operation key."""
        self._in_unit_thread()
        if self.operation_key is None:
            raise CustodyError(what + '_outside_a_tool_unit:' + repr(self.path))
        return self.operation_key

    def opened(self, what):
        """The running tool opened ``what`` (a scratch directory); it must close it before the unit ends."""
        self.require_unit(what)
        self._open.append(what)

    def closed(self, what):
        self._open.remove(what)

    def seal_transaction(self):
        """The innermost transaction is about to commit. For the outermost one the Store's own receipt of each
        write is written now, in the Store transaction that holds the writes."""
        if len(self._pending) == 1:
            unit = self._position.position
            for ref in self._pending[0]:
                if ref not in self._held:
                    self._ledger.produced(self._run_id, self.path, ref, unit)

    def commit_transaction(self):
        """The innermost transaction committed: its writes join the enclosing transaction, or (the outermost)
        the journal's copy of their receipts is written."""
        refs = self._pending.pop()
        if self._pending:
            self._pending[-1].extend(ref for ref in refs if ref not in self._pending[-1])
            return
        unit = self._position.position
        for ref in refs:
            self._receive(self._produced_receipt(ref, unit))
            if ref not in self._attempt_produced:
                self._attempt_produced.append(ref)

    def rollback_transaction(self):
        """The innermost transaction rolled back: the Store no longer has its writes, and neither does custody."""
        self._pending.pop()

    def attempt_produced(self):
        """The records the current attempt of the current unit produced, in order."""
        return list(self._attempt_produced)

    def abandoned(self):
        """What the abandoned attempts of the unit now running again wrote: ``({'ref', 'producer_unit', 'written',
        'prior'}, ...)``. For a Store record or artifact ``written`` and ``prior`` are ``None`` (the tool reads it
        through its store). For a work-table row ``written`` is the row as the last abandoned attempt left it and
        ``prior`` the row as it stood before the unit and stands again (``None`` when the attempt created it)."""
        return tuple(dict(entry) for entry in self._abandoned.values())

    def reclaim(self, ref):
        """The unit running again takes ``ref``, which its abandoned attempt produced, as its own product; an
        abandoned row is written again as that attempt left it. Called inside a scoped-store transaction."""
        if ref not in self._abandoned:
            raise CustodyError('record_not_abandoned_by_this_unit:' + repr(self.path) + ':' + str(ref))
        if self._abandoned[ref]['written'] is not None:
            self._ledger.write_abandoned_row(self._owner, self._position.position, ref, self.operation_key)
        self.produced(ref)

    def begin_attempt(self, resumed, operation_key):
        """A unit's attempt starts; a rerun is told what the abandoned attempts of this unit wrote."""
        if self._pending:
            raise CustodyError('unit_began_inside_an_open_transaction:' + repr(self.path))
        unit = self._position.position
        self._abandoned = {}
        if resumed:
            rows = {item['ref']: item for item in self._ledger.abandoned_rows(self._owner, unit)}
            for ref in (*self._journal.abandoned(self._run_id, self.path, unit), *rows):
                row = rows.get(ref, {'written': None, 'prior': None})
                self._abandoned[ref] = {'ref': ref, 'producer_unit': unit, 'written': row['written'],
                                        'prior': row['prior']}
        self._attempt_produced = []
        self._open = []
        self.operation_key = operation_key
        self._unit_thread = threading.get_ident()

    def end_attempt(self):
        """The unit's own work returned: nothing more is written for it, and what its abandoned attempts wrote
        and it did not reclaim is no longer readable by anything."""
        if self._pending:
            raise CustodyError('unit_ended_inside_an_open_transaction:' + repr(self.path))
        if self._open:
            raise CustodyError('unit_ended_with_an_open_' + self._open[-1] + ':' + repr(self.path))
        self._abandoned = {}
        self.operation_key = None
        self._unit_thread = None

    # -- the diagnostics of the Episode's tool outcomes ----------------------------------
    def tool_returned(self, value):
        """The tool of the current unit returned ``value``, the unit's outcome: what it names as a diagnostic is
        from now on a diagnostic of an outcome of this Episode."""
        self._diagnostics.update(diagnostic_refs(value))

    def is_diagnostic(self, ref):
        """Whether the outcome of a tool unit of this Episode names ``ref`` as its diagnostic."""
        self._in_unit_thread()
        return ref in self._diagnostics

    def _receive(self, receipt):
        receipt = {**receipt, 'to': self.path}
        self._journal.record_receipt(self._run_id, self.path, receipt)
        self._held.setdefault(receipt['ref'], receipt)


# -- the runner's passes between Episodes ----------------------------------------------
# Every pass is all or nothing: one record that may not pass refuses the whole pass.
def admit_entry(custody, refs):
    """The records the run's caller names in the entry assignment (the runner has checked that each exists)."""
    for ref in refs:
        custody._receive({'ref': ref, 'how': 'entry', 'from': None, 'unit': None, 'producer': None,
                          'producer_unit': None})


def pass_records(giver, receiver, refs):
    """Records ``giver`` passes to the child ``receiver`` in a commission at its current unit."""
    giver.require_held(refs, 'record_not_held_by_commissioner')
    for ref in refs:
        given = giver._held[ref]
        receiver._receive({'ref': ref, 'how': 'commissioned', 'from': giver.path, 'unit': giver._position.position,
                           'producer': given['producer'], 'producer_unit': given['producer_unit']})


def return_records(giver, receiver, refs):
    """Records ``giver`` returns in its result; its parent ``receiver`` (``None`` at the entry) receives them."""
    giver.require_held(refs, 'returned_record_not_held')
    if receiver is None:
        return
    for ref in refs:
        given = giver._held[ref]
        receiver._receive({'ref': ref, 'how': 'returned', 'from': giver.path, 'unit': receiver._position.position,
                           'producer': given['producer'], 'producer_unit': given['producer_unit']})


@dataclass(frozen=True)
class Attempt:
    """One attempt of one unit: its stable operation key and whether an earlier attempt began and did not finish."""
    operation_key: str
    resumed: bool


class UnitCeilings:
    """The journal of the ceilings of one Episode's decisions (``bound.ceilings``): what each offered action type could
    add at most, the action type taken with its ceiling, and how far the credit actually rose. ``UNBOUNDED`` is
    written as ``'unbounded'``."""

    def __init__(self, journal, run_id, path):
        self._journal, self._run_id, self._path = journal, run_id, tuple(path)

    @staticmethod
    def _written(ceiling):
        return 'unbounded' if ceiling is UNBOUNDED else ceiling

    def offered(self, position, ceilings):
        self._journal.record_offered_ceilings(self._run_id, self._path, position,
                                              {name: self._written(value) for name, value in ceilings.items()})

    def chosen(self, position, action_type, ceiling):
        self._journal.record_chosen_ceiling(self._run_id, self._path, position,
                                            {'action_type': action_type, 'ceiling': self._written(ceiling)})

    def rise(self, position, rise):
        self._journal.record_ceiling_rise(self._run_id, self._path, position, rise)


class UnitAttempts:
    """The journal of unit attempts for one Episode (``bound.attempts``)."""

    def __init__(self, journal, run_id, path, custody, position):
        self._journal, self._run_id, self._path = journal, run_id, tuple(path)
        self._custody, self._position = custody, position

    def begin(self, position, label, arguments):
        """Journal that unit ``position`` began; the returned attempt says whether it is being run again."""
        if position != self._position.position:
            raise ValueError('unit_attempt_must_begin_at_the_sources_position')
        key = 'op_' + content_digest([self._run_id, [list(part) for part in self._path], position, label])
        resumed = self._journal.begin_unit(self._run_id, self._path, position, label, key,
                                           content_digest(arguments))
        self._custody.begin_attempt(resumed, key)
        return Attempt(key, resumed)

    def end(self):
        self._custody.end_attempt()


@dataclass(frozen=True)
class DecisionContext:
    """What ``decide`` and ``action`` receive besides the summary (read-only).

    ``settings`` is a copy of the episode's own entry of the run's ``continuation`` collaborator (journaled at
    link and compared on resume); ``services`` maps each service the episode declared to its read handle
    (``services.ServiceReader``: ``ctx.services[name].read(member, *arguments)``, recorded once per unit position
    and replayed, like the clock; the service object itself is not handed to a decision); ``clock`` the recorded
    ``DecisionClock`` of this decision; ``run_id``, ``episode_id``, ``binding_path`` and ``key`` identify the run
    and the Episode."""
    settings: Mapping
    services: Mapping
    clock: object
    run_id: str
    episode_id: str
    binding_path: str
    key: str


@dataclass(frozen=True)
class UnitContext:
    """What a tool receives besides its arguments.

    ``store`` is the custody-scoped Store (every record read and write of the unit); ``services`` the services
    the episode declared; ``model`` the recorded model (``await ctx.model.complete(role, instructions, context,
    output_schema)``, recorded and replayed under this unit); ``operation_key`` is stable for this unit;
    ``resumed`` is true when an earlier attempt of this unit began and did not finish; ``abandoned`` names what
    such attempts wrote (``({'ref', 'producer_unit', 'written', 'prior'}, ...)``, see ``Custody.abandoned``);
    ``settings`` is a copy of the episode's own continuation settings; ``run_id``, ``episode_id`` and
    ``binding_path`` identify the run and the Episode."""
    store: object
    services: Mapping
    model: RecordedModel
    operation_key: str
    resumed: bool
    abandoned: tuple
    settings: Mapping
    run_id: str
    episode_id: str
    binding_path: str


__all__ = ['Attempt', 'Custody', 'CustodyError', 'DecisionContext', 'InitialCredit', 'RecordedModel', 'ServiceReads',
           'UnitAttempts', 'UnitCeilings', 'UnitContext', 'UnitPosition', 'admit_entry', 'pass_records', 'return_records']
