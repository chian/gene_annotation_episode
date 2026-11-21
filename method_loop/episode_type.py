"""The Episode type: every episode is ``class X(EpisodeBinding)``, and inherits from nothing else.

An episode is written only as this class. Its ``EpisodeBindingDeclaration`` is generated from it by
``declaration(controller)``; a subclass supplies the members below, one group per file of its episode folder.
The class carries the system behaviour: request admission, the decision loop (the Episode's ``UnitSource``),
tool units and child commissions through ``Leaf`` and ``ChildEpisodeUnit``, the controller input of every
unit, and the result. The generic runner (``runner.py``) builds each Episode and gives it its recording
services (``BoundEpisode``); this type only calls them, and an episode's own files call none of them.

| Episode file | Members (signature) |
|---|---|
| ``goal.py`` | ``binding_path``, ``goal``, ``unit``, ``result`` (text) |
| ``task.py`` | ``child_slots`` ({slot: child binding path}), ``tools`` ({name: ``tool(arguments, ctx)``}), ``services`` (names), ``decide(summary, feedback, ctx)``, ``offered_actions(summary, ctx)`` -> the action types this decision offers, ``action(response, summary, records, ctx)``; optional ``resume_action(summary, records, ctx)`` (``OPTIONAL_MEMBERS``) |
| ``credit.py`` | ``credit(summary, records)`` -> finite number; ``ceiling(summary, records, action_type, arguments, ctx)`` -> ``UNBOUNDED`` or a finite number >= 0; optional ``best_arguments(summary, records, action_type, ctx)`` and ``outcome_pending(summary, records, position)`` (``OPTIONAL_MEMBERS``) |
| ``yield_estimator.py`` | ``yield_controller(initial_credit, settings, parent_input)`` -> a ``yield_control`` controller |
| ``messages/read_from_parent.py`` | ``assignment_form``, ``read_from_parent(assignment, message)`` -> parent input |
| ``messages/msg_to_child.py`` | ``msg_to_child(slot, arguments, summary)`` -> ``ChildMessage(objective, message, assignment, selection)`` |
| ``messages/read_from_child.py`` | ``read_from_child(slot, result, summary, records)`` -> report |
| ``messages/internal_summary.py`` | ``internal_summary(view)`` -> summary |
| ``messages/final_to_parent.py`` | ``return_form`` (with the required fields ``credit`` and ``finding``), ``final_to_parent(summary, completion, selection)`` -> result |

``episode.py`` defines exactly one ``class X(EpisodeBinding)`` in a module named ``<package>.episode`` and assigns
each member from its file; each function, and each tool, must be a module-level function of the file named above
(``<package>.credit``, ``<package>.task``, ``<package>.messages.internal_summary``, ...). ``__init_subclass__``
(below) raises ``TypeError`` for everything else; ``BINDING_CONTRACT.md`` lists the checks.

The loop of one Episode:

1. ``read_from_parent(assignment, message)`` is the Episode's ``parent_input``. Before each unit the summary is
   ``internal_summary(view)``, a function of the ``method_loop.EpisodeView`` (its request, ``parent_input``,
   ``outcomes`` of its completed units, ``updates`` and ``child_reports``, ``units_consumed``,
   ``controller_state``, and ``records``, the read-only reader of the records it holds). The loop restores all of
   it on resume, so nothing is recalled by hand.
2. ``decide(summary, feedback, ctx)`` returns a ``ModelRequest`` (the model is asked through ``bound.model``) or an
   action; ``ctx`` is the read-only ``DecisionContext`` (settings, read handles of the declared services, the
   recorded clock of this decision, run identity). ``action(response, summary, records, ctx)`` turns a response
   into an action or raises ``Rejected(feedback)``. A rejected response creates no unit and no observation, and
   ``decide`` is called again with that feedback. An action is a ``ToolCall`` or a ``ChildCall`` and nothing else:
   the task always offers a unit and cannot end its Episode. A model answer that selects no unit is an invalid
   answer, which ``action`` rejects like any other.
3. ``ToolCall(name, arguments)`` runs ``tools[name](arguments, ctx)`` as one ``Leaf`` (``ctx`` a ``UnitContext``);
   its outcome is ``{'kind': 'tool', 'tool', 'arguments', 'outcome', 'produced'}``. ``ChildCall(slot, arguments)``
   commissions the child from ``msg_to_child`` as one ``ChildEpisodeUnit``; its outcome is ``{'kind': 'child',
   'slot', 'arguments', 'message', 'completion', 'result', 'report'}`` (``message`` is the ``ChildMessage`` as a
   record, ``result`` the child's admitted typed result, ``report`` what ``read_from_child`` made of it, called
   once). The unit's attempt is journaled before a tool runs or a child is built. A commission the child's forms
   do not admit, or that passes a record the Episode does not hold, raises and ends the run.
   The action types are the name of a ``ToolCall`` (``tool``), the slot of a ``ChildCall`` and ``reason`` where the
   episode's reasoning commit is a tool of that name: exactly the names a unit is recorded under. After ``decide``
   the system asks ``ceiling(summary, records, action_type, None, ctx)`` for every offered action type, the MOST
   the episode's credit can rise if that action is the next unit (over every arguments it can take now): a finite
   number >= 0, or ``UNBOUNDED``, which a ceiling returns deliberately for an action whose gain has no finite
   upper bound (there is no default: an episode answers for every action it offers). After ``action`` it asks again
   with the chosen action type and its arguments, and after the unit it compares the credit's rise with that
   ceiling: a rise above it (beyond 1e-9) raises ``episode_ceiling_exceeded:<episode>:<action type>:<rise>:<ceiling>``
   (nothing exceeds ``UNBOUNDED``). The journal records, per unit, the offered ceilings, the chosen action's ceiling
   and the rise. With the three older yield controllers nothing here changes what the model is shown or how the
   Episode stops. With a ``ForecastYieldController`` the ceilings are its input: the system gives it, with each unit's
   completion, the ceilings the next decision will offer, it adds the forecast of every offered action to the model's
   request under the key ``action_forecasts`` (one row per offered action: ``action_type``, ``ceiling`` (a number or
   ``'unbounded'``), ``forecast_gain`` and ``expected_seconds`` (numbers or ``'unknown'``) and ``worth`` (the forecast exceeds
   expected seconds x exchange rate, or is unknown); facts only, a task changes nothing for it), it refuses the
   chosen action before any unit when its forecast (for the ceiling asked with its arguments) is not worth its
   cost, exactly like a ``Rejected`` (feedback ``{'status': 'invalid', 'category': 'forecast', 'code':
   'action_forecast_not_worth_its_cost', 'detail': {action_type, ceiling, forecast_gain, expected_seconds,
   threshold, and ``choose_from``: the best commission's arguments when the episode supplies ``best_arguments``}}``; an unknown
   forecast is not refused), and it records the unit's forecast before the unit and its result after it in the
   estimate ledger (``episode_runtime.forecast_ledger``). A unit whose outcome is pending (the optional member
   ``outcome_pending``, below: its action started work, such as a job a child launched and returned parked, that a later
   unit of the same action finishes) is not an observation of its action: the controller learns no share and no unit
   seconds of its action from it, and its ledger row is resolved ``pending``, which no history reads. An Episode with a
   forecast controller and child slots must supply ``outcome_pending`` (a child can park): without it the unit's facts
   raise ``forecast_episode_with_children_must_supply_outcome_pending``; one without children has none to declare (a tool
   unit ends its work in the unit).
   Started work is finished (the owner, 2026-11-21: "the head must finish parked jobs"). The optional member ``task.py``
   ``resume_action(summary, records, ctx)`` returns ``None`` while the Episode holds no work it started and has not
   finished, else the unit that resumes it: ``{'action_type', 'arguments', 'due'}`` (the action type is a tool name or a
   child slot; ``arguments`` exactly those the episode's own ``action`` would make, e.g. a parked job's commission again
   with ``until`` extracted; ``due`` True once the work is expected to have ended). With a forecast controller: (a) each
   unit's facts carry ``must_continue`` (a resume is owed after the unit) and the controller does not stop while it is
   True; (b) while a resume is owed its action type must be offered (``episode_resume_not_offered``); when it is due it is
   the only action offered (the decision's offered actions and the facts' ``next_offered`` are narrowed to it); (c) the
   resume is taken by the system as the unit, without asking the model, when it is due, or when no offered action's
   forecast is worth its cost (where the Episode would otherwise have stopped); (d) the forecast gate never refuses that
   resume (only that exact action type and arguments, taken in (c)): completing started work is not optional. Its
   forecast is still recorded in the ledger. Before the resume is due and while another action is worth its cost the
   model chooses as usual (the resume is an ordinary, gated choice then). An Episode with a forecast controller and
   child slots must supply ``resume_action`` (``forecast_episode_with_children_must_supply_resume_action``); one whose
   controller is not a forecast controller may not (``resume_action_requires_a_forecast_controller``).
4. Each unit's controller input is ``{'credit': credit(internal_summary(view.with_unit(outcome)), records),
   'estimation_context': {'progress_time': bound.progress.receipt(position)}}``. The episode's yield controller
   observes it and alone decides whether the Episode stops: nothing else ends an Episode. The controller is built
   from ``credit`` of the summary before any unit; the system computes that credit when the Episode is first
   entered and records it, and builds the controller of an Episode that is entered again (resume) from the record,
   because such an Episode already holds what its recorded units produced. A value the model
   writes when it closes its work (a closing text, a report) is the outcome of a tool unit the episode declares
   for it; the summary holds it like every other outcome.
5. The result is ``final_to_parent(internal_summary(view of the closed record), completion, selection)`` with
   ``completion = {'ended_by', 'units_consumed', 'credit'}``: ``ended_by`` is ``'yield_stop'`` and ``credit`` is
   the Episode's credit as its controller last saw it (the credit it stopped on). Every result carries ``credit``
   and ``finding``: the class definition requires both as required fields of the episode's own ``return_form``.

A run's caller may step the entry Episode through this same loop (``EpisodeRun.next_decision`` and
``EpisodeRun.run_unit``, ``runner.py``): the first ``decide`` of step 2 without the model call, and a unit of step 3
whose action the caller names. Steps 1, 4 and 5 are unchanged.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import inspect
import math
import re
import sys
import time
from types import MappingProxyType

from . import (ChildEpisodeUnit, ChildProjection, Commission, EpisodeBindingDeclaration, EpisodeChildSlot,
               EpisodeControllerBinding, EpisodeFunctionBinding, EpisodeGoal, EpisodeRef, EpisodeRequest,
               EpisodeTopologyRole, EpisodeView, Episode, JsonRecord, Leaf, RecordForm, ReportContract)
from .jsonvalue import closed_copy, same_json
from yield_control import (AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController,
                           ForecastYieldController, ForecastYieldState, UNBOUNDED_TEXT)

_NAME = re.compile(r'^[a-z][a-z0-9_]*$')
_SEGMENT = r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*'
_BINDING_PATH = re.compile('^' + _SEGMENT + '(?:/' + _SEGMENT + ')*$')
YIELD_CONTROLLERS = (AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController,
                     ForecastYieldController)
# The one key under which the system adds the forecasts to the context of a decision's model request, when the
# Episode's yield controller is a ``ForecastYieldController``.
FORECASTS_KEY = 'action_forecasts'


class _Unbounded:
    def __repr__(self):
        return 'UNBOUNDED'


# What a ``ceiling`` returns, deliberately and for one action, when the credit that action can add has no finite upper
# bound. There is no default: a ``ceiling`` answers for every action its episode offers.
UNBOUNDED = _Unbounded()


@dataclass(frozen=True)
class ModelRequest:
    """``decide`` asks the model."""
    role: str
    instructions: str
    context: Mapping
    output_schema: Mapping


@dataclass(frozen=True)
class ToolCall:
    """Run the episode's own tool ``name`` with ``arguments`` as one unit."""
    name: str
    arguments: Mapping


