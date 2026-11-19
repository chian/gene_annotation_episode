"""Explicit binding registry. Nothing is inferred, defaulted or instantiated.

Every registered binding is an instance of a class that inherits directly from the system type
``episode_runtime.EpisodeBinding``; its class definition has already checked that it supplies every
member its episode files must supply, and the registry accepts the instance only when its class passed that
check and its bases and members are still the checked ones. The runner never constructs a binding; each home
constructs its own binding instances.
"""
from __future__ import annotations

from .episode_type import EpisodeBinding, checked_members


class MissingBinding(LookupError):
    """No supplied binding has this binding path."""


class BindingRegistry:
    """Bindings addressed by their explicit ``binding_path``."""

    def __init__(self, bindings):
        self._by_path = {}
        for binding in bindings:
            if not isinstance(binding, EpisodeBinding):
                raise TypeError('binding_must_be_an_EpisodeBinding:' + type(binding).__name__)
            checked_members(type(binding))
            if vars(binding):
                # An instance attribute would stand in for a member its class definition checked.
                raise TypeError('binding_instance_has_attributes_of_its_own:' + type(binding).__name__ + ':'
                                + ','.join(sorted(vars(binding))))
            path = binding.binding_path
            if path in self._by_path:
                raise ValueError('duplicate_binding_path:' + path)
            self._by_path[path] = binding

    @property
    def paths(self):
        return tuple(self._by_path)

    def binding(self, path):
        try:
            return self._by_path[path]
        except KeyError as error:
            raise MissingBinding('binding_not_registered:' + str(path)) from error

    def subtree(self, entry_path):
        """Every binding reachable from the entry, each once (recursive slots are not expanded again)."""
        found, frontier = {}, [entry_path]
        while frontier:
            path = frontier.pop()
            if path in found:
                continue
            binding = self.binding(path)
            found[path] = binding
            frontier.extend(binding.child_slots.values())
        return found
