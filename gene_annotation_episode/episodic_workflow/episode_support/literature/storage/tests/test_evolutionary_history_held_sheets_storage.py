"""Eleven repositories of the evolutionary-history storage on the custody-scoped store: each is built on the
Episode's scoped store and lists the saved sheets the Episode holds (none yet), through the real runner."""
import pytest

from .evolutionary_history_world import read, run, world  # noqa: F401

REPOSITORIES = (
    'literature_active_site_storage:LiteratureActiveSiteRepository',
    'literature_aggregation_storage:LiteratureA105AggregationRepository',
    'literature_assay_grading_storage:LiteratureAssayGradingRepository',
    'literature_calibration_recovery_storage:LiteratureCalibrationRecoveryRepository',
    'literature_channel_storage:LiteratureChannelRepository',
    'literature_completion_time_storage:LiteratureCompletionTimeRepository',
    'literature_parent_depletion_storage:LiteratureParentDepletionRepository',
    'literature_stoichiometric_balance_storage:LiteratureStoichiometricBalanceRepository',
    'literature_ion_discrimination_storage:LiteratureIonDiscriminationRepository',
    'literature_measurement_validation_storage:LiteratureMeasurementValidationRepository',
    'literature_product_coupling_storage:LiteratureProductCouplingRepository',
)


@pytest.mark.parametrize('repository', REPOSITORIES)
def test_a_repository_holds_no_sheet_before_one_is_saved(world, repository):  # noqa: F811
    name = repository.split(':')[1]
    assert run(world, 'held_' + name, [read(repository, 'held_sheet_refs')]) == [[]]


@pytest.mark.parametrize('repository', REPOSITORIES[1:3])
def test_aggregation_and_grading_list_no_selected_or_available_sheet_before_one_is_saved(world, repository):  # noqa: F811
    name = repository.split(':')[1]
    assert run(world, 'listed_' + name, [read(repository, 'selected_sheet_refs', {}),
                                         read(repository, 'available_sheet_refs', {})]) == [[], []]
