"""The nine native-source repositories on the custody-scoped store, before any sheet exists: each is built on the
Episode's store, holds no sheet, and lists none, through the real runner."""
import pytest

from .evolutionary_history_world import read, run, world  # noqa: F401

REPOSITORIES = (
    'literature_concentration_window_storage:LiteratureConcentrationWindowRepository',
    'literature_endpoint_signal_storage:LiteratureEndpointSignalRepository',
    'literature_kinetic_summary_precision_storage:LiteratureKineticSummaryPrecisionRepository',
    'literature_measurement_comparison_storage:LiteratureMeasurementComparisonRepository',
    'literature_compiled_assay_storage:LiteratureCompiledAssayRepository',
    'literature_rate_observation_storage:LiteratureRateObservationRepository',
    'literature_rate_observation_storage:LiteratureReportedCurveRepository',
    'literature_rate_replicate_storage:LiteratureRateReplicateRepository',
    'literature_kinetic_storage:LiteratureKineticRepository',
    'literature_kinetic_model_storage:LiteratureKineticModelRepository',
)


@pytest.mark.parametrize('repository', REPOSITORIES)
def test_a_repository_on_a_store_with_no_sheet_holds_none(world, repository):  # noqa: F811
    held, = run(world, 'empty', [read(repository, 'held_sheet_refs')])
    assert held == []
