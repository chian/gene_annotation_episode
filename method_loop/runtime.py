"""Path-addressed controller routing for the generic Episode method."""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable


__all__ = [
    "Controller",
    "ControllerFactory",
    "ControllerRuntime",
    "Path",
    "Scope",
]

Path = tuple[tuple[str, str], ...]
Scope = Path


@runtime_checkable
class Controller(Protocol):
    """The behavior an Episode controller supplies.

    The method does not know the controller's estimator, observation shape,
    thresholds, or state schema. It routes the binding-produced value into
    ``observe`` and uses only the boolean ``stop`` of the returned step and of
    ``state()``.
    """

    epoch: str

    def observe(
        self,
        unit_label: str,
        value: object,
        *,
        is_root: bool,
    ) -> Any: ...

    def state(self) -> Any: ...


ControllerFactory = Callable[[Path], Controller]


class ControllerRuntime:
    """Open and route one injected controller per Episode path."""

    def __init__(self) -> None:
        self._controllers: dict[Scope, Controller] = {}

    @staticmethod
    def _normalize_path(path: Path) -> Path:
        if not isinstance(path, tuple) or not path:
            raise ValueError(
                "a scope path is a non-empty tuple of (grain name, key) pairs"
            )
        out: list[tuple[str, str]] = []
        for segment in path:
            if not isinstance(segment, tuple) or len(segment) != 2:
                raise ValueError(
                    f"path segment {segment!r} is not a (grain name, key) pair"
                )
            grain, key = segment
            if not isinstance(grain, str) or not grain:
                raise ValueError("path grain names must be non-empty strings")
            if not isinstance(key, str) or not key:
                raise ValueError("path keys must be non-empty strings")
            out.append((grain, key))
        return tuple(out)

    def controller(self, scope: Scope) -> Controller:
        scope = self._normalize_path(scope)
        if scope not in self._controllers:
            raise LookupError(f"path scope {scope!r} was never opened")
        return self._controllers[scope]

    def open_scope(self, path: Path, factory: ControllerFactory) -> Scope:
        if not callable(factory):
            raise TypeError("open_scope needs a controller function")
        scope = self._normalize_path(path)
        if scope in self._controllers:
            raise ValueError(f"scope already open at path {scope!r}")
        controller = factory(scope)
        if not isinstance(controller, Controller):
            raise TypeError(
                "a Grain controller function must return an object with "
                "observe(), state(), and epoch"
            )
        self._controllers[scope] = controller
        return scope

    def epoch(self, scope: Scope) -> str:
        return str(self.controller(scope).epoch)

    def advance(self, scope: Scope, unit_label: str, value: object) -> Any:
        """Observe once; the controller step must expose a boolean ``stop``."""
        scope = self._normalize_path(scope)
        step = self.controller(scope).observe(str(unit_label), value, is_root=len(scope) == 1)
        if not isinstance(getattr(step, "stop", None), bool):
            raise TypeError("a controller step must expose a boolean stop")
        return step

    def state(self, scope: Scope) -> Any:
        return self.controller(scope).state()
