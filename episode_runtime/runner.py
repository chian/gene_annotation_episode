"""Link a bound subtree from any entry point, run it durably, and resume it.

``link`` builds one Grain per binding, the declared tree from the bindings' own child slots, a Context, child
builders per slot, and the entry Episode built by its binding. Each Episode is built lazily when commissioned,
so a slot that commissions its own kind (recursive child) is expanded only per actual commission. An entry may
be any registered binding. With ``ancestors`` the entry is an inner node whose typed ancestors are recorded as a
scoped boundary of the Context and never built or executed.

``EpisodeRun.run`` runs the entry Episode until its yield controller stops it (nothing else ends an Episode).
Every run is journaled (``RunJournal``) and ``resume`` re-links a recorded run: rebuilt commissions, the
continuation settings, the declared services and each Episode's parent input must equal their records, each
Episode's yield controller is built from the initial credit recorded when the Episode was first entered, completed
units replay through ``resume_units`` and are not executed again, recorded model responses are returned instead
of asking again, what a decision read from a service is given back as recorded, and every record receipt is
reloaded. A unit that began and did not finish runs again with the same operation key.

``EpisodeRun.next_decision`` and ``EpisodeRun.run_unit`` step the entry Episode of a linked or resumed run in
place of ``run``: the first returns what the episode's ``decide`` returns first, without asking the model; the
second runs one ``ToolCall`` the caller names as the Episode's next unit. Both go through the Episode's own loop
(``_Steps``), so the controller, the journal, custody and replay are those of any run; ``run`` finishes a stepped
run, and ``resume`` replays its units.

The runner decides nothing an episode owns. Its source, tools, credit, yield controller and messages are the
members of its ``EpisodeBinding``. The runner records: every commission and the records it
passes, the credit every Episode's controller is built from, every unit's attempt, outcome, controller input,
controller step and update, every model call, every return and the records it carries, every closure (with the
credit the controller stopped on) and result, the continuation settings, the declared and built services, what
each decision read from a service, and the clock points.
"""
from __future__ import annotations

from collections.abc import Mapping
import copy
import dataclasses
from dataclasses import dataclass
import inspect
import math
from types import MappingProxyType

from method_loop import (ClosedRecord, Commission, Context, Controller, Episode, EpisodeGoal, EpisodeRef,
                         EpisodeRequest, EpisodeTree, EpisodeUpdate, Grain, RecordForm, ResumeUnit,
                         YIELD_CONTROLLERS, closing_credit)
from method_loop.jsonvalue import closed_copy, content_digest

from .bindings import BindingRegistry
from .collaborators import STANDARD_COLLABORATORS, interface_failures
from .journal import EpisodeRecorder, JournalError, RunJournal
from .progress import ProgressClock
from .recording import (Custody, DecisionContext, InitialCredit, RecordedModel, ServiceReads, UnitAttempts,
                        UnitCeilings, UnitContext, UnitPosition, admit_entry, pass_records, return_records)
from .services import DecisionServices, RunServices
from .store_ledger import StoreLedger
from .store_scope import RecordReader, ScopedStore, require_in_store
from .work_tables import WorkRows


class LinkError(RuntimeError):
    """A binding's construction broke the linked structure."""


def _record(value, what):
    if not isinstance(value, ClosedRecord):
        raise LinkError(what + ' must be a ClosedRecord')
    return value.as_record()


def _failure(error):
    return type(error).__name__ + ': ' + str(error)


def _step_record(step):
    """The controller's step for one unit as journal JSON (a number that is not finite is written as its text)."""
    def plain(value):
        if isinstance(value, float) and not math.isfinite(value):
            return repr(value)
        if isinstance(value, Mapping):
            return {str(key): plain(child) for key, child in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(child) for child in value]
        return value
    return closed_copy(plain(step.as_record()), 'controller_step', TypeError)


_DECIDE = object()      # the caller's answer to a waiting stepped loop: show the first decision for this unit
_RUN_ON = object()      # the caller's answer to a waiting stepped loop: the Episode decides its own units from here


class _Waiting:
    """Awaited by the source of a stepped Episode at each unit. The loop waits here, with the view the unit is
    chosen from (and the decision the caller asked to see), until the run's caller answers."""

    def __init__(self, view, decision):
        self.view, self.decision = view, decision

    def __await__(self):
        return (yield self)


