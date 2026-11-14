"""Privately select the shared owner while preserving the original dynamic override.

The bound method is evaluated at the caller's original expression position.
No source, path, registry, binding or provider callback is probed by this bridge.
"""
from types import MethodType


def invoke(bound, selected, source, **keywords):
    if type(bound) is MethodType and bound.__func__ is selected:
        return selected(bound.__self__, source, **keywords)
    return bound(source, **keywords)
