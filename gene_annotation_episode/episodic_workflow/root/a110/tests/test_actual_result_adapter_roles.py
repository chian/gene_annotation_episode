"""Actual adapter predicates short-circuit without reading foreign assignments."""
from __future__ import annotations
import importlib
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
ADAPTERS = (('local_file_capture_results', 'LocalFileSourceResults', 'local_file_source_selector_v1'),
    ('native_flux_balance_results', 'NativeFluxBalanceResults', 'flux_balance_result_selector_v1'))

@pytest.mark.parametrize('module,classname,version', ADAPTERS)
@pytest.mark.parametrize('role', ('launch', 'launch_local', 'launch_hpc'))
def test_actual_nonresults_predicate_never_reads_assignment(module, classname, version, role):
    adapter_type = getattr(importlib.import_module(AXIS + '.' + module), classname)
    adapter = object.__new__(adapter_type)
    # Missing assignment would raise immediately if the original role-first
    # short circuit were lost. No adapter/store/receipt constructor runs.
    assert adapter.applies(SimpleNamespace(role=role)) is False

@pytest.mark.parametrize('module,classname,version', ADAPTERS)
def test_actual_results_predicate_keeps_original_selector_admission(module, classname, version):
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
    adapter_type = getattr(importlib.import_module(AXIS + '.' + module), classname)
    adapter = object.__new__(adapter_type)
    context = BindingContext(run_id='controlled-predicate', episode_id='controlled-results', role='results',
        path=(('results', 'controlled'),), scope={'subject_refs': []}, assignment={'selector': {'version': version}}, request={})
    assert adapter.applies(context) is True
    assert adapter.applies(SimpleNamespace(role='results', assignment={})) is False