class _Advance:
    """Awaitable: give ``answer`` to the waiting loop of a stepped Episode and run that loop, inside the caller's
    own task, until its source waits again (``(view, decision, None)``) or its controller has stopped the Episode
    (``(None, None, record)``). What the loop awaits on the way (a tool's worker thread, the model call of a
    child) is awaited by the caller's event loop, and a cancellation of the caller is raised in the loop where
    it waits. The loop holds nothing of an event loop while it waits for the caller, so each step may be run by
    an ``asyncio.run`` of its own."""

    def __init__(self, loop, answer):
        self._loop, self._answer = loop, answer

    def __await__(self):
        step, value = self._loop.send, self._answer
        while True:
            try:
                awaited = step(value)
            except StopIteration as ended:
                return None, None, ended.value
            if isinstance(awaited, _Waiting):
                return awaited.view, awaited.decision, None
            try:
                step, value = self._loop.send, (yield awaited)
            except GeneratorExit:
                self._loop.close()
                raise
            except BaseException as error:
                step, value = self._loop.throw, error


class _Steps:
    """The loop of the entry Episode while the run's caller steps it (``EpisodeRun.next_decision``, ``run_unit``).

    It is the Episode's own loop (``Episode.run_async``: entered, its yield controller built, its recorded units
    replayed, every unit journaled by the runner's hooks) with this object as its unit source. At each unit the
    source waits for the caller, who asks for the first decision, names the unit's action, or lets the Episode
    run on; after that its own source decides every unit. ``view`` is the ``EpisodeView`` the loop waits at
    (the view of the closed Episode once its controller has stopped it), ``decision`` what the caller last asked
    to see, ``record`` the closed Episode's record."""

    def __init__(self, episode, context):
        self._episode, self._source = episode, episode.source
        self._loop = dataclasses.replace(episode, source=self).run_async(context)
        self._stepped = True
        self.view = self.decision = self.record = None

    async def next(self, view):
        if self._stepped:
            answer = await _Waiting(view, None)
            while answer is _DECIDE:
                answer = await _Waiting(view, self._source.next_decision(view))
            if answer is not _RUN_ON:
                return self._source.unit_of(view, answer)
            self._stepped = False
        return await self._source.next(view)

    async def advance(self, answer):
        """Give the waiting loop ``answer`` (``None`` starts it) and run it until it waits again or the Episode
        is closed; the closed Episode's record, else ``None``."""
        view, self.decision, self.record = await _Advance(self._loop, answer)
        self.view = self._episode.view_of(self.record) if view is None else view
        return self.record


