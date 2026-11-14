"""Bind moved source functions to their authentic live provider namespace.

This is code-object assembly, not a forwarding call. The substantive definitions
remain in their responsibility modules; relative imports and global reads keep
the original runtime namespace, including later supported rebinding.
"""
from types import FunctionType
import sys


def bind_functions(namespace, definitions, *, runtime_module, qualified_names,
                   defining_module=None):
    module = sys.modules.get(runtime_module)
    if module is None or type(namespace) is not dict or namespace is not vars(module):
        raise TypeError('authentic_live_runtime_namespace_required')
    if set(definitions) != set(qualified_names):
        raise ValueError('exact_moved_function_names_required')
    bound = {}
    for name, function in definitions.items():
        if type(function) is not FunctionType or function.__closure__ is not None:
            raise TypeError('closure_free_moved_function_required')
        if function.__code__.co_freevars or function.__annotations__:
            raise TypeError('unannotated_original_function_required')
        if getattr(function, '__type_params__', ()):
            raise TypeError('original_function_type_parameters_unsupported')
        if function.__globals__ is namespace:
            selected = function
        else:
            selected = FunctionType(function.__code__, namespace, function.__name__,
                                    function.__defaults__)
            selected.__kwdefaults__ = (None if function.__kwdefaults__ is None
                                      else dict(function.__kwdefaults__))
            selected.__annotations__ = dict(function.__annotations__)
            selected.__dict__.update(function.__dict__)
            selected.__doc__ = function.__doc__
        selected.__module__ = runtime_module if defining_module is None else defining_module
        selected.__qualname__ = qualified_names[name]
        bound[name] = selected
    return bound
