"""Invoke a privately selected shared function without bypassing overrides.

The bound method is evaluated by the caller at the original call site. A real
instance/class override or other custom callable receives the original call.
No source/binding/role callback is added before that invocation.
"""
from types import MethodType


def invoke(bound, selected, source, **keywords):
    if type(bound) is MethodType and bound.__func__ is selected:
        return selected(bound.__self__, source, **keywords)
    return bound(source, **keywords)
