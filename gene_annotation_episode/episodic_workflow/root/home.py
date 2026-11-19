"""The root's home factory: construct the root binding from ``services['annotation']``.

The settings are exactly ``axis_weights``, ``axis_cutoffs`` (each naming the
nine attached axes) and ``uncertainty_alpha``; anything missing or extra raises.
"""
from __future__ import annotations

from collections.abc import Mapping

from .binding import RootAnnotationBinding

ROOT_SERVICE = 'annotation'
ROOT_SETTINGS = frozenset({'axis_weights', 'axis_cutoffs', 'uncertainty_alpha'})


def root_home_factory(services):
    if not isinstance(services, Mapping) or ROOT_SERVICE not in services:
        raise KeyError('annotation_home_service_required:' + ROOT_SERVICE)
    settings = services[ROOT_SERVICE]
    if not isinstance(settings, Mapping) or set(settings) != ROOT_SETTINGS:
        raise KeyError('annotation_home_settings_must_be_exactly:' + ','.join(sorted(ROOT_SETTINGS)))
    return (RootAnnotationBinding(settings['axis_weights'], settings['axis_cutoffs'],
                                  settings['uncertainty_alpha']),)


__all__ = ['ROOT_SERVICE', 'ROOT_SETTINGS', 'root_home_factory']