@dataclass(frozen=True)
class ChildCall:
    """Commission the child in ``slot`` as one unit; ``arguments`` go to ``msg_to_child``."""
    slot: str
    arguments: Mapping


class Rejected(Exception):
    """``action`` rejects a model response before any unit; ``feedback`` goes to the next ``decide``."""

    def __init__(self, feedback):
        super().__init__('model_response_rejected')
        self.feedback = feedback


@dataclass(frozen=True)
class ChildMessage:
    """What ``msg_to_child`` sends: the child's objective, its message and the assignment its form requires
    (its ``record_refs`` fields name the records passed in custody: exactly those records pass, and none of the
    records they name) and ``selection``: the optional fields of the child's own ``return_form``
    (``required=False``) this commission asks it to return. The child's result is admitted against the required
    fields (``credit`` and ``finding`` among them) plus the selected ones; nothing else can be requested."""
    objective: str
    message: Mapping
    assignment: Mapping
    selection: tuple


SUPPLIED_BY_FILE = MappingProxyType({
    'goal.py': ('binding_path', 'goal', 'unit', 'result'),
    'task.py': ('child_slots', 'tools', 'services', 'decide', 'offered_actions', 'action'),
    'credit.py': ('credit', 'ceiling'),
    'yield_estimator.py': ('yield_controller',),
    'messages/read_from_parent.py': ('assignment_form', 'read_from_parent'),
    'messages/msg_to_child.py': ('msg_to_child',),
    'messages/read_from_child.py': ('read_from_child',),
    'messages/internal_summary.py': ('internal_summary',),
    'messages/final_to_parent.py': ('return_form', 'final_to_parent'),
})
CHILD_MEMBERS = ('msg_to_child', 'read_from_child')
# The members an episode may supply: ``credit.py`` ``best_arguments(summary, records, action_type, ctx)`` returns the arguments of
# the action whose ceiling is the one asked with ``arguments`` None (a dict), or None when no choice of arguments matters;
# ``credit.py`` ``outcome_pending(summary, records, position)`` (``summary`` after unit ``position``) returns ``True`` when
# that unit's outcome is pending (its action started work that a later unit of the same action finishes: a child that
# returned parked), else ``False``. An Episode with a forecast controller and child slots must supply it.
# ``task.py`` ``resume_action(summary, records, ctx)`` returns ``None`` or the unit that resumes work the Episode started and
# has not finished, ``{'action_type', 'arguments', 'due'}`` (module docstring, step 3). An Episode with a forecast controller
# and child slots must supply it.
OPTIONAL_MEMBERS = ('best_arguments', 'outcome_pending', 'resume_action')
SUPPLIED = tuple(name for names in SUPPLIED_BY_FILE.values() for name in names)
# Each function member: the parameters it takes, and the module (below the episode package) that defines it.
SIGNATURES = MappingProxyType({
    'decide': ('summary', 'feedback', 'ctx'),
    'action': ('response', 'summary', 'records', 'ctx'),
    'credit': ('summary', 'records'),
    'ceiling': ('summary', 'records', 'action_type', 'arguments', 'ctx'),
    'best_arguments': ('summary', 'records', 'action_type', 'ctx'),
    'outcome_pending': ('summary', 'records', 'position'),
    'resume_action': ('summary', 'records', 'ctx'),
    'offered_actions': ('summary', 'ctx'),
    'yield_controller': ('initial_credit', 'settings', 'parent_input'),
    'read_from_parent': ('assignment', 'message'),
    'msg_to_child': ('slot', 'arguments', 'summary'),
    'read_from_child': ('slot', 'result', 'summary', 'records'),
    'internal_summary': ('view',),
    'final_to_parent': ('summary', 'completion', 'selection'),
})
FILE_OF = MappingProxyType({
    'decide': 'task', 'action': 'task', 'offered_actions': 'task', 'credit': 'credit', 'ceiling': 'credit', 'best_arguments': 'credit', 'outcome_pending': 'credit', 'resume_action': 'task', 'yield_controller': 'yield_estimator',
    'read_from_parent': 'messages.read_from_parent', 'msg_to_child': 'messages.msg_to_child',
    'read_from_child': 'messages.read_from_child', 'internal_summary': 'messages.internal_summary',
    'final_to_parent': 'messages.final_to_parent'})
