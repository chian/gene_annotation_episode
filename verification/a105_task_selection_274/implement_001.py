from pathlib import Path
root=Path('gene_annotation_episode')
native=Path('verification/a105_common_section_assembly_261/NATIVE_KINETIC_TASK_PROPOSAL_003.txt').read_text().split('\n\n',1)[1].strip()
header='''"""Select full literature TASK inserts from actual requested or received work.

Pure instructional selection only: no source access, sheet loading, scientific
calculation, action selection or observations. Capability catalogues and legacy
work booleans are deliberately not evidence that a method was selected.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
import json

from .literature_numerical_contracts import is_registered_schema

'''
rows=[
# code, task module, task constant, storage module, class, rosters, operation
('kinetic','kinetic_model','NATIVE_KINETIC_TASK','kinetic','LiteratureKineticRepository','kinetic','literature.kinetic.populate'),
('kinetic_summary_precision','kinetic_summary_precision','KINETIC_SUMMARY_PRECISION_TASK','kinetic_summary_precision','LiteratureKineticSummaryPrecisionRepository','kinetic_summary_precision','literature.kinetic.populate'),
('endpoint_signal','endpoint_signal','ENDPOINT_SIGNAL_TASK','endpoint_signal','LiteratureEndpointSignalRepository','endpoint_signal','literature.figure.populate'),
('measurement_comparison','measurement_comparison','MEASUREMENT_COMPARISON_TASK','measurement_comparison','LiteratureMeasurementComparisonRepository','measurement_comparison','literature.measurement_comparison.populate'),
('product_coupling','product_coupling','PRODUCT_COUPLING_TASK','product_coupling','LiteratureProductCouplingRepository','product_coupling','literature.product_coupling.populate'),
('calibration_recovery','calibration_recovery','CALIBRATION_RECOVERY_TASK','calibration_recovery','LiteratureCalibrationRecoveryRepository','calibration_recovery','literature.calibration.recovery.populate'),
('measurement_validation','measurement_validation','MEASUREMENT_VALIDATION_TASK','measurement_validation','LiteratureMeasurementValidationRepository','measurement_validation','literature.measurement_validation.populate'),
('compiled_assay','compiled_assay','COMPILED_ASSAY_TASK','compiled_assay','LiteratureCompiledAssayRepository','compiled_assay','literature.assay.components.populate'),
('compiled_assay_v2','compiled_assay','COMPILED_ASSAY_TASK','compiled_assay','LiteratureCompiledAssayRepository','compiled_assay_components_v2','literature.assay.components.populate'),
('compiled_assay_v3','compiled_assay','COMMON_ASSESSMENT_TASK','compiled_assay','LiteratureCompiledAssayRepository','compiled_assay_components_v3','literature.assay.components.populate'),
('rate_observation','rate_observation','RATE_OBSERVATION_TASK','rate_observation','LiteratureRateObservationRepository','rate_observation','literature.rate.observations.populate'),
('rate_grid','rate_observation','REPORTED_CURVE_TASK','rate_observation','LiteratureReportedCurveRepository','rate_grid','literature.rate.observations.populate'),
('rate_replicate','rate_replicate','RATE_REPLICATE_TASK','rate_replicate','LiteratureRateReplicateRepository','rate_replicate','literature.rate.replicates.populate'),
('assay','assay','ASSAY_TASK','assay','LiteratureAssayRepository','assay','literature.assay.populate'),
('binding','binding','BINDING_TASK','binding','LiteratureBindingRepository','binding','literature.binding.populate'),
('binding_model','binding','BINDING_MODEL_TASK','binding_model','LiteratureBindingModelRepository','binding_model','literature.binding.model.populate'),
('binding_interaction','binding','BINDING_TASK','binding_interaction','LiteratureBindingInteractionRepository','binding_interaction','literature.binding.interaction.populate'),
('binding_interaction_model','binding_interaction_model','BINDING_INTERACTION_MODEL_TASK','binding_interaction_model','LiteratureBindingInteractionModelRepository','binding_interaction_model','literature.binding.interaction.model.populate'),
('kinetic_model','kinetic_model','KINETIC_MODEL_TASK','kinetic_model','LiteratureKineticModelRepository','kinetic_model','literature.kinetic.model.populate'),
('transport','transport','TRANSPORT_TASK','transport','LiteratureTransportRepository','transport','literature.transport.response.populate'),
('perturbation','perturbation','PERTURBATION_TASK','perturbation','LiteraturePerturbationRepository','perturbation','literature.perturbation.populate'),
('structure','structure','STRUCTURE_TASK','structure','LiteratureStructureRepository','structure','literature.structure.populate'),
('reaction','reaction','REACTION_TASK','reaction','LiteratureReactionRepository','reaction','literature.reaction.populate'),
('context','context','CONTEXT_TASK','context','LiteratureContextRepository','context','literature.context.populate'),
('figure','figure','FIGURE_TASK','figure','LiteratureFigureRepository','figure','literature.figure.populate'),
('partner','partner','PARTNER_TASK','partner','LiteraturePartnerRepository','partner','literature.partner.populate'),
('ratio_source','ratio_source','SOURCE_RATIO_TASK','ratio_source','LiteratureRatioSourceRepository','ratio_source','literature.ratio.source.populate'),
('controlled_response_component','controlled_response','CONTROLLED_RESPONSE_TASK','controlled_response','LiteratureControlledResponseRepository','controlled_response','literature.controlled_response.source_v3.populate'),
('gel_component','gel','GEL_TASK','gel','LiteratureGelRepository','gel','literature.gel.populate'),
('completion_time','completion_time','COMPLETION_TIME_TASK','completion_time','LiteratureCompletionTimeRepository','completion_time','literature.completion_time.populate'),
('active_site','active_site','ACTIVE_SITE_TASK','active_site','LiteratureActiveSiteRepository','active_site','literature.active_site.populate'),
('product_partition','product_partition','PRODUCT_PARTITION_TASK','product_partition','LiteratureProductPartitionRepository','product_partition','literature.product_partition.populate'),
('channel','channel','CHANNEL_TASK','channel','LiteratureChannelRepository','channel','literature.channel.populate'),
('ion_discrimination','ion_discrimination','ION_DISCRIMINATION_TASK','ion_discrimination','LiteratureIonDiscriminationRepository','ion_discrimination','literature.ion_discrimination.populate'),
]
imports=[]
for _,m,t,*_ in rows:
 if t=='NATIVE_KINETIC_TASK':continue
 line=f'from .literature_{m}_prompt import {t}'
 if line not in imports:imports.append(line)
