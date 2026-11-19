"""An episode's configured yield declaration and the yield controller it opens.

An episode's configuration declares, per credit task it can be commissioned for, how its continuation is forecast:
the estimator kind, its cutoff (the continuation cost), its parameters and the exact credit definition the
forecast is fitted to. These two functions are what every episode's own ``yield_estimator.py`` did with its
declaration; everything that differs between episodes is a parameter.

* ``checked_yield_declaration(declarations, task, *, credit_definition, yield_method, code_prefix)`` returns the
  declaration configured for ``task`` after checking that it was declared for exactly this credit definition
  (``credit_definition``: the episode's credit projector record) and this estimator kind (``yield_method``: the
  kind the projector's credit requires). It raises ``ValueError('<code_prefix>_yield_binding_missing_for_task:...')``,
  ``..._yield_credit_definition_mismatch:...`` or ``..._yield_method_credit_mismatch:...``.
* ``open_yield_controller(kind, *, epoch, initial_credit, cutoff, parameters, maximum_credit=None, target=None)``
  opens the matching ``yield_control`` controller: ``'accumulation'`` (credit without a declared limit),
  ``'bounded_quality'`` (a quality credit whose definition declares ``maximum_credit``) or ``'completion'``
  (credit toward the commission's finite ``target``). An operand the kind does not take, a missing one, or any
  other kind raises. The controller is returned unchanged: it is a ``method_loop`` Controller, so
  ``build_controller`` returns it directly.
"""
from __future__ import annotations

from collections.abc import Mapping

from method_loop.jsonvalue import canonical

from yield_control import (AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController,
                           YieldParameters)

KINDS = ('accumulation', 'bounded_quality', 'completion')


def _prefix(code_prefix):
    if type(code_prefix) is not str or not code_prefix:
        raise ValueError('yield_declaration_code_prefix_required')
    return code_prefix


def checked_yield_declaration(declarations, task, *, credit_definition, yield_method, code_prefix):
    """The declaration configured for ``task``, checked against the credit it forecasts."""
    prefix = _prefix(code_prefix)
    if not isinstance(declarations, Mapping):
        raise ValueError(prefix + '_yield_bindings_not_configured')
    if type(task) is not str or not task:
        raise ValueError(prefix + '_yield_task_required')
    declaration = declarations.get(task)
    if not isinstance(declaration, Mapping):
        raise ValueError(prefix + '_yield_binding_missing_for_task:' + task)
    if canonical(declaration.get('credit_definition')) != canonical(credit_definition):
        raise ValueError(prefix + '_yield_credit_definition_mismatch:' + task)
    if declaration.get('kind') != yield_method:
        raise ValueError(prefix + '_yield_method_credit_mismatch:' + task)
    return declaration


def _parameters(parameters):
    if isinstance(parameters, YieldParameters):
        return parameters
    if not isinstance(parameters, Mapping):
        raise TypeError('yield_parameters_must_be_a_mapping')
    return YieldParameters(**parameters)


def open_yield_controller(kind, *, epoch, initial_credit, cutoff, parameters, maximum_credit=None, target=None):
    """The ``yield_control`` controller of ``kind`` (see the module docstring)."""
    settings = _parameters(parameters)
    if kind == 'accumulation':
        if maximum_credit is not None or target is not None:
            raise ValueError('accumulation_yield_takes_no_maximum_or_target')
        return AccumulationYieldController(epoch, initial_credit, cutoff, settings)
    if kind == 'bounded_quality':
        if maximum_credit is None or target is not None:
            raise ValueError('bounded_quality_yield_requires_its_declared_maximum_only')
        return BoundedQualityYieldController(epoch, initial_credit, cutoff, maximum_credit, settings)
    if kind == 'completion':
        if target is None or maximum_credit is not None:
            raise ValueError('completion_yield_requires_its_commission_target_only')
        return CompletionYieldController(epoch, initial_credit, cutoff, target, settings)
    raise ValueError('yield_kind_not_available:' + repr(kind))


__all__ = ['KINDS', 'checked_yield_declaration', 'open_yield_controller']