@dataclass
class EpisodeRun:
    """One linked subtree. ``run()`` executes it (or finishes a resumed run). ``next_decision()`` and
    ``run_unit(tool_call)`` step its entry Episode instead: the same loop, journal, custody and replay, with the
    run's caller in the place of the model."""
    run_id: str
    entry_path: str
    episode: Episode
    context: Context
    journal: RunJournal
    _steps: object = dataclasses.field(default=None, repr=False)
    _closed: object = dataclasses.field(default=None, repr=False)

    async def run(self):
        """Run the entry Episode until its yield controller stops it, build its result and close the run:
        ``{'entry', 'record', 'result'}``. A run that was stepped goes on from where its steps left it."""
        if self._closed is None:
            await self._part(self.episode.run_async(self.context) if self._steps is None
                             else self._steps.advance(_RUN_ON))
        return self._closed

    async def next_decision(self):
        """What the entry Episode's ``decide`` returns first, from where the run stands: a ``ModelRequest``, a
        ``ToolCall`` or a ``ChildCall``.

        The Episode is entered as ``run()`` enters it: its yield controller is built from ``credit`` of its
        initial summary (in a resumed run: from that credit as it was recorded), the units recorded for it (none
        in a new run) are replayed, ``internal_summary`` is built and ``decide(summary, None, ctx)`` is called
        with the decision context of the next unit (its clock and service reads recorded as in any run). The
        model is not asked and no unit is consumed. After ``run_unit`` it is the first decision for the unit that
        follows."""
        steps = await self._waiting()
        await self._part(steps.advance(_DECIDE))
        return steps.decision

    async def run_unit(self, tool_call):
        """Run ``tool_call`` (a ``ToolCall``) as the entry Episode's next unit and return the unit's outcome
        (``{'kind': 'tool', 'tool', 'arguments', 'outcome', 'produced'}``).

        It is the unit the loop runs for that action when the episode's own decision names it: its attempt is
        journaled before the tool runs, the tool is handed the Episode's ``UnitContext`` (the custody-scoped
        Store, the declared services, the recorded model, the unit's operation key), what it writes is
        receipted, ``credit`` of the summary with the outcome goes to the yield controller, and the unit is
        journaled with the controller's step, so ``resume`` replays it. Only the decision is the caller's:
        ``decide`` and the model are not asked. When the controller stops the Episode on this unit the result
        is built and the run closed, as ``run()`` does; ``run()`` then returns it."""
        steps = await self._waiting()
        position = steps.view.units_consumed
        await self._part(steps.advance(tool_call))
        return steps.view.outcomes[position]

    @property
    def view(self):
        """The entry Episode's ``EpisodeView`` where the stepped run stands: after the units run so far (the view
        of the closed Episode once its controller has stopped it). Its ``records`` is the Episode's read-only
        reader and its ``controller_state`` the state of its yield controller."""
        return self._steps.view

    async def _waiting(self):
        """The stepped loop of the entry Episode, waiting at its next unit (the first step starts it). A unit
        of an Episode its yield controller has stopped does not exist: asking for one raises."""
        if self._steps is None:
            self._steps = _Steps(self.episode, self.context)
            await self._part(self._steps.advance(None))
        if self._steps.record is not None:
            raise RuntimeError('episode_stopped_by_its_yield_controller:' + self.entry_path)
        return self._steps

    async def _part(self, part):
        """Await one part of the run: the entry Episode's whole loop, or one step of its stepped loop. ``part``
        returns the Episode's record once its yield controller has stopped it (``None`` while a stepped Episode
        waits at its next unit); the result is then built and the run closed. An error is recorded as the run's
        failure."""
        try:
            record = await part
            if record is None:
                return
            result = self.episode.build_result(record)
            if inspect.isawaitable(result):
                result = await result
            value = _record(result, 'entry build_result')
        except BaseException as error:
            self.journal.record_run_failure(self.run_id, _failure(error))
            raise
        self.journal.close_run(self.run_id, {'ended_by': record.ended_by, 'units': record.units_consumed,
                                             'result': value})
        self._closed = MappingProxyType({'entry': self.entry_path, 'record': record, 'result': result})


def _check_collaborators(bindings, collaborators):
    """The system collaborators are present and conform, every binding has continuation settings and every
    declared service is supplied."""
    missing = [name for name in STANDARD_COLLABORATORS if name not in collaborators]
    if missing:
        raise LinkError('collaborator_required:' + ','.join(missing))
    for name in STANDARD_COLLABORATORS:
        failures = interface_failures(name, collaborators[name])
        if failures:
            raise LinkError('collaborator_interface:' + name + ':' + ','.join(failures))
    unset = sorted(path for path in bindings if path not in collaborators['continuation'])
    if unset:
        raise LinkError('continuation_settings_required:' + ','.join(unset))
    absent = sorted(path + ':' + service for path, binding in bindings.items() for service in binding.services
                    if service not in collaborators['services'])
    if absent:
        raise LinkError('service_required:' + ','.join(absent))