TOOL_FILE = 'task'
REPORT_FIELD = 'report'
TOOL_PARAMETERS = ('arguments', 'ctx')
# The fields every episode's own ``return_form`` declares as required: every Episode returns them and no
# commission selects them. ``credit`` is a number; the content form of ``finding`` is the episode's own.
ALWAYS_RETURNED = ('credit', 'finding')
SYSTEM_MEMBERS = ('grain_name', 'declaration', 'parent_input', 'entry_request', 'build_controller', 'build_episode',
                  'restore_controller_input')
# The names Python itself puts into a class body.
PYTHON_CLASS_NAMES = ('__module__', '__qualname__', '__doc__', '__firstlineno__', '__static_attributes__')
# The one episode class each ``<package>.episode`` module has defined.
_EPISODE_OF_MODULE = {}
# Every class the definition check passed, with the members it checked (``checked_members``).
_CHECKED = {}


def controller_input_schema():
    """The JSON schema of every unit's controller input."""
    return {'type': 'object', 'additionalProperties': False, 'required': ['credit', 'estimation_context'],
            'properties': {'credit': {'type': 'number'},
                           'estimation_context': {'type': 'object', 'required': ['progress_time']}}}


def _function(name, role, function):
    return EpisodeFunctionBinding(name=name, library=function.__module__, function_id=function.__qualname__,
                                  interface='method_loop.episode_type.' + role,
                                  definition_id=function.__module__ + ':' + function.__qualname__)


def _closed(value, what):
    return closed_copy(value, what, TypeError)


