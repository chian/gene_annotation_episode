"""Select full literature TASK inserts from actual requested or received work.

Pure instructional selection only: no source access, sheet loading, scientific
calculation, action selection or observations. Capability catalogues and legacy
work booleans are deliberately not evidence that a method was selected.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
import json

from .library.literature_kinetic_summary_precision_prompt import KINETIC_SUMMARY_PRECISION_TASK
from .library.literature_endpoint_signal_prompt import ENDPOINT_SIGNAL_TASK
from .library.literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK
from .library.literature_concentration_window_prompt import CONCENTRATION_WINDOW_TASK
from .library.literature_product_coupling_prompt import PRODUCT_COUPLING_TASK
from .library.literature_calibration_recovery_prompt import CALIBRATION_RECOVERY_TASK
from .library.literature_measurement_validation_prompt import MEASUREMENT_VALIDATION_TASK
from .library.literature_compiled_assay_prompt import COMPILED_ASSAY_TASK
from .library.literature_compiled_assay_prompt import COMMON_ASSESSMENT_TASK
from .library.literature_rate_observation_prompt import RATE_OBSERVATION_TASK
from .library.literature_rate_observation_prompt import REPORTED_CURVE_TASK
from .library.literature_rate_replicate_prompt import RATE_REPLICATE_TASK
from .library.literature_assay_prompt import ASSAY_TASK
from .library.literature_binding_prompt import BINDING_TASK
from .library.literature_binding_prompt import BINDING_MODEL_TASK
from .library.literature_binding_interaction_model_prompt import BINDING_INTERACTION_MODEL_TASK
from .library.literature_kinetic_model_prompt import KINETIC_MODEL_TASK
from .library.literature_transport_prompt import TRANSPORT_TASK
from .library.literature_perturbation_prompt import PERTURBATION_TASK
from .library.literature_structure_prompt import STRUCTURE_TASK
from .library.literature_reaction_prompt import REACTION_TASK
from .library.literature_a106_task_declaration import TASK as A106_SUBSCORE_TASK
from .library.literature_figure_prompt import FIGURE_TASK
from .library.literature_partner_prompt import PARTNER_TASK
from .library.literature_ratio_source_prompt import SOURCE_RATIO_TASK
from .library.literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK
from .library.literature_gel_prompt import GEL_TASK
from .library.literature_completion_time_prompt import COMPLETION_TIME_TASK
from .library.literature_active_site_prompt import ACTIVE_SITE_TASK
from .library.literature_product_partition_prompt import PRODUCT_PARTITION_TASK
from .library.literature_parent_depletion_prompt import PARENT_DEPLETION_TASK
from .library.literature_stoichiometric_balance_prompt import STOICHIOMETRIC_BALANCE_TASK
from .library.literature_channel_prompt import CHANNEL_TASK
from .library.literature_ion_discrimination_prompt import ION_DISCRIMINATION_TASK
from .library.literature_amount_prompt import AMOUNT_TASK
from .library.literature_rate_observation_prompt import REPORTED_CURVE_SCOPE_TASK
from .library.literature_assay_grading_declarations import ASSAY_TYPES, ASSAY_TYPE_LABELS
from .library.literature_assay_grading_prompt import ASSAY_GRADING_TASK
from .library.literature_a105_aggregation_prompt import A105_AGGREGATION_TASK
from .library.literature_a108_prompt import A108_CONTEXT_TASK, A108_GRADING_TASK, A108_AGGREGATION_TASK

from .library.literature_task_selection import _FAMILIES


def population_task_metadata_specs():
    """Existing table/provider/version facts; importing classes installs no state."""
    for family in _FAMILIES:
        module = import_module('.' + family.storage_module, __package__)
        repository = getattr(module, family.repository_class)
        if family.source == 'literature_compiled_assay_v2_cells':
            versions = (module.VERSION_V2,)
        elif family.source == 'literature_compiled_assay_v3_cells':
            versions = (module.VERSION_V3,)
        elif family.source == 'literature_rate_grid_cells':
            versions = (module.GRID_RECORD,)
        elif family.source == 'literature_kinetic_cells':
            versions = (module.VERSION, module.LEGACY_VERSION)
        else:
            versions = (getattr(module, 'VERSION', repository.record_version),)
        flag = {'literature_a108_grading_cells': 'a108_context_evidence',
            'literature_a108_aggregation_cells': 'a108_context_evidence',
            'literature_assay_grading_cells': 'assay_grading_population',
            'literature_intervention_grading_cells': 'a106_intervention',
            'literature_a106_subscore_cells': 'a106_intervention',
            'literature_a105_aggregation_cells': 'assay_grading_population',
            'literature_compiled_assay_cells': 'compiled_assay_population',
            'literature_compiled_assay_v2_cells': 'compiled_assay_population',
            'literature_compiled_assay_v3_cells': 'compiled_assay_population',
            'literature_ratio_source_cells': 'ratio_source_population',
            'literature_controlled_response_component_cells': 'controlled_response_population',
            'literature_gel_component_cells': 'gel_population',
            'literature_completion_time_cells': 'completion_time_population',
            'literature_active_site_cells': 'active_site_population',
            'literature_product_partition_cells': 'product_partition_population',
            'literature_parent_depletion_cells':'parent_depletion_population',
            'literature_stoichiometric_balance_cells':'stoichiometric_balance_population',
            'literature_channel_cells': 'channel_population',
            'literature_ion_discrimination_cells': 'ion_discrimination_population'}.get(family.source, 'rate_population')
        yield (family.source, flag, repository.operations_table, module.PROVIDER, versions)