def _tree(bindings, top, collaborators, bound_by_path, journal, run_id):
    grains = {}
    for path, binding in bindings.items():
        def controller(episode_path, *, binding=binding):
            bound = bound_by_path.get(tuple(episode_path))
            if bound is None or bound.binding_path != binding.binding_path:
                raise LinkError('controller_opened_for_an_episode_the_runner_did_not_build:'
                                + binding.binding_path + ':' + repr(episode_path))
            value = binding.build_controller(bound, bound.settings())
            # Only the three ``yield_control`` controllers decide continuation.
            if not isinstance(value, YIELD_CONTROLLERS):
                raise LinkError('yield_controller_must_be_a_yield_control_controller:' + binding.binding_path)
            if not isinstance(value, Controller):
                raise LinkError('build_controller returned another type:' + binding.binding_path)
            if not isinstance(getattr(value.state(), 'stop', None), bool):
                raise LinkError('controller_state_must_expose_a_boolean_stop:' + binding.binding_path)
            binding.declaration(value)
            journal.record_parent_input(run_id, bound.path, content_digest(bound.parent_input))
            return value
        grains[path] = Grain(binding.grain_name, binding.unit, binding.result, controller)
    children = {grains[path]: tuple(grains[child] for child in dict.fromkeys(binding.child_slots.values()))
                for path, binding in bindings.items()}
    adjacency = {binding.grain_name: {bindings[child].grain_name for child in binding.child_slots.values()}
                 for binding in bindings.values()}

    def reaches(start, target):
        frontier, seen = [start], set()
        while frontier:
            value = frontier.pop()
            if value == target:
                return True
            if value not in seen:
                seen.add(value)
                frontier.extend(adjacency.get(value, ()))
        return False
    tree = EpisodeTree(grains[top], children,
                       self_nesting=tuple(name for name, values in adjacency.items() if name in values),
                       recursive_edges=tuple((parent, child) for parent, values in adjacency.items()
                                             for child in values if child != parent and reaches(child, parent)))
    return grains, tree


def _ancestry(registry, ancestors, entry_path):
    """Validate typed ancestors top-down; returns (binding_path, key, goal) tuples."""
    typed = []
    for index, item in enumerate(ancestors):
        if not isinstance(item, Mapping) or set(item) != {'binding_path', 'key', 'goal'}:
            raise LinkError('ancestor_requires_binding_path_key_goal')
        binding = registry.binding(item['binding_path'])
        if type(item['key']) is not str or not item['key']:
            raise LinkError('ancestor_key_required:' + binding.binding_path)
        goal = EpisodeGoal.from_record(item['goal'])
        if index == 0 and goal.parent_goal_id:
            raise LinkError('top_ancestor_goal_must_be_a_root_goal')
        if index and goal.parent_goal_id != typed[-1][2].goal_id:
            raise LinkError('ancestor_goal_does_not_refine_its_parent:' + binding.binding_path)
        if index and binding.binding_path not in registry.binding(typed[-1][0]).child_slots.values():
            raise LinkError('ancestor_is_not_a_declared_child:' + binding.binding_path)
        typed.append((binding.binding_path, item['key'], goal))
    if typed and entry_path not in registry.binding(typed[-1][0]).child_slots.values():
        raise LinkError('entry_is_not_a_declared_child_of_its_parent:' + entry_path)
    return typed


@dataclass(frozen=True)
class BoundEpisode:
    """What the runner tells a binding about one Episode it builds (seen only by ``EpisodeBinding``).

    ``path`` is the Episode's full structural path (path-qualified grain names and keys, the scoped ancestors
    included); ``episode_id`` is ``EpisodeRef(run_id, path).episode_id``. ``request`` and ``assignment`` are the
    admitted commission, ``parent_input`` what its ``read_from_parent`` made of it, ``selection`` the optional
    return fields its commissioner selected and ``return_form`` the form its result is admitted against (the
    required fields plus the selection). ``progress`` gives its recorded clock points (per-unit progress receipts,
    per-decision clocks); ``grain`` is its Grain; ``position`` is the unit its source is at; ``model`` records each
    model call (the decision's and its tools'); ``custody`` holds the records the Episode holds (runner-only);
    ``reader`` is their read-only view for ``view.records``, ``credit``, ``action`` and ``read_from_child``;
    ``store`` is the custody-scoped Store of its tools; ``services`` are the services the episode declared
    (handed to its tools); ``reads`` records what its decisions read from them; ``attempts`` journals each unit's
    attempt; ``initial_credit`` records the credit its yield controller is built from (computed when the Episode
    is first entered, read from the journal ever after); ``ceilings`` journals each decision's ceilings, the ceiling
    of the action taken and the credit's actual rise;
    ``settings()`` is a copy of the episode's continuation settings; ``decision_context(position)`` is
    what ``decide`` and ``action`` receive (the services as read handles whose reads are recorded for that
    position) and ``context(attempt)`` what a tool receives.
    """
    run_id: str
    binding_path: str
    path: tuple
    key: str
    episode_id: str
    request: EpisodeRequest
    assignment: Mapping
    parent_input: Mapping
    selection: tuple
    return_form: RecordForm
    progress: ProgressClock
    grain: Grain
    position: UnitPosition
    model: RecordedModel
    custody: Custody
    reader: RecordReader
    store: ScopedStore
    services: Mapping
    reads: ServiceReads
    attempts: UnitAttempts
    initial_credit: InitialCredit
    continuation: Mapping
    ceilings: UnitCeilings

    def settings(self):
        """A copy of the episode's own continuation settings (so no episode function can change the run's)."""
        return copy.deepcopy(self.continuation)

    def decision_context(self, position):
        return DecisionContext(settings=self.settings(),
                               services=DecisionServices(self.services, self.reads.at(position)),
                               clock=self.progress.decision_point(position), run_id=self.run_id,
                               episode_id=self.episode_id, binding_path=self.binding_path, key=self.key)

    def context(self, attempt):
        return UnitContext(store=self.store, services=self.services, model=self.model,
                           operation_key=attempt.operation_key, resumed=attempt.resumed,
                           abandoned=self.custody.abandoned(), settings=self.settings(), run_id=self.run_id,
                           episode_id=self.episode_id, binding_path=self.binding_path)