def _credit(value, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TypeError('episode_credit_must_be_a_finite_number:' + path + ':' + repr(value))
    return value


CEILING_TOLERANCE = 1e-9


def _ceiling(value, path, action_type):
    """A ceiling is ``UNBOUNDED`` or a finite number that is not below zero."""
    if value is UNBOUNDED:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise TypeError('episode_ceiling_must_be_unbounded_or_a_finite_number_not_below_zero:' + path + ':'
                        + str(action_type) + ':' + repr(value))
    return value


def closing_credit(record, path):
    """The credit of a closed Episode: the cumulative credit its yield controller last saw."""
    return _credit(record.controller_state.current_credit, path)


def _parameters(function):
    """The parameter names of a plain function that takes only plain positional-or-keyword parameters."""
    parameters = inspect.signature(function).parameters.values()
    if any(parameter.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD or parameter.default is not parameter.empty
           for parameter in parameters):
        return None
    return tuple(parameter.name for parameter in parameters)


def _check_function(name, key, function, expected, parameters, *, may_be_async):
    """``function`` is a module-level function of the module ``expected`` with exactly ``parameters``."""
    what = name + ':' + key
    if not inspect.isfunction(function) or not function.__name__.isidentifier():
        raise TypeError('episode_member_must_be_a_plain_function:' + what)
    if inspect.isgeneratorfunction(function) or inspect.isasyncgenfunction(function):
        raise TypeError('episode_member_must_not_be_a_generator:' + what)
    if inspect.iscoroutinefunction(function) and not may_be_async:
        raise TypeError('episode_member_must_not_be_async:' + what)
    module = sys.modules.get(expected)
    if (function.__module__ != expected or module is None or function.__globals__ is not vars(module)
            or function.__closure__ is not None or function.__qualname__ != function.__name__):
        raise TypeError('episode_member_must_be_defined_in_its_own_file:' + what + ':' + str(function.__module__)
                        + ':' + expected)
    if _parameters(function) != parameters:
        raise TypeError('episode_member_parameters_must_be:' + what + ':' + ','.join(parameters))


def _check_functions(cls, name, own, package):
    for key in SIGNATURES:
        if (key in CHILD_MEMBERS or key in OPTIONAL_MEMBERS) and key not in own:
            continue
        _check_function(name, key, vars(cls)[key], package + '.' + FILE_OF[key], SIGNATURES[key],
                        may_be_async=False)
    for tool, function in vars(cls)['tools'].items():
        _check_function(name, 'tool.' + tool, function, package + '.' + TOOL_FILE, TOOL_PARAMETERS,
                        may_be_async=True)


def checked_members(cls):
    """Raise ``TypeError`` unless ``cls`` is an episode class whose definition was checked and whose bases and
    members are still the checked ones (``BindingRegistry`` asks before it registers an instance)."""
    checked = _CHECKED.get(cls)
    if checked is None or cls.__bases__ != (EpisodeBinding,):
        raise TypeError('episode_class_was_not_checked_at_its_definition:' + cls.__qualname__)
    now = {key: value for key, value in vars(cls).items() if key not in PYTHON_CLASS_NAMES}
    changed = sorted(key for key in set(checked) | set(now) if checked.get(key) is not now.get(key))
    if changed:
        raise TypeError('episode_class_changed_after_its_definition:' + cls.__qualname__ + ':'
                        + ','.join(changed))


class EpisodeBinding:
    """The Episode type every episode binding inherits from directly (see the module docstring)."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        name = cls.__qualname__
        if cls.__bases__ != (EpisodeBinding,):
            raise TypeError('episode_must_inherit_only_from_EpisodeBinding:' + name)
        if type(cls) is not type:
            raise TypeError('episode_must_not_have_a_metaclass:' + name + ':' + type(cls).__name__)
        hooks = sorted(key for key in vars(cls) if key.startswith('__') and key not in PYTHON_CLASS_NAMES)
        if hooks:
            raise TypeError('episode_defines_python_hooks:' + name + ':' + ','.join(hooks))
        own = {key for key in vars(cls) if key not in PYTHON_CLASS_NAMES}
        overridden = sorted(own & (set(SYSTEM_MEMBERS) | {key for key in vars(EpisodeBinding)
                                                           if not key.startswith('__')}))
        if overridden:
            raise TypeError('episode_overrides_system_members:' + name + ':' + ','.join(overridden))
        missing = [key for key in SUPPLIED if key not in CHILD_MEMBERS and key not in own]
        if missing:
            raise TypeError('episode_lacks_members:' + name + ':' + ','.join(missing))
        extra = sorted(own - set(SUPPLIED) - set(OPTIONAL_MEMBERS))
        if extra:
            raise TypeError('episode_members_outside_the_episode_files:' + name + ':' + ','.join(extra))
        for key in ('binding_path', 'goal', 'unit', 'result'):
            if type(vars(cls)[key]) is not str or not vars(cls)[key].strip():
                raise TypeError('episode_' + key + '_must_be_text:' + name)
        binding_path = vars(cls)['binding_path']
        if not _BINDING_PATH.fullmatch(binding_path):
            raise TypeError('episode_binding_path_must_be_lowercase_segments:' + name + ':' + binding_path)
        slots = vars(cls)['child_slots']
        if not isinstance(slots, Mapping):
            raise TypeError('episode_child_slots_must_be_a_mapping:' + name)
        if any(type(slot) is not str or not _NAME.fullmatch(slot) or type(child) is not str
               or not _BINDING_PATH.fullmatch(child) for slot, child in slots.items()):
            raise TypeError('episode_child_slots_must_map_slot_names_to_binding_paths:' + name)
        present = [key for key in CHILD_MEMBERS if key in own]
        if slots and len(present) != len(CHILD_MEMBERS):
            raise TypeError('episode_with_children_lacks_members:' + name + ':'
                            + ','.join(key for key in CHILD_MEMBERS if key not in own))
        if not slots and present:
            raise TypeError('episode_without_children_has_child_members:' + name + ':' + ','.join(present))
        for key in ('assignment_form', 'return_form'):
            if not isinstance(vars(cls)[key], RecordForm):
                raise TypeError('episode_' + key + '_must_be_a_RecordForm:' + name)
        returned = vars(cls)['return_form'].fields
        absent = [key for key in ALWAYS_RETURNED if key not in returned or not returned[key].required]
        if absent:
            raise TypeError('episode_return_form_must_require:' + name + ':' + ','.join(absent))
        if returned['credit'].type != 'number':
            raise TypeError('episode_return_form_credit_must_be_a_number:' + name)
        tools = vars(cls)['tools']
        if not isinstance(tools, Mapping) or any(type(tool) is not str or not _NAME.fullmatch(tool)
                                                 for tool in tools):
            raise TypeError('episode_tools_must_map_tool_names_to_functions:' + name)
        services = vars(cls)['services']
        if (not isinstance(services, tuple) or len(set(services)) != len(services)
                or any(type(service) is not str or not _NAME.fullmatch(service) for service in services)):
            raise TypeError('episode_services_must_be_a_tuple_of_distinct_service_names:' + name)
        if not cls.__module__.endswith('.episode'):
            raise TypeError('episode_must_be_defined_in_its_episode_file:' + name + ':' + cls.__module__)
        package = cls.__module__[:-len('.episode')]
        if not ('.' + package).endswith('.' + binding_path.replace('/', '.')):
            raise TypeError('episode_binding_path_must_end_its_package_path:' + name + ':' + binding_path + ':'
                            + package)
        _check_functions(cls, name, own, package)
        first = _EPISODE_OF_MODULE.setdefault(cls.__module__, cls)
        if first is not cls:
            raise TypeError('episode_file_defines_two_episodes:' + cls.__module__ + ':' + first.__qualname__ + ','
                            + name)
        # The class keeps its own unchangeable copies: a later change of the file's mapping does not reach it.
        cls.tools = MappingProxyType(dict(tools))
        cls.child_slots = MappingProxyType(dict(slots))
        _CHECKED[cls] = {key: vars(cls)[key] for key in own}

    # -- system members --------------------------------------------------------------
    @property
    def grain_name(self):
        return self.binding_path.replace('/', '__')

    def _member(self, name):
        """A supplied function, called as a plain function of its file (never bound to the binding)."""
        return getattr(type(self), name)

    def declaration(self, controller):
        """This Episode type as ``EpisodeBindingDeclaration``; its progress and stopping text describe
        ``controller``, the yield controller the episode's ``yield_controller`` builds."""
        member = self._member
        progress, stopping = _controller_text(controller)
        components = (_function('action', 'action', member('action')),
                      *(_function('tool.' + tool, 'tool', function) for tool, function in self.tools.items()))
        slots = tuple(EpisodeChildSlot(
            name=slot, accepted_interfaces=(child,),
            build_child=_function(slot + '.build_child', 'build_child', _SystemSource._child),
            prepare_request=_function(slot + '.prepare_request', 'msg_to_child', member('msg_to_child')),
            receive_result=_function(slot + '.receive_result', 'read_from_child', member('read_from_child')))
            for slot, child in self.child_slots.items())
        estimator = member('yield_controller')
        return EpisodeBindingDeclaration(
            grain_name=self.grain_name, interface=self.binding_path,
            topology_role=EpisodeTopologyRole.BRANCH if slots else EpisodeTopologyRole.LEAF,
            goal=self.goal, unit=self.unit, result=self.result, progress=progress, stopping=stopping,
            admit_request=_function('read_from_parent', 'read_from_parent', member('read_from_parent')),
            open_source=_function('decide', 'decide', member('decide')),
            controller=EpisodeControllerBinding(
                schema=_function('controller_input_schema', 'controller_input_schema', controller_input_schema),
                composer=_function('compose_controller_input', 'compose_controller_input',
                                   _SystemSource._controller_input),
                credit=_function('credit', 'credit', member('credit')),
                rarefaction=_function('yield_estimator', 'yield_controller', estimator),
                continuation=_function('continuation', 'yield_controller', estimator)),
            build_result=_function('final_to_parent', 'final_to_parent', member('final_to_parent')),
            components=components, child_slots=slots,
            internal_summary=_function('internal_summary', 'internal_summary', member('internal_summary')))

    def entry_request(self, entry_input, *, parent_goal):
        """Admit a caller's ``{'assignment', 'message', 'selection'}``; below a scoped ancestor the entry refines
        its goal."""
        if not isinstance(entry_input, Mapping) or set(entry_input) != {'assignment', 'message', 'selection'}:
            raise ValueError('entry_input_requires_exactly:assignment,message,selection')
        assignment = self.assignment_form.admit(entry_input['assignment'], 'entry_assignment:' + self.binding_path)
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract={'unit': self.unit, 'result': self.result})
            contract = None
        else:
            contract = _report_contract(self.goal)
            goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=contract.as_record())
        return Commission(EpisodeRequest(goal, JsonRecord(entry_input['message']), contract), assignment,
                          tuple(entry_input['selection']))

    def parent_input(self, assignment, request):
        """What the Episode's ``read_from_parent`` makes of its assignment: the only place an assignment is read."""
        return _closed(self._member('read_from_parent')(dict(assignment), request.message.as_record()),
                       'parent_input')

    def _summary(self, view):
        return _closed(self._member('internal_summary')(view), 'summary')

    def _credit_of(self, summary, bound):
        return _credit(self._member('credit')(summary, bound.reader), self.binding_path)

    def build_controller(self, bound, settings):
        """The episode's yield controller over the credit of its summary before any unit. That credit is computed
        when the Episode is first entered and recorded (``bound.initial_credit``); an Episode that is entered
        again (a resumed run) holds what its recorded units produced, so its controller is built from the record
        and ``credit`` is not asked again."""
        def before_any_unit():
            view = EpisodeView(grain=bound.grain, key=bound.key, path=bound.path, units_consumed=0, updates=(),
                               controller_state=None, episode_ref=EpisodeRef(bound.run_id, bound.path),
                               request=bound.request, parent_input=bound.parent_input, outcomes=(),
                               records=bound.reader)
            return self._credit_of(self._summary(view), bound)
        return self._member('yield_controller')(bound.initial_credit.recorded(before_any_unit), settings,
                                                bound.parent_input)

    def build_episode(self, grain, bound, child_builders):
        source = _SystemSource(self, bound, child_builders)
        episode = Episode(grain, bound.key, source, bound.request, source.build_result,
                          parent_input=bound.parent_input, records=bound.reader)
        source.episode = episode
        return episode

    def restore_controller_input(self, record):
        return JsonRecord(record)


