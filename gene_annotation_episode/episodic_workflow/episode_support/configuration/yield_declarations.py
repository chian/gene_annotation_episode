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
* ``forecast_definition(credit_definition, ceiling_version)`` is the name of the definition a forecast controller's
  learned shares are on: the sha256 digest of the canonical credit definition record (what credit means) and the
  episode's ceiling version (what its ``ceiling`` means, which is code). The estimate ledger keeps only the rows of
  one definition together (``ForecastParameters.definition``).
* ``forecast_definitions(credit_definition, ceiling_versions)`` is the same name per action:
  ``{action type: forecast_definition(credit_definition, version)}`` for ``ceiling_versions`` ``{action type: version}``
  (each action's own ceiling version), so changing one action's ceiling changes only that action's definition and the
  ledger keeps every other action's history.
* ``open_yield_controller(kind, *, epoch, initial_credit, parameters, cutoff=None, maximum_credit=None, target=None,
  definition=None)`` opens the matching ``yield_control`` controller: ``'accumulation'`` (credit without a declared limit),
  ``'bounded_quality'`` (a quality credit whose definition declares ``maximum_credit``), ``'completion'``
  (credit toward the commission's finite ``target``) or ``'forecast'`` (credit whose every offered action declares a
  ceiling: ``ForecastYieldController``; its ``parameters`` are ``ForecastParameters`` (exchange rate, forgetting, job
  kinds) and it requires ``definition`` (``forecast_definitions`` per action, or ``forecast_definition`` for every
  action; never in the declared parameters), it takes no
  ``cutoff``: its cost of one more unit is the expected seconds of each
  action times the exchange rate). An operand the kind does not take, a missing one, or any
  other kind raises. The controller is returned unchanged: it is a ``method_loop`` Controller, so
  ``build_controller`` returns it directly.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib

from method_loop.jsonvalue import canonical

from yield_control import (AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController,
                           ForecastParameters, ForecastYieldController, YieldParameters)

KINDS = ('accumulation', 'bounded_quality', 'completion', 'forecast')


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


def forecast_definition(credit_definition, ceiling_version):
    """The definition of credit and ceiling a forecast controller's shares are on (see the module docstring)."""
    if not isinstance(credit_definition, Mapping) or not credit_definition:
        raise ValueError('forecast_definition_requires_the_credit_definition_record')
    if type(ceiling_version) is not str or not ceiling_version:
        raise ValueError('forecast_definition_requires_the_ceiling_version')
    digest = hashlib.sha256(canonical(credit_definition).encode('utf-8')).hexdigest()
    return 'credit_sha256:' + digest + '|ceiling:' + ceiling_version


def forecast_definitions(credit_definition, ceiling_versions):
    """The definition of credit and ceiling each action's shares are on (see the module docstring)."""
    if not isinstance(ceiling_versions, Mapping) or not ceiling_versions:
        raise ValueError('forecast_definitions_require_the_ceiling_version_of_each_action')
    for action_type in ceiling_versions:
        if type(action_type) is not str or not action_type:
            raise ValueError('forecast_definitions_require_action_types')
    return {action_type: forecast_definition(credit_definition, version)
            for action_type, version in ceiling_versions.items()}


def _parameters(parameters):
    if isinstance(parameters, YieldParameters):
        return parameters
    if not isinstance(parameters, Mapping):
        raise TypeError('yield_parameters_must_be_a_mapping')
    return YieldParameters(**parameters)


def open_yield_controller(kind, *, epoch, initial_credit, parameters, cutoff=None, maximum_credit=None, target=None,
                          definition=None):
    """The ``yield_control`` controller of ``kind`` (see the module docstring)."""
    if kind == 'forecast':
        if cutoff is not None or maximum_credit is not None or target is not None:
            raise ValueError('forecast_yield_takes_no_cutoff_maximum_or_target')
        if definition is None:
            raise ValueError('forecast_yield_requires_its_definition')
        if 'definition' in parameters:
            raise ValueError('forecast_definition_is_derived_not_declared')
        return ForecastYieldController(epoch, initial_credit, ForecastParameters(**parameters, definition=definition))
    if definition is not None:
        raise ValueError('only_the_forecast_yield_takes_a_definition')
    if cutoff is None:
        raise ValueError('yield_cutoff_required:' + str(kind))
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


__all__ = ['KINDS', 'checked_yield_declaration', 'forecast_definition', 'forecast_definitions', 'open_yield_controller']