def _admit(binding, commission, what):
    """A commission against the Episode's own forms: its selected return form, its admitted assignment and the
    records the assignment passes. Raises ``FormError``; changes nothing."""
    return_form = binding.return_form.select(commission.selection)
    assignment = MappingProxyType(binding.assignment_form.admit(commission.assignment, what))
    return return_form, assignment, binding.assignment_form.record_refs(assignment)


class ChildBuilder:
    """The parent's builder for one declared child slot.

    Calling the builder builds the child Episode, once per commission. In order: the child's own forms take the
    selection and the assignment (``FormError``), the records the assignment names pass from the parent's custody
    (``CustodyError`` when the parent does not hold one), then the child's commission is journaled. An error at
    any of these steps is the commission's error and ends the run; nothing looks at a commission before this
    point. ``admit`` admits the child's returned result.
    """

    def __init__(self, slot, child_binding, build):
        self.slot, self.binding_path = slot, child_binding.binding_path
        self.assignment_form, self.return_form = child_binding.assignment_form, child_binding.return_form
        self._build = build

    def __call__(self, child_key, commission):
        return self._build(child_key, commission)

    def admit(self, result, selection):
        """The child's returned result as a plain record of its required return fields plus the selected ones."""
        return self.return_form.select(selection).admit(result, 'child_return:' + self.binding_path)


def _prepare(registry, entry_path, entry_input, ancestors, collaborators):
    """What ``link`` and ``resume`` do before a run is recorded, in this order: look up the entry binding
    (``MissingBinding``); check the ancestors (``LinkError``); check the collaborators, the settings and the
    services of the subtree (``LinkError``); and build the entry's commission from the caller's entry input
    (``entry_request``), which requires the three keys ``assignment``, ``message``, ``selection``
    (``ValueError``) and puts the assignment through the entry's own assignment form (``FormError``). Nothing
    else of the entry input is looked at here: its selection and the records its assignment names are first
    used when the entry Episode is built, after the run is recorded."""
    registry.binding(entry_path)
    typed = _ancestry(registry, ancestors, entry_path)
    top = typed[0][0] if typed else entry_path
    bindings = registry.subtree(top)
    _check_collaborators(bindings, collaborators)
    commission = bindings[entry_path].entry_request(entry_input, parent_goal=typed[-1][2] if typed else None)
    if not isinstance(commission, Commission):
        raise LinkError('entry_request must return a Commission:' + entry_path)
    return typed, top, bindings, commission


