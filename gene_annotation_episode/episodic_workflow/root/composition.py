"""The whole registry for a run: the root's home factory plus the nine attached axis home factories.

``compose_registry(services)`` calls ``BindingRegistry.compose`` over
``home.root_home_factory`` and each attached axis's home factory
(``axes.ATTACHMENTS``), so a run can be linked at the root head (``annotation``)
or at any axis head. ``services`` carries the run's shared ``store``, the root's
``annotation`` settings and each axis's own construction services; a missing one
raises in the factory that needs it. Each root slot must then resolve to exactly
the attached head binding class.
"""
from __future__ import annotations

from episode_runtime import BindingRegistry

from .axes import ATTACHMENTS
from .binding import RootAnnotationBinding
from .home import root_home_factory


def compose_registry(services):
    loaded = [(attachment, *attachment.entry_points()) for attachment in ATTACHMENTS]
    registry = BindingRegistry.compose([root_home_factory, *(factory for _, _, factory in loaded)], services)
    root = registry.binding(RootAnnotationBinding.binding_path)
    for attachment, head, _ in loaded:
        if root.child_slots[attachment.role] != attachment.role:
            raise LookupError('annotation_slot_not_bound_to_its_head:' + attachment.role)
        binding = registry.binding(attachment.role)
        if type(binding) is not head:
            raise TypeError('annotation_slot_head_is_not_the_attached_binding:' + attachment.role + ':'
                            + type(binding).__name__)
    return registry


__all__ = ['compose_registry']
