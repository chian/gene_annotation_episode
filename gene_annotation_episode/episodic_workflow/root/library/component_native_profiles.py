"""Declared source-table formats for A107/A110 native component calculations.

These schemas describe supplied records, not experimental truth or target
attribution. Only the shared HPC adapter authenticates their input/output bytes.
"""
from collections.abc import Mapping
import importlib


VERSION = 'component_axis_native_v1'
OPERATIONS = {'A107': 'partner.request_expression_hpc',
    'A110': 'chemistry.request_accounting_hpc'}
MODULES = {'A107': 'gene_annotation_episode.episodic_workflow.root.a107.a107_expression_contracts',
    'A110': 'gene_annotation_episode.episodic_workflow.root.a110.a110_chemical_contracts'}


def _contract(axis):
    if axis not in MODULES:
        raise ValueError('component_axis_native_unknown_axis')
    return importlib.import_module(MODULES[axis])


class _Profiles(Mapping):
    def __getitem__(self, axis):
        if axis not in MODULES:
            raise KeyError(axis)
        return _contract(axis).VERSION

    def __iter__(self):
        return iter(MODULES)

    def __len__(self):
        return len(MODULES)


PROFILES = _Profiles()