def _link(journal, run_id, entry, collaborators, prepared):
    entry_path, key = entry['entry_path'], entry['key']
    typed, top, bindings, commission = prepared
    for path, binding in bindings.items():
        journal.record_settings(run_id, path, collaborators['continuation'][path])
        journal.record_services(run_id, path, binding.services)
    bound_by_path = {}
    grains, tree = _tree(bindings, top, collaborators, bound_by_path, journal, run_id)
    parent_path = tuple((bindings[path].grain_name, ancestor_key) for path, ancestor_key, _ in typed)
    entry_binding = bindings[entry_path]
    parent_goal = typed[-1][2] if typed else None
    request = commission.request
    if typed:
        if request.goal.parent_goal_id != parent_goal.goal_id or request.report_contract is None:
            raise LinkError('inner entry_request must refine its parent goal and carry a report contract:' + entry_path)
        context = Context.from_commission(tree=tree, run_id=run_id, parent_path=parent_path,
                                          parent_goal_id=parent_goal.goal_id, child_goal_id=request.goal.goal_id,
                                          grain=entry_binding.grain_name, key=key)
    else:
        if request.goal.parent_goal_id:
            raise LinkError('entry_request must return a root EpisodeRequest:' + entry_path)
        context = Context(tree=tree, run_id=run_id)

    store, provider = collaborators['store'], collaborators['model_provider']
    rows = WorkRows(store)
    ledger = StoreLedger(store, rows)
    run_services = RunServices(collaborators['services'], lambda name, user: journal.record_service_build(
        run_id, name, user.path, user.unit))

    def build(path, episode_key, episode_commission, *, parent):
        binding = bindings[path]
        if not isinstance(episode_commission, Commission):
            raise LinkError('an Episode requires a Commission:' + path)
        episode_request = episode_commission.request
        return_form, assignment, passed = _admit(binding, episode_commission, 'assignment:' + path)
        episode_path = (*parent, (binding.grain_name, episode_key))
        if episode_path in bound_by_path:
            raise LinkError('episode_path_built_twice:' + repr(episode_path))
        position = UnitPosition(journal, run_id, episode_path)
        episode_id = EpisodeRef(run_id, episode_path).episode_id
        custody = Custody(journal, ledger, run_id, episode_path, episode_id, position)
        # The records pass first, then the commission is journaled. For the entry Episode (it has no parent
        # in this run) the pass is: each record the entry assignment names must exist in the Store.
        if parent in bound_by_path:
            pass_records(bound_by_path[parent].custody, custody, passed)
        else:
            for ref in passed:
                require_in_store(store, rows, ref)
            admit_entry(custody, passed)
        journal.open_episode(run_id, episode_path, path, {'request': episode_request.as_record(),
                                                          'assignment': dict(assignment),
                                                          'selection': list(episode_commission.selection)})
        bound = BoundEpisode(
            run_id, path, episode_path, episode_key, episode_id, episode_request, assignment,
            binding.parent_input(assignment, episode_request), episode_commission.selection, return_form,
            ProgressClock(EpisodeRecorder(journal, run_id, episode_path), run_id=run_id, episode_id=episode_id),
            grains[path], position, RecordedModel(journal, run_id, episode_path, episode_id, provider, position),
            custody, RecordReader(store, custody, rows), ScopedStore(store, custody, rows, (run_id, episode_id)),
            run_services.view(binding.services, custody), ServiceReads(journal, run_id, episode_path),
            UnitAttempts(journal, run_id, episode_path, custody, position),
            InitialCredit(journal, run_id, episode_path), collaborators['continuation'][path],
            UnitCeilings(journal, run_id, episode_path))
        bound_by_path[episode_path] = bound
        child_builders = {}
        for slot, child_path in binding.child_slots.items():
            def child_build(child_key, child_commission, *, child_path=child_path):
                if type(child_key) is not str or not child_key:
                    raise LinkError('child key must be non-empty text:' + child_path)
                if tuple(context.path) != episode_path:
                    raise LinkError('child builder called outside its owning parent:' + child_path)
                if not isinstance(child_commission, Commission):
                    raise LinkError('a child builder requires a Commission:' + child_path)
                if child_commission.request.goal.parent_goal_id != episode_request.goal.goal_id:
                    raise LinkError('child Goal does not refine its parent Goal:' + child_path)
                return build(child_path, child_key, child_commission, parent=episode_path)
            child_builders[slot] = ChildBuilder(slot, bindings[child_path], child_build)
        episode = binding.build_episode(grains[path], bound, MappingProxyType(child_builders))
        parent_bound = bound_by_path.get(parent)
        return _durable(episode, binding, return_form, journal, run_id, episode_path, custody,
                        None if parent_bound is None else parent_bound.custody)

    episode = build(entry_path, key, commission, parent=parent_path)
    return EpisodeRun(run_id, entry_path, episode, context, journal)