header+='\n'.join(imports)+'\nfrom .literature_rate_observation_prompt import REPORTED_CURVE_SCOPE_TASK\n\n'
header+='NATIVE_KINETIC_TASK = '+repr(native)+'\n\n'
header+='''@dataclass(frozen=True)
class _Family:
    source: str
    task: str
    storage_module: str
    repository_class: str
    requested: str
    operation: str


# These describe existing instructions and selected-operation metadata only.
# They do not register capabilities or expand any numerical return.
_FAMILIES = (
'''
for code,tm,t,sm,cl,r,op in rows:
 req='requested_'+r if '_components' in r else 'requested_'+r+'_components'
 header+=f'    _Family("literature_{code}_cells", {t}, "literature_{sm}_storage", "{cl}", "{req}", "{op}"),\n'
header+=')\n_BY_SOURCE = {f.source: f for f in _FAMILIES}\n_BY_REQUEST = {f.requested: f.source for f in _FAMILIES}\n_BY_REQUEST.update({"requested_perturbation_summary_components": "literature_perturbation_cells",\n    "requested_gel_views": "literature_gel_component_cells",\n    "requested_controlled_response_views": "literature_controlled_response_component_cells"})\n\n'
Path('verification/a105_task_selection_274/task_selection_header_001.txt').write_text(header)
