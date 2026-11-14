"""The monitor owns its information-yield rule in saved execution setup."""

from types import SimpleNamespace

import pytest

from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory


def test_monitor_yield_binding_round_trips_with_its_credit_unit():
    settings = {'kind': 'information_accumulation', 'cutoff': 0.25,
        'uncertainty_alpha': 0.05}
    factory = ExecutionServiceFactory({'api': {'kind': 'api', 'service': 'uniprot'}},
        {}, 1, 1, 0.5, monitor_yield_settings=settings)
    restored = ExecutionServiceFactory.from_record(factory.as_record())
    assert restored.as_record() == factory.as_record()

    binding = MonitorEpisodes(None, information_unit=restored.monitoring_information_unit,
        yield_settings=restored.monitor_yield_settings)
    assert binding.private_yield_binding
    assert binding.as_record()['configuration']['information_unit'] == 0.5
    controller = binding.yield_controller(SimpleNamespace(role='monitor'), 0, 'monitor-epoch')
    assert controller.cost == 0.25
    assert controller.state().estimate.estimator_binding['kind'] == 'monitor_information_accumulation_v1'


def test_monitor_rejects_an_implicit_or_decreasing_information_forecast():
    with pytest.raises(ValueError, match='monitor_information_unit_required_for_yield'):
        MonitorEpisodes(None, yield_settings={'kind': 'information_accumulation',
            'cutoff': 0.25, 'uncertainty_alpha': 0.05})
    binding = MonitorEpisodes(None, information_unit=0.5,
        yield_settings={'kind': 'information_accumulation', 'cutoff': 0.25,
            'uncertainty_alpha': 0.05})
    controller = binding.yield_controller(SimpleNamespace(role='monitor'), 0, 'monitor-epoch')
    controller.observe('new fact', 0.5)
    with pytest.raises(ValueError, match='monitor_information_credit_cannot_decrease'):
        controller.observe('invalid correction', 0)
