"""The generic, nestable Episode method.

``Episode`` owns one loop: pull a unit, acquire it, send its binding-produced
value to the injected controller, publish a compact update, and then obey the
controller's structural stop decision.  It has no knowledge of columns,
incidence, rarefaction, hypervolume, or any other surface-specific result.

Nested communication and tracing are deliberately separate:

* :class:`EpisodeGoal` is the immutable objective at one Episode boundary.
* :class:`EpisodeRequest` carries that Goal plus one already-admitted closed record.
* :class:`ChildEpisodeUnit` owns separate credit and report projections for one child.
* :class:`EpisodeUpdate` separates credit, the parent's report and method-owned completion.
* :class:`EpisodeRecord` is the complete recursive trace retained for audit.

The loop is asynchronous only, runs one Episode at a time and has no pending, detached or
suspended work: a unit is acquired completely (a leaf's value or a child Episode's closed
return) before the controller observes it.

An Episode ends in one way only: its controller's step for a completed unit says stop
(``END_YIELD_STOP``). A source always returns a unit; it cannot end its Episode.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
import math
from types import MappingProxyType
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Protocol,
)

from .identities import EpisodeRef, UnitRef
from .jsonvalue import closed_copy
from .runtime import ControllerFactory, ControllerRuntime, Path, Scope
from .communication import ParentReport, ReportContract

__all__ = [
    "END_YIELD_STOP",
    "Acquirable",
    "ChildEpisodeUnit",
    "ClosedRecord",
    "Context",
    "Contribution",
    "Episode",
    "EpisodeCompletion",
    "EpisodeGoal",
    "EpisodeRecord",
    "EpisodeRequest",
    "EpisodeTree",
    "EpisodeUpdate",
    "EpisodeView",
    "Grain",
    "JsonRecord",
    "Leaf",
    "ResumeUnit",
    "UnitRecord",
    "UnitSource",
    "UnitView",
    "ChildProjection",
]

# The one way an Episode ends: its controller stopped it.
END_YIELD_STOP = "yield_stop"
EPISODE_END_KINDS = (END_YIELD_STOP,)


def _record_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "as_record"):
        return value.as_record()
    if isinstance(value, Mapping):
        return {str(name): _record_value(item) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_record_value(item) for item in value]
    raise TypeError(f"{type(value).__name__} is not a JSON-compatible record value")


def _freeze_json(value: Any) -> Any:
    """Return an immutable JSON value or raise at the Goal boundary."""

    def thaw(item: Any) -> Any:
        if item is None or isinstance(item, (str, int, float, bool)):
            return item
        if isinstance(item, Mapping):
            return {str(name): thaw(child) for name, child in item.items()}
        if isinstance(item, (tuple, list)):
            return [thaw(child) for child in item]
        raise TypeError(
            f"{type(item).__name__} is not a JSON-compatible Goal value"
        )

    try:
        normalized = json.loads(
            json.dumps(
                thaw(value),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        )
    except (TypeError, ValueError) as exc:
        raise TypeError("EpisodeGoal values must be JSON-compatible") from exc

    def freeze(item: Any) -> Any:
        if isinstance(item, dict):
            return MappingProxyType(
                {str(name): freeze(child) for name, child in item.items()}
            )
        if isinstance(item, list):
            return tuple(freeze(child) for child in item)
        return item

    return freeze(normalized)


class ClosedRecord(ABC):
    """An admitted boundary value with a JSON audit projection.

    The surface-owned admission function constructs this value before it enters
    the method loop. Requiring an object instead of a raw mapping prevents an
    unvalidated payload from being substituted at the Episode boundary while
    keeping the generic method independent of any surface's record class.
    """

    @abstractmethod
    def as_record(self) -> Mapping[str, Any]:
        """Return the closed record's JSON audit projection."""

        raise NotImplementedError

    def audit_identifiers(self) -> tuple[str, ...]:
        """Identify bookkeeping values that must stay out of a parent report.

        Records carrying artifact or correlation identities declare them here.
        Records containing only task values have no audit identities.
        """
        return ()


def _require_closed_record(value: Any, name: str) -> ClosedRecord:
    if not isinstance(value, ClosedRecord):
        raise TypeError(f"{name} must be an admitted ClosedRecord")
    record = value.as_record()
    if not isinstance(record, Mapping):
        raise TypeError(f"{name}.as_record() must return a mapping")
    # Validation must not construct and discard several copies of a full
    # inherited ledger. The surface has already admitted the closed record.
    active = set()
    def validate(item):
        if item is None or isinstance(item, (str, bool, int)):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                raise TypeError("Closed record values must be finite JSON values")
            return
        if isinstance(item, (Mapping, tuple, list)):
            identity = id(item)
            if identity in active:
                raise TypeError("Closed record values cannot contain circular references")
            active.add(identity)
            try:
                for child in item.values() if isinstance(item, Mapping) else item:
                    validate(child)
            finally:
                active.remove(identity)
            return
        raise TypeError(f"{type(item).__name__} is not a JSON-compatible closed record value")
    validate(record)
    return value


