"""The runtime collaborators every run is linked with, and the interface each must expose.

Every run is linked with the same four system collaborators. The runner checks at link time, before anything is
built or recorded, that each is present and exposes the interface below; it raises ``LinkError`` otherwise.

| Name | Interface |
|---|---|
| ``store`` | the run's one shared ``gene_annotation_episode.state.Store`` (checked at link: ``get``, ``get_artifact``, ``put``, ``artifact``); episodes reach it only through custody (``store_scope.py``) |
| ``model_provider`` | ``async complete(episode_id, role, instructions, context, output_schema) -> response`` |
| ``continuation`` | a ``Mapping`` of yield controller settings, keyed by binding path; recorded in the run journal and compared on resume |
| ``services`` | a ``Mapping`` of service name -> zero-argument factory; every name an episode declares must be present |
"""
from __future__ import annotations

from collections.abc import Mapping
import inspect

# name -> ((method, must_be_async), ...); 'continuation' and 'services' are mappings, not methods.
STANDARD_COLLABORATORS = {
    'store': (('get', False), ('get_artifact', False), ('put', False), ('artifact', False)),
    'model_provider': (('complete', True),),
    'continuation': (),
    'services': (),
}


def interface_failures(name, value):
    """What the supplied collaborator lacks of its standard interface (empty when it conforms)."""
    if name == 'continuation':
        return [] if isinstance(value, Mapping) else ['mapping']
    if name == 'services':
        if not isinstance(value, Mapping):
            return ['mapping']
        return ['factory:' + str(key) for key, factory in value.items() if not callable(factory)]
    failures = []
    for method, must_be_async in STANDARD_COLLABORATORS[name]:
        bound = getattr(value, method, None)
        if not callable(bound):
            failures.append(method)
        elif must_be_async and not inspect.iscoroutinefunction(bound):
            failures.append(method + ':async')
    return failures


__all__ = ['STANDARD_COLLABORATORS', 'interface_failures']