def _report_contract(objective):
    """The reporting contract the method loop requires of every child edge. It is derived, never authored: the
    parent's report is what ``read_from_child`` made of the child's admitted result."""
    return ReportContract(decision=objective, measurements={},
                          information={REPORT_FIELD: "what the parent's read_from_child made of the child's "
                                                     "admitted result"})


def _controller_text(controller):
    """Progress and stopping text for the yield controller an episode actually built."""
    if isinstance(controller, ForecastYieldController):
        return ('credit(summary) rises by what the chosen action earns, at most its ceiling; each offered action is '
                'forecast from its ceiling and what actions of its kind realized before',
                'stops when no offered action\'s forecast gain exceeds its expected seconds times the exchange rate '
                + repr(controller.exchange_rate))
    cost = controller.cost
    if isinstance(controller, AccumulationYieldController):
        return ('credit(summary) accumulates after each unit without a declared limit',
                'stops when the forecast upper bound of the next unit\'s credit is at or below its cost '
                + repr(cost))
    if isinstance(controller, BoundedQualityYieldController):
        return ('credit(summary) is a quality that cannot pass its declared maximum ' + repr(controller.maximum_credit),
                'stops when the forecast upper bound of further credit below that maximum is at or below its cost '
                + repr(cost))
    if isinstance(controller, CompletionYieldController):
        return ('credit(summary) counts toward the commission\'s finite target ' + repr(controller.target),
                'stops when the forecast of the credit still to come before the target is at or below its cost '
                + repr(cost))
    raise TypeError('episode_yield_controller_must_be_a_yield_control_controller:' + type(controller).__name__)