@dataclass(frozen=True)
class EpisodeGoal:
    """The immutable objective and result contract for one Episode.

    A root Goal has no ``parent_goal_id``. A child Goal is made with
    :meth:`child`, which records the parent Goal it refines. The method loop
    validates that link before it runs a nested Episode.
    """

    objective: Any
    result_contract: Any
    task_context: Any = None
    parent_goal_id: str = ""
    goal_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.parent_goal_id, str):
            raise TypeError("EpisodeGoal.parent_goal_id must be a string")
        if self.parent_goal_id and self.task_context is None:
            raise ValueError(
                "a child EpisodeGoal must preserve its root task_context"
            )
        objective = _freeze_json(self.objective)
        result_contract = _freeze_json(self.result_contract)
        task_context = _freeze_json(
            self.task_context
            if self.task_context is not None
            else {
                "root_objective": _record_value(objective),
                "root_result_contract": _record_value(result_contract),
            }
        )
        body = {
            "objective": _record_value(objective),
            "result_contract": _record_value(result_contract),
            "task_context": _record_value(task_context),
            "parent_goal_id": self.parent_goal_id,
        }
        digest = hashlib.sha256(
            json.dumps(
                body,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "result_contract", result_contract)
        object.__setattr__(self, "task_context", task_context)
        object.__setattr__(self, "goal_id", f"goal_{digest[:24]}")

    @classmethod
    def root(
        cls,
        *,
        objective: Any,
        result_contract: Any,
        task_context: Any = None,
    ) -> "EpisodeGoal":
        return cls(
            objective=objective,
            result_contract=result_contract,
            task_context=task_context,
        )

    @classmethod
    def child(
        cls,
        parent: "EpisodeGoal",
        *,
        objective: Any,
        result_contract: Any,
    ) -> "EpisodeGoal":
        if not isinstance(parent, EpisodeGoal):
            raise TypeError("a child Goal requires an EpisodeGoal parent")
        return cls(
            objective=objective,
            result_contract=result_contract,
            task_context=parent.task_context,
            parent_goal_id=parent.goal_id,
        )

    @classmethod
    def for_grain(
        cls,
        grain: Any,
        *,
        objective: Any,
        parent: Optional["EpisodeGoal"] = None,
        result_contract: Any = None,
    ) -> "EpisodeGoal":
        """Build the standard Goal for a declared Grain.

        Bindings supply only the local objective. The Grain supplies the
        generic unit/result contract unless a binding has a more precise JSON
        contract to record.
        """

        if not isinstance(grain, Grain):
            raise TypeError("EpisodeGoal.for_grain requires a Grain")
        contract = (
            result_contract
            if result_contract is not None
            else {
                "grain": grain.name,
                "unit": grain.unit,
                "result": grain.result,
            }
        )
        if parent is None:
            return cls.root(objective=objective, result_contract=contract)
        return cls.child(
            parent,
            objective=objective,
            result_contract=contract,
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "parent_goal_id": self.parent_goal_id,
            "objective": _record_value(self.objective),
            "result_contract": _record_value(self.result_contract),
            "task_context": _record_value(self.task_context),
        }

    @classmethod
    def from_record(cls, value: Any) -> "EpisodeGoal":
        """Restore a Goal while revalidating its content-derived identity."""

        if not isinstance(value, Mapping):
            raise TypeError("EpisodeGoal state must be a mapping")
        expected = {
            "goal_id",
            "parent_goal_id",
            "objective",
            "result_contract",
            "task_context",
        }
        if set(value) != expected:
            raise ValueError("malformed EpisodeGoal state")
        goal = cls(
            objective=value["objective"],
            result_contract=value["result_contract"],
            task_context=value["task_context"],
            parent_goal_id=value["parent_goal_id"],
        )
        if value["goal_id"] != goal.goal_id:
            raise ValueError("EpisodeGoal goal_id does not match its persisted content")
        return goal



class JsonRecord(ClosedRecord):
    """A closed JSON record (an admitted message, controller input or result)."""

    def __init__(self, value):
        if not isinstance(value, Mapping):
            raise TypeError("json_record_requires_a_mapping")
        self._value = closed_copy(dict(value), "json_record", TypeError)

    def as_record(self):
        return json.loads(json.dumps(self._value))


@dataclass(frozen=True)
class EpisodeRequest:
    """The Goal and admitted closed record supplied when an Episode opens."""

    goal: EpisodeGoal
    message: ClosedRecord
    report_contract: Optional[ReportContract] = None

    def __post_init__(self) -> None:
        if not isinstance(self.goal, EpisodeGoal):
            raise TypeError("EpisodeRequest.goal must be an EpisodeGoal")
        _require_closed_record(self.message, "EpisodeRequest.message")
        if self.report_contract is not None and not isinstance(self.report_contract, ReportContract):
            raise TypeError("EpisodeRequest.report_contract must be a ReportContract")

    def as_record(self) -> dict[str, Any]:
        return {
            "goal": self.goal.as_record(),
            "message": _record_value(self.message),
            "report_contract": None if self.report_contract is None else self.report_contract.as_record(),
        }


@dataclass(frozen=True)
class EpisodeCompletion:
    """Method-owned facts about how one child Episode ended."""

    ended_by: str
    units_consumed: int

    def __post_init__(self) -> None:
        if self.ended_by not in EPISODE_END_KINDS:
            raise ValueError("EpisodeCompletion.ended_by must be a method end kind")
        if (
            isinstance(self.units_consumed, bool)
            or not isinstance(self.units_consumed, int)
            or self.units_consumed < 0
        ):
            raise ValueError(
                "EpisodeCompletion.units_consumed must be a non-negative integer"
            )

    @classmethod
    def from_record(cls, record: "EpisodeRecord") -> "EpisodeCompletion":
        if not isinstance(record, EpisodeRecord):
            raise TypeError("EpisodeCompletion requires an EpisodeRecord")
        return cls(
            ended_by=record.ended_by,
            units_consumed=record.units_consumed,
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "ended_by": self.ended_by,
            "units_consumed": self.units_consumed,
        }



@dataclass(frozen=True)
class EpisodeUpdate:
    """Method-owned correlation of completion and the parent's report of one child."""

    record_id: str
    goal: EpisodeGoal
    completion: EpisodeCompletion
    controller_input: ClosedRecord
    report: ParentReport
    _audit_identifiers: tuple[str, ...] = field(default=(), repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not self.record_id:
            raise ValueError("EpisodeUpdate.record_id must be a non-empty string")
        if not isinstance(self.goal, EpisodeGoal):
            raise TypeError("EpisodeUpdate.goal must be an EpisodeGoal")
        if not isinstance(self.completion, EpisodeCompletion):
            raise TypeError("EpisodeUpdate.completion must be an EpisodeCompletion")
        _require_closed_record(self.controller_input, "EpisodeUpdate.controller_input")
        if not isinstance(self.report, ParentReport):
            raise TypeError("EpisodeUpdate.report must be an admitted ParentReport")
        if not isinstance(self._audit_identifiers, tuple) or any(
                not isinstance(value, str) or not value for value in self._audit_identifiers):
            raise TypeError("child audit identities must be declared explicitly")

    def as_record(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "goal": self.goal.as_record(),
            "completion": self.completion.as_record(),
            "controller_input": _record_value(self.controller_input),
            "report": self.report.as_record(),
            "report_contract": self.report.contract.as_record(),
            "audit_identifiers": list(self._audit_identifiers),
        }

    @classmethod
    def from_record(cls, value: Mapping[str, Any]) -> "EpisodeUpdate":
        """Restore the update ``as_record`` produced (a resumed Episode's view gets its updates back)."""
        if not isinstance(value, Mapping) or set(value) != {
                "record_id", "goal", "completion", "controller_input", "report", "report_contract",
                "audit_identifiers"}:
            raise ValueError("episode update record fields must be exact")
        identifiers = tuple(value["audit_identifiers"])
        report = ParentReport(ReportContract.from_record(value["report_contract"]), value["report"])
        object.__setattr__(report, "_audit_identifiers", identifiers)
        return cls(record_id=value["record_id"], goal=EpisodeGoal.from_record(value["goal"]),
                   completion=EpisodeCompletion(**value["completion"]),
                   controller_input=JsonRecord(value["controller_input"]), report=report,
                   _audit_identifiers=identifiers)


@dataclass(frozen=True)
class Contribution:
    """Only projected steering state visible to a containing Episode hook."""

    controller_input: Any
    episode_update: Optional[EpisodeUpdate] = None
    # What the unit produced (a Leaf's accepted value, a child unit's ``ChildProjection.outcome``), kept in the trace and
    # shown to the source in its view.
    outcome: Any = None


@dataclass(frozen=True)
class ChildProjection:
    """What a parent makes of one completed child: the report it keeps (admitted against the child's reporting
    contract), the outcome of the unit and the controller input of the unit."""

    report: Mapping[str, Any]
    outcome: Any
    controller_input: ClosedRecord


@dataclass(frozen=True)
class _AcquiredUnit:
    contribution: Contribution
    child_record: Optional["EpisodeRecord"] = None
    child_result: Optional[ClosedRecord] = None

    def __post_init__(self) -> None:
        if not isinstance(self.contribution, Contribution):
            raise TypeError("an acquired unit requires a Contribution")
        if (self.child_record is None) != (self.child_result is None):
            raise ValueError(
                "a nested acquisition must retain both its child record and "
                "closed child result"
            )
        if self.child_result is not None:
            _require_closed_record(self.child_result, "child_result")


@dataclass(frozen=True)
class UnitRecord:
    """The full trace of one acquired unit."""

    unit_label: str
    controller_input: Any
    controller_step: Any
    epoch: str
    unit_ref: UnitRef
    episode_update: Optional[EpisodeUpdate] = None
    child: Optional["EpisodeRecord"] = None
    child_result: Optional[ClosedRecord] = None
    outcome: Any = None

    @property
    def unit_id(self) -> str:
        return self.unit_ref.unit_id

    def as_record(self) -> dict[str, Any]:
        return {
            "unit_label": self.unit_label,
            "unit_ref": self.unit_ref.as_record(),
            "unit_id": self.unit_id,
            "epoch": self.epoch,
            "controller_input": _record_value(self.controller_input),
            "controller_step": _record_value(self.controller_step),
            "episode_update": (
                self.episode_update.as_record()
                if self.episode_update is not None
                else None
            ),
            "outcome": _record_value(self.outcome),
            "child": self.child.as_record() if self.child is not None else None,
            "child_result": (
                _record_value(self.child_result)
                if self.child_result is not None
                else None
            ),
        }


@dataclass(frozen=True)
class UnitView:
    """The per-unit information visible to a post-controller hook."""

    unit_label: str
    controller_input: Any
    controller_step: Any
    epoch: str
    unit_ref: UnitRef
    episode_update: Optional[EpisodeUpdate] = None
    outcome: Any = None


@dataclass(frozen=True)
class ResumeUnit:
    """One previously completed unit restored at a durable boundary: its controller input, its outcome and,
    for a child unit, the update the parent received."""

    label: str
    controller_input: Any
    outcome: Any = None
    episode_update: Optional[EpisodeUpdate] = None

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("ResumeUnit.label must be a non-empty string")


@dataclass(frozen=True)
class EpisodeRecord:
    """The complete recursive trace of one Episode."""

    scope_level: str
    scope_key: str
    units_consumed: int
    ended_by: str
    unit_records: tuple[UnitRecord, ...]
    controller_state: Any
    request: EpisodeRequest
    path: Path = ()
    episode_ref: Optional[EpisodeRef] = None

    @property
    def goal(self) -> EpisodeGoal:
        return self.request.goal

    @property
    def episode_id(self) -> str:
        return self.episode_ref.episode_id if self.episode_ref is not None else ""

    @property
    def run_id(self) -> str:
        return self.episode_ref.run_id if self.episode_ref is not None else ""

    def as_record(self) -> dict[str, Any]:
        return {
            "scope_level": self.scope_level,
            "scope_key": self.scope_key,
            "path": [list(item) for item in self.path],
            "episode_ref": (
                self.episode_ref.as_record() if self.episode_ref else None
            ),
            "episode_id": self.episode_id,
            "run_id": self.run_id,
            "goal": self.goal.as_record(),
            "request": self.request.as_record(),
            "units_consumed": self.units_consumed,
            "ended_by": self.ended_by,
            "controller_state": _record_value(self.controller_state),
            "units": [unit.as_record() for unit in self.unit_records],
        }


@dataclass(frozen=True)
class Grain:
    """One loop level and the controller function bound to that level."""

    name: str
    unit: str
    result: str
    controller: ControllerFactory

    def __post_init__(self) -> None:
        for field_name in ("name", "unit", "result"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Grain.{field_name} must be a non-empty sentence")
        if not callable(self.controller):
            raise TypeError("Grain.controller must be a controller function")


def _episode_tree_options(
    root: Any,
    self_nesting: Any,
    recursive_edges: Any,
) -> tuple[set[str], set[tuple[str, str]]]:
    """Validate tree-wide recursion declarations."""

    if not isinstance(root, Grain):
        raise TypeError("EpisodeTree.root must be a Grain")
    if not isinstance(self_nesting, tuple) or any(
        not isinstance(name, str) or not name for name in self_nesting
    ):
        raise TypeError("EpisodeTree.self_nesting must be a tuple of grain names")
    if len(set(self_nesting)) != len(self_nesting):
        raise ValueError("EpisodeTree.self_nesting contains duplicates")
    if not isinstance(recursive_edges, tuple):
        raise TypeError("EpisodeTree.recursive_edges must be a tuple")
    normalized_edges: set[tuple[str, str]] = set()
    for edge in recursive_edges:
        if (
            not isinstance(edge, tuple)
            or len(edge) != 2
            or any(not isinstance(name, str) or not name for name in edge)
        ):
            raise TypeError(
                "EpisodeTree.recursive_edges must contain grain-name pairs"
            )
        normalized_edges.add(edge)
    if len(normalized_edges) != len(recursive_edges):
        raise ValueError("EpisodeTree.recursive_edges contains duplicates")
    normalized_edges.update((name, name) for name in self_nesting)
    return set(self_nesting), normalized_edges


def _declare_tree_grain(by_name: dict[str, Grain], grain: Any, role: str) -> Grain:
    if not isinstance(grain, Grain):
        raise TypeError(f"EpisodeTree {role} must be Grain values")
    known = by_name.get(grain.name)
    if known is not None and known != grain:
        raise ValueError(f"grain {grain.name!r} has conflicting declarations")
    by_name[grain.name] = grain
    return grain


def _normalize_tree_children(
    children: Mapping[Grain, Iterable[Grain]],
    recursive_names: set[str],
    by_name: dict[str, Grain],
) -> dict[Grain, tuple[Grain, ...]]:
    normalized: dict[Grain, tuple[Grain, ...]] = {}
    for raw_parent, raw_children in children.items():
        parent = _declare_tree_grain(by_name, raw_parent, "parent keys")
        declared_children = tuple(raw_children)
        child_names: set[str] = set()
        for raw_child in declared_children:
            if not isinstance(raw_child, Grain):
                raise TypeError("EpisodeTree children must be Grain values")
            if raw_child.name in child_names:
                raise ValueError(
                    f"grain {raw_child.name!r} is listed twice under {parent.name!r}"
                )
            child_names.add(raw_child.name)
            child = _declare_tree_grain(by_name, raw_child, "children")
            if child.name == parent.name:
                if child.name not in recursive_names:
                    raise ValueError(
                        f"grain {child.name!r} may self-nest only when "
                        "declared in EpisodeTree.self_nesting"
                    )
                continue
        normalized[parent] = declared_children
    return normalized


def _tree_edges(
    normalized: Mapping[Grain, tuple[Grain, ...]],
) -> set[tuple[str, str]]:
    return {
        (parent.name, child.name)
        for parent, children in normalized.items()
        for child in children
    }


def _cyclic_tree_edges(
    normalized: Mapping[Grain, tuple[Grain, ...]],
) -> set[tuple[str, str]]:
    adjacency = {
        parent.name: {child.name for child in children}
        for parent, children in normalized.items()
    }

    def reaches(start: str, target: str) -> bool:
        frontier = [start]
        seen: set[str] = set()
        while frontier:
            current = frontier.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            frontier.extend(adjacency.get(current, ()))
        return False

    return {
        (parent, child)
        for parent, children in adjacency.items()
        for child in children
        if reaches(child, parent)
    }


def _reachable_tree_grains(
    root: Grain,
    normalized: Mapping[Grain, tuple[Grain, ...]],
) -> set[str]:
    reachable = {root.name}
    frontier = [root]
    while frontier:
        parent = frontier.pop()
        for child in normalized.get(parent, ()):
            if child.name not in reachable:
                reachable.add(child.name)
                frontier.append(child)
    return reachable


def _validate_tree_graph(
    root: Grain,
    normalized: Mapping[Grain, tuple[Grain, ...]],
    by_name: Mapping[str, Grain],
    recursive_names: set[str],
    recursive_edges: set[tuple[str, str]],
) -> None:
    unreachable = set(by_name) - _reachable_tree_grains(root, normalized)
    if unreachable:
        raise ValueError(
            f"EpisodeTree has unreachable parent grains: {sorted(unreachable)}"
        )
    unknown_recursive = recursive_names - set(by_name)
    if unknown_recursive:
        raise ValueError(
            "EpisodeTree.self_nesting names undeclared grains: "
            f"{sorted(unknown_recursive)}"
        )
    self_edges = {
        child.name
        for parent, declared_children in normalized.items()
        for child in declared_children
        if parent.name == child.name
    }
    missing_self_edges = recursive_names - self_edges
    if missing_self_edges:
        raise ValueError(
            "self-nesting grains must declare their own Grain as a child: "
            f"{sorted(missing_self_edges)}"
        )
    actual_edges = _tree_edges(normalized)
    undeclared_edges = recursive_edges - actual_edges
    if undeclared_edges:
        raise ValueError(
            "EpisodeTree.recursive_edges names undeclared edges: "
            f"{sorted(undeclared_edges)}"
        )
    missing_recursive = _cyclic_tree_edges(normalized) - recursive_edges
    if missing_recursive:
        raise ValueError(
            "cyclic EpisodeTree edges require explicit recursive_edges: "
            f"{sorted(missing_recursive)}"
        )


@dataclass(frozen=True)
class EpisodeTree:
    """The Episode types allowed beneath each parent Episode type.

    Runtime Episode instances still form an ordinary tree of paths. This
    declaration describes which *types* may occupy each child position, so a
    parent may choose among several child bindings without weakening nesting
    validation. Type-level cycles are allowed only when every cyclic edge is
    declared. Each Episode instance applies its own numerical progress
    controller to determine when its loop has yielded enough.
    """

    root: Grain
    children: Mapping[Grain, Iterable[Grain]] = field(default_factory=dict)
    self_nesting: tuple[str, ...] = ()
    recursive_edges: tuple[tuple[str, str], ...] = ()
    def __post_init__(self) -> None:
        recursive_names, recursive_edges = _episode_tree_options(
            self.root,
            self.self_nesting,
            self.recursive_edges,
        )
        by_name: dict[str, Grain] = {self.root.name: self.root}
        normalized = _normalize_tree_children(
            self.children,
            recursive_names,
            by_name,
        )
        _validate_tree_graph(
            self.root,
            normalized,
            by_name,
            recursive_names,
            recursive_edges,
        )

        object.__setattr__(self, "children", normalized)
        object.__setattr__(self, "_by_name", by_name)
        object.__setattr__(
            self,
            "recursive_edges",
            tuple(sorted(recursive_edges)),
        )

    @classmethod
    def linear(cls, grains: Iterable[Grain]) -> "EpisodeTree":
        """Build the declaration for a single linear path."""

        ordered = tuple(grains)
        if not ordered:
            raise ValueError("a linear EpisodeTree needs at least one Grain")
        return cls(
            root=ordered[0],
            children={
                parent: (child,)
                for parent, child in zip(ordered, ordered[1:])
            },
        )

    @classmethod
    def recursive(cls, grain: Grain) -> "EpisodeTree":
        """Declare one reusable Episode type that may construct itself.

        Every instance owns its own controller and stopping rule.
        """

        return cls(
            root=grain,
            children={grain: (grain,)},
            self_nesting=(grain.name,),
        )

    def allowed_children(self, parent_name: str) -> tuple[Grain, ...]:
        parent = self._by_name.get(str(parent_name))
        if parent is None:
            return ()
        return tuple(self.children.get(parent, ()))


@dataclass(frozen=True)
class EpisodeView:
    """The compact running state visible to one Episode's source."""

    grain: Grain
    key: str
    path: Path
    units_consumed: int
    # The update of each completed child unit, in order (restored on resume). A unit's own update joins
    # ``updates`` after the unit completes, so the view that prices a child unit (``with_unit``) lists only the
    # updates of the units before it; that unit's own report is in ``outcomes``.
    updates: tuple[EpisodeUpdate, ...]
    controller_state: Any
    episode_ref: EpisodeRef
    request: EpisodeRequest
    # What the Episode admitted from its commissioner, the outcome of each completed unit in order (restored
    # on resume) and the read-only reader of the records the Episode holds (``None`` when the builder gives none).
    parent_input: Any = None
    outcomes: tuple[Any, ...] = ()
    records: Any = None

    @property
    def goal(self) -> EpisodeGoal:
        return self.request.goal

    def with_unit(self, outcome: Any) -> "EpisodeView":
        """This view as it stands once the unit being acquired completes with ``outcome``."""
        return replace(self, units_consumed=self.units_consumed + 1, outcomes=self.outcomes + (outcome,))

    @property
    def child_reports(self) -> tuple[ParentReport, ...]:
        return tuple(update.report for update in self.updates)


class UnitSource(Protocol):
    """Return the next unit (``next`` may be a coroutine function). A source always returns a unit: only the
    Episode's controller ends the Episode, so returning ``None`` raises."""

    def next(self, view: EpisodeView) -> Any: ...


class Acquirable(Protocol):
    """Implemented by :class:`Leaf` and :class:`ChildEpisodeUnit`."""

    label: str

    async def acquire_async(self, ctx: "Context") -> _AcquiredUnit: ...


@dataclass(frozen=True)
class Leaf:
    """A raw unit bound to extraction, acceptance, and result projection."""

    unit: Any
    extract: Callable[[Any], Any]
    result: Callable[[Any, Any], Any]
    label: str
    accept: Optional[Callable[[Any, Any], Any]] = None

    async def acquire_async(self, ctx: "Context") -> _AcquiredUnit:
        extracted = self.extract(self.unit)
        if inspect.isawaitable(extracted):
            extracted = await extracted
        accepted = self.accept(self.unit, extracted) if self.accept is not None else extracted
        if inspect.isawaitable(accepted):
            accepted = await accepted
        projected = self.result(self.unit, accepted)
        if inspect.isawaitable(projected):
            projected = await projected
        return _AcquiredUnit(Contribution(controller_input=projected, outcome=_record_value(accepted)))


@dataclass(frozen=True)
class Episode:
    """One instance of one Grain, composed from swappable parts."""

    grain: Grain
    key: str
    source: UnitSource
    request: EpisodeRequest
    build_result: Callable[
        [EpisodeRecord], ClosedRecord | Awaitable[ClosedRecord]
    ]
    on_unit: Optional[Callable[[Any, Contribution, UnitView], Any]] = None
    on_close: Optional[Callable[[EpisodeRecord], Any]] = None
    resume_units: tuple[ResumeUnit, ...] = ()
    # What the Episode admitted from its commissioner (``EpisodeView.parent_input``) and the reader of the
    # records it holds (``EpisodeView.records``).
    parent_input: Any = None
    records: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.grain, Grain):
            raise TypeError(
                f"Episode.grain must be a Grain, got {type(self.grain).__name__}"
            )
        if not isinstance(self.key, str) or not self.key:
            raise ValueError("Episode.key must be a non-empty string")
        if not hasattr(self.source, "next"):
            raise TypeError("Episode.source must implement UnitSource.next(view)")
        if not callable(self.build_result):
            raise TypeError("Episode.build_result must be callable")
        if self.on_close is not None and not callable(self.on_close):
            raise TypeError("Episode.on_close must be callable")
        if not isinstance(self.request, EpisodeRequest):
            raise TypeError("Episode.request must be an EpisodeRequest")
        if not isinstance(self.resume_units, tuple) or any(
            not isinstance(unit, ResumeUnit) for unit in self.resume_units
        ):
            raise TypeError("Episode.resume_units must contain ResumeUnit values")

    @property
    def label(self) -> str:
        return self.key

    @property
    def goal(self) -> EpisodeGoal:
        return self.request.goal

    @classmethod
    def identity(
        cls,
        ctx: "Context",
        grain: Grain,
        key: str,
        *,
        parent_path: Path = (),
    ) -> EpisodeRef:
        path = tuple(parent_path) + ((grain.name, str(key)),)
        return EpisodeRef(run_id=ctx.require_run_id(), path=path)

    async def run_async(self, ctx: "Context") -> EpisodeRecord:
        self._validate_position(ctx)
        if not ctx.path and not ctx.has_run_id:
            ctx.bind_run_id(self.key)
        scope = ctx.enter(self.grain, self.key)
        ctx._active_episodes[scope] = self
        try:
            record = await self._run_loop_async(ctx, scope)
            if self.on_close is not None:
                result = self.on_close(record)
                if inspect.isawaitable(result):
                    await result
            return record
        finally:
            ctx.leave(scope)

    def _view(self, ctx: "Context", scope: Scope, records: list[UnitRecord]) -> EpisodeView:
        return EpisodeView(
            grain=self.grain,
            key=self.key,
            path=scope,
            units_consumed=len(records),
            updates=tuple(ctx._child_updates.get(scope, ())),
            controller_state=ctx.runtime.state(scope),
            episode_ref=EpisodeRef(run_id=ctx.require_run_id(), path=scope),
            request=self.request,
            parent_input=self.parent_input,
            outcomes=tuple(record.outcome for record in records),
            records=self.records,
        )

    def view_of(self, record: "EpisodeRecord") -> EpisodeView:
        """The view of a closed Episode from its record (for its result)."""
        return EpisodeView(
            grain=self.grain, key=self.key, path=record.path, units_consumed=record.units_consumed,
            updates=tuple(unit.episode_update for unit in record.unit_records if unit.episode_update is not None),
            controller_state=record.controller_state, episode_ref=record.episode_ref, request=self.request,
            parent_input=self.parent_input, outcomes=tuple(unit.outcome for unit in record.unit_records),
            records=self.records)

    def _validate_position(self, ctx: "Context") -> None:
        if ctx.path and not self.goal.parent_goal_id:
            raise ValueError("a nested Episode must carry a child Goal")
        if not ctx.path and self.goal.parent_goal_id:
            raise ValueError("a root Episode Goal may not name a parent Goal")
        parent = ctx._active_episodes.get(ctx.path)
        if parent is None and ctx._boundary_commission is not None and ctx.path == ctx._boundary_path:
            parent_goal, child_goal, grain, key = ctx._boundary_commission
            if (self.goal.parent_goal_id != parent_goal or self.goal.goal_id != child_goal
                    or self.grain.name != grain or self.key != key
                    or not isinstance(self.request.report_contract, ReportContract)):
                raise ValueError("entry Episode differs from its commission below the scoped boundary")
        if parent is not None:
            if not isinstance(self.request.report_contract, ReportContract):
                raise ValueError("a child requires its parent's reporting contract before execution")
            if not ctx._child_edges or ctx._child_edges[-1] is not self:
                raise ValueError("nested execution requires the parent's ChildEpisodeUnit reporting boundary")
            if self.goal.parent_goal_id != parent.goal.goal_id:
                raise ValueError("child Goal does not belong to the active parent Episode")

    def _validate_child(self, item: Any) -> None:
        if isinstance(item, Episode):
            raise TypeError(
                "a nested Episode must be carried by a parent-owned "
                "ChildEpisodeUnit"
            )
        if not isinstance(item, ChildEpisodeUnit):
            return
        if item.child.goal.parent_goal_id != self.goal.goal_id:
            raise ValueError(
                "a child Episode Goal must name the containing Episode Goal"
            )

    def _record(
        self,
        ctx: "Context",
        scope: Scope,
        records: list[UnitRecord],
        ended_by: str,
    ) -> EpisodeRecord:
        path = scope
        return EpisodeRecord(
            scope_level=path[-1][0],
            scope_key=path[-1][1],
            units_consumed=len(records),
            ended_by=ended_by,
            unit_records=tuple(records),
            controller_state=ctx.runtime.state(scope),
            path=path,
            episode_ref=EpisodeRef(run_id=ctx.require_run_id(), path=path),
            request=self.request,
        )

    def _append_record(
        self,
        ctx: "Context",
        scope: Scope,
        records: list[UnitRecord],
        label: str,
        acquired: _AcquiredUnit,
    ) -> tuple[UnitRecord, UnitView]:
        if scope != ctx.path:
            raise ValueError("completed unit requires its active Episode scope")
        unit_ref = UnitRef(
            EpisodeRef(run_id=ctx.require_run_id(), path=scope).episode_id,
            len(records),
        )
        controller_input = acquired.contribution.controller_input
        step = ctx.runtime.advance(scope, label, controller_input)
        record = UnitRecord(
            unit_label=label,
            controller_input=controller_input,
            controller_step=step,
            epoch=ctx.runtime.epoch(scope),
            unit_ref=unit_ref,
            episode_update=acquired.contribution.episode_update,
            child=acquired.child_record,
            child_result=acquired.child_result,
            outcome=acquired.contribution.outcome,
        )
        view = UnitView(
            unit_label=label,
            controller_input=record.controller_input,
            controller_step=record.controller_step,
            epoch=record.epoch,
            unit_ref=record.unit_ref,
            episode_update=record.episode_update,
            outcome=record.outcome,
        )
        records.append(record)
        return record, view

    def _restore_units(self, ctx: "Context", scope: Scope) -> list[UnitRecord]:
        records: list[UnitRecord] = []
        for prior in self.resume_units:
            self._append_record(
                ctx,
                scope,
                records,
                prior.label,
                _AcquiredUnit(Contribution(prior.controller_input, outcome=prior.outcome,
                                           episode_update=prior.episode_update)),
            )
            if prior.episode_update is not None:
                ctx._receive_child_update(prior.episode_update)
        return records

    @staticmethod
    def _state_stops(state: Any) -> bool:
        stop = getattr(state, "stop", None)
        if not isinstance(stop, bool):
            raise TypeError("a controller state must expose a boolean stop")
        return stop

    async def _run_loop_async(self, ctx: "Context", scope: Scope) -> EpisodeRecord:
        records = self._restore_units(ctx, scope)
        stopped = bool(records) and self._state_stops(ctx.runtime.state(scope))
        while not stopped:
            item = self.source.next(self._view(ctx, scope, records))
            if inspect.isawaitable(item):
                item = await item
            if item is None:
                raise TypeError("an Episode source must return a unit: only the controller ends an Episode")
            stopped = (await self._acquire_unit_async(ctx, scope, records, item)).stop
        return self._record(ctx, scope, records, END_YIELD_STOP)

    async def _acquire_unit_async(self, ctx, scope, records, item):
        self._validate_child(item)
        acquired = await item.acquire_async(ctx)
        if not isinstance(acquired, _AcquiredUnit):
            raise TypeError("Acquirable.acquire_async() returned an invalid result")
        _, unit_view = self._append_record(ctx, scope, records, item.label, acquired)
        if self.on_unit is not None:
            result = self.on_unit(item, acquired.contribution, unit_view)
            if inspect.isawaitable(result):
                await result
        return unit_view.controller_step


@dataclass(frozen=True)
class ChildEpisodeUnit:
    """A parent-owned invocation edge around one child Episode.

    The child owns ``build_result``. The parent owns one projection of the child's closed result
    (:class:`ChildProjection`): the report it keeps, the unit's outcome and the unit's controller input.
    """

    child: Episode
    project: Callable[
        [ClosedRecord, EpisodeCompletion, EpisodeRequest],
        ChildProjection | Awaitable[ChildProjection],
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.child, Episode):
            raise TypeError("ChildEpisodeUnit.child must be an Episode")
        if not callable(self.project):
            raise TypeError("ChildEpisodeUnit.project must be callable")
        if not isinstance(self.child.request.report_contract, ReportContract):
            raise TypeError("a child invocation requires a reporting contract")

    @property
    def label(self) -> str:
        return self.child.label

    async def acquire_async(self, ctx: "Context") -> _AcquiredUnit:
        with ctx._child_invocation(self.child):
            record = await self.child.run_async(ctx)
            acquired = await self._finish_async(record)
        ctx._receive_child_update(acquired.contribution.episode_update)
        return acquired

    async def _finish_async(self, record: EpisodeRecord) -> _AcquiredUnit:
        child_result = self.child.build_result(record)
        if inspect.isawaitable(child_result):
            child_result = await child_result
        child_result = _require_closed_record(child_result, "Episode.build_result()")
        request = self.child.request
        completion = EpisodeCompletion.from_record(record)
        identifiers = tuple(dict.fromkeys((record.episode_id, record.goal.goal_id,
                                           *request.message.audit_identifiers(), *child_result.audit_identifiers())))
        projection = self.project(child_result, completion, request)
        if inspect.isawaitable(projection):
            projection = await projection
        if not isinstance(projection, ChildProjection):
            raise TypeError("ChildEpisodeUnit.project must return a ChildProjection")
        admitted = request.report_contract.admit(projection.report, audit_identifiers=identifiers)
        controller_input = _require_closed_record(projection.controller_input, "ChildProjection.controller_input")
        update = EpisodeUpdate(record_id=record.episode_id, goal=record.goal, completion=completion,
                               controller_input=controller_input, report=admitted, _audit_identifiers=identifiers)
        return _AcquiredUnit(
            contribution=Contribution(controller_input=controller_input, episode_update=update,
                                      outcome=_record_value(projection.outcome)),
            child_record=record, child_result=child_result)



class Context:
    """Run identity, nesting and controller routing."""

    def __init__(
        self,
        *,
        tree: EpisodeTree,
        run_id: Optional[str] = None,
        runtime: Optional[ControllerRuntime] = None,
        boundary_path: Path = (),
    ) -> None:
        if not isinstance(tree, EpisodeTree):
            raise TypeError("Context.tree must be an EpisodeTree")
        self.runtime = runtime if runtime is not None else ControllerRuntime()
        self.tree = tree
        parent: Path = ()
        for grain_name, key in boundary_path:
            allowed = (tree.root,) if not parent else tree.allowed_children(parent[-1][0])
            if not isinstance(key, str) or not key or grain_name not in {grain.name for grain in allowed}:
                raise ValueError("frozen context boundary is outside the declared Episode tree")
            parent = (*parent, (grain_name, key))
        self._boundary_path = parent
        self._boundary_commission = None
        self._stack: list[Path] = []
        self._active_episodes: dict[Path, Episode] = {}
        self._child_edges: list[Episode] = []
        self._child_updates: dict[Path, list[EpisodeUpdate]] = {}
        self._grains: dict[str, Grain] = {}
        self._run_id: Optional[str] = None
        if run_id is not None:
            self.bind_run_id(run_id)

    @classmethod
    def from_commission(cls, *, tree, run_id, parent_path, parent_goal_id,
                        child_goal_id, grain, key, runtime=None):
        """An entry Episode below a scoped, unexecuted ancestor boundary (no live parent stack).

        The caller must first validate the commission. The Episode validates its goal, role and key before
        work. No parent controller, source or history is loaded by this constructor.
        """
        if not parent_path or any(not isinstance(value, str) or not value
                for value in (parent_goal_id, child_goal_id, grain, key)):
            raise ValueError('complete parent-owned commission identity required')
        boundary = tuple(tuple(segment) for segment in parent_path)
        context = cls(tree=tree, run_id=run_id, runtime=runtime, boundary_path=boundary)
        if grain not in {child.name for child in tree.allowed_children(boundary[-1][0])}:
            raise ValueError('commissioned child is outside the declared episode tree')
        context._boundary_commission = (parent_goal_id, child_goal_id, grain, key)
        return context

    def _receive_child_update(self, update: EpisodeUpdate) -> None:
        if not self.path:
            raise ValueError("a child report requires an active parent Episode")
        self._child_updates.setdefault(self.path, []).append(update)

    @contextmanager
    def _child_invocation(self, child: Episode):
        if self.path not in self._active_episodes:
            raise ValueError("a child invocation requires an active parent Episode")
        self._child_edges.append(child)
        try:
            yield
        finally:
            self._child_edges.pop()

    def bind_run_id(self, run_id: str) -> None:
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("Context run_id must be a non-empty string")
        if self._run_id is not None and self._run_id != run_id:
            raise ValueError("Context run_id is already bound")
        self._run_id = run_id

    @property
    def has_run_id(self) -> bool:
        return self._run_id is not None

    def require_run_id(self) -> str:
        if self._run_id is None:
            raise RuntimeError(
                "Context run_id must be bound before Episode identity is read"
            )
        return self._run_id

    @property
    def path(self) -> Path:
        return self._stack[-1] if self._stack else self._boundary_path

    def _allowed_next(self, parent: Path) -> tuple[Grain, ...]:
        if not parent:
            return (self.tree.root,)
        return self.tree.allowed_children(parent[-1][0])

    def enter(self, grain: Grain, key: str) -> Scope:
        if not isinstance(grain, Grain):
            raise TypeError(f"enter() needs a Grain, got {type(grain).__name__}")
        known = self._grains.get(grain.name)
        if known is not None and known is not grain and known != grain:
            raise ValueError(f"grain {grain.name!r} was declared more than once")
        parent = self.path
        allowed = self._allowed_next(parent)
        declared = next(
            (item for item in allowed if item.name == grain.name),
            None,
        )
        if declared is None:
            raise ValueError(
                f"grain {grain.name!r} may not nest under "
                f"{parent[-1][0] if parent else 'the root'}; allowed: "
                f"{[item.name for item in allowed]}"
            )
        if declared != grain:
            raise ValueError(
                f"grain {grain.name!r} differs from its EpisodeTree declaration"
            )
        path: Path = tuple(parent) + ((grain.name, str(key)),)
        scope = self.runtime.open_scope(path, grain.controller)
        self._grains[grain.name] = grain
        self._stack.append(scope)
        return scope

    def leave(self, scope: Scope) -> None:
        if not self._stack or self._stack[-1] != scope:
            raise RuntimeError("episodes must close in nesting order")
        self._stack.pop()
        self._active_episodes.pop(scope, None)
