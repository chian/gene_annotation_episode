"""Compose the existing axis registries for a shared annotation parent."""
from .a102_tools import A102ToolRegistry
from .a104_tools import A104ToolRegistry
from .a107_tools import A107ToolRegistry
from .a110_tools import A110ToolRegistry


class AllEvidenceToolRegistry(A107ToolRegistry, A102ToolRegistry,
                              A104ToolRegistry, A110ToolRegistry):
    COMPONENT_NATIVE_AXES = ('A107', 'A110')