def _written(ceiling):
    """A ceiling as the journal and the forecast controller write it: a number, or ``'unbounded'``."""
    return UNBOUNDED_TEXT if ceiling is UNBOUNDED else ceiling


class _SystemSource:
    """The ``UnitSource`` of one Episode of an ``EpisodeBinding`` (see the module docstring)."""

    def __init__(self, binding, bound, child_builders):
        self._binding, self._bound, self._builders = binding, bound, child_builders
        self.episode = None

    def _controller_input(self, view, position, outcome, chosen=None):
        summary = self._binding._summary(view.with_unit(outcome))
        context = {'progress_time': self._bound.progress.receipt(position)}
        if isinstance(view.controller_state, ForecastYieldState):
            context['forecast'] = self._forecast_facts(summary, position, chosen)
        return JsonRecord({'credit': self._binding._credit_of(summary, self._bound), 'estimation_context': context})

    def _unit_seconds(self, position):
        """The measured seconds of unit ``position``: from the progress receipt of the unit before it (the Episode's
        origin for the first) to its own, so the model's decision time is in it."""
        progress = self._bound.progress
        now = progress.receipt(position)
        before = progress.receipt(position - 1) if position else {'elapsed_seconds': 0.0, 'status': 'available'}
        if now['status'] != 'available' or before['status'] != 'available':
            raise ValueError('forecast_requires_measured_unit_seconds:' + self._binding.binding_path)
        return now['elapsed_seconds'] - before['elapsed_seconds']

    def _pending(self, summary, position):
        """Whether unit ``position``'s outcome is pending, from the episode's ``outcome_pending`` (``summary`` after the
        unit). An Episode without children has no unit that can be pending; one with children must answer."""
        path = self._binding.binding_path
        member = getattr(type(self._binding), 'outcome_pending', None)
        if member is None:
            if self._binding.child_slots:
                raise TypeError('forecast_episode_with_children_must_supply_outcome_pending:' + path)
            return False
        pending = member(summary, self._bound.reader, position)
        if type(pending) is not bool:
            raise TypeError('episode_outcome_pending_must_be_a_boolean:' + path + ':' + repr(pending))
        return pending

    def _forecast_facts(self, summary, position, chosen):
        """What a ``ForecastYieldController`` is given with the completion of unit ``position``: the action and its
        ceiling, the unit's measured seconds, whether its outcome is pending, and the ceilings the next decision offers
        (computed from the summary after the unit, as that decision will compute them)."""
        context = self._bound.decision_context(position + 1)
        resume = self._resume(summary, context, forecast=True)
        offered = self._offered_ceilings(summary, context, resume)
        return {'action_type': chosen['action_type'], 'ceiling': _written(chosen['ceiling']),
                'unit_seconds': self._unit_seconds(position), 'decision_seconds': chosen['decision_seconds'],
                'pending': self._pending(summary, position), 'must_continue': resume is not None,
                'next_offered': {name: _written(ceiling) for name, ceiling in offered.items()}}

    def _resume(self, summary, context, *, forecast):
        """The resume the Episode owes, from its optional ``resume_action`` (module docstring, step 3): ``None``, or
        ``{'action_type', 'arguments', 'due'}``. ``forecast``: whether the Episode's controller is a forecast controller.
        A forecast Episode with children must supply the member; one with another controller must not."""
        path, binding = self._binding.binding_path, self._binding
        member = getattr(type(binding), 'resume_action', None)
        if member is None:
            if forecast and binding.child_slots:
                raise TypeError('forecast_episode_with_children_must_supply_resume_action:' + path)
            return None
        if not forecast:
            raise TypeError('resume_action_requires_a_forecast_controller:' + path)
        resume = member(summary, self._bound.reader, context)
        if resume is None:
            return None
        if (not isinstance(resume, Mapping) or set(resume) != {'action_type', 'arguments', 'due'}
                or type(resume['due']) is not bool or not isinstance(resume['arguments'], Mapping)
                or (resume['action_type'] not in binding.tools and resume['action_type'] not in binding.child_slots)):
            raise TypeError('episode_resume_action_must_be_none_or_action_type_arguments_due:' + path + ':'
                            + repr(resume))
        return {'action_type': resume['action_type'], 'arguments': _closed(dict(resume['arguments']), 'resume_arguments'),
                'due': resume['due']}

    def _resume_call(self, resume):
        """The resume as the action it is: a ``ChildCall`` of its slot or a ``ToolCall`` of its tool."""
        if resume['action_type'] in self._binding.child_slots:
            return ChildCall(resume['action_type'], dict(resume['arguments']))
        return ToolCall(resume['action_type'], dict(resume['arguments']))

    def _ceiling_of(self, summary, action_type, arguments, context):
        return _ceiling(self._binding._member('ceiling')(summary, self._bound.reader, action_type, arguments, context),
                        self._binding.binding_path, action_type)

    def _offered_ceilings(self, summary, context, resume):
        """The ceiling of every action type a decision offers: the episode's ``offered_actions``; while a resume is owed
        (``resume``) its action type must be among them, and when it is due it is the only one."""
        path = self._binding.binding_path
        names = self._binding._member('offered_actions')(summary, context)
        if (not isinstance(names, (list, tuple)) or len(set(names)) != len(names)
                or any(type(name) is not str or not name for name in names)):
            raise TypeError('episode_offered_actions_must_be_distinct_action_type_names:' + path + ':' + repr(names))
        if resume is not None:
            if resume['action_type'] not in names:
                raise LookupError('episode_resume_not_offered:' + path + ':' + resume['action_type'])
            if resume['due']:
                names = [resume['action_type']]
        return {name: self._ceiling_of(summary, name, None, context) for name in names}

    def _offered(self, summary, position, context, resume):
        """The ceiling of every action type this decision offers (journaled for unit ``position``)."""
        offered = self._offered_ceilings(summary, context, resume)
        self._bound.ceilings.offered(position, offered)
        return offered

    def _forecast_rows(self, view, offered):
        """The forecast of every offered action, from what the controller has learned (``None`` when the Episode's
        controller is not a ``ForecastYieldController``)."""
        if not isinstance(view.controller_state, ForecastYieldState):
            return None
        return view.controller_state.forecast({name: _written(ceiling) for name, ceiling in offered.items()})

    def _best(self, summary, action_type, context):
        """The arguments of the commission that reaches the action's ceiling asked with ``arguments`` None, from the
        episode's optional ``best_arguments`` (``None`` where the episode has none or no choice of arguments matters)."""
        member = getattr(type(self._binding), 'best_arguments', None)
        if member is None:
            return None
        best = member(summary, self._bound.reader, action_type, context)
        return None if best is None else _closed(best, 'best_arguments')

    def _shown(self, rows, summary=None, context=None):
        """The forecast rows as the model sees them: facts only, and for an action with a best commission its arguments
        (``best_arguments``: the ceiling and forecast of the row are those of exactly that commission)."""
        shown = []
        for row in rows:
            item = {'action_type': row['action_type'], 'ceiling': row['ceiling'],
                    'forecast_gain': 'unknown' if row['forecast_gain'] is None else row['forecast_gain'],
                    'expected_seconds': 'unknown' if row['expected_seconds'] is None else row['expected_seconds'],
                    'worth': row['worth']}
            best = None if summary is None else self._best(summary, row['action_type'], context)
            if best is not None:
                item['best_arguments'] = best
            shown.append(item)
        return shown

    def _gate(self, view, decision, summary, context, offered, owed=None):
        """The per-action gate of a ``ForecastYieldController``: the chosen action's forecast row, for its ceiling
        asked with its arguments, must be worth its cost (threshold: expected seconds x exchange rate), else the
        response is rejected like any ``Rejected``: no unit, feedback to the next ``decide``.

        The one exception, explicit and narrow: ``owed``, the resume the system takes (``next``: due, or in place of a
        stop), is never refused, whatever its forecast: completing started work is not optional. Only a decision of
        exactly its action type and arguments is exempt; any other decision is gated as usual."""
        action_type = decision.name if isinstance(decision, ToolCall) else decision.slot
        if action_type not in offered:
            return
        if (owed is not None and action_type == owed['action_type']
                and same_json(_closed(dict(decision.arguments), 'gate_arguments'), owed['arguments'])):
            return
        ceiling = self._ceiling_of(summary, action_type, _closed(dict(decision.arguments), 'ceiling_arguments'), context)
        rows = self._forecast_rows(view, {action_type: ceiling})
        if rows is not None and not rows[0]['worth']:
            row = rows[0]
            detail = {'action_type': action_type, 'ceiling': row['ceiling'], 'forecast_gain': row['forecast_gain'],
                      'expected_seconds': row['expected_seconds'], 'threshold': row['threshold']}
            best = self._best(summary, action_type, context)
            if best is not None:
                detail['choose_from'] = best
            raise Rejected({'status': 'invalid', 'category': 'forecast', 'code': 'action_forecast_not_worth_its_cost',
                            'detail': detail})

    def _chosen(self, view, position, decision, summary, context, offered):
        """The action taken: its type, its ceiling (asked again with its arguments), the credit before the unit and
        the seconds the decision took. With a ``ForecastYieldController`` its forecast, for that ceiling, is recorded
        in the estimate ledger before the unit runs."""
        path = self._binding.binding_path
        action_type = decision.name if isinstance(decision, ToolCall) else decision.slot
        if action_type not in offered:
            raise LookupError('episode_action_not_offered:' + path + ':' + str(action_type))
        ceiling = self._ceiling_of(summary, action_type, _closed(dict(decision.arguments), 'ceiling_arguments'), context)
        self._bound.ceilings.chosen(position, action_type, ceiling)
        chosen = {'action_type': action_type, 'ceiling': ceiling, 'decision_seconds': time.monotonic() - self._began,
                  'before': self._binding._credit_of(summary, self._bound)}
        rows = self._forecast_rows(view, {action_type: ceiling})
        if rows is not None:
            self._bound.forecast_ledger.expect(position, action_type, rows[0], context.clock.now)
        return chosen

    def _unit_input(self, view, position, outcome, chosen):
        """The controller input of a completed unit, after the credit's rise is compared with the ceiling of the action."""
        record = self._controller_input(view, position, outcome, chosen)
        rise = record.as_record()['credit'] - chosen['before']
        self._bound.ceilings.rise(position, rise)
        if chosen['ceiling'] is not UNBOUNDED and rise > chosen['ceiling'] + CEILING_TOLERANCE:
            raise ValueError('episode_ceiling_exceeded:' + self._binding.binding_path + ':' + chosen['action_type']
                             + ':' + repr(rise) + ':' + repr(chosen['ceiling']))
        facts = record.as_record()['estimation_context'].get('forecast')
        if facts is not None:
            self._bound.forecast_ledger.resolve(position, rise, facts['unit_seconds'], facts['decision_seconds'],
                                                facts['pending'], self._bound.progress.receipt(position)['captured_at'])
        return record

    def _choosing(self, view):
        """The source is choosing the unit after ``view``: that unit's position and the summary it is chosen
        from."""
        position = view.units_consumed
        self._bound.position.begin(position)
        self._began = time.monotonic()
        return position, self._binding._summary(view)

    def next_decision(self, view):
        """What the episode's ``decide`` returns first for the unit after ``view``: called with the summary, no
        feedback and the unit's decision context. The model is not asked and no unit is made
        (``EpisodeRun.next_decision``)."""
        position, summary = self._choosing(view)
        return self._binding._member('decide')(summary, None, self._bound.decision_context(position))

    def unit_of(self, view, action):
        """The unit after ``view`` of an action the run's caller names in place of the episode's own decision
        (``EpisodeRun.run_unit``)."""
        position, summary = self._choosing(view)
        context = self._bound.decision_context(position)
        resume = self._resume(summary, context, forecast=isinstance(view.controller_state, ForecastYieldState))
        return self._unit(view, position, action, summary, context, self._offered(summary, position, context, resume))

    async def next(self, view):
        position, summary = self._choosing(view)
        context = self._bound.decision_context(position)
        resume = self._resume(summary, context, forecast=isinstance(view.controller_state, ForecastYieldState))
        offered = self._offered(summary, position, context, resume)
        if resume is not None and (resume['due'] or not any(row['worth'] for row in self._forecast_rows(view, offered))):
            # The owed resume is the unit (module docstring, step 3): due, or no offered action is worth its cost and the
            # Episode may not stop. The model is not asked; the gate is asked and lets exactly this resume pass.
            decision = self._resume_call(resume)
            self._gate(view, decision, summary, context, offered, owed=resume)
            return self._unit(view, position, decision, summary, context, offered)
        decide, act = self._binding._member('decide'), self._binding._member('action')
        feedback = None
        while True:
            decision = decide(summary, feedback, context)
            if not isinstance(decision, ModelRequest):
                break
            rows = self._forecast_rows(view, offered)
            if rows is not None:
                decision = replace(decision, context={**decision.context, FORECASTS_KEY: self._shown(rows, summary, context)})
            response = await self._bound.model.complete(decision.role, decision.instructions, decision.context,
                                                        decision.output_schema)
            try:
                decision = act(response, summary, self._bound.reader, context)
                self._gate(view, decision, summary, context, offered)
            except Rejected as rejection:
                # Rejected before acquisition: no unit, no observation; the task decides again.
                feedback = _closed(rejection.feedback, 'rejection_feedback')
                continue
            break
        return self._unit(view, position, decision, summary, context, offered)

    def _unit(self, view, position, decision, summary, context, offered):
        """The unit of an action. An action is a ``ToolCall`` or a ``ChildCall``: the task cannot end its
        Episode, so anything else is an error of the episode's ``decide`` or ``action``."""
        if isinstance(decision, (ToolCall, ChildCall)):
            chosen = self._chosen(view, position, decision, summary, context, offered)
            if isinstance(decision, ToolCall):
                return self._tool(view, position, decision, chosen)
            return self._child(view, position, decision, summary, chosen)
        raise TypeError('task_action_must_be_a_ToolCall_or_a_ChildCall:' + self._binding.binding_path + ':'
                        + repr(decision))

    def _tool(self, view, position, call, chosen):
        tools, bound = self._binding.tools, self._bound
        if call.name not in tools:
            raise LookupError('task_tool_not_declared:' + self._binding.binding_path + ':' + str(call.name))
        arguments = _closed(dict(call.arguments), 'tool_arguments')
        label = 'tool:' + call.name + ':' + str(position)

        async def extract(_call):
            attempt = bound.attempts.begin(position, label, arguments)
            value = tools[call.name](arguments, bound.context(attempt))
            if inspect.isawaitable(value):
                value = await value
            bound.attempts.end()
            outcome = _closed({'kind': 'tool', 'tool': call.name, 'arguments': arguments, 'outcome': value,
                               'produced': bound.custody.attempt_produced()}, 'tool_outcome')
            bound.custody.tool_returned(outcome['outcome'])
            return outcome
        return Leaf(call, extract, lambda _call, outcome: self._unit_input(view, position, outcome, chosen), label)

    def _child(self, view, position, call, summary, chosen):
        binding, bound = self._binding, self._bound
        if call.slot not in self._builders:
            raise LookupError('task_child_slot_not_declared:' + binding.binding_path + ':' + str(call.slot))
        builder = self._builders[call.slot]
        arguments = _closed(dict(call.arguments), 'child_arguments')
        message = binding._member('msg_to_child')(call.slot, arguments, summary)
        if not isinstance(message, ChildMessage):
            raise TypeError('msg_to_child_must_return_a_ChildMessage:' + binding.binding_path)
        asked = _closed({'slot': call.slot, 'arguments': arguments,
                         'message': {'objective': message.objective, 'message': dict(message.message),
                                     'assignment': dict(message.assignment), 'selection': list(message.selection)}},
                        'child_commission')
        key = call.slot + '_' + str(position)
        bound.attempts.begin(position, key, asked)
        contract = _report_contract(message.objective)
        goal = EpisodeGoal.child(bound.request.goal, objective=message.objective,
                                 result_contract=contract.as_record())
        child = builder(key, Commission(EpisodeRequest(goal, JsonRecord(message.message), contract),
                                        message.assignment, tuple(message.selection)))
        read = binding._member('read_from_child')

        def project(result, completion, request):
            admitted = builder.admit(result, message.selection)
            report = _closed(read(call.slot, admitted, summary, bound.reader), 'child_report')
            outcome = {**asked, 'kind': 'child', 'completion': completion.as_record(), 'result': admitted,
                       'report': report}
            return ChildProjection({REPORT_FIELD: report}, outcome, self._unit_input(view, position, outcome, chosen))
        return ChildEpisodeUnit(child, project)

    def build_result(self, record):
        completion = {'ended_by': record.ended_by, 'units_consumed': record.units_consumed,
                      'credit': closing_credit(record, self._binding.binding_path)}
        return JsonRecord(self._binding._member('final_to_parent')(
            self._binding._summary(self.episode.view_of(record)), completion, self._bound.selection))


__all__ = ['ALWAYS_RETURNED', 'CEILING_TOLERANCE', 'UNBOUNDED', 'ChildCall', 'ChildMessage', 'EpisodeBinding', 'ModelRequest', 'Rejected',
           'SUPPLIED_BY_FILE', 'SIGNATURES', 'ToolCall', 'YIELD_CONTROLLERS', 'closing_credit',
           'controller_input_schema']