def _durable(episode, binding, return_form, journal, run_id, path, custody, parent_custody):
    """Attach the journal to one Episode: replay its recorded units, record new ones and its return receipts."""
    resume = tuple(ResumeUnit(label, binding.restore_controller_input(value), outcome,
                              None if update is None else EpisodeUpdate.from_record(update))
                   for label, value, outcome, update in journal.units(run_id, path))
    own_unit, own_close, own_result = episode.on_unit, episode.on_close, episode.build_result
    async def on_unit(item, contribution, view):
        journal.record_unit(run_id, path, view.unit_ref.unit_index, view.unit_label,
                            _record(view.controller_input, 'controller input'), view.outcome,
                            None if view.episode_update is None else view.episode_update.as_record(),
                            _step_record(view.controller_step))
        if own_unit is not None:
            value = own_unit(item, contribution, view)
            if inspect.isawaitable(value):
                await value

    async def on_close(record):
        journal.close_episode(run_id, path, {'ended_by': record.ended_by, 'units': record.units_consumed,
                                             'credit': closing_credit(record, binding.binding_path)})
        if own_close is not None:
            value = own_close(record)
            if inspect.isawaitable(value):
                await value

    async def build_result(record):
        value = own_result(record)
        if inspect.isawaitable(value):
            value = await value
        admitted = return_form.admit(_record(value, 'build_result'), 'return:' + binding.binding_path)
        return_records(custody, parent_custody, return_form.record_refs(admitted))
        journal.record_result(run_id, path, admitted)
        return value
    return dataclasses.replace(episode, on_unit=on_unit, on_close=on_close, build_result=build_result,
                               resume_units=resume)


def _start(registry, journal, collaborators):
    if not isinstance(registry, BindingRegistry):
        raise TypeError('binding_registry_required')
    if not isinstance(journal, RunJournal):
        raise TypeError('run_journal_required')
    if not isinstance(collaborators, Mapping):
        raise TypeError('collaborators_must_be_a_mapping')
    return MappingProxyType(dict(collaborators))


def _claim(journal, run_id, collaborators):
    """The run claims its id in the Store it writes to. A run id is unique within one journal only, and rows,
    operation keys and accounts in the Store are keyed by it: a run of another journal with the same id over the
    same Store is refused."""
    store = collaborators['store']
    if not StoreLedger(store, WorkRows(store)).claim_run(run_id, journal.identity):
        raise LinkError('run_id_claimed_in_this_store_by_another_journal:' + run_id)


def link(registry, entry_path, entry_input, *, run_id, journal, collaborators, ancestors=(), key=None):
    """Record a new run and build the entry Episode below ``entry_path``.

    ``ancestors`` (top-down ``{'binding_path', 'key', 'goal'}`` records) makes the entry an inner node below a
    scoped, unexecuted boundary. ``_prepare`` says what is done before the run is recorded. The run then claims
    its id in the Store (``LinkError`` when a run of another journal holds it there), is recorded in the journal,
    and the entry Episode is built.
    """
    collaborators = _start(registry, journal, collaborators)
    if type(run_id) is not str or not run_id:
        raise ValueError('run_id_required')
    prepared = _prepare(registry, entry_path, entry_input, list(ancestors), collaborators)
    entry = {'entry_path': entry_path, 'entry_input': entry_input, 'ancestors': list(ancestors),
             'key': run_id if key is None else key}
    _claim(journal, run_id, collaborators)
    journal.open_run(run_id, entry)
    return _link(journal, run_id, journal.entry(run_id), collaborators, prepared)


def resume(registry, *, run_id, journal, collaborators):
    """Re-link a recorded run; completed work replays instead of executing."""
    collaborators = _start(registry, journal, collaborators)
    entry = journal.entry(run_id)
    prepared = _prepare(registry, entry['entry_path'], entry['entry_input'], entry['ancestors'], collaborators)
    _claim(journal, run_id, collaborators)
    return _link(journal, run_id, entry, collaborators, prepared)


__all__ = ['BoundEpisode', 'ChildBuilder', 'EpisodeRun', 'JournalError', 'LinkError', 'link', 'resume']
